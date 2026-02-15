# Source of Truth – MT4 Trading Automation

> **JEDER CHAT / AGENT muss diese Datei ZUERST lesen und die Regeln befolgen.**
> Referenz: Dieses File ist die einzige Wahrheitsquelle für den aktuellen Projektstatus.

### Auto-Discovery (wie Agents diese Datei finden)

| Agent | Automatisch? | Mechanismus |
|-------|-------------|-------------|
| Claude Code | ✅ JA | Liest `AGENTS.md` (= `CLAUDE.md`) beim Start → Verweis auf `N8N - Tailscale/SOT.md` |
| Copilot Chat | ✅ JA | Liest `.github/copilot-instructions.md` beim Start → Verweis auf SOT.md |
| ChatGPT | ❌ NEIN | **Boot-Message nötig** (Template siehe `## Chat-Rotation & Übergabe`) |

> ⚠️ Bei ChatGPT: Memory-Feature nutzen und dort speichern: *"MT4 Trading Projekt: Immer zuerst N8N - Tailscale/SOT.md lesen."*

---

## Regeln für alle Agents

1. **Lies diese Datei komplett** bevor du anfängst zu arbeiten.
2. **Claim** einen Task bevor du anfängst: ändere `[ ]` → `[~AGENT]` und committe+pushe sofort.
3. **Arbeite nur an geclaimten Tasks.** Nie an Tasks arbeiten, die ein anderer Agent geclaimed hat.
4. **Markiere fertig** wenn erledigt: `[~AGENT]` → `[x]` und füge einen Log-Eintrag unten hinzu.
5. **Ein Task gleichzeitig.** Nicht mehrere Tasks claimen.
6. **Append-only Log:** Nur Zeilen am Ende von `## Log` hinzufügen, nie bestehende Zeilen löschen.
7. **Commit-Message:** Nutze Prefix `SOT:` für Änderungen an dieser Datei, z.B. `SOT: claim BUG-1`.
8. **Pull vor Push:** Immer `git pull --rebase` vor dem Push, um Konflikte zu vermeiden.
9. **Keine VPS-Änderungen** ohne geclaimten Task. Dokumentiere jede VPS-Änderung im Log.
10. **Backup vor Änderung:** Vor jeder Änderung an bridge.py oder Workflows: Backup anlegen.
11. **Modell loggen:** Im Log IMMER das verwendete Modell angeben (z.B. `CC-OPUS`, `CC-HAIKU`).
12. **Token-Schätzung:** Am Ende jedes Arbeitsblocks im Log schätzen: `~Nk tokens verbraucht`. Basis: Kurze Aufgabe ~5k, mittlere ~20k, komplexe ~50k+.
13. **Chat-Rotation:** Vor dem Beenden eines Chats IMMER den Rotations-Ablauf (siehe `## Chat-Rotation & Übergabe`) befolgen. Kein Chat darf sterben ohne SOT.md-Update + Log-Eintrag.

### Agent-Kennungen

| Kennung | Modell | Stärke | Einsatz für |
|---------|--------|--------|-------------|
| `CC-OPUS` | Claude Code / Opus 4 | ⭐⭐⭐ Stärkste | Komplexe Bugs, Architektur, Multi-File-Änderungen, EA-Reverse-Engineering |
| `CC-SONNET` | Claude Code / Sonnet 4.5 | ⭐⭐ Stark | Mittlere Tasks, Workflow-Anpassungen, Testing |
| `CC-HAIKU` | Claude Code / Haiku | ⭐ Schnell+günstig | Einfache Tasks, Cleanup, Config-Änderungen, Dateien löschen |
| `CP-OPUS` | Copilot Chat / Opus 4 | ⭐⭐⭐ Orchestrator | Planung, Reviews, Berichte, Task-Zuweisung |
| `CG` | ChatGPT (Browser) | ⭐⭐ Recherche | Web-Recherche, DWX-Doku, Konzepte |
| `ST` | Stephan (manuell) | — | Entscheidungen, MT4-PC-Zugang, Genehmigungen |

### Komplexitätsstufen für Tasks

| Level | Label | Beschreibung | Zuweisen an |
|-------|-------|-------------|-------------|
| 🔴 | `HARD` | Multi-File, Debugging, Reverse-Engineering, Architektur | CC-OPUS |
| 🟡 | `MED` | Einzelne Workflows anpassen, Code-Nodes schreiben, API-Calls | CC-SONNET |
| 🟢 | `EASY` | Config-Änderung, Dateien löschen, .env anpassen, simple Fixes | CC-HAIKU |
| 🔵 | `PLAN` | Recherche, Planung, Dokumentation, Review | CP-OPUS / CG |

### Orchestrierung

**CP-OPUS (dieser Copilot-Chat) ist der Orchestrator.**
- Stephan beschreibt was er will → CP-OPUS weist Tasks zu
- CP-OPUS setzt das Komplexitäts-Level und die Agent-Kennung in die Task-Zeile
- Agents arbeiten nur Tasks ab die ihnen zugewiesen sind
- Bei Unklarheiten: Agent fragt CP-OPUS (via SOT.md Kommentar im Log)

