"""
MT4 ZMQ <-> HTTP Bridge
=======================
Läuft auf dem VPS. Spricht via ZeroMQ mit dem DWX-Client in MT4
und stellt n8n eine einfache HTTP-API zur Verfügung.

Architektur:
  MT4 (PUSH :32768)  →  Bridge PULL  →  Buffer / Push to n8n
  MT4 (PULL :32769)  ←  Bridge PUSH  ←  n8n POST /mt4/command
  MT4 (PUB  :32770)  →  Bridge SUB   →  Buffer / Push to n8n
"""

import ast
import asyncio
import json
import logging
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
import zmq
import zmq.asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from pydantic import BaseModel

load_dotenv()

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
MT4_HOST        = os.getenv("ZMQ_MT4_HOST",          "100.121.91.27")
MT4_SIGNAL_PORT = int(os.getenv("ZMQ_MT4_PUSH_PORT", "32768"))  # MT4 sendet Signale
MT4_CMD_PORT    = int(os.getenv("ZMQ_MT4_PULL_PORT",  "32769"))  # MT4 empfängt Befehle
MT4_MARKET_PORT = int(os.getenv("ZMQ_MT4_PUB_PORT",   "32770"))  # MT4 sendet Marktdaten

# Symbole die beim Start automatisch via TRACK_PRICES abonniert werden (Semikolon-getrennt)
TRACK_SYMBOLS   = os.getenv("TRACK_SYMBOLS", "EURUSD")

N8N_BASE_URL      = os.getenv("N8N_WEBHOOK_BASE_URL",     "http://100.127.134.70:5678/webhook")
N8N_SIGNAL_PATH   = os.getenv("N8N_SIGNAL_WEBHOOK_PATH",  "mt4-signal")
N8N_MARKET_PATH   = os.getenv("N8N_MARKET_WEBHOOK_PATH",  "mt4-market")

BRIDGE_API_TOKEN  = os.getenv("BRIDGE_API_TOKEN", "")
BRIDGE_HTTP_PORT  = int(os.getenv("BRIDGE_HTTP_PORT", "8765"))
MAX_BUFFER        = int(os.getenv("MAX_BUFFER_SIZE",  "500"))
PUSH_TO_N8N       = os.getenv("PUSH_TO_N8N", "true").lower() == "true"
PUSH_MARKET_TO_N8N = os.getenv("PUSH_MARKET_TO_N8N", "false").lower() == "true"
ZMQ_CONNECT_TIMEOUT = int(os.getenv("ZMQ_CONNECT_TIMEOUT_MS", "5000"))
LOG_LEVEL         = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("mt4_bridge")

# ---------------------------------------------------------------------------
# Shared State
# ---------------------------------------------------------------------------
signal_buffer: deque = deque(maxlen=MAX_BUFFER)
market_buffer: deque = deque(maxlen=MAX_BUFFER)

zmq_ctx: zmq.asyncio.Context | None = None
push_socket: zmq.asyncio.Socket | None = None  # Bridge → MT4 (Befehle)

stats = {
    "signals_received": 0,
    "market_received":  0,
    "commands_sent":    0,
    "n8n_push_ok":      0,
    "n8n_push_fail":    0,
    "started_at":       datetime.now(timezone.utc).isoformat(),
    "zmq_connected":    False,
}

# ---------------------------------------------------------------------------
# ZMQ Receiver Tasks
# ---------------------------------------------------------------------------

async def _push_to_n8n(client: httpx.AsyncClient, path: str, payload: dict) -> None:
    url = f"{N8N_BASE_URL}/{path.lstrip('/')}"
    try:
        r = await client.post(url, json=payload, timeout=5.0)
        r.raise_for_status()
        stats["n8n_push_ok"] += 1
        log.debug("n8n push OK  %s  %s", path, r.status_code)
    except Exception as exc:
        stats["n8n_push_fail"] += 1
        log.warning("n8n push FAIL  %s  %s", path, exc)


async def recv_signals(ctx: zmq.asyncio.Context) -> None:
    """Empfängt Trading-Signale vom MT4 PUSH-Socket."""
    sock = ctx.socket(zmq.PULL)
    addr = f"tcp://{MT4_HOST}:{MT4_SIGNAL_PORT}"
    sock.connect(addr)
    log.info("ZMQ PULL verbunden mit %s  (Signale)", addr)

    async with httpx.AsyncClient() as client:
        while True:
            try:
                raw = await sock.recv_string()
                msg = _parse_message(raw)
                msg.setdefault("_source", "signal")
                msg.setdefault("_ts", datetime.now(timezone.utc).isoformat())
                signal_buffer.append(msg)
                stats["signals_received"] += 1
                log.debug("Signal empfangen: %s", msg)

                if PUSH_TO_N8N:
                    await _push_to_n8n(client, N8N_SIGNAL_PATH, msg)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.error("recv_signals Fehler: %s", exc)
                await asyncio.sleep(1)

    sock.close()


