# Handoff-Bericht für Claude Code

> **Datum:** 15. Februar 2026  
> **Status:** 6 kritische Bugs, System läuft aber fehlerhaft  
> **Priorität:** TRADE-Format fixen → Workflows optimieren → Datenqualität  
> **⚠️ SOT:** Lies zuerst [SOT.md](./SOT.md) – dort steht der aktuelle Status und wer woran arbeitet.

---

## TL;DR

Das MT4 Trading-Automatisierungssystem (10 Workflows, Python/FastAPI Bridge, ZMQ) läuft auf dem VPS, hat aber **6 konkrete Probleme**, die behoben werden müssen. Die Bridge empfängt Marktdaten und HIST-Daten korrekt, aber **TRADE-Befehle scheitern** (Error 4051), **Google Sheets wird geflutet** (Rate Limiting), **TA-Log ist leer**, **Trade-Log unvollständig**, und **Telegram-Nachrichten sind generisch**.

---

## 1. Infrastruktur (alles läuft)

| Komponente | Adresse | Status |
|------------|---------|--------|
| VPS (Ubuntu) | `72.60.84.181` / Tailscale `100.127.134.70` | ✅ läuft |
| MT4 Trading PC | Tailscale `100.121.91.27` | ✅ läuft |
| MT4 Bridge | `http://localhost:8765` (auf VPS) | ✅ läuft |
| n8n | `http://100.127.134.70:5678` | ✅ läuft |
| ZMQ Verbindung | Ports 32768/32769/32770 | ✅ verbunden |

### SSH-Zugriff
```bash
ssh -i C:\Users\Stephan\.ssh\id_rsa_vps root@72.60.84.181
```

### Bridge Service
```bash
systemctl {start|stop|restart|status} mt4-bridge
journalctl -u mt4-bridge -f  # Logs
```

### Bridge Auth
```
Authorization: Bearer 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb
```
> ⚠️ NICHT `X-API-Token`! Die Bridge prüft `Authorization: Bearer <token>`.

