# Autonomes Trading-System – Gesamtarchitektur

Vollständiger Plan: n8n + MT4 + openclaw-Agenten + menschliches Oversight.

---

## Systemübersicht

```
┌──────────────────────────────────────────────────────────────────────┐
│                        DATEN-QUELLEN                                 │
│  MT4 Ticks ──┐   News APIs ──┐   Economic Calendar ──┐              │
│              │               │                        │              │
└──────────────┼───────────────┼────────────────────────┼──────────────┘
               │               │                        │
┌──────────────▼───────────────▼────────────────────────▼──────────────┐
│                      n8n ORCHESTRATION                               │
│                                                                      │
│  [Workflow 1] Tick-Empfang & TA-Berechnung  (jede Minute)           │
│  [Workflow 2] News-Monitor & Sentiment       (alle 15 Min)          │
│  [Workflow 3] Trade-Entscheidung             (nach TA + News)       │
│  [Workflow 4] Risk-Manager                   (vor jeder Order)      │
│  [Workflow 5] Order-Ausführung               (nach Freigabe)        │
│  [Workflow 6] Portfolio-Überwachung          (alle 5 Min)           │
│  [Workflow 7] Tagesreport                    (täglich 22 Uhr)       │
│  [Workflow 8] Manueller Override             (Telegram-Commands)    │
│                                                                      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               │               │               │
┌──────────────▼──┐  ┌─────────▼──────┐  ┌────▼──────────────────┐
│  Python Bridge  │  │  openclaw      │  │  Benachrichtigungen   │
│  → MT4 ZMQ      │  │  AI-Agenten    │  │  Telegram / Gmail     │
└─────────────────┘  └───────────────-┘  └───────────────────────┘
```

---

## Agenten-Rollen & Verantwortlichkeiten

### Wer tut was?

```
┌─────────────────────┬──────────────────────────────────────────────┐
│ Agent               │ Aufgabe                                      │
├─────────────────────┼──────────────────────────────────────────────┤
│ market-data         │ Empfängt Ticks, berechnet OHLCV-Kerzen,      │
│                     │ cached Preishistorie in Google Sheets         │
├─────────────────────┼──────────────────────────────────────────────┤
│ technical-analysis  │ RSI, MACD, Bollinger, EMA, Support/Resist,   │
│                     │ Trend-Richtung, Signalstärke 0-100           │
├─────────────────────┼──────────────────────────────────────────────┤
│ news-monitor        │ Scrapt Reuters/Investing.com/ForexFactory,   │
│                     │ bewertet Sentiment per LLM (+/-/neutral)      │
├─────────────────────┼──────────────────────────────────────────────┤
│ economic-calendar   │ Überwacht High-Impact-Events (NFP, FOMC,     │
│                     │ CPI), setzt automatisch "No-Trade"-Fenster    │
├─────────────────────┼──────────────────────────────────────────────┤
│ risk-manager        │ Berechnet Position-Size (% vom Konto),       │
│                     │ prüft max. Drawdown, Korrelation offener      │
│                     │ Positionen, R:R-Verhältnis                    │
├─────────────────────┼──────────────────────────────────────────────┤
│ trade-decision      │ FINALE Entscheidung: kombiniert TA-Score,    │
│                     │ News-Sentiment, Risiko → BUY/SELL/HOLD       │
│                     │ mit Begründung (LLM-basiert)                  │
├─────────────────────┼──────────────────────────────────────────────┤
│ portfolio-tracker   │ Überwacht offene Positionen, trailing SL,    │
│                     │ tägliches P&L, Drawdown-Alarm                 │
└─────────────────────┴──────────────────────────────────────────────┘
```

---

## n8n Workflows im Detail

### Workflow 1 – Tick-Empfang & Technische Analyse
**Trigger:** Webhook `POST /webhook/mt4-market` (Push von Bridge)
**Interval:** Pro Tick, Analyse aber gedrosselt auf 1x/Minute

```
[Webhook: mt4-market]
  ↓
[Throttle: max 1x pro Minute pro Symbol]
  ↓
[Code: OHLCV-Kerze aus Ticks berechnen]
  ↓
[HTTP: POST zu openclaw market-data Agent]
  → "Speichere Kerze EURUSD M1, berechne letzte 50 Kerzen"
  ↓
[HTTP: POST zu openclaw technical-analysis Agent]
  → Input: letzte 200 Kerzen EURUSD
  → Output: { rsi: 67, macd: "bullish", trend: "up", signal_score: 73 }
  ↓
[Google Sheets: Zeile in "TA-Log" schreiben]
  ↓
[IF signal_score > 70 ODER < 30]
  └── Ja → [Workflow 3: Trade-Entscheidung triggern]
```

