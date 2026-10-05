# ---
# jupyter:
#   jupytext:
#     formats: py:percent
# ---

# %% [markdown]
# # NB4 — Feast Feature Store: 3 Feature Views
#
# **Stack:** Feast (LF AI&Data 2024+) + SQLite online store + Parquet offline.
# Maps to slide §6 (Feast Feature Store) + deliverable bullet 3.
#
# > Mục tiêu: định nghĩa 3 feature views, sinh dữ liệu vào offline store
# > (Parquet), `materialize` sang online store (SQLite), gọi
# > `get_online_features` < 10ms — đó là lookup latency rubric.

# %%
import _setup  # noqa: F401
import subprocess
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl

REPO_ROOT = Path(_setup.__file__).resolve().parent.parent
FEAST_DIR = Path(os.environ.get("FEAST_REPO", str(REPO_ROOT / "app" / "feast_repo")))
FEAST_DATA = FEAST_DIR / "data"
FEAST_DATA.mkdir(exist_ok=True)

# %% [markdown]
# ## 1. Sinh dữ liệu offline (Parquet) cho 3 feature views
#
# Trong production, dữ liệu này sẽ đến từ data warehouse (BigQuery/Snowflake/Delta).
# Ở lab, sinh từ corpus + synthetic user activity để học pattern materialize.

# %%
NOW = datetime.now(timezone.utc).replace(microsecond=0)


def make_user_profile(n_users: int = 100) -> pl.DataFrame:
    return pl.DataFrame({
        "user_id": [f"u_{i:03d}" for i in range(n_users)],
        "reading_speed_wpm": [180 + (i * 7) % 200 for i in range(n_users)],
        "preferred_language": ["vi" if i % 3 != 0 else "en" for i in range(n_users)],
        "topic_affinity": [
            ["ai_ml", "cloud", "security", "database", "devops"][i % 5]
            for i in range(n_users)
        ],
        "event_timestamp": [NOW - timedelta(hours=i % 48) for i in range(n_users)],
    })


def make_item_popularity(n_items: int = 1000) -> pl.DataFrame:
    return pl.DataFrame({
        "doc_id": [f"item_{i:04d}" for i in range(n_items)],
        "click_count_24h": [(i * 13) % 500 for i in range(n_items)],
        "ctr_7d": [round(((i * 7) % 100) / 100.0, 3) for i in range(n_items)],
        "avg_dwell_seconds": [10.0 + (i * 0.7) % 90 for i in range(n_items)],
        "event_timestamp": [NOW - timedelta(minutes=i % 720) for i in range(n_items)],
    })


def make_query_velocity(n_users: int = 100) -> pl.DataFrame:
    return pl.DataFrame({
        "user_id": [f"u_{i:03d}" for i in range(n_users)],
        "queries_last_hour": [(i * 11) % 50 for i in range(n_users)],
        "distinct_topics_24h": [1 + (i * 3) % 10 for i in range(n_users)],
        "event_timestamp": [NOW - timedelta(minutes=i % 30) for i in range(n_users)],
    })


profile = make_user_profile()
# Keep two versions for u_001: historical lookup sees the older profile,
# online serving sees the newest. This makes the temporal boundary observable.
older_profile = profile.filter(pl.col("user_id") == "u_001").with_columns(
    pl.lit(170).cast(pl.Int64).alias("reading_speed_wpm"),
    pl.lit("security").alias("topic_affinity"),
    pl.lit(NOW - timedelta(hours=3)).alias("event_timestamp"),
)
profile.vstack(older_profile).write_parquet(FEAST_DATA / "user_profile.parquet")
make_item_popularity().write_parquet(FEAST_DATA / "item_popularity.parquet")
make_query_velocity().write_parquet(FEAST_DATA / "query_velocity.parquet")
print(f"Wrote 3 Parquet sources to {FEAST_DATA}")
for p in sorted(FEAST_DATA.glob("*.parquet")):
    print(f"  {p.name}  {p.stat().st_size/1024:.1f} KB")
