"""Check privacy at BOTH retrievers and immediate memory visibility."""
import pytest

from bonus.agent import HybridMemoryAgent, chunks, tokenize


@pytest.fixture(scope="module")
def memory():
    agent = HybridMemoryAgent()
    agent.remember("ALICE-PRIVATE cloud security JWT issuer audience expiration", "alice")
    agent.remember("BOB-PRIVATE cloud security IAM least privilege MFA", "bob")
    return agent


def test_both_rankings_are_user_scoped(memory):
    context = memory.recall("cloud security JWT", "alice")
    assert "ALICE-PRIVATE" in context and "BOB-PRIVATE" not in context
    allowed = {row["id"] for row in memory.memories["alice"]}
    assert set(memory.last_trace["keyword_ids"]) <= allowed
    assert set(memory.last_trace["vector_ids"]) <= allowed
    assert set(memory.last_trace["selected_ids"]) <= allowed


def test_empty_user_receives_no_other_users_memory(memory):
    context = memory.recall("cloud security", "new-user")
    assert "No memories exist" in context
    assert "PRIVATE" not in context
    assert memory.last_trace["selected_ids"] == []


def test_memory_is_visible_immediately_after_remember(memory):
    memory.remember("FRESH-NOTE kiểm tra authorization trước khi truy cập hồ sơ", "fresh-user")
    assert "FRESH-NOTE" in memory.recall("authorization hồ sơ", "fresh-user")
    assert memory.last_trace["session_queries_last_hour"] == 1


def test_security_identifiers_and_vietnamese_are_preserved():
    assert tokenize("CVE-2024-1234 và T1059 JWT") == ["cve-2024-1234", "và", "t1059", "jwt"]
    assert len(chunks(" ".join(f"w{i}" for i in range(250)))) == 3
    # A note exactly one chunk long must not create an overlap-only extra chunk.
    assert len(chunks(" ".join(f"w{i}" for i in range(120)))) == 1


def test_empty_memory_is_rejected(memory):
    with pytest.raises(ValueError, match="text"):
        memory.remember("   ", "alice")
