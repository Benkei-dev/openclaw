#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
#  MT4 ZMQ Bridge – Installations-Skript für Ubuntu VPS
#  Ausführen als root: bash install.sh
# ──────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="/opt/mt4-bridge"
SERVICE_NAME="mt4-bridge"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installiere System-Abhängigkeiten …"
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv libzmq3-dev

echo "==> Erstelle Installationsverzeichnis $INSTALL_DIR …"
mkdir -p "$INSTALL_DIR"

echo "==> Kopiere Dateien …"
cp "$REPO_DIR/bridge.py"       "$INSTALL_DIR/"
cp "$REPO_DIR/requirements.txt" "$INSTALL_DIR/"

# .env nur kopieren wenn noch nicht vorhanden (überschreibt keine bestehende Konfig)
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$INSTALL_DIR/.env"
    echo ""
    echo "  ⚠️  WICHTIG: Bitte $INSTALL_DIR/.env anpassen!"
    echo "      nano $INSTALL_DIR/.env"
    echo ""
else
    echo "  → $INSTALL_DIR/.env bereits vorhanden, wird nicht überschrieben."
fi

echo "==> Erstelle Python Virtual Environment …"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

echo "==> Installiere systemd Service …"
cp "$REPO_DIR/$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo ""
echo "══════════════════════════════════════════════"
echo "  Installation abgeschlossen!"
echo ""
echo "  Nächste Schritte:"
echo "  1) Konfiguriere .env:  nano $INSTALL_DIR/.env"
echo "  2) Starte den Service: systemctl start $SERVICE_NAME"
echo "  3) Logs prüfen:        journalctl -u $SERVICE_NAME -f"
echo "  4) Health-Check:       curl http://localhost:8765/health"
echo "  5) API-Doku:           http://<vps-ip>:8765/docs"
echo "══════════════════════════════════════════════"
