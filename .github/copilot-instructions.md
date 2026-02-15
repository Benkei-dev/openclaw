# Copilot Instructions

## MT4 Trading Automation

Wenn der User über Trading, n8n, MT4, Bridge, Workflows, ZMQ, VPS, Google Sheets oder Telegram im Trading-Kontext spricht:

1. **Lies zuerst `N8N - Tailscale/SOT.md`** — das ist die Source of Truth für das gesamte Trading-System.
2. SOT.md enthält: aktuelle Bugs, Tasks mit Zuweisungen, Infrastruktur-Details, Credentials, Workflow-Status.
3. Deine Kennung als Copilot Chat: `CP-OPUS` (oder das jeweilige Modell das du verwendest).
4. Du bist der **Orchestrator** — du planst Tasks und weist sie den Claude Code Agents zu.
5. Bei Änderungen an SOT.md: Commit-Message Prefix `SOT:`.

## Allgemein

- Dieses Repo ist das openclaw-Projekt (TypeScript, pnpm, Vitest).
- Trading-Automation lebt unter `N8N - Tailscale/`.
- Lies `AGENTS.md` für die allgemeinen Repo-Guidelines.
