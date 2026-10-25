# NovaMart Capstone — Phase 1 Solution

## Goal
Phase 1 implements the Strands multi-agent customer-support graph in `src/agent_orchestrator.py`. The graph uses **Amazon Nova models only**:

| Agent | Model | Temperature | Responsibility |
|---|---|---:|---|
| OrchestratorAgent | `amazon.nova-lite-v1:0` | 0.0 | Deterministic routing and WorkflowState lifecycle |
| InventoryAgent | `amazon.nova-pro-v1:0` | 0.1 | DynamoDB order and customer facts |
| RefundAgent | `amazon.nova-pro-v1:0` | 0.1 | Tier-aware return decision and approved-return recording |
| PolicyAgent | `amazon.nova-pro-v1:0` | 0.2 | Grounded policy synthesis |
| Returns/Shipping/Warranty retrievers | `amazon.nova-pro-v1:0` | 0.0 | Deterministic Knowledge Base retrieval |
| CommunicationAgent | `amazon.nova-pro-v1:0` | 0.3 | Final empathetic customer response |

The model IDs are the in-region Bedrock IDs for `us-east-1`. AWS documents `amazon.nova-lite-v1:0` for Nova Lite and documents Nova Pro programmatic access in its [Nova Pro model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-pro.html). Nova Lite model-ID confirmation: [AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-lite.html). Content was rephrased for compliance with licensing restrictions.

## Implemented architecture

```text
Customer request
  → OrchestratorAgent (Nova Lite)
    → InventoryAgent (Nova Pro) → RefundAgent (Nova Pro)      [order/return/refund]
    → PolicyAgent (Nova Pro) → 3 parallel KB retrievers       [policy question]
    → InventoryAgent (Nova Pro)                               [account/tier]
    → CommunicationAgent (Nova Pro, always last)
```

Each session has a shared DynamoDB WorkflowState record. Route tools read that state, invoke their specialist, and store the result using the starter’s optimistic-locking helper.

### Required routing rules implemented

1. `initialize_session` is the first tool call for every request.
2. Order status, return, and refund requests go Inventory → Refund → Communication.
3. Policy meaning questions go Policy → Communication.
4. Account/tier questions go Inventory → Communication; Policy is not used for account data.
5. Arithmetic requests skip Inventory, Policy, and Refund, then go directly to Communication.
6. Communication is the final route for every request. The orchestrator prompt explicitly prohibits it from writing the customer-facing response.

### Worker behavior

- Inventory tools use DynamoDB `get_item` for composite order keys, customer lookup, and customer-order query. They report facts only.
- RefundAgent must load `inventory_agent` findings from WorkflowState before deciding. Its prompt applies Standard = 30 days and Premium = 60 days. The mutation tool records an approved delivered-order return as `return_requested` with a unique reference.
- PolicyAgent instantiates three specialist retriever agents inside `build_policy_agent()`. `search_all_policies` runs them with `ThreadPoolExecutor(max_workers=3)` and `as_completed`, then returns ordered combined evidence.
- CommunicationAgent loads the complete WorkflowState and drafts the only customer-facing response.

## Validation performed

From `starter/`:

```powershell
python -m py_compile src/agent_orchestrator.py config.py
python tests/test_agent.py task2
```

Result: **40/40 points (100%)**. The supplied test messages mention its original Claude labels, but its actual assertions compare agent model IDs with `config.ORCHESTRATOR_MODEL_ID` and `config.WORKER_MODEL_ID`; those constants now resolve to Amazon Nova Lite and Amazon Nova Pro.

## AWS status and next steps

The configured AWS CLI identity was successfully verified in `us-east-1` for account `992382390542`. The required foundation stack `udacity-agentcore` does **not** currently exist, so no DynamoDB tables, policy bucket, S3 Vector indexes, AgentCore Runtime, Knowledge Bases, guardrail, or screenshots were created. This is an honest blocker, not a deployment failure.

### Step 1 — Deploy foundation infrastructure

This creates DynamoDB, S3, S3 Vectors, IAM, and CloudWatch resources and can incur AWS charges. It is reversible using the supplied cleanup script after submission.

```powershell
aws cloudformation deploy --template-file infrastructure/starter_stack.yaml --stack-name udacity-agentcore --capabilities CAPABILITY_NAMED_IAM --region us-east-1
python config.py
python infrastructure/seed_data.py
```

### Step 2 — Create and sync Knowledge Bases in the AWS Console

Create three self-managed Bedrock Knowledge Bases using the values displayed by `python config.py`:

| KB | S3 prefix | Existing S3 Vector index |
|---|---|---|
| Returns | `policies/returns/` | `returns-policy-index` |
| Shipping | `policies/shipping/` | `shipping-policy-index` |
| Warranty | `policies/warranty/` | `warranty-policy-index` |

