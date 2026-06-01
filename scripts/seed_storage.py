"""
Executa uma vez para subir o tse.sqlite local para o Supabase Storage.
Requer SUPABASE_KEY preenchida com a service_role key em .streamlit/secrets.toml.

Uso: python scripts/seed_storage.py
"""

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
secrets_path = ROOT / ".streamlit" / "secrets.toml"

if not secrets_path.exists():
    print("Erro: .streamlit/secrets.toml não encontrado.")
    sys.exit(1)

with open(secrets_path, "rb") as f:
    secrets = tomllib.load(f)

url = secrets["SUPABASE_URL"]
key = secrets["SUPABASE_KEY"]

if "PREENCHA" in key:
    print("Erro: preencha SUPABASE_KEY com a service_role key no secrets.toml.")
    sys.exit(1)

from supabase import create_client  # noqa: E402

client = create_client(url, key)

sqlite_path = ROOT / "tse_core" / "dados" / "tse.sqlite"
if not sqlite_path.exists():
    print(f"Erro: {sqlite_path} não encontrado. Rode `python cli.py ingest` primeiro.")
    sys.exit(1)

data = sqlite_path.read_bytes()
size_mb = len(data) / 1e6
print(f"Enviando {sqlite_path.name} ({size_mb:.1f} MB) para bucket 'tse-data'...")

try:
    client.storage.from_("tse-data").upload(
        "tse.sqlite", data, {"upsert": "true", "content-type": "application/octet-stream"}
    )
    print("Upload concluído.")
except Exception as e:
    print(f"Erro no upload: {e}")
    sys.exit(1)
