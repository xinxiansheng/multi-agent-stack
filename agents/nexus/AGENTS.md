# Agent Directory

## Active Agents

### ⚡ Nexus (main)
- **Role:** Central dispatcher, daily operations
- **Model:** Primary (opus)
- **Can call:** All registered agents

### 👁️ Observer
- **Role:** Intelligence analyst, information collection
- **Model:** Cost-effective (GPT-5.2)
- **Can call:** Nexus

### ⚖️ Arbiter
- **Role:** Strategic advisor, decision analysis
- **Model:** Claude Opus (no fallback — quality over availability)
- **Can call:** Nexus, Prism

## Adding New Agents
Use `./new-agent.sh <agent-id> <agent-name> <emoji>` to scaffold a new agent.
Then update this file and openclaw.json to register it.