async def recv_market(ctx: zmq.asyncio.Context) -> None:
    """Abonniert Marktdaten vom MT4 PUB-Socket."""
    sock = ctx.socket(zmq.SUB)
    addr = f"tcp://{MT4_HOST}:{MT4_MARKET_PORT}"
    sock.connect(addr)
    sock.setsockopt_string(zmq.SUBSCRIBE, "")  # alle Topics
    log.info("ZMQ SUB verbunden mit %s  (Marktdaten)", addr)

    async with httpx.AsyncClient() as client:
        while True:
            try:
                raw = await sock.recv_string()
                msg = _parse_message(raw)
                msg.setdefault("_source", "market")
                msg.setdefault("_ts", datetime.now(timezone.utc).isoformat())
                market_buffer.append(msg)
                stats["market_received"] += 1
                log.debug("Marktdaten: %s", msg)

                if PUSH_MARKET_TO_N8N:
                    await _push_to_n8n(client, N8N_MARKET_PATH, msg)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.error("recv_market Fehler: %s", exc)
                await asyncio.sleep(1)

    sock.close()


def _parse_message(raw: str) -> dict:
    """Parst DWX-Nachrichten: JSON, PUB-Tick-Format oder Raw-String."""
    raw = raw.strip()
    if not raw:
        return {"raw": raw}

    # JSON (EA-Antwort auf Befehle)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Python-Dict-Format (DWX EA sendet single-quoted dicts wie {'_action': 'EXECUTION', ...})
    try:
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    # DWX PUB-Format: "SYMBOL:|:bid;ask"  oder  "SYMBOL_TF:|:ts;o;h;l;c;vol;spread;rvol"
    if ":|:" in raw:
        symbol_part, _, data_part = raw.partition(":|:")
        fields = data_part.split(";")
        if len(fields) == 2:
            try:
                return {
                    "symbol": symbol_part,
                    "bid":    float(fields[0]),
                    "ask":    float(fields[1]),
                    "type":   "tick",
                }
            except ValueError:
                pass
        elif len(fields) >= 5:
            try:
                # OHLC: Symbol hat evtl. _TF-Suffix  z.B. "EURUSD_M1"
                sym, _, tf = symbol_part.rpartition("_")
                if not sym:
                    sym, tf = symbol_part, ""
                return {
                    "symbol":    sym,
                    "timeframe": tf,
                    "timestamp": int(fields[0]),
                    "open":      float(fields[1]),
                    "high":      float(fields[2]),
                    "low":       float(fields[3]),
                    "close":     float(fields[4]),
                    "volume":    int(fields[5]) if len(fields) > 5 else 0,
                    "type":      "ohlc",
                }
            except (ValueError, IndexError):
                pass
        return {"raw": raw, "type": "pub_raw"}

    # Semikolon-getrennte DWX-Signale  z.B. "SIGNAL;EURUSD;BUY;..."
    parts = raw.split(";")
    if len(parts) > 1:
        return {"raw": raw, "parts": parts, "type": parts[0]}
    return {"raw": raw}


# ---------------------------------------------------------------------------
# DWX Command Builder  (JSON-Payload → Semikolon-Format)
# ---------------------------------------------------------------------------

