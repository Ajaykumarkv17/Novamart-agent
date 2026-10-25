# Submission screenshots

Evidence for the NovaMart submission. Write-up: `../solution.md`; reflection: `../reflection.md`.

## Required by the rubric
| File | What to capture | Command / location |
|---|---|---|
| `01-test-suite-105-of-120.png` | End of the full test run: Task 5 parallel retrieval and Task 6 passing, final score 105/120 (the missing 15 points are Task 4, see `03`) | `python tests/test_agent.py all` |
| `02-xray-service-map.png` | Service Map showing `NovaMart-Orchestrator` linked to InventoryAgent, RefundAgent, PolicyAgent, CommunicationAgent and the `KnowledgeBase:returns/shipping/warranty` nodes | Run `python src/agent_orchestrator.py test`, wait 60 s, then open CloudWatch → X-Ray traces → Service map, time range "Last 5 minutes" |

## Evidence for the AgentCore Memory limitation
| File | What to capture |
|---|---|
| `03-agentcore-memory-access-denied.png` | The `AccessDeniedException ... CreateMemory` error from the first deploy. If you no longer have it, rerun deploy with `AGENTCORE_MEMORY_ENABLED=true` to show it again |
| `04-deploy-memory-skipped.png` | Final deploy output: "Step 4/6 ... [Skipped: AGENTCORE_MEMORY_ENABLED=false]" and "Deployment Complete!" |

## Standout extensions
| File | What to capture |
|---|---|
| `05-guardrail-adversarial-5-of-5.png` | `python src/guardrail_validation.py`: five PASS lines with blocked responses and trace IDs |
| `06-dynamodb-session-recall.png` | `python src/session_validation.py --live`: the three `[PASS]` lines |
| `07-runtime-session-recall.png` | The two `invoke ... CUST-002 demo1234` calls: the second recalls ORD-28001 |
| `08-agent-sessions-table.png` | DynamoDB console → `udacity-agentcore-agent-sessions` → Explore items, showing `SESSION` / `AGENT#` / `MESSAGE#` records |

## Supporting images
| File | What it shows |
|---|---|
| `09-agentcore-runtime-ready.png` | AgentCore console: runtime `udacity_agentcore_runtime` READY |
| `10-knowledge-bases-synced.png` | Bedrock console: the 3 Knowledge Bases with synced data sources |
| `11-guardrail-config.png` | Bedrock console: guardrail `nn1xj4lj97ni`, version 1 |
