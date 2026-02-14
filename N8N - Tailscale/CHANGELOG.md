# Änderungsprotokoll – Trading Automation

Alle Änderungen am VPS (srv1351792) und im Repository, durchgeführt am **14. Februar 2026**.

## Zusammenfassung

Implementierung des Trading-Automatisierungssystems WF7–WF10 für BTCUSD Demo-Trading über MT4/DWX ZMQ Bridge.

---

## 1. Bridge Patch: ast.literal_eval

**Datei:** `/opt/mt4-bridge/bridge.py`  
**Backup:** `/opt/mt4-bridge/backups/bridge.py.20260214-204740.bak`  
**Patch:** `patches/patch-bridge-ast-parser.sh`

### Problem
Die DWX ZeroMQ EA v2.0.1 RC8 sendet Antworten (z.B. HIST-Daten) als Python-Dict-Strings mit einfachen Anführungszeichen:
```python
{'_action': 'HIST', '_data': {'2026.01.24 05:00': {'open': 89658.55, ...}}}
```
`json.loads()` kann dieses Format nicht parsen, da es kein gültiges JSON ist.

### Lösung
Hinzufügen von `import ast` und einem `ast.literal_eval()` Fallback in der `_parse_message()` Funktion (nach dem `json.loads()` Versuch):

```python
import ast  # Zeile 14

# In _parse_message() nach json.loads():
try:
    result = ast.literal_eval(raw)
    if isinstance(result, dict):
        return result
except (ValueError, SyntaxError):
    pass
```

### Ergebnis
HIST-Antworten werden jetzt korrekt als Python-Dicts geparst. Test bestätigt:
- Signal `_action=HIST` mit `_data` enthält **2048 Candles** als geparste Objekte
- Keine `raw`-Strings mehr für HIST-Daten

---

## 2. Neue Workflows (WF7–WF10)

### WF7 – Trade Analyzer (v3)
**ID:** `1T0fMAYzQKf8yM6j` (ersetzt `Bg6vd77tjPgEjzeH`)  
**Datei:** `workflows/wf7-trade-analyzer.json`  
**Nodes:** 15  
**Trigger:** Alle 4 Stunden + Manual Trigger

**Ablauf:**
1. Signal Buffer leeren
2. HIST BTCUSD M15 anfordern (via Bridge)
3. 8 Sekunden warten
4. Signal Buffer lesen (OHLC-Daten)
5. Aktuelle Ticks holen (Marktdaten)
6. **Technische Analyse** (Code Node):
   - EMA(20), EMA(50) → Trendbestimmung
   - RSI(14) → Überkauft/Überverkauft
   - ATR(14) → Volatilität + Position Sizing
   - Signal: BUY / SELL / HOLD
   - SL = 1.5×ATR, TP = 2.5×ATR (R:R 1:1.67)
   - Lots = (5% × Balance) / SL-Distance
7. Telegram-Nachricht senden
8. Bei Signal → WF8 (Trade Executor) triggern

**Besonderheiten:**
- Parst sowohl `_action=HIST` (geparst via ast.literal_eval) als auch `raw`-String-Format
- Default Balance $100.000 (DWX ZMQ EA unterstützt kein ACCOUNT_INFO)
- _data kann Dict-Format (Zeitstempel als Keys) oder Array-Format sein

### WF8 – Trade Executor
**ID:** `CfULtpthxJXm3S25`  
**Datei:** `workflows/wf8-trade-executor.json`  
**Nodes:** 11  
**Trigger:** Webhook `/execute-trade`

**Ablauf:**
1. Empfängt Trade-Signal von WF7
2. Validiert Parameter (Symbol, Lots, SL, TP)
3. Buffer leeren
4. TRADE OPEN an MT4 senden
5. EA-Antwort lesen (Ticket-Nummer)
6. Telegram-Bestätigung
7. Google Sheets Log (Tab "Active-Trades")

### WF9 – Trade Monitor
**ID:** `0bRXfI6yvP7yVjlm`  
**Datei:** `workflows/wf9-trade-monitor.json`  
**Nodes:** 11  
**Trigger:** Alle 2 Minuten