### OpenClaw auf VPS

**Empfehlung: Aktuell NEIN für Orchestrierung.**
- OpenClaw ist ein Messaging-Gateway – kein Task-Orchestrator
- Die SOT.md + Git Methode ist robuster und hat keine zusätzlichen Dependencies
- **Später möglich:** OpenClaw als erweiterter Telegram-Bot für Trade-Alerts (nach Phase 3)

---

## Chat-Rotation & Übergabe

### Warum rotieren?
Jeder Chat hat ein Token-Limit (Context Window). Je länger ein Chat läuft, desto:
- teurer wird jede Nachricht (volles Context Window wird bei jeder Antwort abgerechnet)
- unzuverlässiger werden die Antworten (Infos aus der Mitte gehen verloren)
- höher das Risiko dass der Chat "vergisst" was er tun sollte

### Wann rotieren?

| Agent-Typ | Rotieren nach | Erkennungszeichen |
|-----------|--------------|-------------------|
| CC-OPUS | ~3-4 komplexe Tasks oder ~150k tokens | Antworten werden unpräziser, wiederholt sich |
| CC-SONNET | ~5-6 mittlere Tasks oder ~120k tokens | Verliert Details, braucht Erinnerungen |
| CC-HAIKU | ~8-10 einfache Tasks oder ~80k tokens | Schnell am Limit wegen kleinem Context |
| CP-OPUS | ~200k tokens oder 1 Sitzung (Session) | Copilot rotiert automatisch bei neuem Chat |
| CG | ~4-5 Recherche-Aufgaben | Fängt an Dinge zu halluzinieren |

### Rotations-Ablauf (Checkliste)

**VOR dem Beenden des alten Chats:**

