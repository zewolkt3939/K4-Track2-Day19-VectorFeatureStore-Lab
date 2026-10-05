"""Run five study queries and verify that another user's private note is absent."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FASTEMBED_CACHE_PATH", str(ROOT / "data" / "model_cache"))
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "hf_cache"))

from feast import FeatureStore
from bonus.agent import HybridMemoryAgent


def main():
    repo = ROOT / "app" / "feast_repo"
    if not (repo / "registry.db").exists():
        raise RuntimeError("Run notebook 04 first to populate Feast")
    agent = HybridMemoryAgent(FeatureStore(repo_path=str(repo)))
    user = "u_002"
    notes = [
        "Kubernetes và cloud: horizontal pod autoscaling tự động mở rộng số pod theo lưu lượng CPU.",
        "Cloud security: IAM least privilege, MFA và tách biệt mạng giúp giảm quyền truy cập dư thừa.",
        "Trong pentest lab được phép, tôi học cách kiểm tra IDOR bằng hai tài khoản thử nghiệm.",
        "JWT: xác minh chữ ký, issuer, audience và expiration; token chỉ là dữ liệu chưa đáng tin.",
        "SOC và AI: tìm log bất thường rồi đối chiếu timestamp và baseline theo từng người dùng.",
    ]
    for note in notes:
        agent.remember(note, user)
    agent.remember("PRIVATE-OTHER-USER: cloud security account note", "u_003")
    queries = ["Tôi đã đọc gì về Kubernetes?", "Recommend đọc gì tiếp?",
               "Tôi đang quan tâm gì gần đây?", "Tài liệu về tự động mở rộng hạ tầng?",
               "Cho tôi summary cloud security"]
    for i, query in enumerate(queries, 1):
        context = agent.recall(query, user)
        assert "PRIVATE-OTHER-USER" not in context
        assert agent.last_trace["session_queries_last_hour"] == i
        print(f"\nQUERY {i}: {query}\n{context}")
    assert "No memories exist" in agent.recall("cloud security", "new_user")
    print("\nPASS — five queries, immediate activity, empty user, and cross-user isolation")


if __name__ == "__main__":
    main()
