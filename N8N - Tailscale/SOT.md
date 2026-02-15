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
| 2026-02-15 | CP-OPUS | Demo-Trade offen: BUY 0.01 BTCUSD Ticket #14155371 @ $70,806.16. Trade läuft. Ggf. beobachten/schließen. | ❌ |
| 2026-02-15 | CP-OPUS | llama-server lief auf Port 8765 und blockierte Bridge — wurde manuell gestoppt. Falls er wiederkommt: `kill $(lsof -ti:8765)` vor Bridge-Restart | ❌ |
| 2026-02-15 | CP-OPUS | EA-Port-Naming ist intern vertauscht (PUSH_PORT→bindet als PULL). Ist jetzt korrekt. Nicht nochmal "fixen"! | ❌ |

### Chat-Sitzungen (Tracking)

> Jede Chat-Session wird hier protokolliert für Nachvollziehbarkeit.

| # | Agent | Start | Ende | Tasks erledigt | ~Tokens | Archiv |
|---|-------|-------|------|----------------|---------|--------|
| 1 | CP-OPUS | 2026-02-14 19:00 | laufend | WF7-10, Bridge-Patch, SOT, HANDOFF | ~220k | — |
| 2 | CC-HAIKU | 2026-02-15 07:00 | 07:45 | TASK-1,2,3,14,15, BUG-1,6 | ~85k | — |

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

### Pfade auf VPS
```
/opt/mt4-bridge/bridge.py          ← LIVE Bridge (495 Zeilen)
/opt/mt4-bridge/.env               ← Konfiguration
/opt/mt4-bridge/venv/              ← Python venv
/etc/systemd/system/mt4-bridge.service
/etc/systemd/system/n8n.service
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
- [ ] TASK-6 🟡 `CC-SONNET`: WF7 → Google Sheets: Analyse-Ergebnisse (RSI, EMA, ATR) in TA-Log schreiben
- [ ] TASK-7 🟡 `CC-SONNET`: WF2 Signal-Daten korrekt extrahieren und in Trade-Log schreiben
- [ ] TASK-8 🟡 `CC-SONNET`: WF2 Telegram-Nachricht mit Signal-Details formatieren

### Phase 3 – Testen & Stabilisieren
- [ ] TASK-9 🟡 `CC-SONNET`: WF8 Trade Executor End-to-End testen
- [ ] TASK-10 🟡 `CC-SONNET`: WF9 Trade Monitor mit offenem Trade testen
- [ ] TASK-11 🟡 `CC-SONNET`: WF10 Trade Journal nach Trade-Close prüfen
- [ ] TASK-12 🟢 `CC-HAIKU`: Google Sheets alle Tabs verifizieren (Trade-Log, TA-Log, Active-Trades, etc.)

### Housekeeping
- [ ] TASK-13 🟢 `CC-HAIKU`: Temp-Dateien löschen (lokal: d:\GH\demo_trade.py etc., VPS: /tmp/test_*.py etc.)
- [x] TASK-14 🟢 `CC-HAIKU`: bridge.py Repo mit ast-Patch + /mt4/raw Endpoint synchronisiert. Beide Patches in lokale Version integriert + deployed.
- [x] TASK-15 🟢 `CC-HAIKU`: Git commit + push aller Änderungen (commit 6333378f8f)

---

## Workflows (n8n)

| WF | n8n ID | Name | Aktiv | Zustand |
|----|--------|------|-------|---------|
| 1 | TsesAyfkGln2WH00 | Marktdaten Empfang & Log | ✅ | 🔴 Rate Limit + Symbol UNKNOWN |
| 2 | 6DcFnzHicZOh0FxZ | Signal Empfang & Alert | ✅ | 🟡 Nur "SIGNAL", generische Telegram-Msg |
| 3 | GjpBqxXZdHGGp218 | Telegram Commands | ❌ | ⬜ Nicht getestet |
| 4 | 2a1wXTU56DD2s0Yc | Portfolio Monitor | ✅ | ⬜ Nicht getestet |
| 5 | EVwU9BzKSKXuitLL | Tagesreport | ✅ | ⬜ Nicht getestet |
| 6 | 8KAXUPF2J9EHbFAN | News Monitor | ✅ | ⬜ Nicht getestet |
| 7 | 1T0fMAYzQKf8yM6j | Trade Analyzer | ✅ | 🟡 Analyse OK, Trade-Exec scheitert |
| 8 | CfULtpthxJXm3S25 | Trade Executor | ✅ | ✅ TRADE funktioniert (Ticket #14155371) |
| 9 | 0bRXfI6yvP7yVjlm | Trade Monitor | ✅ | ⬜ Ungetestet |
| 10 | Y1Z1WK5KInRXLlVY | Trade Journal | ✅ | ⬜ Ungetestet |

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
```
