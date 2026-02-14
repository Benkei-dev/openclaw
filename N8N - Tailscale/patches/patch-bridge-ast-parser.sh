#!/bin/bash
# =============================================
# Bridge Fix: ast.literal_eval für DWX EA Responses
# =============================================
# DWX EA v2.0.1 sendet Antworten im Python-Dict-Format
# (single quotes), nicht JSON. Dieser Patch fügt
# ast.literal_eval als Fallback hinzu.
#
# BACKUP wird erstellt vor Änderung!
# =============================================

set -e

BRIDGE="/opt/mt4-bridge/bridge.py"
BACKUP="/opt/mt4-bridge/backups/bridge.py.$(date +%Y%m%d-%H%M%S).bak"

echo "=== Bridge Patch: Python-Dict-Parser ==="
echo ""

# Backup
mkdir -p /opt/mt4-bridge/backups
cp "$BRIDGE" "$BACKUP"
echo "✅ Backup: $BACKUP"

# Check ob Patch schon angewendet wurde
if grep -q "ast.literal_eval" "$BRIDGE"; then
    echo "⚠️  Patch bereits vorhanden, überspringe..."
    exit 0
fi

# Füge 'import ast' zum Import-Block hinzu (nach 'import json')
sed -i '/^import json$/a import ast' "$BRIDGE"

# Füge ast.literal_eval Fallback nach dem JSON-Block ein
# Suche nach dem Kommentar "# DWX PUB-Format" und füge davor den neuen Block ein
sed -i '/# DWX PUB-Format/i\    # Python-Dict-Format (DWX EA sendet single-quoted dicts)\n    try:\n        result = ast.literal_eval(raw)\n        if isinstance(result, dict):\n            return result\n    except (ValueError, SyntaxError):\n        pass\n' "$BRIDGE"

echo "✅ Patch angewendet"
echo ""

# Validieren
echo "--- Prüfe Syntax ---"
python3 -c "import py_compile; py_compile.compile('$BRIDGE', doraise=True)" && echo "✅ Syntax OK" || echo "❌ Syntax-Fehler! Backup wiederherstellen: cp $BACKUP $BRIDGE"

echo ""
echo "--- Geänderte Zeilen ---"
diff "$BACKUP" "$BRIDGE" || true
echo ""
echo "Restart mit: systemctl restart mt4-bridge"