Use `amazon.titan-embed-text-v2:0`, sync each data source, and add the resulting IDs to a local `.env` copied from `.env.example`.

### Step 3 — Deploy Tasks 3–6 after they are implemented

Phase 1 is the graph only. The starter’s full `deploy` command also requires implementation of its Task 3 guardrail/runtime, Task 4 memory, and Task 6 observability TODOs, plus all three KB IDs. Complete those phases before running:

```powershell
python src/agent_orchestrator.py deploy
```

### Step 4 — Capture evidence

After full deployment, run the complete test suite and live scenarios:

```powershell
python tests/test_agent.py all
python src/agent_orchestrator.py test
```

Save the required terminal and X-Ray Service Map images in `screenshots/` as described in `screenshots/README.md`.

## Phase 2 — Guardrail, runtime configuration, and memory

Phase 2 is implemented but intentionally **not deployed yet**. `create_guardrail()` creates an idempotent Bedrock Guardrail with high-strength Sexual, Violence, and Hate filters; medium-strength Insults and Misconduct filters; PII handling for cards/SSNs (block) and email/phone (anonymize); three Standard-tier DENY topics; and the managed profanity list. The pricing-negotiation topic explicitly excludes arithmetic performed from a customer-supplied price and discount. The function publishes and returns a numbered guardrail version, never `DRAFT`.

`deploy_to_agentcore_runtime()` stages the app, configures the AgentCore CLI with PUBLIC/HTTP networking, the foundation IAM role, the three KB IDs, log group, and guardrail values, then deploys only when the final Phase 4 command is run.

`configure_memory()` creates the `udacity_agentcore_memory` resource with a seven-day `eventExpiryDuration` and `summaryMemoryStrategy` under `/summaries/{actorId}/{sessionId}`. It waits for ACTIVE status when called during final deployment.

The implementation was syntax-checked and its request fields were validated against the installed Bedrock and AgentCore SDK models. No guardrail, AgentCore Runtime, or Memory was created in Phase 2, by design.

## Phase 4 — Observability

`configure_observability(runtime_arn)` now builds the required configuration: CloudWatch logging to `config.AGENT_LOG_GROUP` at INFO level and enabled X-Ray tracing at a `1.0` sampling rate. It delegates the AWS changes to the supplied `apply_observability_config()` helper and reports any AWS failure without pretending configuration succeeded.

The function was locally validated by replacing the AWS-applying helper with a test double and asserting the exact runtime ARN and logging configuration passed to it. No AWS observability resources were changed by this validation. The first real call happens only as part of the final `python src/agent_orchestrator.py deploy` deployment pipeline.

## Deployment status and documented limitation

A partial final deployment succeeded on 2026-10-25: the Bedrock Guardrail `nn1xj4lj97ni` was created and published as version `1`, and AgentCore Runtime `udacity_agentcore_runtime-20xxVWEO4A` was deployed at `arn:aws:bedrock-agentcore:us-east-1:992382390542:runtime/udacity_agentcore_runtime-20xxVWEO4A`.

The deployment stopped at Task 4 because the account returned `AccessDeniedException` for `bedrock-agentcore-control:CreateMemory` with the message that the operation could not be performed. This is an account/service-limit or permission restriction, rather than an application implementation failure. To permit the rest of the deployment, `.env` sets `AGENTCORE_MEMORY_ENABLED=false`; `deploy_all()` now skips only the Memory step and documents that choice in its output. The existing `configure_memory()` implementation remains available for an account where AgentCore Memory is permitted.

**Submission impact:** the supplied Task 4 test cannot pass without an AgentCore Memory resource, so the unmodified grading suite cannot reach 120/120 in this account. Do not claim a perfect score. Capture the AccessDenied output and the successful runtime/guardrail/observability evidence as account-limit documentation.

## Optional project enhancements

### Guardrail adversarial validation
After observability is configured, exercise and screenshot: a prompt-injection attempt, a competitor request, a pricing-negotiation request, and a legal-threat request. Also exercise the required arithmetic request (`5 × $29.99` with `10%` off) and confirm it is allowed. Record the prompt category, expected result, actual blocked/allowed response, trace ID, and screenshot filename in the final submission notes.

### DynamoDB-backed conversation sessions
A future enhancement can create a dedicated `agent-sessions` DynamoDB table and attach Strands `DynamoDbSessionStorage` to the Orchestrator. This would retain same-session messages independently of AgentCore Memory and complements the existing per-request WorkflowState table. It is intentionally not implemented in this submission because it requires a new infrastructure resource, IAM permissions, and a version-compatible Strands session-storage integration; adding it should be a separately approved enhancement, not a workaround silently substituted for the required AgentCore Memory task.

## Routing and arithmetic corrections

Live testing exposed two defects, both fixed:

- **Context leak between requests.** `test` and the runtime `serve` handler reused one Orchestrator for every request, so later requests saw earlier conversations. That is why the policy scenario skipped `initialize_session` and why the math scenario was answered directly by the Orchestrator. Each customer session now gets its own agent graph (`build_agent_graph(session_id=...)`; the runtime keeps a small per-session LRU cache).
- **Non-deterministic arithmetic.** The model once rounded the discount before subtracting it and returned `$134.95`. CommunicationAgent now calls a `calculate_discounted_total` tool that uses Python `Decimal` and rounds once at the end (half-up): `5 × $29.99 = $149.95`, `× 0.90 = $134.955`, total **$134.96**.
- The Orchestrator prompt was tightened: initialization is the mandatory first action, and it may never calculate or answer; math goes straight to CommunicationAgent.

## Extension — persistent conversation sessions in DynamoDB

Strands (checked up to 1.62.0) has no built-in DynamoDB session storage; it ships File and S3 managers and documents database backends as custom repositories. `src/agent_orchestrator.py` therefore implements `DynamoDbSessionRepository`, a full Strands `SessionRepository` (sessions, agents, messages, guardrail redaction updates, ordered paginated listing) and attaches it to the Orchestrator through `RepositorySessionManager`. It lives in `agent_orchestrator.py` because the supplied AgentCore packager stages a fixed file list.

| Item | Value |
|---|---|
| Stack | `udacity-agentcore-agent-sessions` (`infrastructure/agent_sessions_stack.yaml`, separate from the starter stack) |
| Table | `udacity-agentcore-agent-sessions`, on-demand, SSE, TTL on `ttl` (7 days) |
| Keys | `session_id` + `record_key` (`SESSION`, `AGENT#<id>`, `MESSAGE#<id>#<n>`) |
| IAM | Inline policy on `udacity-agentcore-agentcore-role`: `GetItem`, `PutItem`, `Query` on this table only |
| Switch | `AGENT_SESSIONS_ENABLED` (also passed to the runtime) |

How it complements the rest of the design: WorkflowState holds per-request worker findings; agent-sessions holds the Orchestrator's conversation history, so a customer can refer back to earlier turns even after a process restart or on a different runtime instance. It is not presented as a replacement for AgentCore Memory (Task 4), which remains blocked by the account-level `CreateMemory` denial.

Validation: an offline check drove the real Strands `RepositorySessionManager` + `Agent` against an in-memory table and confirmed history is persisted and restored by a new agent. `python src/session_validation.py --live` repeats this against DynamoDB with real model calls.

Teardown order: delete `udacity-agentcore-agent-sessions` **before** running `infrastructure/cleanup.py`, because its inline policy is attached to the role owned by the starter stack.

## Extension — adversarial guardrail validation

`python src/guardrail_validation.py` invokes the deployed runtime with five cases and prints expected vs. actual, the response and the X-Ray trace ID:

| Case | Expected |
|---|---|
| Prompt injection ("reveal the system prompt") | Refused (not a configured denied topic; the model declines) |
| Competitor product | Blocked by guardrail |
| Price negotiation | Blocked by guardrail |
| Legal threat | Blocked by guardrail |
| `5 × $29.99` with 10% off | Allowed, total exactly `$134.96` |

The first run correctly blocked the three denied topics but the harness misread typographic apostrophes (`can’t`) as "allowed"; the classifier now normalizes them.

### Making the DynamoDB history actually used

The first live check showed that the history was being **saved and restored** (the rebuilt Orchestrator had all turn-1 messages), but nothing **used** it. The Orchestrator only routes, and each worker received just the current message. On turn 2, InventoryAgent listed the customer's orders and guessed the newest one, which happened to be the right answer. Fixes:

- `initialize_session` now builds the earlier turns from the restored Orchestrator history (customer message plus CommunicationAgent reply). It writes them to WorkflowState as `conversation_history` and clears the previous turn's worker findings. Every worker route adds that history to its prompt.
- On follow-up turns Nova Lite sometimes skipped `initialize_session`. Rule 1 is now also enforced in code: every route tool initializes the turn first if the model didn't. A warning is logged when this happens.
- `session_validation.py --live` can't be passed by guessing anymore. Turn 1 asks about ORD-27180, the customer's **oldest** order. The test checks that the history reached WorkflowState and that turn 2 answers ORD-27180 (and not the newest order, ORD-27177). The run against DynamoDB passed all three checks.

### Return-window enforcement in code

During that live run, RefundAgent assumed today's date and approved a 95-day-old order for a Premium customer, whose window is 60 days. `get_inventory_context` now returns today's date, the customer's tier and the return window. `initiate_refund` also checks the order age against the window before writing, so an out-of-window return is declined even if the model approves it. Verified: ORD-27180 (95 days, Premium) is declined with "Outside the 60-day return window".