if os.environ.get("FEAST_PROFILE") == "docker":
    from sqlalchemy import create_engine
    engine = create_engine("postgresql+psycopg://feast:feast@127.0.0.1:5432/feast_offline", connect_args={"connect_timeout": 5})
    for p in sorted(FEAST_DATA.glob("*.parquet")):
        pl.read_parquet(p).to_pandas().to_sql(p.stem, engine, schema="lab19", if_exists="replace", index=False)
        print("Uploaded PostgreSQL table: lab19." + p.stem)
    engine.dispose()

# %% [markdown]
# ## 2. `feast apply` — register 3 feature views với metadata registry
#
# `app/feast_repo/feature_views.py` đã định nghĩa 3 feature views (xem file đó).
# Chạy `feast apply` để Feast đọc file definition và ghi vào `registry.db`.

# %%
res = subprocess.run(
    ["feast", "apply"],
    cwd=str(FEAST_DIR),
    capture_output=True, text=True, check=False,
)
print("STDOUT:")
print(res.stdout)
if res.stderr:
    print("STDERR:")
    print(res.stderr)
assert res.returncode == 0, f"feast apply failed: {res.stderr}"

# %% [markdown]
# ## 3. `feast materialize` — load offline → online
#
# Feast scan offline store cho mọi sự kiện đến `now`, ghi giá trị mới nhất
# (per entity_key) vào online store. SQLite trong lite path; Redis trong docker path.

# %%
end_dt = NOW.isoformat()
res = subprocess.run(
    # Explicit bounded materialization is repeatable when regenerating the sources.
    # An incremental watermark from a previous run could skip regenerated rows.
    ["feast", "materialize", (NOW - timedelta(days=3)).isoformat(), end_dt],
    cwd=str(FEAST_DIR),
    capture_output=True, text=True, check=False,
)
print(res.stdout[-1500:])
if res.stderr:
    print("STDERR (tail):")
    print(res.stderr[-500:])
assert res.returncode == 0, f"materialize failed: {res.stderr}"
res = subprocess.run(
    ["feast", "materialize-incremental", (NOW + timedelta(seconds=1)).isoformat()],
    cwd=str(FEAST_DIR), capture_output=True, text=True,
)
print("materialize-incremental:", res.stdout, res.stderr)
assert res.returncode == 0, "incremental materialization failed"
res = subprocess.run(["feast", "feature-views", "list"], cwd=str(FEAST_DIR), capture_output=True, text=True)
print("feature-views list:", res.stdout)
assert res.returncode == 0

# %% [markdown]
# ## 4. Online lookup — đo latency
#
# `get_online_features()` query online store cho 1 batch entity rows.
# Rubric threshold: P99 < 10ms cho lookup khi online store là SQLite local
# (Redis/Dynamo trong production sẽ < 5ms).

# %%
import time

from feast import FeatureStore

fs = FeatureStore(repo_path=str(FEAST_DIR))
registered = sorted(view.name for view in fs.list_feature_views())
print("Registered feature views:", registered)
assert registered == ["item_popularity_features", "query_velocity_features", "user_profile_features"]
item_values = fs.get_online_features(
    features=["item_popularity_features:click_count_24h"],
    entity_rows=[{"doc_id": "item_0001"}],
).to_dict()
assert item_values["click_count_24h"][0] == 13
print("Item online lookup:", item_values)

REQUEST_FEATURES = [
    "user_profile_features:reading_speed_wpm",
    "user_profile_features:preferred_language",
    "user_profile_features:topic_affinity",
    "query_velocity_features:queries_last_hour",
    "query_velocity_features:distinct_topics_24h",
]

# Single lookup
t0 = time.perf_counter()
features = fs.get_online_features(
    features=REQUEST_FEATURES,
    entity_rows=[{"user_id": "u_001"}],
).to_dict()
single_latency_ms = (time.perf_counter() - t0) * 1000
print(f"Single lookup: {single_latency_ms:.2f}ms")
print({k: v[0] for k, v in features.items()})

