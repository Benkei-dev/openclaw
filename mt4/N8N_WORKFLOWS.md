# n8n Workflows – MT4 Trading System

Alle Workflows sind unter `http://100.127.134.70:5678` zu finden.
Credentials und IDs: siehe `openclaw/vps/CREDENTIALS.md` (lokal, nicht im Repo).

---

## Übersicht

| # | Name | Trigger | Zweck | Status |
|---|------|---------|-------|--------|
| 1 | MT4 - 1 Marktdaten Empfang & Log | Webhook `mt4-market` | Ticks → Google Sheets TA-Log | ✅ Aktiv |
| 2 | MT4 - 2 Signal Empfang & Alert | Webhook `mt4-signal` | Signale → Telegram + Trade-Log | ✅ Aktiv |
| 3 | MT4 - 3 Telegram Commands | Telegram Trigger | Bot-Commands verarbeiten | ✅ Aktiv |
| 4 | MT4 - 4 Portfolio Monitor | Schedule 5min | Bridge-Health + Performance-Log | ✅ Aktiv |
| 5 | MT4 - 5 Tagesreport | Schedule Mo–Fr 21:45 | Tagesreport via Telegram | ✅ Aktiv |

---

## Webhook-URLs (n8n)

| Webhook | URL |
|---------|-----|
| Marktdaten | `http://100.127.134.70:5678/webhook/mt4-market` |
| Signale | `http://100.127.134.70:5678/webhook/mt4-signal` |

Diese URLs werden von der **Python Bridge** automatisch angesprochen wenn `PUSH_TO_N8N=true`.

---

## Workflow 1 – Marktdaten Empfang & Log

**Trigger:** `POST /webhook/mt4-market`
**Nodes:** Webhook → Code (Format) → Google Sheets (TA-Log append)

```
MT4 Bridge (PUSH) → Webhook → Format → TA-Log!A:J
```

**Was wird geloggt:** Timestamp, Symbol, Timeframe
**Erweiterung:** Code-Node kann RSI/MACD berechnen sobald genug Kerzen gesammelt sind.

---

## Workflow 2 – Signal Empfang & Alert

**Trigger:** `POST /webhook/mt4-signal`
**Nodes:** Webhook → Code (Format) → [Telegram Alert] + [Trade-Log append]

```
MT4 Signal → Webhook → Format → Telegram (sofort)
                               → Trade-Log (persistent)
```

**Telegram-Format:**
```
✅ MT4 Signal
Typ: EXECUTION
Symbol: EURUSD
Preis: 1.08542
Vol: 0.1
SL: 1.0800  TP: 1.0950
Ticket: #12345678
14.02.2026, 11:30:00
```

---

## Workflow 3 – Telegram Commands

**Trigger:** Telegram Bot (`@mt4_deinname_bot`)
**Unterstützte Commands:**

| Command | Wirkung |
|---------|---------|
| `/status` | Bridge-Health, ZMQ-Status, Statistiken |
| `/pause` | Bestätigung senden (Trading muss in Config deaktiviert werden) |
| `/resume` | Bestätigung senden |
| `/closeall` | `CLOSE_ALL_TRADES` an MT4 Bridge senden |

**Erweiterbar:** Switch-Node in n8n um weitere Commands ergänzen.

---

## Workflow 4 – Portfolio Monitor

**Trigger:** Schedule alle 5 Minuten
**Logik:**
1. `GET /health` → Bridge erreichbar?
2. Wenn offline → Telegram Alert
3. Wenn online → Performance-Snapshot in Sheets schreiben

**Alarm-Bedingung:** `status != "ok"` → sofortige Benachrichtigung

---

## Workflow 5 – Tagesreport

**Trigger:** Mo–Fr 21:45 Uhr (Cron: `45 21 * * 1-5`)
**Inhalt:**
- System-Status (Bridge online/offline, Uptime)
- Aktivitäts-Zahlen (Signale, Befehle, n8n-Push)
- Link zum Google Sheet

---

## Google Sheets Tabs

| Tab | Befüllt von | Inhalt |
|-----|------------|--------|
| Trade-Log | Workflow 2 | Alle Signale/Executions |
| TA-Log | Workflow 1 | Marktdaten-Ticks pro Symbol |
| News-Log | (geplant WF 6) | News + Sentiment |
| Performance | Workflow 4 | 5-Min Snapshots |
| Config | Manuell | System-Parameter |
| Errors | (geplant) | Fehler-Protokoll |

**Config-Parameter** (direkt im Sheets Config-Tab änderbar):

| Key | Standardwert | Bedeutung |
|-----|-------------|-----------|
| `TRADING_ACTIVE` | `false` | Trading ein/aus |
| `MAX_RISK_PERCENT` | `1.5` | Max. Risiko pro Trade |
| `MAX_DAILY_DRAWDOWN` | `5.0` | Tägliches Stop-Loss in % |
| `MIN_RR_RATIO` | `2.0` | Mind. Risk/Reward |
| `MIN_CONFIDENCE` | `0.75` | Min. KI-Confidence für Auto-Trade |
| `SYMBOLS` | `EURUSD,GBPUSD,XAUUSD` | Aktive Symbole |

---

## Nächste Schritte (Phase 3)

```
□ Workflow 6: News-Monitor (ForexFactory + Sentiment)
□ Workflow 7: Trade-Entscheidung (TA + News → Risk → Decision)
□ openclaw Skill: mt4-technical-analysis (RSI, MACD, EMA)
□ openclaw Skill: mt4-risk-manager (Position-Sizing)
□ Dry-Run-Modus: Vorschläge loggen aber nicht ausführen
```

---

## Import / Update

Workflows als JSON exportieren:
```bash
# Alle Workflows exportieren
curl -s -H "X-N8N-API-KEY: <key>" http://100.127.134.70:5678/api/v1/workflows
```

Neu importieren nach Änderungen:
```bash
node openclaw/vps/import_workflows.js
```
