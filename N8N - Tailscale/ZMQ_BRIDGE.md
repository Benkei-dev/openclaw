# ZMQ Bridge für MT4 Integration

Dokumentation des MT4 ZMQ Bridge Services zur Verbindung zwischen MT4 Trading PC und n8n auf dem VPS.

## Status: ✅ Implementiert und aktiv

- **Service**: `systemctl {start|stop|restart|status} mt4-bridge`
- **Pfad**: `/opt/mt4-bridge/bridge.py`
- **Port**: 8765
- **Sprache**: Python/FastAPI + ZeroMQ
- **Backup**: `/opt/mt4-bridge/backups/`

## Architektur

```
[MT4 + DWX ZMQ EA auf Windows PC]         [VPS Ubuntu - srv1351792]
  Tailscale: 100.121.91.27                  Tailscale: 100.127.134.70
                                             Public:    72.60.84.181
  ┌─────────────────────┐                  ┌─────────────────────────┐
  │  DWX_ZMQ_Expert.mq4 │                  │  /opt/mt4-bridge/       │
  │                      │                  │  bridge.py (FastAPI)    │
  │  REP: tcp://*:32768 ─┼──── Tailscale ──┼→ REQ: 100.121.91.27:   │
  │  (Empfängt Commands) │     VPN          │       32768             │
  │                      │                  │  (Sendet Commands)      │
  │  PUSH: tcp://*:32769 ┼──── Tailscale ──┼→ PULL: 100.121.91.27:  │
  │  (Sendet Responses)  │     VPN          │       32769             │
  │                      │                  │  (Empfängt Signals)     │
  │  PUB: tcp://*:32770 ─┼──── Tailscale ──┼→ SUB: 100.121.91.27:   │
  │  (Market Data)       │     VPN          │      32770              │
  └─────────────────────┘                  │  (Empfängt Market)      │
                                            │                         │
                                            │  HTTP :8765             │
                                            │  ├─ GET  /health        │
                                            │  ├─ POST /mt4/command   │
                                            │  ├─ GET  /mt4/signals   │
                                            │  ├─ GET  /mt4/market    │
                                            │  ├─ DELETE /mt4/buffer  │
                                            │  └─ GET  /mt4/stats     │
                                            └────────┬────────────────┘
                                                     │ HTTP
                                            ┌────────┴────────────────┐
                                            │  n8n v2.7.5 :5678       │
                                            │  WF1-WF10 Workflows     │
                                            └─────────────────────────┘
```

## Bridge Service

### Dateien auf dem VPS

| Pfad | Beschreibung |
|------|-------------|
| `/opt/mt4-bridge/bridge.py` | Haupt-Service (Python/FastAPI + pyzmq) |
| `/opt/mt4-bridge/backups/` | Backups vor Patches |
| `/etc/systemd/system/mt4-bridge.service` | systemd Unit |

### Service-Verwaltung

```bash
# Status prüfen
systemctl status mt4-bridge

# Neustart
systemctl restart mt4-bridge

# Logs (live)
journalctl -u mt4-bridge -f

# Port prüfen
ss -tlnp | grep 8765
```

### API-Token

```
77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb
```

Wird als `X-API-Token` Header bei allen Bridge-Requests mitgeschickt.

## API Endpoints

### GET /health

Health-Check, kein Token nötig.

```bash
curl http://100.127.134.70:8765/health
```

### POST /mt4/command

Sendet einen Befehl an MT4 via ZMQ REQ socket.

```bash
curl -X POST http://100.127.134.70:8765/mt4/command \
  -H "Content-Type: application/json" \
  -H "X-API-Token: 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb" \
  -d '{"command":"HIST","symbol":"BTCUSD","timeframe":"M15","count":500}'
```

### GET /mt4/signals

Liest den Signal-Buffer (PULL socket Nachrichten vom EA).

```bash
curl http://100.127.134.70:8765/mt4/signals \
  -H "X-API-Token: 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb"
```

### GET /mt4/market

Liest den Market-Buffer (PUB socket Tick-Daten).

```bash
curl http://100.127.134.70:8765/mt4/market \
  -H "X-API-Token: 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb"
```

### DELETE /mt4/buffer

Löscht Signal- und Market-Buffer.

```bash
curl -X DELETE http://100.127.134.70:8765/mt4/buffer \
  -H "X-API-Token: 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb"
```

### GET /mt4/stats

Zeigt Statistiken: Nachrichten-Zähler, Buffer-Größen, Uptime.

## DWX ZMQ EA – Kommando-Protokoll

### Befehlsformat

Die Bridge konvertiert JSON-Objekte in das DWX-Semikolon-Format:

