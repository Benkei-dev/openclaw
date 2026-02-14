# Troubleshooting Guide - n8n + Tailscale

Häufige Probleme und Lösungen für das n8n + Tailscale Setup.

## n8n Web-Interface nicht erreichbar

### Problem 1: "This site can't provide a secure connection" oder ERR_SSL_PROTOCOL_ERROR

**Symptom**: Browser zeigt SSL/TLS-Fehler beim Zugriff auf http://100.127.134.70:5678

**Ursache**: n8n's `N8N_SECURE_COOKIE` ist standardmäßig `true` und erfordert HTTPS-Verbindung.

**Lösung**:

1. Service stoppen:
```bash
sudo systemctl stop n8n
```

2. Service-Datei bearbeiten und `N8N_SECURE_COOKIE=false` hinzufügen:
```bash
sudo nano /etc/systemd/system/n8n.service
```

Füge nach der Zeile `Environment="N8N_LOG_OUTPUT=console"` hinzu:
```ini
Environment="N8N_SECURE_COOKIE=false"
```

Oder mit sed automatisch:
```bash
sudo sed -i '/Environment="N8N_LOG_OUTPUT=console"/a Environment="N8N_SECURE_COOKIE=false"' /etc/systemd/system/n8n.service
```

3. systemd neu laden und Service starten:
```bash
sudo systemctl daemon-reload
sudo systemctl start n8n
```

4. Status prüfen:
```bash
sudo systemctl status n8n
```

### Problem 2: Connection refused oder Timeout

**Symptom**: Browser kann http://100.127.134.70:5678 nicht erreichen.

**Diagnose**:

1. Prüfe, ob n8n läuft:
```bash
systemctl status n8n
```

2. Prüfe, ob Port 5678 lauscht:
```bash
ss -tlnp | grep 5678
```

Sollte zeigen: `LISTEN 0  511  *:5678  *:*`

3. Prüfe Tailscale-Verbindung:
```bash
tailscale status
ping -c 3 100.127.134.70
```

4. Teste lokalen Zugriff auf dem VPS:
```bash
curl -I http://localhost:5678
```

**Lösung je nach Diagnose**:

- **n8n läuft nicht**: `sudo systemctl start n8n`
- **Port nicht offen**: Prüfe `N8N_HOST=0.0.0.0` in Service-Datei
- **Tailscale-Problem**: `sudo tailscale up` erneut ausführen
- **Lokaler Zugriff funktioniert, remote nicht**: Firewall-Regeln prüfen

### Problem 3: Lizenz-Registrierungsdialog erscheint

**Symptom**: Bei erstem Zugriff erscheint Dialog "Register for n8n Enterprise License".

**Lösung**: 

- Klicke auf "Skip" Button unten rechts
- Du kannst die Community Edition ohne Registrierung verwenden
- Alternativ: Registriere für Enterprise-Features (optional)

## n8n Service Probleme

### Service startet nicht

**Diagnose**:

```bash
# Status prüfen
sudo systemctl status n8n

# Logs anzeigen
journalctl -u n8n -n 100 --no-pager
```

**Häufige Fehler**:

#### Fehler: "ExecStart path not found"

```bash
# Prüfe n8n-Installation
which n8n

# Sollte ausgeben: /usr/bin/n8n
# Falls nicht, n8n neu installieren:
sudo npm install -g n8n
```

#### Fehler: "Permission denied"

```bash
# Service läuft als root, prüfe Berechtigungen:
ls -la /root/.n8n/

# Falls nötig, Berechtigungen korrigieren:
sudo chown -R root:root /root/.n8n/
```

#### Fehler: Port 5678 bereits in Verwendung

```bash
# Prüfe, welcher Prozess Port 5678 verwendet:
sudo lsof -i :5678

# Prozess beenden (ersetze PID):
sudo kill -9 <PID>

# Oder ändere Port in Service-Datei:
Environment="N8N_PORT=5679"
```

### Service stirbt nach kurzer Zeit

**Diagnose**:

```bash
# Prüfe Restart-Events
journalctl -u n8n | grep -i restart

# Prüfe auf Out-of-Memory Fehler
journalctl -u n8n | grep -i memory
```

**Lösung**:

- **Memory-Problem**: VPS-RAM erhöhen oder Swap aktivieren
- **Crash bei Start**: Logs prüfen auf spezifische Fehler
- **Automatische Restarts**: `RestartSec=10` in Service-Datei erhöhen

## Tailscale Verbindungsprobleme

### Geräte sehen sich nicht im Netzwerk

**Diagnose**:

```bash
# Auf VPS
tailscale status

# Sollte beide Geräte zeigen:
# 100.127.134.70  srv1351792
# 100.121.91.27   [trading-pc]
```

**Lösung**:

1. Tailscale auf beiden Geräten neu starten:
```bash
# VPS
sudo tailscale down
sudo tailscale up

# Windows (PowerShell als Admin)
Restart-Service Tailscale
```