---

### Workflow 2 – News-Monitor & Sentiment
**Trigger:** Schedule alle 15 Minuten + bei Economic Calendar Events

```
[Schedule: alle 15 Min]
  ↓
[HTTP: GET ForexFactory Calendar API]  ← High/Medium Impact Events
  ↓
[IF High-Impact-Event in nächsten 30 Min]
  ├── Ja → [Set Variable: TRADING_PAUSED = true]
  │         [Telegram: "⚠️ High-Impact-Event in 30 Min: NFP – Trading pausiert"]
  │         [Google Calendar: Event erstellen "No-Trade Window"]
  └── Nein ↓
[HTTP: POST zu openclaw news-monitor Agent]
  → "Analysiere aktuelle Forex-News für EURUSD, GBPUSD, XAUUSD"
  → Output: { eurusd_sentiment: -0.3, gbpusd_sentiment: 0.7, ... }
  ↓
[IF stark negatives Sentiment < -0.7]
  └── Telegram: "📰 News-Alarm: Stark negatives EURUSD-Sentiment – prüfe manuell"
  ↓
[Set Variable: CURRENT_SENTIMENT = {...}]
```

---

### Workflow 3 – Trade-Entscheidung (Herzstück)
**Trigger:** Wird von Workflow 1 aufgerufen wenn Signal-Score > 70

```
[Trigger: Signal von Workflow 1]
  ↓
[Check: TRADING_PAUSED == true?]
  ├── Ja → [Abort + Log "Trading pausiert"]
  └── Nein ↓
[Hole aktuellen Kontostand von MT4]
  → GET /mt4/signals (filtert auf account_info Antwort)
  ↓
[HTTP: POST zu openclaw risk-manager Agent]
  → Input: {
      symbol: "EURUSD",
      signal: "BUY",
      sl_pips: 20,
      tp_pips: 40,
      account_balance: 10000,
      open_positions: [...],
      max_risk_percent: 1.5
    }
  → Output: {
      approved: true,
      volume: 0.08,
      actual_risk_eur: 16.0,
      rr_ratio: 2.0,
      reason: "Position size 0.08 lot = 1.45% Risiko, R:R 1:2 ✓"
    }
  ↓
[IF risk.approved == false]
  ├── Log + Telegram: "❌ Trade abgelehnt vom Risk-Manager: {reason}"
  └── Abort
  ↓
[HTTP: POST zu openclaw trade-decision Agent]
  → Input: {
      symbol, signal, ta_score, news_sentiment,
      risk_assessment, recent_trades, market_context
    }
  → Output: {
      decision: "EXECUTE",      // EXECUTE | WAIT | REJECT
      confidence: 0.82,
      reasoning: "RSI 67 + MACD bullish + Sentiment neutral + R:R 2:1...",
      suggested_sl: 1.0812,
      suggested_tp: 1.0852
    }
  ↓
[IF confidence > 0.85 UND kein manueller Eingriff nötig]
  ├── Ja → [Workflow 5: Order direkt ausführen]
  └── Nein → [Warte auf Nutzer-Freigabe via Telegram]
              [Telegram: "🤔 Trade-Vorschlag: BUY EURUSD 0.08 Lot
                          SL: 1.0812 | TP: 1.0852 | R:R 1:2
                          Confidence: 82% | Begründung: ...
                          👍 /approve_{id}  👎 /reject_{id}
                          ⏰ Läuft ab in 10 Min"]
              [Wait 10 Minuten für Antwort]
              [IF keine Antwort → Auto-Reject + Log]
```

---

### Workflow 4 – Nutzer-Freigabe via Telegram
**Trigger:** Webhook `POST /webhook/telegram-command`

```
[Telegram Webhook]
  ↓
[Parse Command]
  ├── /approve_{id} → [Führe Trade aus] → [Workflow 5]
  ├── /reject_{id}  → [Ablehnen + Log]
  ├── /pause        → [Set TRADING_PAUSED = true] → "⏸ Trading pausiert"
  ├── /resume       → [Set TRADING_PAUSED = false] → "▶️ Trading aktiv"
  ├── /closeall     → [MT4: CLOSE_ALL_TRADES] → "🚨 Alle Positionen geschlossen"
  ├── /status       → [Hole Portfolio-Status + Antwort]
  ├── /report       → [Tagesreport generieren + senden]
  └── /news {text}  → [trade-decision Agent: "Bewerte Auswirkung dieser News: {text}"]
                       → Antwort mit Empfehlung (Pause? Welche Symbole betroffen?)
```