### Bridge API Endpoints
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/health` | Health Check + Buffer-Status |
| POST | `/mt4/command` | JSON → DWX-Befehl an EA |
| POST | `/mt4/raw` | Raw-String direkt an EA (Debug) |
| GET | `/mt4/signals?limit=50&clear=true` | Signal-Buffer lesen |
| GET | `/mt4/market?limit=100&clear=false` | Marktdaten-Buffer lesen |
| DELETE | `/mt4/buffer` | Beide Buffer leeren |
| GET | `/mt4/stats` | Statistiken |

### Dateien auf VPS
```
/opt/mt4-bridge/
├── bridge.py                          ← Hauptdatei (LIVE, 495 Zeilen)
├── bridge.py.20260214-204740.bak      ← Backup vor ast-Patch
├── bridge.py.before_raw_endpoint.bak  ← Backup vor /mt4/raw
├── .env                               ← Konfiguration
├── venv/                              ← Python venv
└── requirements.txt
```

### Bridge .env (WICHTIG – Ports sind vertauscht benannt!)
```env
ZMQ_MT4_HOST=100.121.91.27
ZMQ_MT4_PUSH_PORT=32769    # ← heißt PUSH, ist aber der MT4-CMD-Port
ZMQ_MT4_PULL_PORT=32768    # ← heißt PULL, ist aber der MT4-Signal-Port
ZMQ_MT4_PUB_PORT=32770
BRIDGE_API_TOKEN=77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb
BRIDGE_HTTP_PORT=8765
PUSH_TO_N8N=true
N8N_WEBHOOK_BASE_URL=http://100.127.134.70:5678/webhook
N8N_SIGNAL_WEBHOOK_PATH=mt4-signal
N8N_MARKET_WEBHOOK_PATH=mt4-market
TRACK_SYMBOLS=EURUSD
MAX_BUFFER_SIZE=500
```

> **Hinweis zum Port-Mapping:** Die Variablennamen `ZMQ_MT4_PUSH_PORT` und `ZMQ_MT4_PULL_PORT` sind irreführend. Im Code wird `PUSH_PORT` als `MT4_SIGNAL_PORT` (von MT4 empfangen) und `PULL_PORT` als `MT4_CMD_PORT` (an MT4 senden) verwendet. Die tatsächliche Verbindung funktioniert korrekt.

---

## 2. Die 6 Bugs (nach Priorität)

### BUG 1: TRADE-Befehl Error 4051 (KRITISCH) 🔴

**Symptom:** Jeder TRADE-Befehl an die EA gibt Error 4051 zurück: `"invalid function parameter value"`.

**Getestet mit diesen Formaten (ALLE fehlgeschlagen):**
```
TRADE;OPEN;0;BTCUSD;0;0.01;69704.36;70429.4;WF7-DEMO;0;0
TRADE;OPEN;0;BTCUSD;0;0.01;0;0;;0;0                        (ohne SL/TP)
OPEN_ORDER|BTCUSD,buy,0.01,0,0,0,0,,0                       (DWX-File-Format)
OPEN_ORDER;BTCUSD;0;0.01;0;0;0;0;;0                         (Semikolon-Variante)
```

**Root Cause Analyse:**
- Die Bridge-Funktion `_build_dwx_command()` (Zeile ~228 in bridge.py) generiert: `TRADE;OPEN;{type};{symbol};0;{vol};{sl};{tp};{comment};{magic};0`
- DWX Connect (GitHub `darwinex/dwxconnect`) nutzt **dateibasierte** Befehle: `<:ID|OPEN_ORDER|symbol,buy,lots,price,sl,tp,magic,comment,expiration:>`
- Die ZMQ-Variante der EA könnte ein **anderes Format** erwarten als die dateibasierte Version
- **HIST funktioniert** mit dem Semikolon-Format (`HIST;BTCUSD;15;start;end`), also ist das ZMQ-Protokoll nicht komplett anders
- **Wahrscheinlichste Ursache**: Die Reihenfolge der Parameter in `TRADE;OPEN;...` stimmt nicht, oder der Order-Type-Code ist falsch

**Was zu tun ist:**
1. **EA-Quellcode prüfen**: Die `.mq4`-Datei auf dem MT4-PC lesen (DWX_ZMQ_EA.mq4). Dort steht exakt, wie die EA den TRADE-Befehl parst.
   - Pfad auf MT4 PC: vermutlich `C:\Users\Stephan\AppData\Roaming\MetaTrader 4\MQL4\Experts\` oder ähnlich
2. Die korrekte Parameter-Reihenfolge in `_build_dwx_command()` anpassen
3. Testen mit einem einfachen BUY BTCUSD 0.01 (Markt muss offen sein! Sa/So kein Handel)

**Relevanter Code in bridge.py:**
```python
# Zeile ~228-237
_ot_map = {
    "BUY": "0", "SELL": "1",
    "BUY_LIMIT": "2", "SELL_LIMIT": "3",
    "BUY_STOP": "4",  "SELL_STOP": "5",
}
if action in ("OPEN_TRADE", "NEW_TRADE", "BUY", "SELL"):
    ot      = (payload.order_type or ("BUY" if action != "SELL" else "SELL")).upper()
    tp_code = _ot_map.get(ot, "0")
    magic   = str((payload.extra or {}).get("magic", 0))
    return (f"TRADE;OPEN;{tp_code};{payload.symbol or ''};0;"
            f"{payload.volume or 0.01};{payload.sl or 0};{payload.tp or 0};"
            f"{payload.comment or ''};{magic};0")
