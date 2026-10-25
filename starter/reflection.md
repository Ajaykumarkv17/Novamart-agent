# Reflection — NovaMart Multi-Agent Support System

## Architecture decisions
Splitting the work into an Orchestrator and five specialists kept each agent's job small. The router only routes, InventoryAgent only reports facts, RefundAgent makes the decision, PolicyAgent answers from the Knowledge Bases, and CommunicationAgent writes the reply. A shared DynamoDB WorkflowState with optimistic locking was the right link between them. Every finding is inspectable, and no agent has to trust another agent's free-text summary of the conversation.

Using Amazon Nova only (Lite for routing, Pro for workers) kept the cost-versus-capability split the rubric asks for. Routing is the cheapest, most frequent call, so it gets the small model at temperature 0.0.

The parallel RAG design (three retriever sub-agents behind one `search_all_policies` tool) took about 6 s per policy question instead of three sequential retrievals. It also kept each domain's evidence separate until the final answer was written.

## What live testing taught me
The automated tests passed early, but live runs found real defects:

- **One Orchestrator served every request.** Its history leaked across customers, so it "remembered" that a session was already set up and skipped `initialize_session`. It also answered a math question directly. Giving each session its own graph fixed the routing, and it is also a privacy requirement.
- **Arithmetic needed a tool.** The model once rounded the discount before subtracting it and returned $134.95. A `Decimal` tool that rounds once at the end returns $134.96 every time.
- **The model ignored the date.** RefundAgent assumed today's date and approved a 95-day-old return for a 60-day Premium customer. Policy limits now live in code, and the model is given today's date.
- **Prompts are not enough.** Nova Lite still skipped `initialize_session` on follow-up turns, so that rule is now also enforced in the route tools.

Lesson: when a mistake costs money or breaks the workflow, prompts should be backed by a check in code.

## Safety and observability
The guardrail blocks the three denied topics in practice, not just in configuration: all of them returned the blocked message from the deployed runtime. The PII filter visibly anonymized customer emails. The calculation was still allowed because the pricing-negotiation topic is defined narrowly. Prompt injection was handled by the model refusing, which is why the test expects "refused" rather than "blocked". With 100% X-Ray sampling, every request appeared on the Service Map, which made routing mistakes easy to see.

## AgentCore Memory and the account switch
In my first account, `CreateMemory` returned AccessDenied with a "contact customer support" message even though the rest of the deployment succeeded. I didn't fake the resource or the score. I added an explicit `.env` switch so the rest of the system could deploy, and submitted at 105/120.

For the resubmission I redeployed everything to a second account where AgentCore Memory is available. Before rebuilding anything, I ran `configure_memory()` on its own. It created `udacity_agentcore_memory-YxJfPa8yAn`, which became ACTIVE, and the full deploy then found and reused it. The move needed no code changes, only new account-specific values. That showed the configuration-driven design was worth it: every resource name comes from CloudFormation exports or `.env`, so nothing in the code was tied to the old account.

## DynamoDB session extension
I expected a native `DynamoDbSessionStorage`, but the SDK doesn't have one, so I implemented the SDK's `SessionRepository` interface instead. The first version stored and restored history correctly, but nothing used it: the right answer came from a lucky guess. Two changes fixed this: writing the earlier turns into WorkflowState, and a test whose answer can't be guessed. It is deployed as a separate, removable stack with a policy scoped to one table, so the graded infrastructure stays untouched.

## Next steps
- Test the expired-session case explicitly (reviewer suggestion). DynamoDB TTL deletes items in the background, so the repository should ignore records whose `ttl` has passed.
- Read the AgentCore Memory session summaries back into the Orchestrator, alongside the DynamoDB turn history.
- Add regex filters for order-specific PII.
- Lower X-Ray sampling to about 5% for production.
- Use Strands hooks to enforce the tool-call order instead of checking it inside each tool.
