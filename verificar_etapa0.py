from tse_core.db import criar_schema, conectar

criar_schema()
conn = conectar()
rows = conn.execute("PRAGMA table_info(candidatura)").fetchall()
print("Colunas da tabela candidatura:")
for r in rows:
    print(f"  {r['cid']}. {r['name']} ({r['type']})")

indices = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
print("\nIndices:")
for i in indices:
    print(f"  {i['name']}")

print("\nEtapa 0 OK")
