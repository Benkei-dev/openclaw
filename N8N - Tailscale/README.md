# n8n + Tailscale Setup für MT4 Trading Automation

Dieses Verzeichnis dokumentiert die Installation und Konfiguration von n8n auf einem VPS mit Tailscale-Netzwerkanbindung für MT4 Trading-Automatisierung.

## Überblick

- **VPS**: Ubuntu 24.04.4 LTS (srv1351792)
- **Tailscale IP (VPS)**: 100.127.134.70
- **Tailscale IP (Trading PC)**: 100.121.91.27
- **n8n Version**: 2.7.5
- **n8n Port**: 5678
- **Installationsdatum**: 14. Februar 2026

## Architektur

```
[MT4 Trading PC] <---> [Tailscale Network] <---> [VPS mit n8n]
   (ZMQ Ports)              (verschlüsselt)        (Port 5678)
   - 32768 (PUSH)                                  - Webhooks
   - 32769 (PULL)                                  - Workflows
   - 32770 (PUB)                                   - API
```

## Komponenten

1. **Tailscale**: Sicheres VPN-Netzwerk zwischen VPS und Trading PC
2. **n8n**: Workflow-Automatisierungsplattform für MT4-Integration
3. **ZMQ Bridge**: (Geplant) Node.js-Service zur Verbindung von MT4 und n8n

## Dokumentation

- [Tailscale Installation](./TAILSCALE_SETUP.md) - Schritt-für-Schritt Tailscale-Installation auf VPS
- [n8n Installation](./N8N_SETUP.md) - n8n-Installation und systemd-Service-Konfiguration
- [Troubleshooting](./TROUBLESHOOTING.md) - Häufige Probleme und Lösungen
- [ZMQ Bridge](./ZMQ_BRIDGE.md) - (TODO) ZMQ-Bridge-Implementierung für MT4-Anbindung

## Quick Start

### Zugriff auf n8n

```
http://100.127.134.70:5678
```

Von jedem Gerät im Tailscale-Netzwerk erreichbar.

### Service Management

```bash
# Status prüfen
systemctl status n8n

# Service starten
sudo systemctl start n8n

# Service stoppen
sudo systemctl stop n8n

# Service neu starten
sudo systemctl restart n8n

# Logs anzeigen
journalctl -u n8n -f
```

## Workflows

### Bestehende Workflows (WF1-6)
| ID | Name | Status | Trigger |
|----|------|--------|---------|
| TsesAyfkGln2WH00 | WF1 - Marktdaten Empfang & Log | ✅ aktiv | Webhook `mt4-market` |
| 6DcFnzHicZOh0FxZ | WF2 - Signal Empfang & Alert | ✅ aktiv | Webhook `mt4-signal` |
| GjpBqxXZdHGGp218 | WF3 - Telegram Commands | ⏸ inaktiv | Telegram Bot |
| 2a1wXTU56DD2s0Yc | WF4 - Portfolio Monitor | ✅ aktiv | 5min Schedule |
| EVwU9BzKSKXuitLL | WF5 - Tagesreport | ✅ aktiv | Cron 21:45 |
| 8KAXUPF2J9EHbFAN | WF6 - News Monitor (ForexFactory) | ✅ aktiv | Stündlich |

### Neue Workflows (WF7-10) – Trading Automation
| ID | Name | Status | Trigger | Beschreibung |
|----|------|--------|---------|-------------|
| 1T0fMAYzQKf8yM6j | WF7 - Trade Analyzer | ✅ aktiv | 4h + Manual | Technische Analyse BTCUSD M15: EMA20/50, RSI14, ATR14 |
| CfULtpthxJXm3S25 | WF8 - Trade Executor | ✅ aktiv | Webhook `/execute-trade` | Empfängt Signal von WF7, sendet TRADE an MT4 |
| 0bRXfI6yvP7yVjlm | WF9 - Trade Monitor | ✅ aktiv | 2min Schedule | Überwacht offene Trades, Trailing Stop Management |
| Y1Z1WK5KInRXLlVY | WF10 - Trade Journal | ✅ aktiv | Webhook + 22:00 | Trade-Closure-Log + täglicher Account-Report |