```

---

### BUG 2: WF1 Google Sheets Rate Limiting 🔴

**Symptom:** WF1 ("Marktdaten Empfang & Log") zeigt abwechselnd Success und Error. Fehler: `"Der Dienst erhält zu viele Anfragen"` (Google Sheets API Limit: 100 requests/100 seconds).

**Root Cause:** 
- Bridge hat `PUSH_TO_N8N=true` → jeder eingehende Market-Tick wird sofort als Webhook an n8n gepusht
- WF1 empfängt Webhook `mt4-market` → schreibt JEDE Nachricht in Google Sheets TA-Log
- Bei aktiver EA kommen Ticks alle paar Sekunden → Google Sheets API-Limit wird überschritten
- 7750+ Ausführungen sichtbar im n8n Execution Log

**Was zu tun ist:**
- **Option A**: WF1 so umbauen, dass es Ticks sammelt und z.B. nur alle 60 Sekunden (oder alle 5 Minuten) einen Batch-Write macht
- **Option B**: In der Bridge `PUSH_TO_N8N` für Market-Daten deaktivieren (nur Signals pushen). WF7 holt sich die Daten sowieso selbst per GET /mt4/market
- **Option C**: Im WF1 Code-Node einen Throttle einbauen (z.B. nur schreiben wenn letzter Eintrag > 60s alt)

**Empfehlung:** Option B – Market-Push deaktivieren. Die Market-Daten werden im Bridge-Buffer gehalten (max 500) und von WF7 bei Bedarf abgerufen. WF1 braucht keinen Echtzeit-Push für jeden Tick.

---

### BUG 3: TA-Log Spalten leer (Symbol = "UNKNOWN") 🟡

**Symptom:** Google Sheets Tab "TA-Log" zeigt:
- Spalte "Symbol" = `UNKNOWN` für alle Zeilen
- Spalte "Timeframe" = `M1` (korrekt)
- Spalten RSI, MACD, MACD_Signal, EMA20, EMA50, Trend, Signal_Score = **ALLE LEER**

**Root Cause:**
- WF1 empfängt rohe Market-Ticks (Format: `{symbol, bid, ask, type: "tick"}` oder `{raw, parts, type}`)
- Der "Format-Fuer-Blätter" Code-Node in WF1 extrahiert das Symbol nicht korrekt aus dem Tick-Format
- Die Indikator-Spalten (RSI, MACD etc.) können aus rohen Ticks NICHT berechnet werden – die kommen erst aus WF7 (Trade Analyzer)
- **Das Konzept ist falsch**: WF1 loggt Ticks, aber der TA-Log erwartet Analyse-Ergebnisse

**Was zu tun ist:**
1. **TA-Log befüllen aus WF7**, nicht aus WF1. Nach der "Technische Analyse" in WF7 einen Google Sheets Append-Node einfügen, der die berechneten Werte (RSI, EMA20, EMA50, Trend, Signal_Score) in den TA-Log schreibt
2. WF1 entweder ganz auf Sheets-Writes verzichten lassen (nur Buffer), oder in einen separaten "Raw-Data" Tab schreiben
3. Im "Format-Fuer-Blätter" Node: `$json.symbol` aus dem Tick-Format korrekt extrahieren (der Bridge-Parser setzt es als Top-Level-Key)

---

### BUG 4: Trade-Log nur "SIGNAL" ohne Daten 🟡

**Symptom:** Google Sheets Tab "Trade-Log" enthält nur:
- Spalte A: Timestamp
- Spalte B: "SIGNAL" (Typ)
- Alle anderen Spalten: leer (kein Symbol, kein Preis, keine Richtung)

**Root Cause:**
- WF2 ("Signal Empfang & Alert") empfängt Signals via Webhook `mt4-signal`
- WF2 loggt nur den Signal-Typ (`parts[0]` = "SIGNAL") ohne die restlichen Daten zu extrahieren
- Die Bridge-parsierte Nachricht hat das Format: `{raw: "...", parts: ["SIGNAL", ...], type: "SIGNAL"}`
- Der Code-Node in WF2 extrahiert nur `$json.type` statt die vollständigen Signal-Daten

**Was zu tun ist:**
1. WF2 Code-Node so anpassen, dass alle Signal-Felder extrahiert werden
2. Für TRADE-Bestätigungen: WF8 schreibt bereits in "Active-Trades" Tab (nicht "Trade-Log") – prüfen ob der Tab-Name in WF2 korrekt ist
3. Alternativ: WF2 nur für Alerts nutzen, Trade-Log-Einträge nur aus WF8/WF10

---

### BUG 5: Telegram nur "MT4 Signal / Typ: SIGNAL" 🟡

**Symptom:** Telegram-Bot sendet nur generische Nachrichten: `"ℹ MT4 Signal / Typ: SIGNAL"` – keine nützlichen Informationen (Symbol, Preis, Richtung).

**Root Cause:**
- WF2 formatiert die Telegram-Nachricht nur mit dem Signal-Typ
- Die eigentlichen Signal-Daten (aus `parts[]` oder den geparsten Feldern) werden nicht in die Nachricht eingebaut

**Was zu tun ist:**
1. WF2 Telegram-Node so anpassen, dass die Nachricht die Signal-Details enthält
2. **Hinweis:** WF7 hat bereits eine korrekte Telegram-Formatierung (Node "Telegram Nachricht" und "HOLD loggen") – diese funktioniert und zeigt EMA, RSI, ATR, Trade-Plan etc.
3. WF2 ist für EA-Signale (nicht WF7-Analyse-Signale). Die EA-Signale haben ein anderes Format und müssen anders geparst werden

---

### BUG 6: TRACK_SYMBOLS nur EURUSD (nicht BTCUSD) 🟢

**Symptom:** In der `.env` steht `TRACK_SYMBOLS=EURUSD`, aber das Trading-System handelt BTCUSD.

**Was zu tun ist:**
```bash
# Auf VPS in /opt/mt4-bridge/.env ändern:
TRACK_SYMBOLS=BTCUSD;EURUSD
# Dann: systemctl restart mt4-bridge
```

---

## 3. Workflow-Übersicht (n8n IDs)

| ID | WF | Name | Active | Problem |
|----|-----|------|--------|---------|
| `TsesAyfkGln2WH00` | WF1 | Marktdaten Empfang & Log | ✅ | 🔴 Sheets Rate Limit + Symbol UNKNOWN |
| `6DcFnzHicZOh0FxZ` | WF2 | Signal Empfang & Alert | ✅ | 🟡 Nur "SIGNAL" geloggt, generische Telegram-Msg |
| `GjpBqxXZdHGGp218` | WF3 | Telegram Commands | ❌ | Nicht getestet |
| `2a1wXTU56DD2s0Yc` | WF4 | Portfolio Monitor | ✅ | Nicht getestet |
| `EVwU9BzKSKXuitLL` | WF5 | Tagesreport | ✅ | Nicht getestet |
| `8KAXUPF2J9EHbFAN` | WF6 | News Monitor | ✅ | Nicht getestet |
| `1T0fMAYzQKf8yM6j` | WF7 | Trade Analyzer | ✅ | 🔴 Analyse OK, Trade-Execution scheitert (Error 4051) |
| `CfULtpthxJXm3S25` | WF8 | Trade Executor | ✅ | 🔴 TRADE-Format falsch |
| `0bRXfI6yvP7yVjlm` | WF9 | Trade Monitor | ✅ | Ungetestet (braucht erst offenen Trade) |
| `Y1Z1WK5KInRXLlVY` | WF10 | Trade Journal | ✅ | Ungetestet |

### Workflow-Dateien im Repo
```
openclaw/N8N - Tailscale/workflows/
├── wf7-trade-analyzer.json
├── wf8-trade-executor.json
├── wf9-trade-monitor.json
├── wf10-trade-journal.json
└── import-workflows.sh
```

---

## 4. Google Sheets

**Sheet ID:** `1J1MNtiITEOTPBW_sZU4hl5Uf-_JlAaR4DDcS5eg-V_g`  
**Service Account:** `n8n-trading@n8n-trading-487411.iam.gserviceaccount.com`  
**Credential ID (n8n):** `82cab318-1cf6-4071-a030-1535dfe88501`

### Tabs
| Tab | Wird befüllt von | Status |
|-----|-----------------|--------|
| Trade-Log | WF2 (Signal Alert) | 🟡 Nur Timestamp + "SIGNAL" |
| TA-Log | WF1 (Marktdaten) | 🔴 Symbol=UNKNOWN, Indikatoren leer |
| News-Log | WF6 (News Monitor) | Ungeprüft |
| Performance | WF10 (Journal) | Ungeprüft |
| Config | Manuell | Ungeprüft |
| Errors | Diverse | Ungeprüft |
| Active-Trades | WF8 (Executor) | Ungetestet (TRADE funktioniert nicht) |

---

## 5. Was funktioniert (verifiziert)

| Feature | Test | Ergebnis |
|---------|------|----------|
| Bridge Health Check | `GET /health` | ✅ OK, ZMQ connected |
| HIST-Befehl | `POST /mt4/command {action: "HIST"}` | ✅ 2048-2088 M15 Candles |
| ast.literal_eval Patch | Python-Dict-Strings | ✅ Korrekt geparst |
| Market Buffer | `GET /mt4/market` | ✅ ~500 Ticks (wenn Markt offen) |
| WF7 Technische Analyse | EMA20/50, RSI14, ATR14 | ✅ Korrekte Werte berechnet |
| WF7 → Telegram (Analyse) | Formatierte Analyse-Nachricht | ✅ Details inkl. Indikatoren |
| Telegram Bot Connectivity | Message ID 49 empfangen | ✅ |
| Tailscale Verbindung | Ping VPS ↔ MT4-PC | ✅ 13ms |

---

## 6. Was NICHT funktioniert

| Feature | Problem | Nächster Schritt |
|---------|---------|------------------|
| TRADE OPEN | Error 4051 | EA-Quellcode lesen → Format anpassen |
| TRADE CLOSE | Nicht getestet | Erst nach OPEN-Fix |
| TRADE MODIFY | Nicht getestet | Erst nach OPEN-Fix |
| ACCOUNT_INFO | EA unterstützt es nicht | Balance hardcoded ($100k) |
| OPEN_TRADES | EA unterstützt es nicht | Tracking via Google Sheets |
| WF1 → Sheets | Rate Limiting | Throttle oder Push deaktivieren |
| WF2 → Sheets | Nur "SIGNAL" geloggt | Signal-Daten korrekt extrahieren |
| WF2 → Telegram | Generische Nachricht | Nachricht mit Daten formatieren |

---

## 7. Empfohlene Reihenfolge zum Fixen

### Phase 1: TRADE-Format reparieren
1. EA-Quellcode auf MT4-PC finden und lesen (via SSH/RDP oder Stephan fragen)
2. `_build_dwx_command()` in `/opt/mt4-bridge/bridge.py` anpassen
3. Testen (nur wenn Markt offen: Mo-Fr)
4. Bridge .env: `TRACK_SYMBOLS=BTCUSD;EURUSD` setzen
5. `systemctl restart mt4-bridge`

### Phase 2: WF1 Rate Limiting fixen
1. Option B empfohlen: Bridge-Push nur für Signals, nicht Market
   - In `/opt/mt4-bridge/bridge.py` → `recv_market()` → `PUSH_TO_N8N` deaktivieren (oder neues Flag `PUSH_MARKET_TO_N8N=false`)
   - Oder: `.env` → `PUSH_TO_N8N=false` setzen und WF1/WF2 auf Polling umstellen
2. Alternativ: WF1 Code-Node mit Throttle (nur alle 60s schreiben)

### Phase 3: Datenqualität
1. **TA-Log**: WF7 nach "Technische Analyse" Node → Google Sheets Append mit RSI, EMA20, EMA50, ATR, Trend, Signal
2. **Trade-Log**: WF2 Code-Node → Signal-Daten vollständig extrahieren und loggen
3. **Telegram**: WF2 → Nachricht mit Signal-Details formatieren (nicht nur Typ)

### Phase 4: Testen
1. Demo-Trade über WF7 → WF8 Pipeline (Markt muss offen sein)
2. WF9 Trade Monitor mit offenem Trade verifizieren
3. WF10 Trade Journal: Trade schließen → Journal-Eintrag prüfen

---

## 8. Credentials & Secrets

| Was | Wert |
|-----|------|
| Bridge API Token | `77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb` |
| Telegram Bot Token | `8546370466:AAFkYIvBHd1Lipxh3SsMTmSioMzYnL241Vc` |
| Telegram Chat ID | `7268021157` |
| n8n Telegram Credential ID | `lwOSLP3ylq10yEW4` |
| n8n Google Sheets Credential ID | `82cab318-1cf6-4071-a030-1535dfe88501` |
| Google Sheets Document ID | `1J1MNtiITEOTPBW_sZU4hl5Uf-_JlAaR4DDcS5eg-V_g` |
| Google Service Account | `n8n-trading@n8n-trading-487411.iam.gserviceaccount.com` |
| Service Account JSON (lokal) | `c:\Users\Stephan\Downloads\n8n-trading-487411-681e7a4b2a53.json` |

---

## 9. Temp-Dateien (aufräumen)

### Lokal (d:\GH\) – löschen:
```
demo_trade.py
trade.json
trade2.json
test_trade_formats.py
test_raw_formats.py
check_health.py
```

### VPS (/tmp/) – löschen:
```
demo_trade.py
test_trade_formats.py
test_raw_formats.py
check_health.py
test_results.txt
trade.json
trade2.json
```

---

## 10. Nützliche Befehle

```bash
# Bridge Status
curl -s http://localhost:8765/health | python3 -m json.tool