2. Firewall-Ausnahmen prüfen (Windows):
```powershell
# Tailscale sollte in Firewall erlaubt sein
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Tailscale*"}
```

### Langsame Verbindung zwischen Geräten

**Diagnose**:

```bash
tailscale netcheck
```

**Lösung**:

- Prüfe, ob direkte Peer-to-Peer-Verbindung besteht
- Firewall/Router könnte UDP blockieren
- Verwende Tailscale Relay Server (DERP) als Fallback

## n8n Workflow-Probleme

### Webhook nicht erreichbar

**Problem**: Externe Webhooks geben Fehler.

**Lösung**:

1. Prüfe `WEBHOOK_URL` in Service-Datei:
```bash
grep WEBHOOK_URL /etc/systemd/system/n8n.service
```

Sollte sein: `Environment="WEBHOOK_URL=http://100.127.134.70:5678/"`

2. Für externe Webhooks (außerhalb Tailscale):
   - Nginx Reverse Proxy einrichten
   - Domain mit SSL konfigurieren
   - `WEBHOOK_URL` auf öffentliche Domain ändern

### Workflows führen nicht aus

**Diagnose**:

1. Prüfe Workflow-Status in n8n Interface
2. Prüfe n8n Logs:
```bash
journalctl -u n8n -f
```

**Häufige Ursachen**:

- Credentials nicht konfiguriert
- Node hat Fehler (rotes Dreieck)
- Trigger nicht aktiviert
- Zeitzone-Probleme bei Cron-Triggers

**Lösung**:

- **Timezone**: `GENERIC_TIMEZONE=Europe/Berlin` in Service-Datei setzen
- **Credentials**: In n8n Interface unter "Credentials" konfigurieren
- **Trigger**: Workflow muss "Active" sein (Toggle oben rechts)

## Performance-Probleme

### n8n reagiert langsam

**Diagnose**:

```bash
# Memory-Verbrauch
systemctl status n8n | grep Memory

# CPU-Last
top -p $(pgrep -f n8n)

# Disk I/O
iostat -x 1 5
```

**Lösung**:

- **Zu viele parallele Workflows**: Execution Concurrency begrenzen
- **Große Datenmengen**: Batching verwenden
- **RAM zu niedrig**: VPS upgraden oder Swap aktivieren
- **Logs zu groß**: Log-Level auf `warn` setzen:
  ```bash
  Environment="N8N_LOG_LEVEL=warn"
  ```

## Datenbank-Probleme

### SQLite-Datenbank korrupt

**Symptom**: n8n startet nicht, Fehler in Logs über Datenbank.

**Lösung**:

1. Backup erstellen:
```bash
cp /root/.n8n/database.sqlite /root/.n8n/database.sqlite.backup
```

2. Datenbank-Integrität prüfen:
```bash
sqlite3 /root/.n8n/database.sqlite "PRAGMA integrity_check;"
```

3. Bei Korruption: Von Backup wiederherstellen oder Datenbank neu initialisieren

## ZMQ Bridge Probleme (für spätere Implementierung)

### Placeholder für kommende ZMQ-Bridge-Troubleshooting

Wird erweitert, sobald ZMQ Bridge implementiert ist.

Erwartete Themen:
- ZMQ-Verbindungsfehler zu MT4
- Port-Binding-Probleme
- Nachrichtenverlust
- Performance-Tuning

## Nützliche Diagnose-Befehle

### Vollständiger System-Check

```bash
#!/bin/bash
echo "=== n8n Service Status ==="
systemctl status n8n --no-pager

echo -e "\n=== n8n Port Listening ==="
ss -tlnp | grep 5678

echo -e "\n=== Tailscale Status ==="
tailscale status

echo -e "\n=== Recent n8n Logs ==="
journalctl -u n8n -n 20 --no-pager

echo -e "\n=== System Resources ==="
free -h
df -h
```

### Log-Analyse

```bash
# Fehler der letzten Stunde
journalctl -u n8n --since "1 hour ago" | grep -i error

# Restart-Events
journalctl -u n8n | grep -i "Started n8n"

# Memory-Warnungen
journalctl -u n8n | grep -i "memory\|oom"
```

## Weiterführende Hilfe

- n8n Community: https://community.n8n.io/
- Tailscale Support: https://tailscale.com/contact/support/
- GitHub Issues: https://github.com/n8n-io/n8n/issues

## Notfall-Recovery

### Kompletter Reset

```bash
# Service stoppen
sudo systemctl stop n8n

# Daten sichern
sudo tar -czf n8n-emergency-backup-$(date +%Y%m%d-%H%M%S).tar.gz /root/.n8n/

# n8n neu installieren
sudo npm uninstall -g n8n
sudo npm install -g n8n

# Datenbank neu initialisieren (ACHTUNG: Alle Workflows gehen verloren!)
sudo rm -rf /root/.n8n/
sudo mkdir -p /root/.n8n/

# Service neu starten
sudo systemctl start n8n
```

Verwende diesen Reset nur als letzte Option!
