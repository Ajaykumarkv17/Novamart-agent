# Submission screenshots

Store capstone evidence in this folder. Do not submit placeholder images as evidence.

## Required final screenshots

1. `01-all-tests-passed.png` — terminal after `python tests/test_agent.py all`, showing the final score.
2. `02-xray-service-map.png` — AWS Console **CloudWatch → X-Ray traces → Service map** after a live request. Set the time range to **Last 5 minutes** and capture the full NovaMart-Orchestrator → worker-agent chain, including the policy Knowledge Base nodes when using a policy scenario.
3. Optional: `03-agentcore-runtime-ready.png` — AgentCore Runtime status is READY.
4. Optional: `04-knowledge-bases-synced.png` — three Bedrock Knowledge Bases and their synced data sources.

The project has not created these screenshots yet: the foundation CloudFormation stack was not present in the configured AWS account when Phase 1 was implemented.