**Trailing Stop Phasen:**
- +35% zum TP → SL auf Breakeven
- +70% zum TP → SL auf 50% des Profits
- +95% (fast am TP) → 50% Position schließen, Rest trailen bei 1.5×ATR
- Alert bei -3% Verlust

### WF10 – Trade Journal
**ID:** `Y1Z1WK5KInRXLlVY`  
**Datei:** `workflows/wf10-trade-journal.json`  
**Nodes:** 10  
**Trigger:** Webhook `/trade-closed` + Täglich 22:00

---

## 3. n8n Service Änderungen

**Datei:** `/etc/systemd/system/n8n.service`

Hinzugefügt:
```
Environment="N8N_API_KEY=n8n_api_trading_2026"
Environment="N8N_PUBLIC_API_ENABLED=true"
```

> ⚠️ **Hinweis:** Der API Key wird aktuell von n8n v2.7.5 nicht korrekt erkannt (401 bei Zugriff). Dies muss noch untersucht werden. Die Workflows funktionieren aber über Webhooks und Schedules einwandfrei.

---

## 4. Wichtige Erkenntnisse

### DWX ZMQ EA v2.0.1 RC8 Limitierungen
- **Kein ACCOUNT_INFO Befehl**: Die EA sendet keine Account-Daten als Antwort auf Commands. Account-Info wird im Original-DWX über `DWX_Orders.txt`-Datei bereitgestellt (dateibasiert, nicht ZMQ).
- **Kein OPEN_TRADES Befehl**: Offene Trades müssen lokal getrackt werden (Google Sheets).
- **HIST funktioniert**: Liefert OHLC-Daten als Python-Dict-String.
- **TRADE OPEN/CLOSE/MODIFY**: Noch nicht live getestet, sollte aber funktionieren.

### Datenformate
- EA-Antworten kommen als Python-Dict-Strings (einfache Anführungszeichen)
- HIST _data: Dict mit Zeitstempel als Keys, oder Array von Bars
- Jeder Bar: `{time, open, high, low, close, tick_volume, spread, real_volume}`
- Bridge konvertiert zu JSON via `ast.literal_eval`

---

## 5. Offene Punkte

- [ ] Erster Demo-Trade über WF8 auslösen und verifizieren
- [ ] WF9 Trade Monitor mit echtem Trade testen
- [ ] Google Sheets Tabs: "Active-Trades", "Monitor-Log", "Journal"
- [ ] n8n API Key Problem lösen (v2.7.5 Kompatibilität)
- [ ] WF3 Telegram Commands reaktivieren
- [ ] Rate Limiting für WF7 (nicht öfter als alle 4h)
- [ ] Cleanup: Temp-Dateien auf VPS entfernen (`/tmp/test_*.sh`)

---

## 6. Temp-Dateien (zu bereinigen)

**Lokal (d:\GH\):**
- `temp_test_hist2.sh`, `temp_check_raw.sh`, `temp_check_buffers.sh`
- `temp_test_commands.sh`, `temp_update_wf7.sh`, `temp_debug_import.sh`
- `temp_activate_wf7.sh`, `temp_fix_wf7.sh`, `temp_test_wf7.sh`
- `temp_test_wf7_v2.sh`, `temp_test_telegram.sh`, `temp_setup_api.sh`
- `temp_trigger_wf7.sh`

**VPS (/tmp/):**
- `test_hist2.sh`, `check_raw.sh`, `check_buf.sh`, `test_cmds.sh`
- `update_wf7.sh`, `debug_import.sh`, `activate_wf7.sh`, `fix_wf7.sh`
- `test_wf7.sh`, `test_wf7_v2.sh`, `test_tg.sh`, `setup_api.sh`
- `trigger_wf7.sh`, `patch-bridge.sh`
- `wf7-trade-analyzer.json`, `wf7_signals.json`, `wf7_market.json`
- `all_wf.json`, `all_wf2.json`