# %% [markdown]
# ## 5. Batch latency benchmark (100 lookups, P99)

# %%
latencies: list[float] = []
for i in range(100):
    user_id = f"u_{i:03d}"
    t0 = time.perf_counter()
    fs.get_online_features(
        features=REQUEST_FEATURES,
        entity_rows=[{"user_id": user_id}],
    ).to_dict()
    latencies.append((time.perf_counter() - t0) * 1000)

latencies.sort()
p50 = latencies[50]
p95 = latencies[95]
p99 = latencies[99]
print(f"Online lookup latency over 100 calls:")
print(f"  P50 = {p50:.2f}ms")
print(f"  P95 = {p95:.2f}ms")
print(f"  P99 = {p99:.2f}ms")

if p99 < 10:
    print(f"PASS — online lookup P99 < 10ms ({p99:.2f}ms)")
else:
    print(f"WARN — P99 = {p99:.2f}ms (SQLite trên macOS thường tốt hơn 5ms; Linux thường tốt hơn 1ms)")

# %% [markdown]
# ## 6. PIT join (offline) — đảm bảo no data leakage
#
# `get_historical_features` thực hiện Point-in-Time join: cho mỗi event row
# `(user_id, ts)`, lấy feature value tại ts đó (không dùng giá trị tương lai).
# Đây là cơ chế chính để tránh training-serving skew (deck §6).

# %%
import pandas as pd
entity_df = pd.DataFrame({
    "user_id": ["u_001", "u_002", "u_003"],
    "event_timestamp": [NOW - timedelta(hours=2), NOW - timedelta(hours=1), NOW],
})

historical = fs.get_historical_features(
    entity_df=entity_df,
    features=[
        "user_profile_features:reading_speed_wpm",
        "user_profile_features:topic_affinity",
    ],
).to_df()
print(historical)

# u_001 newer profile is NOW-1h; its event is NOW-2h.
# Only the older NOW-3h snapshot may be returned.
early = historical.loc[historical.user_id == "u_001", "reading_speed_wpm"]
assert len(early) == 1 and early.iloc[0] == 170, "PIT join leaked a future profile"
assert historical.loc[historical.user_id == "u_001", "topic_affinity"].iloc[0] == "security"
assert historical.loc[historical.user_id == "u_002", "reading_speed_wpm"].iloc[0] == 194
assert len(historical) == 3
assert features["preferred_language"][0] == "vi"
assert features["topic_affinity"][0] == "cloud"
assert features["reading_speed_wpm"][0] == 187
print("PASS — PIT u_001=170/security, online u_001=187/cloud; future profile excluded")

# %% [markdown]
# ## Deliverable evidence
#
# 1. Output cell 2: 3 Parquet files generated.
# 2. Output cell 3: `feast apply` STDOUT showing "Created feature view <name>" × 3.
# 3. Output cell 4: `materialize` log showing rows materialized to online store.
# 4. Output cell 5: 1 online lookup result + latency.
# 5. Output cell 6: 100-lookup P50/P95/P99 + PASS line.
# 6. Output cell 7: PIT join DataFrame (3 rows × features).
#
# ---
#
# ## Vibe-coding callout
#
# **Delegate freely:** Feast feature view YAML / Python definitions follow strict
# patterns (entity → source → schema). AI nails this in 1 shot if you give it
# the schema. Cũng AI tốt cho synthetic data generators (`make_user_profile`).
#
# **Think hard yourself:** **TTL choices** trong feature_views.py — tại sao
# `user_profile_features` TTL=30 ngày nhưng `query_velocity_features` TTL=1 giờ?
# Nếu sai TTL: query_velocity với TTL=30d sẽ trả giá trị cũ → fraud detection
# bỏ lỡ tín hiệu real-time. **PIT join correctness** cũng là *think-hard* —
# nếu data leakage xảy ra, training accuracy đẹp nhưng prod tệ 20-30% (deck §6).
# Đừng để AI tự chọn TTL hay timestamp_field — bạn phải biết business semantics.