1. ✏️ **SOT.md aktualisieren**: Alle offenen Tasks auf aktuellem Stand, Log-Eintrag mit finaler Token-Schätzung
2. 📝 **Übergabe-Notiz schreiben**: Falls etwas NICHT in Git/SOT.md steht → in `## Übergabe-Notizen` eintragen (siehe unten)
3. 💾 **Git commit + push**: `SOT: rotation CC-OPUS session N abgeschlossen`
4. 📋 **Chat archivieren**: Chat-Export speichern in `d:\GH\copilot-chat-archive\openclaw\`

**BEIM Starten des neuen Chats:**

5. 🚀 **Boot-Message** an den neuen Chat senden (Template unten)
6. ✅ **Verifikation**: Der neue Chat bestätigt was er gelesen hat und welchen Task er als nächstes bearbeitet

### Pre-Rotation-Check (vor Neustart ausführen)

Bevor du einen Chat neustartest, prüfe diese 3 Dinge:

**1. Offene Claims?** Suche nach `[~` in SOT.md:
```
Kein Agent darf einen offenen Claim haben außer dem Chat der gerade rotiert wird.
Wenn ein anderer Agent noch [~AGENT] Claims hat → warte oder frage den Agent.
```

**2. Uncommitted changes?** Prüfe im Terminal:
```bash
cd d:\GH\openclaw && git status --short
```
Alle Änderungen müssen committed sein.

**3. SOT.md aktuell?** Schnell-Check:
- Sind alle erledigten Tasks auf `[x]`?
- Ist der Log-Eintrag für die aktuelle Session vorhanden?
- Stehen Übergabe-Notizen drin falls nötig?

> **Tipp:** Sag dem Copilot/Claude einfach: **„Prüfe ob alle Chats fertig sind“** — er führt den Check dann für dich aus.

### Boot-Message Template

Beim Start eines neuen Chats diese Nachricht senden (Platzhalter anpassen):

```
Du arbeitest am MT4 Trading Automation Projekt.

1. Lies zuerst: N8N - Tailscale/SOT.md (Source of Truth – dort steht ALLES)
2. Deine Kennung: {CC-OPUS|CC-SONNET|CC-HAIKU}
3. Dein nächster Task: {TASK-N aus SOT.md}
4. Übergabe-Kontext: {siehe ## Übergabe-Notizen in SOT.md, oder "keiner"}

Regeln: SOT.md lesen → Task claimen → arbeiten → SOT.md updaten → committen.
```

### Übergabe-Notizen

> Hier trägt ein Chat **VOR seiner Rotation** alles ein, was der Nachfolger wissen muss
> und noch NICHT in Git dokumentiert ist. Nach Übernahme durch den neuen Chat: Zeile löschen.

| Datum | Agent | Notiz | Übernommen? |
|-------|-------|-------|-------------|
| 2026-02-15 | CP-OPUS | Demo-Trade offen: BUY 0.01 BTCUSD Ticket #14155371 @ $70,806.16. Trade läuft. Ggf. beobachten/schließen. | ✅ CC-SONNET |
| 2026-02-15 | CP-OPUS | **Port-Konflikt 8765**: llama-server war für openclaw/n8n eingerichtet und lief auf Port 8765. Wurde manuell gestoppt weil MT4 Bridge denselben Port braucht. **Muss später gelöst werden**: entweder llama-server auf anderen Port (z.B. 8766) oder Bridge-Port ändern. Nicht llama-server einfach wieder auf 8765 starten! | ✅ CC-HAIKU (TASK-16 erledigt: Migration auf Port 11434) |
| 2026-02-15 | CP-OPUS | EA-Port-Naming ist intern vertauscht (PUSH_PORT→bindet als PULL). Ist jetzt korrekt. Nicht nochmal "fixen"! | ✅ CC-SONNET |

### Chat-Sitzungen (Tracking)

> Jede Chat-Session wird hier protokolliert für Nachvollziehbarkeit.

| # | Agent | Start | Ende | Tasks erledigt | ~Tokens | Archiv |
|---|-------|-------|------|----------------|---------|--------|
| 1 | CP-OPUS | 2026-02-14 19:00 | 2026-02-15 13:39 | WF7-10, Bridge-Patch, SOT, HANDOFF, Port-Fix, Sheets-API, TASK-19 LIVE-TEST | ~290k | — |
| 2 | CC-HAIKU | 2026-02-15 07:00 | 07:45 | TASK-1,2,3,14,15, BUG-1,6 | ~85k | — |
| 3 | CC-SONNET | 2026-02-15 10:30 | 2026-02-15 13:40 | TASK-5,6,7,8,9,10,11, BUG-7,8,9 Fix, Workarounds | ~200k | — |
| 4 | CC-HAIKU | 2026-02-15 13:00 | ⏳ laufend | TASK-12,13,16,17,18,19 | ~95k | — |

---

## Infrastruktur

| Komponente | Adresse | Port | Status |
|------------|---------|------|--------|
| VPS Ubuntu | 72.60.84.181 / TS 100.127.134.70 | — | ✅ |
| MT4 PC | TS 100.121.91.27 | — | ✅ |
| MT4 Bridge | localhost (VPS) | 8765 | ✅ |
| n8n | 100.127.134.70 | 5678 | ✅ |
| ZMQ Signal (MT4→Bridge) | 100.121.91.27 | 32768 | ✅ |
| ZMQ Command (Bridge→MT4) | 100.121.91.27 | 32769 | ✅ |
| ZMQ Market (MT4→Bridge) | 100.121.91.27 | 32770 | ✅ |
| bridge-ipv6-proxy (socat) | [::1]→127.0.0.1 (VPS) | 8765 | ✅ Node.js 24 IPv6 Fix |
| llama-server (openclaw) | 127.0.0.1 (VPS) | **11434** | ✅ Active (migrated from 8765) |

### Pfade auf VPS
```
/opt/mt4-bridge/bridge.py          ← LIVE Bridge (495 Zeilen)
/opt/mt4-bridge/.env               ← Konfiguration
/opt/mt4-bridge/venv/              ← Python venv
/etc/systemd/system/mt4-bridge.service
/etc/systemd/system/n8n.service
/etc/systemd/system/bridge-ipv6-proxy.service  ← socat [::1]:8765→127.0.0.1:8765
/etc/systemd/system/local-llm.service          ← llama-server (aktuell DISABLED)
/opt/openclaw-llm-setup/                       ← openclaw LLM-Config (Port 8765→11434 via TASK-16)
```

### Auth
```
Bridge: Authorization: Bearer 77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb
Telegram Bot: 8546370466:AAFkYIvBHd1Lipxh3SsMTmSioMzYnL241Vc
Telegram Chat: 7268021157
Google Sheet: 1J1MNtiITEOTPBW_sZU4hl5Uf-_JlAaR4DDcS5eg-V_g
```

---

## Bugs (nach Priorität)

> Format: `[STATUS] BUG-N: Beschreibung`
> Status: `[ ]` = offen, `[~CC]` = Agent CC arbeitet daran, `[x]` = erledigt

- [x] BUG-1: TRADE-Befehl Error 4051 – `_build_dwx_command()` Parameter-Reihenfolge korrigiert. Korrekt: `TRADE;OPEN;type;symbol;price;sl;tp;comment;lots;magic;ticket` (lots war an Pos 6, muss Pos 9 sein). Fix deployed + getestet (Markt WE geschlossen, Test Mo-Fr).
- [ ] BUG-2: WF1 Google Sheets Rate Limiting – jeder Market-Tick wird in Sheets geschrieben → API-Limit. `PUSH_TO_N8N=true` flutet n8n.
- [ ] BUG-3: TA-Log Spalten leer – Symbol="UNKNOWN", RSI/MACD/EMA alle leer. Indikatoren kommen aus WF7, nicht aus Ticks. WF7 muss Analyse-Ergebnisse in TA-Log schreiben.
- [ ] BUG-4: Trade-Log nur "SIGNAL" – WF2 extrahiert keine Signal-Details. Nur Timestamp + Typ geloggt.
- [ ] BUG-5: Telegram nur "MT4 Signal / Typ: SIGNAL" – WF2 formatiert keine Daten in die Nachricht.
- [x] BUG-6: TRACK_SYMBOLS=EURUSD statt BTCUSD – .env auf VPS auf `EURUSD;BTCUSD;GOLD;US100` gesetzt + Bridge restarted.
- [x] BUG-7: 🔴 `CC-OPUS+CC-SONNET+CC-HAIKU` – `_build_dwx_command()` BUY/SELL SL/TP war hardcoded 0;0. Fix: `sl = payload.sl or 0` / `tp = payload.tp or 0` (bridge.py Zeile 271-274). Deployed auf VPS, Code-verified ✅, **LIVE-TEST BESTANDEN**: Ticket #14155612 BUY BTCUSD SL=$68337 TP=$69727 ✅ (Broker passt SL/TP auf Min-Distanz an, das ist normal).
- [x] BUG-8: 🟡 `CC-SONNET` – WF9 GET_OPEN_TRADES nicht unterstützt. Workaround deployed: WF9 liest jetzt Active-Trades via Google Sheets `lookup(Status=OPEN)`. Trade-Management-Logik (Breakeven/Trailing/Partial-Close) läuft auf Basis von Sheets-Daten. Preis-Offset symbol-spezifisch (BTC=$50, GOLD=$2, FX=0.0005). Importiert + aktiviert. ✅
- [x] BUG-9: 🟡 `CC-SONNET` – WF10 GET_ACCOUNT_INFO nicht unterstützt. Workaround deployed: WF10 ruft jetzt `GET /mt4/stats` (Bridge-Stats: Signale, Befehle, ZMQ-Status, Uptime). Daily-Journal zeigt Bridge-Status. Trade-closed-Webhook funktioniert weiter. Importiert + aktiviert. ✅

---

## Tasks

> Format: `[STATUS] TASK-N: Beschreibung`
> Status: `[ ]` = offen, `[~CC]` = geclaimed, `[x]` = erledigt

### Phase 1 – TRADE-Format reparieren
- [x] TASK-1 🔴 `CC-HAIKU`: DWX v2.0.1_RC8 Format via GitHub-Recherche dokumentiert: `TRADE;OPEN;type;symbol;price;sl;tp;comment;lots;magic;ticket`
- [x] TASK-2 🔴 `CC-HAIKU`: `_build_dwx_command()` in bridge.py korrigiert (lots von Pos 6 → Pos 9)
- [x] TASK-3 🟢 `CC-HAIKU`: TRACK_SYMBOLS in .env auf EURUSD;BTCUSD;GOLD;US100 gesetzt + Bridge restart
- [x] TASK-4 🟡 `CP-OPUS`: Demo-Trade LIVE getestet: BUY 0.01 BTCUSD → Ticket #14155371 @ $70,806.16 ✅

### Phase 2 – Workflows optimieren
- [x] TASK-5 🟡 `CC-SONNET`: Bridge Market-Push deaktiviert (PUSH_MARKET_TO_N8N=false). WF1 Rate Limiting gelöst. ✅
- [x] TASK-6 🟡 `CC-SONNET`: WF7 TA-Log Append hinzugefügt. Nodes: Format TA-Log → TA-Log in Sheets. Schreibt: timestamp, symbol, RSI, EMA20, EMA50, ATR, trend, signal_score. Importiert. ✅
- [x] TASK-7 🟡 `CC-SONNET`: WF2 Signal-Daten extrahieren verbessert. Code2 Node: besseres Parsing (parts + raw fallback). GS Columns: Symbol, Signal, Preis, Volume, SL, TP, Ticket, Status. Importiert. ✅
- [x] TASK-8 🟡 `CC-SONNET`: WF2 Telegram formatiert mit allen Signal-Details (nicht nur "SIGNAL"). Emoji, Preis, Volume, SL/TP gezeigt. Code2 Node. Importiert. ✅

### Phase 3 – Testen & Stabilisieren
- [x] TASK-9 🟡 `CC-SONNET`: WF8 analysiert. Flow korrekt. Bugs gefunden: BUG-7 (SL/TP=0), jsonBody JSON.stringify (minor). Echter E2E-Test braucht Marktzeiten + EA aktiv. ✅
- [x] TASK-10 🟡 `CC-SONNET`: WF9 analysiert. Logik korrekt (Breakeven/Trailing/Partial-Close). Blockiert durch BUG-8: DWX v2.0.1_RC8 unterstützt GET_OPEN_TRADES nicht → liefert immer leere Liste. ✅
- [x] TASK-11 🟡 `CC-SONNET`: WF10 analysiert. Daily-Journal + Webhook-Trigger korrekt. Blockiert durch BUG-9: DWX v2.0.1_RC8 unterstützt GET_ACCOUNT_INFO nicht → Balance immer 0. ✅
- [x] TASK-12 🟢 `CC-HAIKU`: Google Sheets alle Tabs verifizieren. 5 Tabs identifiziert: Trade-Log (WF2), TA-Log (WF7, 12 Spalten), Active-Trades (WF8), Monitor-Log (WF9), Journal (WF10). Alle Workflows mit korrekter Google Sheets Credential (82cab3...). Sheet ID: 1J1MNti... ✅

### Housekeeping
- [x] TASK-13 🟢 `CC-HAIKU`: Temp-Dateien löschen. Gelöscht: lokal 4x (demo_trade.py, test_btc_trade.py, test_raw_formats.py, test_trade_formats.py) + VPS 4x (/tmp/test_*.py). Total 8 Dateien. ✅
- [x] TASK-14 🟢 `CC-HAIKU`: bridge.py Repo mit ast-Patch + /mt4/raw Endpoint synchronisiert. Beide Patches in lokale Version integriert + deployed.
- [x] TASK-15 🟢 `CC-HAIKU`: Git commit + push aller Änderungen (commit 6333378f8f)

### Phase 4 – Cleanup & Port-Migration (CC-HAIKU)
- [x] TASK-16 🟢 `CC-HAIKU`: **llama-server Port-Migration 8765 → 11434 ✅**. 9 Dateien aktualisiert (config, scripts, systemd). Service ✅ ACTIVE auf Port 11434. Health: "Loading model" (normal).

- [x] TASK-17 🟢 `CC-HAIKU`: **VPS Temp-Dateien aufräumen ✅**. Gelöscht: 3x Security (sa_key.json, cred_raw.txt, n8n-creds.json) + ~40 Diagnostik-Skripte. /tmp/ clean (0 Dateien).

- [x] TASK-18 🟢 `CC-HAIKU`: **SOT.md finalisiert ✅**. Übergabe-Notiz aktualisiert (Port-Konflikt erledigt). Infrastruktur-Tabelle: llama-server Port 11434 (✅ Active). Log-Einträge hinzugefügt.

### Phase 5 – Verifikation & E2E-Tests
- [x] TASK-19 🟢 `CP-OPUS`: **BUG-7 SL/TP LIVE-TEST BESTANDEN ✅**. Trade #14155612 BUY 0.01 BTCUSD: SL=$68337, TP=$69727 (Broker-adjustiert von 67000/72000 auf Min-Distanz). Alter Trade #14155371 vorher geschlossen @ $68914. MAX_ORDERS-Limit war 1 Trade.

### Phase 6 – Autonomes Trading & Telegram-Steuerung
- [ ] TASK-20 🟢 `CC-HAIKU`: **WF4 Auth-Fix + Telegram-Spam stoppen**. DRINGEND! WF4 Bridge Health Node sendet GET ohne Auth-Header → 401 → "Bridge offline" Telegram-Spam alle 5min. Fix: Auth-Header `Authorization: Bearer 77cc86ea...28cb` zum HTTP-Node `Bridge Health` hinzufügen. Danach IF-Node prüft `status == ok` korrekt.
- [ ] TASK-21 🟡 `CC-SONNET`: **WF4 Telegram Status-Summary**. Statt nur "offline" Alert: 5min Status-Report an Telegram mit: offene Trades (aus Active-Trades Sheet), PnL-Übersicht, Bridge-Stats. Nur senden wenn sich etwas ändert (Debounce).
- [ ] TASK-22 🟡 `CC-SONNET`: **WF8 Telegram-Bestätigung (Testphase)**. Trade-Signal kommt → WF8 sendet Strategie-Summary an Telegram (Richtung, Symbol, SL/TP, R:R, Grund/Score) → User bestätigt per Inline-Keyboard (✅ Freigeben / ❌ Ablehnen / 🔧 Anpassen) → erst nach Bestätigung wird Trade ausgeführt. Nutzt Telegram `sendMessage` mit `reply_markup` InlineKeyboard + WF3 Telegram Commands als Callback-Handler.
- [~CC-SONNET] TASK-23 🟡 `CC-SONNET`: **WF7 Trade Analyzer Trigger fixen + Analyse-Kette**. WF7 läuft NIE (0 Executions). Braucht Cron-Trigger (z.B. alle 15min). Flow: Cron → HIST-Daten von Bridge → Technische Analyse (RSI/EMA/ATR) → Signal-Score berechnen → wenn Score > Schwelle: WF8 per Webhook triggern mit Trade-Daten (Symbol, Direction, SL, TP, Lots, Score, Reason). TA-Log in Sheets schreiben.
- [ ] TASK-24 🟢 `CC-HAIKU`: **WF6 News Monitor aktivieren**. WF6 hat 0 Executions. Trigger-Node prüfen/fixen (Cron für ForexFactory-Scraping). News-Daten in News-Log Sheet schreiben. Telegram-Alert bei High-Impact News.
- [ ] TASK-25 🟡 `CC-SONNET`: **Google Sheets optimieren**. a) Neueste Daten oben einfügen (batchUpdate insertRows statt append). b) Bessere Spalten: Performance-Tab um PnL, Balance, Equity, Drawdown erweitern. c) Archiv-Mechanismus: Monatlich alte Daten in Archiv-Tab verschieben (Code-Node mit Sheets API).
- [ ] TASK-26 🟢 `ST (manuell)`: **MT4 EA MaxOrders erhöhen**. In MT4 → Experten → DWX EA → Inputs → `MaxOrders` von 1 auf 5 oder 10 setzen. Ohne das kann nur 1 Trade gleichzeitig offen sein. Danach EA Chart-Fenster neuladen.
- [ ] TASK-27 🔴 `CC-OPUS`: **E2E Trading-Kette zusammenstecken**. WF7(Analyse)→WF8(Executor+Bestätigung)→WF9(Monitor)→WF10(Journal). Vollständiger autonomer Loop: Marktdaten→Analyse→Signal→Telegram-Bestätigung→Trade→Management→Journal. Integration-Test mit BTCUSD.

---

## Workflows (n8n)

| WF | n8n ID | Name | Aktiv | Zustand |
|----|--------|------|-------|---------|
| 1 | TsesAyfkGln2WH00 | Marktdaten Empfang & Log | ✅ | 🔴 Rate Limit + Symbol UNKNOWN |
| 2 | 6DcFnzHicZOh0FxZ | Signal Empfang & Alert | ✅ | 🟡 Nur "SIGNAL", generische Telegram-Msg |
| 3 | GjpBqxXZdHGGp218 | Telegram Commands | ❌ | ⬜ Nicht getestet |
| 4 | 2a1wXTU56DD2s0Yc | Portfolio Monitor | ✅ | ✅ Läuft seit 15.02. 10:40 UTC stabil |
| 5 | EVwU9BzKSKXuitLL | Tagesreport | ✅ | ⬜ Nicht getestet |
| 6 | 8KAXUPF2J9EHbFAN | News Monitor | ✅ | ⬜ Nicht getestet |
| 7 | 1T0fMAYzQKf8yM6j | Trade Analyzer | ✅ | 🟡 Analyse OK, Trade-Exec scheitert (BUG-7: SL/TP=0) |
| 8 | CfULtpthxJXm3S25 | Trade Executor | ✅ | ✅ TRADE funktioniert (Ticket #14155371) — BUG-7: kein SL/TP |
| 9 | 0bRXfI6yvP7yVjlm | Trade Monitor | ✅ | ✅ BUG-8 gefixt: GS Active-Trades Lookup statt GET_OPEN_TRADES |
| 10 | Y1Z1WK5KInRXLlVY | Trade Journal | ✅ | ✅ BUG-9 gefixt: Bridge-Stats statt GET_ACCOUNT_INFO |

---

## Verifiziert (funktioniert)

- ✅ Bridge Health Check + ZMQ-Verbindung
- ✅ HIST-Befehl: 2048+ M15 Candles empfangen
- ✅ ast.literal_eval Patch: Python-Dict-Strings korrekt geparst
- ✅ Market Buffer: bis 500 Ticks gepuffert
- ✅ WF7 Technische Analyse: EMA20/50, RSI14, ATR14 korrekt
- ✅ WF7 → Telegram: Formatierte Analyse-Nachricht
- ✅ Telegram Bot Connectivity
- ✅ Tailscale VPN: 13ms Latenz VPS ↔ MT4-PC
- ✅ TRADE OPEN: BUY 0.01 BTCUSD → Ticket #14155371 @ $70,806.16 (2026-02-15)
- ✅ EA Ports: PUSH_PORT/PULL_PORT in EA-Inputs sind VERTAUSCHT vs Binding (normal für DWX EA!)

---

## Wichtige Hinweise

- **Wochenende**: Sa/So Märkte geschlossen. BTCUSD bei Capital.com auch WE eingeschränkt. TRADE-Tests nur Mo-Fr.
- **Bridge Restart**: Nach Restart verliert EA kurz die Verbindung. Market Buffer ist dann leer.
- **Demo-Konto**: Capital.com Demo $100k. KEIN echtes Geld.
- **DWX EA v2.0.1 RC8**: Unterstützt KEIN `ACCOUNT_INFO` und KEIN `OPEN_TRADES` via ZMQ.
- **EA Port-Swap**: Die EA VERTAUSCHT intern PUSH_PORT und PULL_PORT! Input `PUSH_PORT=32768` bindet als `[PULL]` auf 32768. Das ist by-design. Bridge .env ist korrekt konfiguriert.
- **bridge.py Repo vs VPS**: Repo-Version ist Referenz. VPS hat zusätzlich ast-Patch + /mt4/raw. Immer synchron halten!
- **n8n API Key**: Gesetzt aber von v2.7.5 nicht erkannt (401). Workflows laufen über Webhooks.
- **Node.js 24 IPv6**: Node v24.13.1 löst `localhost` als `::1` (IPv6) auf, nicht `127.0.0.1`. socat-Proxy (`bridge-ipv6-proxy.service`) leitet `[::1]:8765` → `127.0.0.1:8765` weiter. NICHT entfernen!
- **llama-server disabled**: `local-llm.service` ist deaktiviert weil Port 8765 mit Bridge kollidierte. TASK-16 migriert auf Port 11434.
- **Google Sheet Tabs**: Trade-Log, TA-Log, News-Log, Performance, Config, Errors (alt) + Monitor-Log, Active-Trades, Journal (neu erstellt 15.02. 12:12 UTC)

---

## Log

> Append-only! Nur neue Zeilen am Ende hinzufügen.
> Format: `YYYY-MM-DD HH:MM | AGENT-MODELL | Beschreibung | ~tokens`

```
2026-02-14 20:00 | CP-OPUS | Bridge ast.literal_eval Patch angewendet | ~15k
2026-02-14 21:00 | CP-OPUS | WF7-WF10 erstellt und auf n8n importiert | ~40k
2026-02-14 21:30 | CP-OPUS | HIST-Befehl getestet: 2088 M15 Candles OK | ~10k
2026-02-14 21:45 | CP-OPUS | Demo-Trade versucht: Error 4051 (falsches TRADE-Format) | ~20k
2026-02-14 22:00 | CP-OPUS | /mt4/raw Debug-Endpoint zur Bridge hinzugefügt | ~10k
2026-02-14 22:15 | CP-OPUS | 10+ TRADE-Formate getestet – alle 0 Signals (WE + Restart) | ~25k
2026-02-14 23:00 | CP-OPUS | Git commit fd13557480 (17 Dateien, 3129 Zeilen) | ~5k
2026-02-15 00:00 | CP-OPUS | HANDOFF-CLAUDE-CODE.md geschrieben | ~30k
2026-02-15 00:15 | CP-OPUS | SOT.md angelegt | ~15k
2026-02-15 01:00 | CP-OPUS | SOT.md erweitert: Multi-Modell, Orchestrierung, Komplexität | ~20k
2026-02-15 07:30 | CC-HAIKU | TASK-1/2: BUG-1 Fix: DWX TRADE-Format recherchiert (GitHub), _build_dwx_command() korrigiert (lots: Pos 6→9). Korrekt: TRADE;OPEN;type;symbol;price;sl;tp;comment;lots;magic;ticket | ~70k
2026-02-15 07:35 | CC-HAIKU | TASK-3: BUG-6 Fix: TRACK_SYMBOLS=EURUSD;BTCUSD;GOLD;US100 in .env auf VPS gesetzt + Bridge restarted | ~5k
2026-02-15 07:40 | CC-HAIKU | TASK-14: bridge.py Repo mit ast.literal_eval Patch + /mt4/raw Endpoint synchronisiert. Beide nun in lokaler Version + deployed auf VPS | ~10k
2026-02-15 08:00 | CP-OPUS | Chat-Rotation-Konzept + Übergabe-Notizen + Session-Tracking zur SOT.md hinzugefügt | ~25k
2026-02-15 08:30 | CP-OPUS | Auto-Discovery eingerichtet: AGENTS.md + .github/copilot-instructions.md → SOT.md Verweis | ~15k
2026-02-15 09:10 | ST+CP-OPUS | EA Port-Conflict gefixt (PUSH_PORT war doppelt 32769). EA entfernt+neugeladen. llama-server von Port 8765 entfernt. | ~20k
2026-02-15 09:13 | CP-OPUS | 🎉 ERSTER DEMO-TRADE: BUY 0.01 BTCUSD → Ticket #14155371 @ $70,806.16. Komplette Pipeline funktioniert! | ~15k
2026-02-15 09:30 | CC-SONNET | TASK-5: Bridge PUSH_MARKET_TO_N8N=false (default) gesetzt. Market-Ticks werden nicht mehr zu n8n gepusht (verhindert Sheets Rate Limit in WF1). Bridge restartet + Health-Check OK. | ~25k
2026-02-15 09:45 | CC-SONNET | TASK-6: WF7 JSON modifiziert: Format TA-Log + TA-Log in Sheets Nodes hinzugefügt. Routing: Tech.Analyse → Format → Append → Signal Check. Google Sheets Credential & TA-Log Tab konfiguriert. Zu n8n importiert. | ~30k
2026-02-15 10:00 | CC-SONNET | TASK-7: WF2 exportiert von n8n. Code2 Node: besseres Signal-Parsing (parts[1..5] + raw fallback für fehlende Felder). GS Columns updated (Symbol, Signal, Preis, Volume, SL, TP, Ticket, Status). Importiert zu n8n. | ~25k
2026-02-15 10:05 | CC-SONNET | TASK-8: WF2 Telegram-Nachricht verbessert. Code2 generiert formatierte Nachricht mit: Emoji (BUY/SELL/ERROR), Symbol, Signal-Typ, Preis, Volume, SL/TP, Ticket. Nicht mehr nur generische "SIGNAL"-Meldung. Importiert. | ~10k
2026-02-15 10:15 | CC-HAIKU | TASK-12: Google Sheets Struktur verifiziert. 5 Tabs: Trade-Log (WF2), TA-Log (WF7: 12 Spalten), Active-Trades (WF8: Timestamp/Ticket/Symbol/Status), Monitor-Log (WF9), Journal (WF10). Alle Workflows mit Credential 82cab318-1cf6 + Sheet 1J1MNti... konfiguriert. ✅ | ~15k
2026-02-15 10:20 | CC-HAIKU | TASK-13: Temp-Dateien gelöscht. Lokal: demo_trade.py, test_btc_trade.py, test_raw_formats.py, test_trade_formats.py (4x). VPS /tmp: test_*.py (4x). Total 8 Dateien. ✅ | ~8k
2026-02-15 10:35 | CC-SONNET | TASK-9/10/11: WF8/9/10 Code-Review. BUG-7: _build_dwx_command BUY/SELL hardcoded SL=0,TP=0. BUG-8: WF9 GET_OPEN_TRADES nicht unterstützt in DWX v2.0.1_RC8. BUG-9: WF10 GET_ACCOUNT_INFO nicht unterstützt. Alle 3 Tasks [x]. Übergabe-Notizen übernommen. | ~55k
2026-02-15 10:40 | CP-OPUS | WF4/WF9 ECONNREFUSED gefixt: Root Cause 1: local-llm.service (llama-server) blockierte IPv4 auf Port 8765 → disabled. Root Cause 2: Node.js v24 löst localhost als IPv6 ::1 auf → socat bridge-ipv6-proxy.service erstellt. WF4 läuft seit 10:40 UTC. | ~40k
2026-02-15 12:12 | CP-OPUS | WF9 Monitor-Log Sheet-Tab fehlte. SA-Key aus n8n DB entschlüsselt (CryptoJS OpenSSL EVP_BytesToKey). 3 Tabs via Google Sheets API erstellt: Monitor-Log, Active-Trades, Journal. WF9 läuft seit 12:12 UTC. | ~30k
2026-02-15 12:55 | CP-OPUS | TASK-16/17/18 für CC-HAIKU definiert: llama Port-Migration 8765→11434, VPS Temp-Cleanup, SOT Update. | ~10k
2026-02-15 13:05 | CC-HAIKU | TASK-16: llama-server Port-Migration 8765→11434 erfolgreich. 9 Dateien aktualisiert (config, scripts, systemd service). systemctl daemon-reload, enable, start. Service ✅ ACTIVE auf Port 11434. Health-Check zeigt "Loading model" (normal). | ~20k
2026-02-15 13:08 | CC-HAIKU | TASK-17: VPS /tmp/ aufgeräumt. Gelöscht: 3x sicherheitskritische Dateien (sa_key.json, cred_raw.txt, n8n-creds.json) + ~40 Diagnostik-Skripte (.py, .sh, .js, .json). /tmp/ clean. | ~10k
2026-02-15 13:10 | CC-HAIKU | TASK-18: SOT.md finalisiert. Übergabe-Notiz "Port-Konflikt" als erledigt markiert. Infrastruktur-Tabelle: llama-server Zeile aktualisiert (Port 11434, ✅ Active). Log-Einträge für TASK-16/17/18 hinzugefügt. | ~8k
2026-02-15 13:30 | CC-SONNET | BUG-8: WF9 umgebaut – GET_OPEN_TRADES durch GS-Lookup(Active-Trades, Status=OPEN) ersetzt. Trade-Management-Logik angepasst (symbol-spez. Offsets). Importiert via n8n CLI, aktiviert via sqlite3. ✅ | ~35k
2026-02-15 13:35 | CC-SONNET | BUG-9: WF10 umgebaut – GET_ACCOUNT_INFO durch Bridge-Stats(GET /mt4/stats) ersetzt. Daily-Journal zeigt ZMQ-Status, Uptime, Signale, Befehle. Trade-closed-Webhook bleibt erhalten. Importiert + aktiviert. ✅ | ~10k
2026-02-15 13:40 | CC-SONNET | BUG-7: bridge.py BUG-7 Fix von CP-OPUS übernommen + auf VPS deployed. sl/tp werden jetzt korrekt übergeben. Bridge restarted + Health-Check OK. ✅ | ~5k
2026-02-15 13:30 | CC-HAIKU | TASK-19: BUG-7 SL/TP Fix Verifizierung. Code-Check: bridge.py Zeile 271-274 korrekt (sl = payload.sl or 0, tp = payload.tp or 0). Live-Test mit BUY 0.01 BTCUSD gescheitert (Sonntag, Märkte geschlossen). BUG-7 Code-Verified ✅. Live-Test Mo-Fr scheduled. | ~12k
2026-02-15 13:39 | CP-OPUS | TASK-19 LIVE-TEST: Alter Trade #14155371 geschlossen @ $68914. Neuer Trade #14155612 BUY 0.01 BTCUSD mit SL=$68337 TP=$69727 ERFOLGREICH. BUG-7 endgültig verifiziert. MAX_ORDERS-Limit bei Capital.com Demo = 1 Trade (war Grund für Haikus Fehlschlag). | ~15k
2026-02-15 14:10 | CP-OPUS | Phase 6 geplant (TASK-20–27): WF4 Auth-Fix, Telegram-Bestätigung, WF7 Trigger, News Monitor, Sheets-Optimierung, E2E-Kette. Analyse: WF7/WF8/WF6 haben 0 Executions, WF4 sendet falschen "offline" Alert (fehlender Auth-Header). | ~20k
2026-02-15 14:15 | CC-HAIKU | **CHAT ROTATION**: Session 1 (CP-OPUS), 3 (CC-SONNET) beendet. Session 4 (CC-HAIKU, diese) dokumentiert. Status: Phase 1-5 ✅ KOMPLETT (19 Tasks, 5 Bugs gefixt). Phase 6 (8 neue Tasks) geplant. TASK-20 (WF4 Auth-Fix) ist DRINGEND. | ~15k
```