# Signal Buffer lesen (ohne löschen)
curl -s -H "Authorization: Bearer 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb" \
  "http://localhost:8765/mt4/signals?limit=10&clear=false"

# HIST anfordern
curl -s -X POST http://localhost:8765/mt4/command \
  -H "Authorization: Bearer 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb" \
  -H "Content-Type: application/json" \
  -d '{"action":"HIST","symbol":"BTCUSD","extra":{"timeframe":"15","start":"2025.01.01 00:00:00","end":"2030.01.01 00:00:00"}}'

# Raw Command senden (Debug)
curl -s -X POST http://localhost:8765/mt4/raw \
  -H "Authorization: Bearer 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb" \
  -H "Content-Type: application/json" \
  -d '{"command":"TRADE;OPEN;0;BTCUSD;0;0.01;0;0;;0;0"}'

# Bridge Logs (live)
journalctl -u mt4-bridge -f --no-pager

# n8n Logs
journalctl -u n8n -f --no-pager

# Bridge neustarten
systemctl restart mt4-bridge
```

---

## 11. Git Status

Letzter Commit: `fd13557480` (14. Feb 2026)  
- 17 Dateien, 3129 Zeilen hinzugefügt  
- Branch: vermutlich `main`  
- Working tree war sauber nach Commit (temp Test-Dateien kamen danach)

### Dateien im Repo (N8N - Tailscale/)
```
CHANGELOG.md              ← Alle Änderungen dokumentiert
HANDOFF-CLAUDE-CODE.md    ← DIESES Dokument
README.md                 ← Übersicht mit Workflow-Tabellen
ZMQ_BRIDGE.md             ← Bridge-Dokumentation (vollständig)
N8N_SETUP.md              ← n8n Installation
TAILSCALE_SETUP.md        ← Tailscale Installation
TROUBLESHOOTING.md        ← Problemlösungen
mt4_bridge/
  bridge.py               ← Bridge-Quellcode (Referenz, LIVE ist auf VPS)
  .env.example            ← Beispiel-Konfiguration
  requirements.txt        ← Python-Dependencies
  install.sh              ← Installations-Script
  mt4-bridge.service      ← systemd Unit