## MT4 Bridge

- **Pfad**: `/opt/mt4-bridge/bridge.py`
- **Port**: 8765
- **Service**: `systemctl {start|stop|restart|status} mt4-bridge`
- **API Token**: `77cc86eaebae04682516f8f781069d14c3d3d46ba95a28cb`
- **Backups**: `/opt/mt4-bridge/backups/`

### Bridge Endpoints
| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/health` | Health Check |
| POST | `/mt4/command` | Befehl an MT4 senden |
| GET | `/mt4/signals` | Signal-Buffer lesen |
| GET | `/mt4/market` | Marktdaten-Buffer lesen |
| DELETE | `/mt4/buffer` | Buffer leeren |
| GET | `/mt4/stats` | Bridge-Statistiken |

### DWX EA Befehle (getestet)
| Befehl | Format | Status |
|--------|--------|--------|
| HIST | `HIST;SYMBOL;TF;START;END` | ✅ funktioniert |
| TRACK_PRICES | `TRACK_PRICES;S1;S2;...` | ✅ auto bei Start |
| TRADE OPEN | `TRADE;OPEN;TYPE;SYMBOL;0;VOL;SL;TP;COMMENT;MAGIC;0` | ⏳ zu testen |
| TRADE CLOSE | `TRADE;CLOSE;TICKET;SYMBOL;0;VOL;0;0;;MAGIC;TICKET` | ⏳ zu testen |
| ACCOUNT_INFO | nicht unterstützt durch DWX ZMQ EA v2 | ❌ |
| OPEN_TRADES | nicht unterstützt durch DWX ZMQ EA v2 | ❌ |

## Trading Konfiguration

- **Symbol**: BTCUSD (Capital.com Demo)
- **Timeframe**: M15 (15 Minuten)
- **Risiko**: 5% per Trade (von $100.000 Demo-Balance)
- **Position Sizing**: ATR-basiert
  - SL = 1.5 × ATR(14)
  - TP = 2.5 × ATR(14)
  - R:R = 1:1.67
  - Lots = RiskAmount / SL-Distance (min 0.01, max 1.0)

## Credentials

| Dienst | Credential ID | Details |
|--------|-------------|---------|
| Telegram Bot | `lwOSLP3ylq10yEW4` | Chat ID: `7268021157` |
| Google Sheets | `82cab318-1cf6-4071-a030-1535dfe88501` | Sheet: `1J1MNtiI...` |

## Nächste Schritte

1. ✅ Tailscale auf VPS installiert
2. ✅ n8n installiert und konfiguriert
3. ✅ n8n Web-Interface zugänglich
4. ✅ ZMQ Bridge Service erstellt und aktiv
5. ✅ WF1-6 Basis-Workflows erstellt
6. ✅ WF7-10 Trading Automation Workflows erstellt
7. ✅ Bridge-Patch: ast.literal_eval für DWX Python-Dict-Responses
8. ✅ HIST-Daten getestet (2049 M15 Candles)
9. ✅ Technische Analyse verifiziert (EMA, RSI, ATR)
10. ✅ Telegram-Benachrichtigungen getestet
11. ⏳ Erster Demo-Trade über WF8
12. ⏳ WF9 Trade Monitor testen
13. ⏳ Google Sheets Integration prüfen
14. ⏳ n8n API Key korrekt konfigurieren

## Sicherheitshinweise

- n8n läuft derzeit mit `N8N_SECURE_COOKIE=false` für HTTP-Zugriff
- Tailscale bietet Netzwerk-Verschlüsselung zwischen den Geräten
- Bridge API Token schützt vor unautorisiertem Zugriff
- **Demo-Konto**: Alle Trades laufen auf Capital.com Demo
- Für Produktivbetrieb sollte HTTPS in Betracht gezogen werden

## Support

Bei Fragen oder Problemen siehe [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).