def _build_dwx_command(payload: "CommandPayload") -> str:
    """
    Übersetzt den HTTP-Payload in das DWX-Semikolon-Befehlsformat.

    DWX erwartet z.B.:
      HEARTBEAT
      TRACK_PRICES;EURUSD;GOLD;BTCUSD
      RATES;EURUSD
      TRADE;OPEN;0;EURUSD;0;0.01;1.08;1.095;;0;0
    """
    action = (payload.action or "").upper()

    if action == "HEARTBEAT":
        return "HEARTBEAT"

    if action == "TRACK_PRICES":
        symbols = [s.strip() for s in (payload.symbol or "").split(";") if s.strip()]
        return "TRACK_PRICES;" + ";".join(symbols)

    if action == "TRACK_RATES":
        tf = str((payload.extra or {}).get("timeframe", "1"))
        return f"TRACK_RATES;{payload.symbol or 'EURUSD'};{tf}"

    if action in ("RATES", "GET_QUOTE"):
        return f"RATES;{payload.symbol or 'EURUSD'}"

    if action in ("HIST", "HISTORY"):
        extra = payload.extra or {}
        tf    = str(extra.get("timeframe", "1"))
        start = str(extra.get("start", "0"))
        end   = str(extra.get("end",   "0"))
        return f"HIST;{payload.symbol or 'EURUSD'};{tf};{start};{end}"

    _ot_map = {
        "BUY": "0", "SELL": "1",
        "BUY_LIMIT": "2", "SELL_LIMIT": "3",
        "BUY_STOP": "4",  "SELL_STOP": "5",
    }
    if action in ("OPEN_TRADE", "NEW_TRADE", "BUY", "SELL"):
        ot      = (payload.order_type or ("BUY" if action != "SELL" else "SELL")).upper()
        tp_code = _ot_map.get(ot, "0")
        magic   = str((payload.extra or {}).get("magic", 0))
        # FIX: DWX v2.0.1_RC8 parameter order: TRADE;OPEN;type;symbol;price;sl;tp;comment;lots;magic;ticket
        # WICHTIG: volume (lots) muss an Position 9 sein, nicht Position 6!
        return (f"TRADE;OPEN;{tp_code};{payload.symbol or ''};0;"
                f"0;0;{payload.comment or ''};"
                f"{payload.volume or 0.01};{magic};0")

    if action == "CLOSE_TRADE":
        magic = str((payload.extra or {}).get("magic", 0))
        return (f"TRADE;CLOSE;{payload.ticket or 0};{payload.symbol or ''};0;"
                f"{payload.volume or 0};0;0;;{magic};{payload.ticket or 0}")

    if action == "CLOSE_ALL_TRADES":
        return "TRADE;CLOSE_ALL;;;;;;;"

    if action == "MODIFY_TRADE":
        magic = str((payload.extra or {}).get("magic", 0))
        return (f"TRADE;MODIFY;{payload.ticket or 0};{payload.symbol or ''};0;"
                f"{payload.volume or 0};{payload.sl or 0};{payload.tp or 0};"
                f";{magic};{payload.ticket or 0}")

    # Unbekannte Action: Passthrough als "ACTION;SYMBOL"
    parts = [action]
    if payload.symbol:
        parts.append(payload.symbol)
    return ";".join(parts)


async def _auto_track_prices() -> None:
    """Sendet nach dem Start automatisch TRACK_PRICES für konfigurierte Symbole."""
    if not TRACK_SYMBOLS.strip():
        return
    await asyncio.sleep(3.0)  # Warten bis ZMQ-Verbindung stabil
    if push_socket is None:
        return
    symbols = [s.strip() for s in TRACK_SYMBOLS.split(";") if s.strip()]
    cmd = "TRACK_PRICES;" + ";".join(symbols)
    try:
        await push_socket.send_string(cmd)
        stats["commands_sent"] += 1
        log.info("Auto-TRACK_PRICES gesendet: %s", cmd)
    except Exception as exc:
        log.warning("Auto-TRACK_PRICES fehlgeschlagen: %s", exc)


# ---------------------------------------------------------------------------
# FastAPI Lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global zmq_ctx, push_socket

    log.info("Bridge startet – MT4 @ %s", MT4_HOST)
    zmq_ctx = zmq.asyncio.Context()

    # PUSH-Socket zum Senden von Befehlen an MT4
    push_socket = zmq_ctx.socket(zmq.PUSH)
    push_addr   = f"tcp://{MT4_HOST}:{MT4_CMD_PORT}"
    push_socket.connect(push_addr)
    log.info("ZMQ PUSH verbunden mit %s  (Befehle)", push_addr)

    stats["zmq_connected"] = True

    # Receiver-Tasks im Hintergrund
    tasks = [
        asyncio.create_task(recv_signals(zmq_ctx), name="recv_signals"),
        asyncio.create_task(recv_market(zmq_ctx),  name="recv_market"),
        asyncio.create_task(_auto_track_prices(),  name="auto_track"),
    ]

    yield  # App läuft

    log.info("Bridge fährt herunter …")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    push_socket.close()
    zmq_ctx.term()
    stats["zmq_connected"] = False
    log.info("Bridge gestoppt.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MT4 ZMQ Bridge",
    description="HTTP-Proxy zwischen n8n und MT4/DWX-Client via ZeroMQ",
    version="1.0.0",
    lifespan=lifespan,
)


def _check_auth(authorization: str | None) -> None:
    """Prüft Bearer-Token, wenn BRIDGE_API_TOKEN gesetzt ist."""
    if not BRIDGE_API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header fehlt")
    token = authorization.removeprefix("Bearer ").strip()
    if token != BRIDGE_API_TOKEN:
        raise HTTPException(status_code=403, detail="Ungültiges Token")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health():
    """Gibt den Status der Bridge und ZMQ-Verbindungen zurück."""
    return {
        "status":       "ok",
        "zmq_connected": stats["zmq_connected"],
        "mt4_host":     MT4_HOST,
        "buffers": {
            "signals": len(signal_buffer),
            "market":  len(market_buffer),
        },
        "stats": stats,
    }


