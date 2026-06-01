from tse_core.db import conectar

conn = conectar()

print("=== Contagem por situacao_turno ===")
rows = conn.execute("""
    SELECT situacao_turno, COUNT(*) as total
    FROM candidatura
    WHERE ano = 2024 AND uf = 'GO'
    GROUP BY situacao_turno
    ORDER BY total DESC
""").fetchall()
for r in rows:
    print(f"  {r['situacao_turno']}: {r['total']}")

print("\n=== Exemplo: Inaciolandia (busca parcial) ===")
rows = conn.execute("""
    SELECT nm_municipio, cd_municipio, ds_cargo, nm_candidato, nm_urna, sg_partido, situacao_turno
    FROM candidatura
    WHERE ano = 2024 AND uf = 'GO'
      AND nm_municipio LIKE '%INACI%'
    ORDER BY cd_cargo, situacao_turno, nm_candidato
""").fetchall()
for r in rows:
    print(f"  [{r['situacao_turno']}] {r['nm_candidato']} ({r['sg_partido']}) - {r['ds_cargo']} - {r['nm_municipio']} ({r['cd_municipio']})")

print("\n=== Total geral ===")
total = conn.execute("SELECT COUNT(*) FROM candidatura WHERE ano=2024 AND uf='GO'").fetchone()[0]
print(f"  {total} registros")
