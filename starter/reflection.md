# Reflection — NovaMart Phase 1

## Architecture decisions

I used an Orchestrator → Workers hierarchy because routing, factual retrieval, policy grounding, refund decisions, and customer communication have different responsibilities. Amazon Nova Lite is appropriate for low-temperature deterministic routing; Amazon Nova Pro is used where tool reasoning, synthesis, or customer-language generation needs greater capability. This keeps the project free of Claude model dependencies.

The DynamoDB WorkflowState is the boundary between agents. It makes each specialist’s output inspectable and preserves a single session record with optimistic locking rather than passing unstructured context through every prompt.

The PolicyAgent intentionally uses three independent retriever agents in a `ThreadPoolExecutor`. This demonstrates multi-agent RAG, reduces end-to-end retrieval latency relative to sequential calls, and keeps returns, shipping, and warranty evidence visibly separate before synthesis.

## Safety and reliability

InventoryAgent is explicitly limited to facts. RefundAgent is required to inspect inventory context before applying the documented 30-day Standard / 60-day Premium window, and it can record only delivered-order return requests. CommunicationAgent is the only agent directed to produce a final customer-facing reply. The orchestrator always delegates that final step.

The supplied observability layer is preserved. Its traced route tools and Knowledge Base retrievals are designed to create the required X-Ray service-map topology once the subsequent deployment and observability phases are complete.

## Validation and current status

`python -m py_compile src/agent_orchestrator.py config.py` and `python tests/test_agent.py task2` passed; Task 2 scored 40/40. AWS CLI authentication was verified for `us-east-1`, but the required `udacity-agentcore` CloudFormation stack was absent. Therefore, no external resources were created, no live request was run, and no screenshot has been claimed as captured.

## Next steps

Deploy the foundation stack, seed its data, create and sync the three Bedrock Knowledge Bases, then complete Tasks 3, 4, and 6 before deploying AgentCore Runtime. Finally, run the full test suite and capture the X-Ray Service Map and all-tests evidence in `screenshots/`.

## Phase 2 reflection

The deployment function uses the supplied AgentCore CLI wrapper instead of bypassing it with a direct SDK runtime-creation call. This keeps the runtime, CDK deployment state, staged arm64 package, and runtime configuration managed by one supported path. Guardrail creation is idempotent: an existing published version is reused; an existing draft is published. External creation remains deferred until all Knowledge Base IDs and observability configuration are ready, avoiding a partial runtime deployment.

## Phase 4 reflection

Observability is applied after runtime deployment because the helper both configures CloudWatch Transaction Search at the account level and redeploys runtime environment variables. Keeping it behind the final deployment command prevents local validation from changing account-wide X-Ray indexing or creating an accidental partial deployment. Development uses 100% sampling so the final evidence includes every exercised request path; production would normally reduce this rate for cost control.

## AgentCore Memory account limitation

The runtime and guardrail deployment succeeded, but `bedrock-agentcore-control:CreateMemory` returned `AccessDeniedException` for this account. Rather than retrying a denied operation or claiming memory was configured, the deployment pipeline now supports an explicit `AGENTCORE_MEMORY_ENABLED=false` opt-out and records the skip. This allows the runtime and observability work to proceed while preserving the `configure_memory()` implementation for accounts with access. The trade-off is explicit: Task 4 and a strict 120/120 automated score remain unavailable until the account administrator enables AgentCore Memory permissions/service access.

## Planned standout validation

The next validation cycle will exercise the guardrail against prompt injection, competitor, pricing-negotiation, and legal-threat inputs, while separately proving the allowed arithmetic path. These runs should be captured with trace IDs and screenshots. A DynamoDB session-storage extension is a possible future enhancement, but it should be implemented as a separate infrastructure-approved feature rather than presented as equivalent to AgentCore Memory.

## What live testing taught me

The most useful bug was invisible in unit tests: one Orchestrator instance served every request, so its conversation history leaked across customers. The model then "remembered" that a session was already initialized and that it had answered math before. Scoping each graph to one session fixed routing order, and it is also a privacy requirement for a support system. Arithmetic is now a deterministic tool rather than a model skill, because a model that rounds an intermediate value is wrong by a cent in a way customers notice.

## DynamoDB sessions

I expected a native `DynamoDbSessionStorage` but the SDK doesn't ship one, so I implemented the SDK's `SessionRepository` contract instead of a lookalike. Storing each Strands record as a JSON string sidesteps DynamoDB's float restriction, and the composite key keeps a session's messages in order with a single `Query`. I deployed it as a separate stack with a policy scoped to one table so it can be removed without touching the graded infrastructure.