patches/
  patch-bridge-ast-parser.sh  ← ast.literal_eval Patch
workflows/
  wf7-trade-analyzer.json
  wf8-trade-executor.json
  wf9-trade-monitor.json
  wf10-trade-journal.json
  import-workflows.sh
```

---

## 12. Wichtige Hinweise

1. **Wochenende:** Sa/So sind die Märkte geschlossen. BTCUSD bei Capital.com hat auch am Wochenende eingeschränkte/keine Verfügbarkeit. TRADE-Tests nur Mo-Fr.
2. **Bridge Restart:** Nach einem Restart der Bridge verliert die EA die Verbindung. Es dauert einige Sekunden bis ZMQ reconnected. Market Buffer ist dann leer bis neue Ticks kommen.
3. **Demo-Konto:** Capital.com Demo mit $100.000. Kein echtes Geld.
4. **DWX EA Version:** v2.0.1 RC8 – unterstützt KEIN `ACCOUNT_INFO` und KEIN `OPEN_TRADES` via ZMQ. Nur dateibasiert (DWX_Orders.txt).
5. **n8n API Key:** `N8N_API_KEY=n8n_api_trading_2026` ist in systemd gesetzt, wird aber von n8n v2.7.5 nicht korrekt erkannt (401). Workflows funktionieren über Webhooks.
6. **bridge.py im Repo vs. VPS:** Die Datei im Repo (`mt4_bridge/bridge.py`) ist die Referenz. Die LIVE-Version auf dem VPS (`/opt/mt4-bridge/bridge.py`) hat zusätzlich den `/mt4/raw` Endpoint und den ast.literal_eval Patch. Nach Änderungen immer beide synchron halten!