class CommandPayload(BaseModel):
    action:    str               # z.B. "open_position", "close_position", "modify"
    symbol:    str | None = None
    order_type: str | None = None  # "BUY" / "SELL"
    volume:    float | None = None
    sl:        float | None = None
    tp:        float | None = None
    ticket:    int | None = None
    comment:   str | None = None
    extra:     dict[str, Any] | None = None


@app.post("/mt4/command", tags=["MT4"])
async def send_command(
    payload: CommandPayload,
    authorization: str | None = Header(default=None),
):
    """
    Sendet einen Befehl an MT4 über den ZMQ PUSH→PULL Kanal.

    n8n-Beispiel (HTTP Request Node):
      POST http://<vps>:8765/mt4/command
      Authorization: Bearer <token>
      Body: {"action": "open_position", "symbol": "EURUSD", "order_type": "BUY", "volume": 0.1, "sl": 1.08, "tp": 1.095}
    """
    _check_auth(authorization)
    if push_socket is None:
        raise HTTPException(status_code=503, detail="ZMQ nicht verbunden")

    dwx_cmd = _build_dwx_command(payload)

    try:
        await push_socket.send_string(dwx_cmd)
        stats["commands_sent"] += 1
        log.info("Befehl gesendet: %s", dwx_cmd)
        return {"status": "sent", "command": dwx_cmd}
    except Exception as exc:
        log.error("Fehler beim Senden: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/mt4/signals", tags=["MT4"])
async def get_signals(
    limit: int = 50,
    clear: bool = True,
    authorization: str | None = Header(default=None),
):
    """
    Gibt gepufferte Trading-Signale von MT4 zurück.

    - **limit**: Maximale Anzahl Einträge (Standard 50)
    - **clear**: Buffer nach dem Lesen leeren (Standard true)

    n8n-Beispiel: GET http://<vps>:8765/mt4/signals?limit=100
    """
    _check_auth(authorization)
    items = list(signal_buffer)[-limit:]
    if clear:
        signal_buffer.clear()
    return {"count": len(items), "signals": items}


@app.get("/mt4/market", tags=["MT4"])
async def get_market(
    limit: int = 100,
    clear: bool = False,
    authorization: str | None = Header(default=None),
):
    """
    Gibt gepufferte Marktdaten von MT4 zurück.

    - **limit**: Maximale Anzahl Einträge (Standard 100)
    - **clear**: Buffer nach dem Lesen leeren (Standard false)
    """
    _check_auth(authorization)
    items = list(market_buffer)[-limit:]
    if clear:
        market_buffer.clear()
    return {"count": len(items), "market": items}


@app.delete("/mt4/buffer", tags=["MT4"])
async def clear_buffers(authorization: str | None = Header(default=None)):
    """Leert beide Puffer (Signale + Marktdaten)."""
    _check_auth(authorization)
    signal_buffer.clear()
    market_buffer.clear()
    return {"status": "cleared"}


@app.get("/mt4/stats", tags=["System"])
async def get_stats(authorization: str | None = Header(default=None)):
    """Gibt detaillierte Statistiken zurück."""
    _check_auth(authorization)
    return stats


class RawCommandPayload(BaseModel):
    command: str


@app.post("/mt4/raw", tags=["MT4"])
async def send_raw_command(
    payload: RawCommandPayload,
    authorization: str | None = Header(default=None),
):
    """
    Sendet einen Raw-String-Befehl direkt an MT4 (Debug-Endpoint).
    Kein Format-Übersetzung – der String wird exakt so gesendet.
    """
    _check_auth(authorization)
    if push_socket is None:
        raise HTTPException(status_code=503, detail="ZMQ nicht verbunden")
    try:
        await push_socket.send_string(payload.command)
        stats["commands_sent"] += 1
        log.info("Raw-Befehl gesendet: %s", payload.command)
        return {"status": "sent", "command": payload.command}
    except Exception as exc:
        log.error("Fehler beim Senden (raw): %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    log.info(
        "Starte MT4 Bridge auf Port %d  |  MT4=%s  |  n8n Push Signals=%s Market=%s",
        BRIDGE_HTTP_PORT, MT4_HOST, PUSH_TO_N8N, PUSH_MARKET_TO_N8N,
    )
    uvicorn.run(
        "bridge:app",
        host="0.0.0.0",
        port=BRIDGE_HTTP_PORT,
        log_level=LOG_LEVEL.lower(),
    )
