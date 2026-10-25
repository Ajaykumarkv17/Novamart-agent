"""
Validate the DynamoDB conversation-session extension.

  python src/session_validation.py           # repository round-trip only (no model calls)
  python src/session_validation.py --live    # + two-turn recall with a rebuilt agent graph

The live check runs turn 1, discards the agent graph (simulating a process or
runtime restart), rebuilds it for the same session and asks a follow-up that
can only be answered from the restored conversation history.
"""
import sys
import uuid

import agent_orchestrator as ao
from strands.types.session import Session, SessionAgent, SessionMessage, SessionType


def repository_round_trip() -> None:
    repo = ao.DynamoDbSessionRepository()
    session_id = f"validate-{uuid.uuid4().hex[:8]}"
    repo.create_session(Session(session_id=session_id, session_type=SessionType.AGENT))
    assert repo.read_session(session_id) is not None, "session not persisted"

    repo.create_agent(session_id, SessionAgent(agent_id="orchestrator", state={},
                                               conversation_manager_state={}))
    for i in range(3):
        repo.create_message(session_id, "orchestrator", SessionMessage(
            message={"role": "user", "content": [{"text": f"message {i}"}]}, message_id=i))

    messages = repo.list_messages(session_id, "orchestrator")
    assert [m.message_id for m in messages] == [0, 1, 2], "messages out of order"
    assert [m.message_id for m in repo.list_messages(session_id, "orchestrator", limit=1, offset=1)] == [1]

    redacted = messages[-1]
    redacted.redact_message = {"role": "user", "content": [{"text": "[REDACTED]"}]}
    repo.update_message(session_id, "orchestrator", redacted)
    assert repo.read_message(session_id, "orchestrator", 2).to_message()["content"][0]["text"] == "[REDACTED]"
    print(f"[PASS] repository round-trip in table '{ao.AGENT_SESSIONS_TABLE}' (session {session_id})")


def live_recall() -> None:
    if not ao.agent_sessions_enabled():
        raise SystemExit("Set AGENT_SESSIONS_ENABLED=true in .env for the live check.")
    session_id = uuid.uuid4().hex[:8]
    customer_id = "CUST-001"

    prompt = f"[Session ID: {session_id}] [Customer ID: {customer_id}] "
    # ORD-27180 is CUST-001's OLDEST order, so a guess such as "the most recent
    # order" (ORD-27177) gives the wrong answer - only real recall passes.
    target = "ORD-27180"

    print(f"\nTurn 1 (session {session_id}): status of {target}")
    graph = ao.build_agent_graph(session_id=session_id)
    graph(prompt + f"What is the status of my order {target}?")
    turn1_count = len(graph.messages)
    del graph                                                    # simulate restart

    # 1. Persistence: the rebuilt Orchestrator comes back with turn 1 from DynamoDB.
    restored = ao.build_agent_graph(session_id=session_id)
    assert len(restored.messages) == turn1_count, (
        f"restored {len(restored.messages)} messages, expected {turn1_count}")
    assert target in str(restored.messages), "restored history does not contain turn 1"
    print(f"[PASS] rebuilt Orchestrator restored {turn1_count} messages from DynamoDB")

    # 2. Usage: the follow-up can only be answered from the restored history.
    print("\nTurn 2: 'Which order number did I ask you about a moment ago?'")
    restored(prompt + "Which order number did I ask you about a moment ago?")
    state = ao._read_workflow_state(session_id) or {}
    reply = ao._strip_xml_tags(state.get("communication_agent", ""))
    print(f"\nTurn 2 reply:\n{reply}\n")
    assert target in (state.get("conversation_history") or ""), (
        "conversation history was not handed to the workers for turn 2")
    print("[PASS] turn-1 history was passed to the worker agents via WorkflowState")
    assert target in reply and "ORD-27177" not in reply, (
        f"turn 2 did not recall {target} from the session history")
    print(f"[PASS] turn 2 answered {target} from DynamoDB-restored conversation history")


if __name__ == "__main__":
    repository_round_trip()
    if "--live" in sys.argv:
        live_recall()
