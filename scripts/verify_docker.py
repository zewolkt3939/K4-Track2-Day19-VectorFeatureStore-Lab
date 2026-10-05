"""Docker path smoke test.

Verifies all 3 services brought up by docker-compose are reachable + Feast
can talk to the Redis online store. Run via `make verify-docker`.
"""
from __future__ import annotations

import os
import socket
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def step(label: str) -> None:
    print(f"  • {label}")


def can_reach(host: str, port: int, timeout: float = 2.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main() -> int:
    print("Day 19 docker smoke test")
    try:
        # ── 1. Qdrant server ────────────────────────────────────────────
        step("Qdrant server reachable on :6333")
        assert can_reach("127.0.0.1", 6333), \
            "Qdrant not reachable. Run `docker compose up -d` first."
        from qdrant_client import QdrantClient
        client = QdrantClient(url="http://127.0.0.1:6333")
        # Smoke: list collections (empty list is fine)
        cols = client.get_collections()
        print(f"    Qdrant collections: {len(cols.collections)}")

        # ── 2. Redis ────────────────────────────────────────────────────
        step("Redis reachable on :6379")
        assert can_reach("127.0.0.1", 6379), "Redis not reachable."
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=5, socket_timeout=5)
        assert r.ping(), "Redis PING failed"

        # ── 3. Postgres ─────────────────────────────────────────────────
        step("Postgres reachable on :5432")
        assert can_reach("127.0.0.1", 5432), "Postgres not reachable."
        import psycopg
        with psycopg.connect("postgresql://feast:feast@127.0.0.1:5432/feast_offline", connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                assert cur.fetchone() == (1,)
                cur.execute("SELECT COUNT(*) FROM lab19.user_profile")
                assert cur.fetchone()[0] == 101

        step("Feast uses PostgreSQL sources and Redis online serving")
        from feast import FeatureStore
        fs = FeatureStore(repo_path=str(ROOT / "app/feast_repo_docker"))
        assert fs.config.online_store.type == "redis"
        assert fs.config.offline_store.type == "postgres"
        assert len(fs.list_feature_views()) == 3
        values = fs.get_online_features(
            features=["user_profile_features:reading_speed_wpm"],
            entity_rows=[{"user_id": "u_001"}],
        ).to_dict()
        assert values["reading_speed_wpm"] == [187], values
        print("    Real Redis lookup:", values)

        # ── 4. Corpus seeded ────────────────────────────────────────────
        step("Corpus + golden set present")
        assert (ROOT / "data" / "corpus_vn.jsonl").exists(), "Run `make seed` first."
        assert (ROOT / "data" / "golden_set.jsonl").exists(), "Run `make seed` first."

        # ── 5. FastAPI app imports ──────────────────────────────────────
        step("FastAPI app imports without error")
        sys.path.insert(0, str(ROOT))
        from app import main as app_main  # noqa: F401

        print("\nAll checks passed — Qdrant + Postgres + Feast + Redis verified.")
        print("  Qdrant dashboard: http://localhost:6333/dashboard")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\nSmoke test FAILED: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
