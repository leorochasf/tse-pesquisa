"""Baixa o ZIP do TSE e imprime o header do CSV de GO sem salvar tudo no disco."""
import io
import zipfile
import urllib.request

ANO = 2024
URL = f"https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{ANO}.zip"

print(f"Baixando {URL} ...")
with urllib.request.urlopen(URL, timeout=120) as resp:
    data = resp.read()

print(f"ZIP baixado: {len(data)/1e6:.1f} MB")

with zipfile.ZipFile(io.BytesIO(data)) as zf:
    nomes = zf.namelist()
    print(f"\nArquivos no ZIP ({len(nomes)}):")
    for n in sorted(nomes):
        print(f"  {n}")

    # Pega o CSV de GO
    alvo = next((n for n in nomes if "GO" in n.upper() and n.endswith(".csv")), None)
    if not alvo:
        print("\nNenhum arquivo GO encontrado!")
    else:
        print(f"\nLendo header de: {alvo}")
        with zf.open(alvo) as f:
            header = f.readline().decode("latin-1").strip()
        colunas = header.split(";")
        print(f"\nColunas ({len(colunas)}):")
        for i, c in enumerate(colunas):
            print(f"  {i:2d}. {c}")

        # Lê também a primeira linha de dados para ver exemplos
        with zf.open(alvo) as f:
            f.readline()  # pula header
            linha = f.readline().decode("latin-1").strip()
        valores = linha.split(";")
        print("\nPrimeira linha de dados (exemplo):")
        for i, (c, v) in enumerate(zip(colunas, valores)):
            print(f"  {c}: {v}")
