"""Prepare a separate Feast repository with real Postgres sources and Redis serving."""
from pathlib import Path
import re
import psycopg

ROOT = Path(__file__).resolve().parent.parent
repo = ROOT / "app" / "feast_repo_docker"
repo.mkdir(exist_ok=True)
with psycopg.connect("postgresql://feast:feast@127.0.0.1:5432/feast_offline", connect_timeout=5) as conn:
    conn.execute("CREATE SCHEMA IF NOT EXISTS lab19")
definitions = (ROOT / "app/feast_repo/feature_views.py").read_text(encoding="utf-8")
definitions = definitions.replace("Field, FileSource, ValueType", "Field, ValueType")
definitions += "\n"
definitions = definitions.replace("from feast.types import", "from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource\nfrom feast.types import")
definitions = definitions.replace("FileSource(", "PostgreSQLSource(")
definitions = re.sub(r'path=str\(_DATA_DIR / "([a-z_]+)\.parquet"\)', r'table="lab19.\1"', definitions)
(repo / "feature_views.py").write_text(definitions, encoding="utf-8")
(repo / "feature_store.yaml").write_text('''project: lab19_docker
provider: local
registry: registry.db
online_store:
  type: redis
  connection_string: 127.0.0.1:6379
offline_store:
  type: postgres
  host: 127.0.0.1
  port: 5432
  database: feast_offline
  user: feast
  password: feast
  db_schema: lab19
  sslmode: disable
entity_key_serialization_version: 3
''', encoding="utf-8")
print("Configured:", repo)
