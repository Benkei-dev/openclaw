# MT4 ZeroMQ Integration – Vollständige Anleitung

Dieses Verzeichnis dokumentiert die komplette Integration von MetaTrader 4 mit n8n
über ZeroMQ (DWX Connect Expert Advisor) und der Python Bridge auf dem VPS.

## Inhaltsverzeichnis

1. [Architektur-Überblick](#architektur)
2. [DWX EA installieren](#dwx-ea-installieren)
3. [EA konfigurieren](#ea-konfigurieren)
4. [Mehrere Kurse abonnieren (Ticks)](#mehrere-kurse--ticks)
5. [Befehle an MT4 senden](#befehle-an-mt4-senden)
6. [Nachrichtenformat (ZMQ)](#nachrichtenformat)
7. [Python Bridge](#python-bridge)
8. [n8n Workflows](#n8n-workflows)
9. [Troubleshooting](#troubleshooting)

---

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                   Windows Trading-PC                        │
│                                                             │
│  MetaTrader 4                                               │
│  ├── DWX_ZeroMQ_MT4.ex4  (Expert Advisor)                  │
│  │   ├── PUSH :32768  → sendet Trade-Signale & Exec-Reports │
│  │   ├── PULL :32769  ← empfängt Befehle von Bridge        │
│  │   └── PUB  :32770  → sendet Tick-Daten (alle Symbole)   │
│  └── Tailscale  100.121.91.27                               │
└────────────────────┬────────────────────────────────────────┘
                     │  WireGuard (Tailscale)
                     │  Ende-zu-Ende verschlüsselt
┌────────────────────▼────────────────────────────────────────┐
│                   Ubuntu VPS                                │
│                   100.127.134.70                            │
│                                                             │
│  Python Bridge  (Port 8765)                                 │
│  ├── ZMQ PULL  ← empfängt Signale von MT4                  │
│  ├── ZMQ PUSH  → sendet Befehle an MT4                     │
│  ├── ZMQ SUB   ← abonniert Ticks von MT4                   │
│  └── HTTP API  → stellt Endpoints für n8n bereit           │
│                                                             │
│  n8n  (Port 5678)                                          │
│  ├── Webhook:  POST /webhook/mt4-signal                    │
│  ├── Webhook:  POST /webhook/mt4-market                    │
│  └── HTTP Request → POST http://localhost:8765/mt4/command  │
└─────────────────────────────────────────────────────────────┘
```

---

## DWX EA installieren

### 1. EA-Dateien herunterladen

```
Repository: https://github.com/darwinex/dwxconnect
Pfad:       MQL4/Experts/DWX_ZeroMQ_MT4_v2.1_RC8.mq4
            + alle Include-Dateien aus MQL4/Include/
```

### 2. Dateien in MT4 kopieren

```
MT4 Data Folder  →  Extras → Datenordner öffnen

MQL4/Experts/       ← DWX_ZeroMQ_MT4_v2.1_RC8.mq4
MQL4/Include/       ← alle .mqh Include-Dateien aus dem Repo
MQL4/Libraries/     ← mql4zmq-master/Bin/mt4/
                       ├── libzmq.dll   (32-bit!)
                       └── mql4zmq.dll  (32-bit!)
```

> **Wichtig:** MT4 ist 32-bit. Nur 32-bit DLLs funktionieren.
> Download: https://github.com/dingmaotu/mql4zmq/releases

### 3. EA kompilieren

- MT4 → Navigator → Expert Advisors → Rechtsklick → Refresh
- Doppelklick auf `DWX_ZeroMQ_MT4_v2.1_RC8`
- Im MetaEditor: Kompilieren (F7)
- Keine Fehler = fertig

### 4. DLL-Nutzung erlauben

```
MT4 → Extras → Optionen → Expert Advisors
☑  DLL-Importe erlauben
☑  Externe Expert Advisors importieren erlauben
```

### 5. EA auf Chart ziehen

- Beliebigen Chart öffnen (z.B. EURUSD H1)
- Navigator → Expert Advisors → `DWX_ZeroMQ_MT4_v2.1_RC8` auf Chart ziehen
- Smiley-Symbol oben rechts im Chart = EA läuft

---

## EA konfigurieren

Im Eingaben-Tab beim Starten des EA (oder Doppelklick auf EA-Icon im Chart):

### Ports

| Parameter | Standardwert | Beschreibung |
|-----------|-------------|--------------|
| `_PUSH_PORT` | `32768` | MT4 sendet Signale/Reports → Bridge |
| `_PULL_PORT` | `32769` | MT4 empfängt Befehle ← Bridge |
| `_PUB_PORT`  | `32770` | MT4 published Tick-Daten → Bridge |

> Diese Werte müssen exakt mit `.env` in der Python Bridge übereinstimmen.

### Wichtige Einstellungen

| Parameter | Empfehlung | Beschreibung |
|-----------|-----------|--------------|
| `_MILLISECOND_TIMER` | `1` | Timer-Interval in ms (1 = maximale Geschwindigkeit) |
| `_LOGLEVEL` | `2` | 0=kein Log, 1=Basis, 2=Detail, 3=Debug |
| `_BINDING` | `true` | true = EA bindet Socket (Bridge connected) |
| `_MAX_BARS_HISTORY` | `500` | Historische Bars beim Start |

---

## Mehrere Kurse / Ticks

### Tick-Daten für Symbole abonnieren

Die Bridge sendet nach dem Start automatisch einen Subscribe-Befehl.
Du kannst auch manuell über n8n oder direkt subscriben:

**Format eines Subscribe-Befehls (JSON an MT4 PULL-Port):**

```json
{
  "action": "SUBSCRIBE_TICKS",
  "instruments": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]
}
```

**Oder über die Bridge HTTP API:**

```bash
curl -X POST http://100.127.134.70:8765/mt4/command \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "SUBSCRIBE_TICKS",
    "symbol": "EURUSD,GBPUSD,USDJPY,XAUUSD"
  }'
```

### Was MT4 dann sendet (PUB-Socket, Port 32770)

Jede Tick-Nachricht kommt als JSON-String:

```json
{
  "action": "MARKET_DATA",
  "symbol": "EURUSD",
  "bid": 1.08542,
  "ask": 1.08545,
  "tick_value": 1.0,
  "timestamp": "2026-02-14T10:30:00.123"
}
```

### Welche Symbole sind verfügbar?

Nur Symbole die im MT4 Market Watch sichtbar sind:

```
MT4 → Ansicht → Market Watch (Strg+M)
→ Rechtsklick → "Alle anzeigen" oder einzeln hinzufügen
```

**Typische Symbole:**

| Kategorie | Beispiele |
|-----------|-----------|
| Forex Major | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD |
| Forex Minor | EURGBP, EURJPY, GBPJPY, EURAUD |
| Metalle | XAUUSD (Gold), XAGUSD (Silber) |
| Energie | USOIL, UKOIL |
| Indizes | US500, GER40, UK100 |
| Krypto | BTCUSD, ETHUSD (broker-abhängig) |

> Symbolnamen können je nach Broker variieren (z.B. `EURUSDm`, `EURUSD.`, `EURUSD_i`)

---

## Befehle an MT4 senden

### Order öffnen

```json
{
  "action": "OPEN_TRADE",
  "symbol": "EURUSD",
  "order_type": 0,
  "volume": 0.1,
  "price": 0,
  "sl": 1.0800,
  "tp": 1.0950,
  "comment": "n8n-signal",
  "magic": 12345
}
```

**order_type Werte:**
| Wert | Typ |
|------|-----|
| `0` | BUY (Market) |
| `1` | SELL (Market) |
| `2` | BUY LIMIT |
| `3` | SELL LIMIT |
| `4` | BUY STOP |
| `5` | SELL STOP |

### Order schließen

```json
{
  "action": "CLOSE_TRADE",
  "ticket": 12345678
}
```

### Alle Orders eines Symbols schließen

```json
{
  "action": "CLOSE_ALL_TRADES",
  "symbol": "EURUSD"
}
```

### Order modifizieren

```json
{
  "action": "MODIFY_TRADE",
  "ticket": 12345678,
  "sl": 1.0820,
  "tp": 1.0980
}
```

### Kontoinfo abfragen

```json
{
  "action": "GET_ACCOUNT_INFO"
}
```

### Offene Positionen abfragen

```json
{
  "action": "GET_OPEN_TRADES"
}
```

---

## Nachrichtenformat

### Von MT4 an Bridge (PUSH → PULL, Port 32768)

**Trade Execution Report:**
```json
{
  "action": "EXECUTION",
  "ticket": 12345678,
  "symbol": "EURUSD",
  "order_type": 0,
  "volume": 0.1,
  "open_price": 1.08542,
  "sl": 1.08000,
  "tp": 1.09500,
  "comment": "n8n-signal",
  "magic": 12345,
  "timestamp": "2026-02-14T10:30:00"
}
```

**Error Report:**
```json
{
  "action": "ERROR",
  "error_code": 131,
  "error_message": "Invalid volume",
  "command": { "...original command..." }
}
```

### Tick-Daten von MT4 (PUB → SUB, Port 32770)

```json
{
  "action": "MARKET_DATA",
  "symbol": "EURUSD",
  "bid": 1.08542,
  "ask": 1.08545,
  "timestamp": "2026-02-14T10:30:00.123"
}
```

---

## Python Bridge

Die Bridge läuft auf dem VPS unter `/opt/mt4-bridge/`.

### Service verwalten

```bash
# Status
systemctl status mt4-bridge

# Starten / Stoppen / Neustarten
systemctl start mt4-bridge
systemctl stop mt4-bridge
systemctl restart mt4-bridge

# Logs live
journalctl -u mt4-bridge -f

# Letzte 50 Zeilen
journalctl -u mt4-bridge -n 50 --no-pager
```

### Konfiguration ändern

```bash
nano /opt/mt4-bridge/.env
systemctl restart mt4-bridge
```

### Health-Check

```bash
curl http://localhost:8765/health
```

Antwort:
```json
{
  "status": "ok",
  "zmq_connected": true,
  "mt4_host": "100.121.91.27",
  "buffers": { "signals": 0, "market": 5 },
  "stats": {
    "signals_received": 142,
    "market_received": 8930,
    "commands_sent": 7,
    "n8n_push_ok": 149,
    "n8n_push_fail": 0,
    "started_at": "2026-02-14T08:00:00Z",
    "zmq_connected": true
  }
}
```

### API Dokumentation (Swagger)

```
http://100.127.134.70:8765/docs
```

---

## n8n Workflows

### Workflow 1: Trading-Signal empfangen und verarbeiten

**Trigger:** Webhook `POST /webhook/mt4-signal`

```
[Webhook]
  ↓ (Signal von MT4)
[IF: action == "EXECUTION"]
  ├── Ja → [Telegram/Slack: "Trade ausgeführt: EURUSD BUY 0.1"]
  └── Nein →
      [IF: action == "ERROR"]
        ├── Ja → [Alert senden]
        └── Nein → [Log/Ignore]
```

### Workflow 2: Tick-Daten analysieren und automatisch traden

**Trigger:** Webhook `POST /webhook/mt4-market`

```
[Webhook]
  ↓ (Tick-Daten: {"symbol":"EURUSD","bid":1.085,"ask":1.0853})
[Code Node: Spread berechnen]
  = (ask - bid) * 10000  → Pips
[IF: spread > 2]
  └── Ja → [Stop / Kein Trade]
[IF: bid > moving_average]  (aus vorherigem Workflow-State)
  └── Ja → [HTTP Request: POST /mt4/command]
             {"action":"OPEN_TRADE","symbol":"EURUSD","order_type":0,"volume":0.01}
```

### Workflow 3: Täglicher Report

**Trigger:** Schedule (täglich 22:00 Uhr)

```
[Schedule]
  ↓
[HTTP Request: GET http://localhost:8765/mt4/signals?limit=1000]
  ↓
[Code Node: Auswertung (Anzahl Trades, P&L)]
  ↓
[Telegram: Tagesreport senden]
```

### HTTP Request Node Konfiguration in n8n

**Befehl an MT4 senden:**
```
Method:  POST
URL:     http://localhost:8765/mt4/command
Headers: Authorization: Bearer <dein-token>
         Content-Type: application/json
Body:    {
           "action": "OPEN_TRADE",
           "symbol": "{{ $json.symbol }}",
           "order_type": 0,
           "volume": 0.01,
           "sl": {{ $json.sl }},
           "tp": {{ $json.tp }}
         }
```

---

## Troubleshooting

### MT4 EA startet nicht

```
Symptom: Rotes X statt Smiley im Chart
Lösung:
  1. Extras → Optionen → Expert Advisors → DLLs erlauben ✓
  2. Prüfen: libzmq.dll + mql4zmq.dll in MQL4/Libraries/ (32-bit!)
  3. MetaEditor → Kompilieren → Fehler im Journal prüfen
```

### Keine Verbindung Bridge → MT4

```
Symptom: health zeigt zmq_connected: false oder keine Nachrichten
Prüfen:
  1. Tailscale verbunden?
     tailscale status   (auf VPS)
     → Trading-PC muss als "online" erscheinen

  2. Firewall auf Trading-PC?
     Windows Defender → Eingehende Regel für Port 32768-32770

  3. MT4 EA läuft?
     → Smiley im Chart sichtbar?

  4. Ports korrekt?
     In MT4 EA Inputs und in /opt/mt4-bridge/.env vergleichen
```

### Bridge startet nicht

```bash
# Detaillierte Fehlerausgabe
journalctl -u mt4-bridge -n 50 --no-pager

# Manuell starten (Fehler direkt sehen)
cd /opt/mt4-bridge
venv/bin/python bridge.py

# Abhängigkeiten prüfen
venv/bin/pip list | grep -E "fastapi|zmq|uvicorn|httpx"
```

### n8n empfängt keine Daten

```
1. PUSH_TO_N8N=true in .env gesetzt?
2. N8N_WEBHOOK_BASE_URL korrekt? (http://100.127.134.70:5678/webhook)
3. Webhook in n8n aktiv (nicht nur "Test Workflow")?
   → Workflow muss "Aktiv" sein (Toggle oben rechts)
4. Webhook-Pfad stimmt mit N8N_SIGNAL_WEBHOOK_PATH überein?
   Bridge: mt4-signal → n8n URL: .../webhook/mt4-signal
```

### Zu viele Tick-Daten (Performance)

```
Problem: Marktdaten überfluten n8n
Lösung 1: PUSH_TO_N8N=false → n8n pollt nur bei Bedarf
           GET http://localhost:8765/mt4/market?limit=50
Lösung 2: Im EA die Tick-Rate drosseln (_MILLISECOND_TIMER=100)
Lösung 3: Nur wenige Symbole abonnieren
Lösung 4: In n8n: Webhook → "Respond immediately" + Filter-Node
```
