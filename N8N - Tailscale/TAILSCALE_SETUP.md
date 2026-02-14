# Tailscale Installation auf Ubuntu VPS

Installation und Konfiguration von Tailscale 1.94.1 auf Ubuntu 24.04.4 LTS.

## Systemvoraussetzungen

- Ubuntu 24.04.4 LTS
- Root- oder sudo-Zugriff
- Internetverbindung

## Installation

### 1. Tailscale Repository hinzufügen

```bash
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-list | sudo tee /etc/apt/sources.list.d/tailscale.list
```

### 2. Paketlisten aktualisieren

```bash
sudo apt-get update
```

### 3. Tailscale installieren

```bash
sudo apt-get install -y tailscale
```

### 4. Tailscale starten und authentifizieren

```bash
sudo tailscale up
```

Dieser Befehl gibt eine URL aus, über die der VPS mit einem Tailscale-Account verbunden werden kann.

## Verifizierung

### Tailscale-Status prüfen

```bash
tailscale status
```

Erwartete Ausgabe zeigt alle verbundenen Geräte im Netzwerk:

```
100.127.134.70  srv1351792           [dein-account]@ linux   -
100.121.91.27   [trading-pc]         [dein-account]@ windows -
```

### IP-Adresse anzeigen

```bash
tailscale ip -4
```

Ausgabe: `100.127.134.70`

### Ping-Test zu Trading PC

```bash
ping -c 3 100.121.91.27
```

## Konfiguration

### Version prüfen

```bash
tailscale version
```

Installierte Version: `1.94.1`

### Tailscale automatisch beim Boot starten

```bash
sudo systemctl enable tailscaled
```

## Netzwerk-Topologie

Nach erfolgreicher Installation:

- **VPS (srv1351792)**: 100.127.134.70
- **Trading PC**: 100.121.91.27
- **Verbindungstyp**: Peer-to-Peer über Tailscale-Mesh-Netzwerk
- **Verschlüsselung**: WireGuard-basiert, Ende-zu-Ende verschlüsselt

## Troubleshooting

### Tailscale startet nicht

```bash
sudo systemctl status tailscaled
sudo journalctl -u tailscaled -n 50
```

### Keine Verbindung zu anderen Geräten

```bash
# Tailscale neu starten
sudo tailscale down
sudo tailscale up

# Netzwerkverbindung prüfen
sudo tailscale netcheck
```

### Authentifizierung erneuern

```bash
sudo tailscale up --force-reauth
```

## Firewall-Überlegungen

Tailscale funktioniert typischerweise durch Firewalls hindurch, da es UDP-Hole-Punching verwendet. Keine zusätzliche Firewall-Konfiguration erforderlich für grundlegende Funktionalität.

## Deinstallation (falls nötig)

```bash
sudo tailscale down
sudo apt-get remove --purge tailscale
sudo rm -rf /var/lib/tailscale
```

## Weiterführende Ressourcen

- [Tailscale Dokumentation](https://tailscale.com/kb/)
- [Tailscale Admin Console](https://login.tailscale.com/admin/machines)
