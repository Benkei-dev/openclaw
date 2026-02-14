# n8n Installation auf Ubuntu VPS

Installation und Konfiguration von n8n 2.7.5 als systemd-Service auf Ubuntu 24.04.4 LTS.

## Systemvoraussetzungen

- Ubuntu 24.04.4 LTS
- Node.js v24.13.1 oder höher
- npm 11.8.0 oder höher
- Root- oder sudo-Zugriff
- Mindestens 1 GB RAM (empfohlen: 2+ GB)

## Installation

### 1. Node.js und npm vorbereiten

Stelle sicher, dass Node.js und npm installiert sind:

```bash
node --version  # v24.13.1
npm --version   # 11.8.0
```

### 2. n8n global installieren

```bash
sudo npm install -g n8n
```

Installation umfasst 2169 Pakete und dauert ca. 1-2 Minuten.

### 3. Installation verifizieren

```bash
n8n --version
```

Erwartete Ausgabe: `2.7.5`

## systemd-Service Konfiguration

### Service-Datei erstellen

```bash
sudo nano /etc/systemd/system/n8n.service
```

Service-Konfiguration:

```ini
[Unit]
Description=n8n - Workflow Automation
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
Environment="N8N_PORT=5678"
Environment="N8N_HOST=0.0.0.0"
Environment="WEBHOOK_URL=http://100.127.134.70:5678/"
Environment="N8N_LOG_LEVEL=info"
Environment="N8N_LOG_OUTPUT=console"
Environment="N8N_SECURE_COOKIE=false"
Environment="GENERIC_TIMEZONE=Europe/Berlin"
Environment="TZ=Europe/Berlin"
ExecStart=/usr/bin/n8n start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=n8n

[Install]
WantedBy=multi-user.target
```

### Wichtige Konfigurationsparameter

- **N8N_PORT=5678**: Port für Web-Interface und API
- **N8N_HOST=0.0.0.0**: Lauscht auf allen Netzwerk-Interfaces
- **WEBHOOK_URL**: Basis-URL für Webhooks (Tailscale-IP)
- **N8N_SECURE_COOKIE=false**: Erlaubt HTTP-Zugriff (wichtig für Tailscale-Setup)
- **GENERIC_TIMEZONE**: Zeitzone für Workflow-Ausführung

### Service aktivieren und starten

```bash
# systemd-Daemon neu laden
sudo systemctl daemon-reload

# Service aktivieren (automatischer Start beim Boot)
sudo systemctl enable n8n

# Service starten
sudo systemctl start n8n

# Status prüfen
sudo systemctl status n8n
```

## Verifizierung

### Service-Status prüfen

```bash
systemctl status n8n
```

Erwartete Ausgabe:

```
● n8n.service - n8n - Workflow Automation
     Loaded: loaded (/etc/systemd/system/n8n.service; enabled)
     Active: active (running) since Sat 2026-02-14 08:00:58 UTC
   Main PID: 75489 (MainThread)
      Tasks: 11 (limit: 9308)
     Memory: 592.0M (peak: 631.5M)
        CPU: 17.729s
     CGroup: /system.slice/n8n.service
```

### Port-Listening prüfen

```bash
ss -tlnp | grep 5678
```

Erwartete Ausgabe:

```
LISTEN 0  511  *:5678  *:*  users:(("node",pid=75489))
```

### Web-Interface testen

Von einem Gerät im Tailscale-Netzwerk:

```
http://100.127.134.70:5678
```

### Logs anzeigen

```bash
# Letzte 50 Zeilen
journalctl -u n8n -n 50

# Live-Logs verfolgen
journalctl -u n8n -f

# Logs mit Zeitstempel
journalctl -u n8n --since "1 hour ago"
```

## Service Management

### Service starten

```bash
sudo systemctl start n8n
```

### Service stoppen

```bash
sudo systemctl stop n8n
```

### Service neu starten

```bash
sudo systemctl restart n8n
```

### Service neu laden (nach Konfigurationsänderung)

```bash
sudo systemctl daemon-reload
sudo systemctl restart n8n
```

### Autostart aktivieren/deaktivieren

```bash
# Aktivieren
sudo systemctl enable n8n

# Deaktivieren
sudo systemctl disable n8n
```

## Erste Schritte in n8n

1. **Web-Interface öffnen**: http://100.127.134.70:5678
2. **Lizenz-Registrierung**: "Skip" klicken für Community Edition
3. **Admin-Konto erstellen**: E-Mail und Passwort eingeben
4. **Erster Workflow**: "+ Add workflow" klicken

## Konfiguration anpassen

### Umgebungsvariablen ändern

Service-Datei bearbeiten:

```bash
sudo nano /etc/systemd/system/n8n.service
```

Nach Änderungen:

```bash
sudo systemctl daemon-reload
sudo systemctl restart n8n
```

### Wichtige optionale Umgebungsvariablen

```ini
# Datenbank (Standard: SQLite)
Environment="DB_TYPE=postgresdb"
Environment="DB_POSTGRESDB_HOST=localhost"
Environment="DB_POSTGRESDB_DATABASE=n8n"

# Authentifizierung
Environment="N8N_BASIC_AUTH_ACTIVE=true"
Environment="N8N_BASIC_AUTH_USER=admin"
Environment="N8N_BASIC_AUTH_PASSWORD=changeme"

# Verschlüsselung (für Credentials)
Environment="N8N_ENCRYPTION_KEY=your-encryption-key"

# Externe Webhooks
Environment="WEBHOOK_TUNNEL_URL=https://your-domain.com/"
```

## Ressourcen-Monitoring

### Speicherverbrauch prüfen

```bash
systemctl status n8n | grep Memory
```

Typischer Verbrauch: 500-700 MB

### CPU-Auslastung prüfen

```bash
systemctl status n8n | grep CPU
```

## Backup und Wartung

### Workflow-Daten sichern

n8n speichert Daten standardmäßig in:

```bash
/root/.n8n/
```

Backup erstellen:

```bash
sudo tar -czf n8n-backup-$(date +%Y%m%d).tar.gz /root/.n8n/
```

### Update auf neue Version

```bash
# Service stoppen
sudo systemctl stop n8n

# n8n aktualisieren
sudo npm update -g n8n

# Service starten
sudo systemctl start n8n

# Version prüfen
n8n --version
```

## Troubleshooting

Siehe [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) für detaillierte Lösungen.

## Sicherheitshinweise

- **N8N_SECURE_COOKIE=false** ist für HTTP-Zugriff erforderlich
- Tailscale bietet Netzwerk-Verschlüsselung zwischen den Geräten
- Für Produktivbetrieb: HTTPS mit Let's Encrypt oder Tailscale HTTPS konfigurieren
- Basic Auth oder SSO für zusätzliche Authentifizierung empfohlen
- Firewall-Regeln konfigurieren (Port 5678 nur für Tailscale-Netzwerk)

## Deinstallation (falls nötig)

```bash
# Service stoppen und deaktivieren
sudo systemctl stop n8n
sudo systemctl disable n8n

# Service-Datei entfernen
sudo rm /etc/systemd/system/n8n.service
sudo systemctl daemon-reload

# n8n deinstallieren
sudo npm uninstall -g n8n

# Daten entfernen (optional)
sudo rm -rf /root/.n8n/
```

## Weiterführende Ressourcen

- [n8n Dokumentation](https://docs.n8n.io/)
- [n8n Community Forum](https://community.n8n.io/)
- [n8n GitHub Repository](https://github.com/n8n-io/n8n)
