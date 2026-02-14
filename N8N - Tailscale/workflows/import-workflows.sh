#!/bin/bash
# ========================================
# Import WF7-WF10 Trading Workflows to n8n
# ========================================
# Erstellt: 2026-02-14
# Beschreibung: Importiert die 4 neuen Trading-Workflows
# WARNUNG: Bestehende Workflows werden NICHT verändert!
# ========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WF_DIR="$SCRIPT_DIR"

echo "========================================="
echo "  n8n Workflow Import - Trading System"
echo "========================================="
echo ""

# Backup bestehender Workflows
echo "[1/5] Backup bestehender Workflows..."
mkdir -p /opt/mt4-bridge/backups
BACKUP_FILE="/opt/mt4-bridge/backups/n8n-workflows-backup-$(date +%Y%m%d-%H%M%S).json"
n8n export:workflow --all --output="$BACKUP_FILE" 2>/dev/null
echo "  ✅ Backup: $BACKUP_FILE"
echo ""

# WF7 - Trade Analyzer
echo "[2/5] Importiere WF7 - Trade Analyzer..."
if [ -f "$WF_DIR/wf7-trade-analyzer.json" ]; then
    n8n import:workflow --input="$WF_DIR/wf7-trade-analyzer.json" 2>&1
    echo "  ✅ WF7 importiert"
else
    echo "  ❌ Datei nicht gefunden: wf7-trade-analyzer.json"
fi
echo ""

# WF8 - Trade Executor
echo "[3/5] Importiere WF8 - Trade Executor..."
if [ -f "$WF_DIR/wf8-trade-executor.json" ]; then
    n8n import:workflow --input="$WF_DIR/wf8-trade-executor.json" 2>&1
    echo "  ✅ WF8 importiert"
else
    echo "  ❌ Datei nicht gefunden: wf8-trade-executor.json"
fi
echo ""

# WF9 - Trade Monitor
echo "[4/5] Importiere WF9 - Trade Monitor..."
if [ -f "$WF_DIR/wf9-trade-monitor.json" ]; then
    n8n import:workflow --input="$WF_DIR/wf9-trade-monitor.json" 2>&1
    echo "  ✅ WF9 importiert"
else
    echo "  ❌ Datei nicht gefunden: wf9-trade-monitor.json"
fi
echo ""

# WF10 - Trade Journal
echo "[5/5] Importiere WF10 - Trade Journal..."
if [ -f "$WF_DIR/wf10-trade-journal.json" ]; then
    n8n import:workflow --input="$WF_DIR/wf10-trade-journal.json" 2>&1
    echo "  ✅ WF10 importiert"
else
    echo "  ❌ Datei nicht gefunden: wf10-trade-journal.json"
fi
echo ""

echo "========================================="
echo "  Import abgeschlossen!"
echo "========================================="
echo ""
echo "WICHTIG: Workflows sind nach Import INAKTIV."
echo "Aktiviere sie in der n8n UI oder mit:"
echo "  - WF8 (Executor) zuerst aktivieren (Webhook)"
echo "  - WF10 (Journal) aktivieren (Webhook)"
echo "  - WF9 (Monitor) aktivieren (Schedule)"
echo "  - WF7 (Analyzer) zuletzt aktivieren (Schedule)"
echo ""
echo "Für manuellen Test von WF7:"
echo "  → n8n UI öffnen → MT4 - 7 Trade Analyzer → Manual Trigger"
echo ""
