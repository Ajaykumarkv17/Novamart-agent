# Submission screenshots

Write-up: `../solution.md`; reflection: `../reflection.md`.

**Which account each screenshot comes from.** The first review accepted every criterion except Task 4 (AgentCore Memory), which the original account `992382390542` couldn't provision. For this resubmission the system was redeployed to account `065988995349` with no code changes:
- `01`, `03` and `04` are new and come from `065988995349`. They show Memory ACTIVE and the 120/120 test run.
- `02` and `05`–`11` are the evidence already accepted in the first review, from `992382390542`. That's why their runtime, guardrail and Knowledge Base IDs differ from the ones in `solution.md`.

## Resubmission evidence (account 065988995349)
| File | What it shows |
|---|---|
| `01-test-suite-120-of-120.png` | `python tests/test_agent.py all` with every task passing, including Task 4 Memory: 120/120 |
| `03-agentcore-memory-active.png` | AgentCore console: memory `udacity_agentcore_memory-YxJfPa8yAn`, status Active, event expiration 7 days |
| `04-deploy-complete.png` | Deploy step 4/6: "AgentCore Memory already exists: …065988995349…" |

## Evidence accepted in the first review (account 992382390542)
| File | What it shows |
|---|---|
| `02-xray-service-map.png` | Service Map: `NovaMart-Orchestrator` linked to InventoryAgent, RefundAgent, PolicyAgent, CommunicationAgent and the `KnowledgeBase:returns/shipping/warranty` nodes |
| `05-guardrail-adversarial-5-of-5.png` | `python src/guardrail_validation.py`: 5/5 PASS (prompt injection, competitor, price negotiation, legal threat, arithmetic `$134.96`) |
| `06-dynamodb-session-recall.png` | `python src/session_validation.py --live`: three `[PASS]` lines |
| `07-runtime-session-recall.png` | Two deployed-runtime `invoke` calls with session `demo1234`; the second recalls ORD-28001 |
| `08-agent-sessions-table.png` | DynamoDB `udacity-agentcore-agent-sessions`: `AGENT#` / `MESSAGE#` records with TTL |
| `09-agentcore-runtime-ready.png` | Runtime `udacity_agentcore_runtime-20xxVWEO4A`, Ready |
| `10-knowledge-bases-synced.png` | The 3 NovaMart Knowledge Bases, Available |
| `11-guardrail-config.png` | Guardrail `nn1xj4lj97ni`, Ready, US Guardrail v1:0 profile |