---

### Workflow 5 – Order-Ausführung
**Trigger:** Intern von Workflow 3 oder 4 aufgerufen

```
[Order-Parameter erhalten]
  ↓
[HTTP: POST http://localhost:8765/mt4/command]
  → {
      "action": "OPEN_TRADE",
      "symbol": "EURUSD",
      "order_type": 0,
      "volume": 0.08,
      "sl": 1.0812,
      "tp": 1.0852,
      "comment": "n8n-auto-{workflow_id}",
      "magic": 20260214
    }
  ↓
[Warte auf Execution-Bestätigung via Webhook mt4-signal]
  ↓
[Google Sheets: Trade in "Trade-Log" schreiben]
  → Symbol, Richtung, Volume, Preis, SL, TP, Begründung, Confidence
  ↓
[Gmail: Trade-Bestätigung senden]
  → "✅ Trade ausgeführt: BUY EURUSD 0.08@1.0832, SL:1.0812, TP:1.0852"
  ↓
[Telegram: Gleiche Info]
```

---

### Workflow 6 – Portfolio-Überwachung
**Trigger:** Schedule alle 5 Minuten

```
[Schedule]
  ↓
[HTTP: GET /mt4/signals?limit=1 + {action: GET_OPEN_TRADES}]
  ↓
[Code: P&L berechnen, Drawdown prüfen]
  ↓
[IF Drawdown > 5% des Tageskapitals]
  └── [Alle Positionen schließen] + [TRADING_PAUSED = true]
       [Telegram: "🚨 Drawdown-Limit erreicht! Alle Positionen geschlossen."]
  ↓
[IF Trade läuft seit > 4h ohne Bewegung]
  └── [Telegram: "⚠️ EURUSD BUY stagniert seit 4h. Manuell prüfen? /close_{ticket}"]
  ↓
[Google Sheets: Portfolio-Snapshot schreiben]
```

---

### Workflow 7 – Tagesreport
**Trigger:** Schedule täglich 21:45 Uhr (vor Marktschluss NY)

```
[Schedule]
  ↓
[Google Sheets: Alle heutigen Trades laden]
  ↓
[HTTP: POST zu openclaw portfolio-tracker Agent]
  → "Erstelle Tagesreport: Trades, P&L, Win-Rate, beste/schlechteste Symbole"
  ↓
[Gmail: Report als HTML senden]
[Telegram: Kurzfassung senden]
[Google Sheets: Tages-Zusammenfassung in "Performance"-Tab]
```

---

## Manueller Eingriff – alle Möglichkeiten

### Telegram-Commands (jederzeit, sofort)

| Command | Wirkung |
|---------|---------|
| `/pause` | Trading sofort pausieren |
| `/resume` | Trading wieder aktivieren |
| `/status` | Alle offenen Positionen + P&L |
| `/closeall` | Alle Positionen sofort schließen |
| `/close_123456` | Einzelne Position (Ticket) schließen |
| `/approve_xyz` | Vorgeschlagenen Trade freigeben |
| `/reject_xyz` | Vorgeschlagenen Trade ablehnen |
| `/news FOMC erhöht Zinsen unerwartet` | KI bewertet Auswirkung sofort |
| `/report` | Tagesreport jetzt generieren |
| `/notradewindow 60` | Trading für 60 Min pausieren |

### Bei News die du selbst hörst

```
Du: /news EZB überraschende Zinserhöhung um 0.5%

Bot antwortet innerhalb Sekunden:
  "📊 Analyse: EZB +0.5% unerwartet
   → EUR stark bullish (kurzfristig)
   → EURUSD: Long-Bias erhöht
   → EURGBP: Wahrscheinlich Anstieg
   ⚠️ Hohe Volatilität für 30-60 Min erwartet
   Empfehlung: Trading pausieren für 30 Min
   Dann: EUR-Long-Chancen beobachten
   👉 /pause oder /resume nach 30 Min"
```

---

## openclaw-Agenten – was muss noch angelegt werden

### Neue Skills/Agenten in `openclaw/skills/` oder `openclaw/extensions/`:

```
skills/
├── mt4-technical-analysis/    ← NEU
│   ├── SKILL.md
│   └── scripts/
│       └── analyze.py         ← RSI, MACD, EMA, Bollinger via pandas-ta
│
├── mt4-news-monitor/          ← NEU
│   ├── SKILL.md
│   └── scripts/
│       └── news.py            ← Scraping + LLM-Sentiment
│
├── mt4-risk-manager/          ← NEU
│   ├── SKILL.md
│   └── scripts/
│       └── risk.py            ← Position-Sizing, Drawdown-Check
│
├── mt4-trade-decision/        ← NEU
│   ├── SKILL.md
│   └── scripts/
│       └── decide.py          ← LLM-basierte Finale Entscheidung
│
└── mt4-portfolio/             ← NEU
    ├── SKILL.md
    └── scripts/
        └── portfolio.py       ← P&L-Tracking, Reporting
```

### Oder als openclaw-Extension (HTTP-Server, immer verfügbar):

```
extensions/
└── mt4-trading-brain/         ← NEU (empfohlen)
    ├── index.ts               ← HTTP-Endpoints für n8n
    ├── agents/
    │   ├── technical.ts       ← TA-Agent
    │   ├── news.ts            ← News-Agent
    │   ├── risk.ts            ← Risk-Manager
    │   └── decision.ts        ← Final-Decision-Agent
    └── package.json
```

---

## Google Account – Empfehlung: JA, definitiv

### Was bringt ein Google-Account?

| Service | Nutzen für das Trading-System |
|---------|-------------------------------|
| **Gmail** | Trade-Bestätigungen, Tagesreports, Fehler-Alerts, Audit-Trail |
| **Google Sheets** | Live Trade-Log, Performance-Tracking, Daten-Backup, Charts |
| **Google Calendar** | Wirtschaftskalender-Events als Kalendereinträge, No-Trade-Fenster |
| **Google Drive** | Backup der n8n-Workflows, Bridge-Configs, historische Daten |
| **Google Cloud Storage** | Tick-Daten archivieren (günstig, skalierbar) |

### In n8n integrieren:
- n8n hat native **Google Sheets**, **Gmail**, **Google Calendar** Nodes
- Einmal OAuth2 einrichten → alle Workflows nutzen es
- Kein eigener Server nötig für Datenspeicherung

### Empfohlene Google Sheets Struktur:

```
Trading-System (Google Sheets Datei)
├── Tab: Trade-Log        ← alle ausgeführten Trades
├── Tab: TA-Log           ← technische Analyse pro Symbol/Zeit
├── Tab: News-Log         ← News + Sentiment
├── Tab: Performance      ← tägl. P&L, Win-Rate, Drawdown
├── Tab: Config           ← Parameter (max_risk, symbole, etc.)
└── Tab: Errors           ← Fehler und Ausnahmen
```

---

## Implementierungs-Reihenfolge (empfohlen)

```
Phase 1 – Fundament (1-2 Tage)
  ✅ Python Bridge (fertig)
  □ Google Account anlegen + Sheets vorbereiten
  □ Telegram Bot erstellen (@BotFather)
  □ n8n: Google + Telegram Credentials konfigurieren

Phase 2 – Daten & Monitoring (2-3 Tage)
  □ Workflow 1: Tick-Empfang + TA (pandas-ta)
  □ Workflow 6: Portfolio-Überwachung
  □ Workflow 7: Tagesreport
  → System läuft passiv, sammelt Daten, keine Trades

Phase 3 – Entscheidungslogik (3-5 Tage)
  □ openclaw Skill: mt4-technical-analysis
  □ openclaw Skill: mt4-risk-manager
  □ Workflow 3: Trade-Entscheidung (erst im "Dry-Run"-Modus)
  → System schlägt Trades vor, führt sie NICHT aus
  → Validierung: Sind Vorschläge sinnvoll?

Phase 4 – News & Kalender (2-3 Tage)
  □ Workflow 2: News-Monitor
  □ openclaw Skill: mt4-news-monitor
  □ Economic Calendar Integration

Phase 5 – Automation & Kontrolle (2 Tage)
  □ Workflow 4: Telegram-Commands (manueller Override)
  □ Workflow 5: Auto-Execution (nach ausreichend Dry-Run-Validierung)
  □ openclaw Skill: mt4-trade-decision (LLM-Final-Decision)
```