| Bridge JSON | DWX Command String |
|---|---|
| `{"command":"HIST","symbol":"BTCUSD","timeframe":"M15","count":500}` | `HIST;BTCUSD;M15;500` |
| `{"command":"TRADE","action":"OPEN","type":0,"symbol":"BTCUSD","price":0,"sl":69800,"tp":70500,"lots":0.01}` | `TRADE;OPEN;0;BTCUSD;0;69800;70500;0.01` |
| `{"command":"TRADE","action":"CLOSE","ticket":12345}` | `TRADE;CLOSE;12345;0` |
| `{"command":"TRADE","action":"MODIFY","ticket":12345,"sl":69900,"tp":70600}` | `TRADE;MODIFY;12345;69900;70600` |
| `{"command":"TRACK_PRICES","symbols":["EURUSD","BTCUSD","GOLD"]}` | `TRACK_PRICES;EURUSD;BTCUSD;GOLD` |

### Order Types

| Wert | Typ |
|------|-----|
| 0 | OP_BUY (Market Buy) |
| 1 | OP_SELL (Market Sell) |
| 2 | OP_BUYLIMIT |
| 3 | OP_SELLLIMIT |
| 4 | OP_BUYSTOP |
| 5 | OP_SELLSTOP |

### Antwortformat

Der DWX EA antwortet im **Python dict Format** (single quotes, nicht JSON):

```python
{'_action': 'HIST', '_data': {'2026.02.14 10:00': {'open': 70244.56, 'high': 70301.23, ...}}}
```

Die Bridge parst dies mit `ast.literal_eval()` (Fallback wenn `json.loads()` fehlschlägt).

### Bekannte Einschränkungen des DWX EA

> **Wichtig:** Der DWX ZMQ Expert Advisor unterstützt NICHT alle Befehle via ZMQ.

| Feature | Status | Alternative |
|---------|--------|------------|
| HIST (Kerzendaten) | ✅ Funktioniert | – |
| TRADE OPEN/CLOSE/MODIFY | ✅ Funktioniert | – |
| TRACK_PRICES (Tick-Daten) | ✅ Funktioniert | – |
| ACCOUNT_INFO | ❌ Nicht via ZMQ | Datei-basiert (DWX Python Client) |
| OPEN_TRADES / GET_OPEN_TRADES | ❌ Nicht via ZMQ | Datei: `DWX_Orders.txt` |
| ORDER_HISTORY | ❌ Nicht via ZMQ | Datei-basiert |

**Workaround**: WF7 nutzt `DEMO_BALANCE = 100000` als Default. Trade-Tracking erfolgt über Google Sheets statt über MT4-Abfragen.

## Patch-Historie

### 2026-02-14: ast.literal_eval Patch

**Problem**: DWX EA sendet Python-Dict-Format (single quotes), nicht JSON. `json.loads()` schlägt fehl.

**Lösung**:
1. `import ast` zu bridge.py hinzugefügt (Zeile 14)
2. `_parse_message()` erweitert: `json.loads()` → bei Fehler → `ast.literal_eval()` → bei Fehler → Raw-String

**Backup**: `/opt/mt4-bridge/backups/bridge.py.20260214-204740.bak`

**Verifiziert**: HIST;BTCUSD;M15 liefert korrekt 2048+ Kerzen als geparstes Dict.

## Auto-Tracking

Beim Start der Bridge werden automatisch folgende Symbole getrackt:

```
TRACK_PRICES;EURUSD;GOLD;BTCUSD;US100
```

Die Tick-Daten fließen über den PUB-Socket (32770) in den Market-Buffer und sind über `/mt4/market` abrufbar.

## Sicherheit

1. **Netzwerk**: Alle ZMQ-Kommunikation läuft über verschlüsseltes Tailscale-VPN
2. **API-Token**: Alle Bridge-Endpoints (außer /health) erfordern `X-API-Token` Header
3. **Keine öffentlichen Ports**: Bridge hört nur auf localhost/Tailscale, nicht auf 0.0.0.0
4. **Firewall**: UFW auf VPS erlaubt nur SSH (22), n8n (5678), Bridge (8765) über Tailscale

## Troubleshooting

### Bridge startet nicht

```bash
# Port belegt?
fuser -k 8765/tcp
systemctl restart mt4-bridge

# Syntax-Fehler?
python3 -m py_compile /opt/mt4-bridge/bridge.py
```

### Keine Antwort vom EA

```bash
# ZMQ-Verbindung testen
curl -X POST http://100.127.134.70:8765/mt4/command \
  -H "Content-Type: application/json" \
  -H "X-API-Token: 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb" \
  -d '{"command":"TRACK_PRICES","symbols":["BTCUSD"]}'

# MT4 läuft? EA attached? Chart aktiv?
# Tailscale-Verbindung prüfen:
tailscale ping 100.121.91.27
```

### Daten kommen als Raw-String

Wenn `_parse_message()` nur Raw-Strings liefert:
1. Bridge-Logs prüfen: `journalctl -u mt4-bridge | grep "parse"`
2. Prüfen ob `import ast` vorhanden: `head -20 /opt/mt4-bridge/bridge.py`
3. Backup vergleichen: `diff /opt/mt4-bridge/bridge.py /opt/mt4-bridge/backups/bridge.py.*.bak`

---

*Letzte Aktualisierung: 2026-02-14 – Bridge implementiert, ast.literal_eval Patch angewendet, alle Workflows aktiv.*
