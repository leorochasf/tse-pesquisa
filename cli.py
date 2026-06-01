"""
CLI da Ferramenta TSE — MVP externo.

Subcomandos:
  ingest   Baixa e importa os CSVs do TSE para o SQLite local.
  listar   Lista candidatos por municipio, cargo e ano.
  rastrear Rastreia uma pessoa ao longo de varias eleicoes com linha do tempo de mandatos.
"""

import argparse
import csv as csv_mod
import sys

from tse_core.db import criar_schema


# ─── Exportacao ────────────────────────────────────────────────────────────────

def _exportar_excel(candidatos: list[dict], caminho: str) -> None:
    from tse_core.export import gerar_excel
    with open(caminho, "wb") as f:
        f.write(gerar_excel(candidatos))
    print(f"Excel salvo: {caminho}")


def _exportar_csv(candidatos: list[dict], caminho: str) -> None:
    campos = ["ano", "municipio", "cargo", "nome", "urna", "partido", "situacao"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv_mod.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidatos)
    print(f"CSV salvo: {caminho}")


# ─── Formatacao terminal ───────────────────────────────────────────────────────

def _imprimir_tabela(candidatos: list[dict]) -> None:
    if not candidatos:
        print("Nenhum candidato encontrado.")
        return

    col_nome = max(len(c["nome"]) for c in candidatos)
    col_urna = max(len(c["urna"] or "") for c in candidatos)
    col_partido = max(len(c["partido"] or "") for c in candidatos)
    col_sit = max(len(c["situacao"]) for c in candidatos)

    fmt = f"  {{:<{col_nome}}}  {{:<{col_urna}}}  {{:<{col_partido}}}  {{:<{col_sit}}}"
    sep = "  " + "-" * (col_nome + col_urna + col_partido + col_sit + 6)

    print(f"\n{candidatos[0]['cargo']} — {candidatos[0]['municipio']} ({candidatos[0]['ano']})")
    print(sep)
    print(fmt.format("NOME", "NOME URNA", "PARTIDO", "SITUACAO"))
    print(sep)
    for c in candidatos:
        print(fmt.format(c["nome"], c["urna"] or "", c["partido"] or "", c["situacao"]))
    print(sep)
    print(f"  Total: {len(candidatos)} candidatos")


# ─── Comandos ─────────────────────────────────────────────────────────────────

def cmd_ingest(args):
    from tse_core.ingest import importar
    for ano in args.anos:
        total = importar(ano, uf=args.uf)
        print(f"  [OK] {ano}/{args.uf.upper()}: {total} registros")


def cmd_listar(args):
    from tse_core.consulta import listar
    try:
        candidatos = listar(args.ano, args.municipio, args.cargo)
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)

    _imprimir_tabela(candidatos)

    if args.excel:
        _exportar_excel(candidatos, args.excel)
    if args.csv:
        _exportar_csv(candidatos, args.csv)


def cmd_rastrear(args):
    from tse_core.consulta import rastrear
    from tse_core.mandato import inferir_mandatos, formatar_linha_do_tempo
    try:
        resultado = rastrear(args.nome, args.municipio, args.cargo)
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)

    if resultado["homonimos"]:
        print("Atencao: multiplos candidatos encontrados com nome similar:")
        for n in resultado["homonimos"]:
            print(f"  - {n}")
        print("Use o nome completo para refinar a busca.\n")

    if not resultado["anos"]:
        print(f"Nenhum registro encontrado para '{args.nome}' em {args.municipio}/{args.cargo}.")
        print(f"Anos pesquisados: {resultado['anos_pesquisados']}")
        return

    mandatos = inferir_mandatos(resultado)
    print(formatar_linha_do_tempo(mandatos, args.nome.upper()))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    criar_schema()

    parser = argparse.ArgumentParser(
        description="Ferramenta TSE — consulta de eleitos e mandatos"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Importa CSVs do TSE para o SQLite")
    p_ingest.add_argument("--anos", nargs="+", type=int, required=True, metavar="ANO")
    p_ingest.add_argument("--uf", default="GO")

    # listar
    p_listar = sub.add_parser("listar", help="Lista candidatos por municipio/cargo/ano")
    p_listar.add_argument("--municipio", required=True)
    p_listar.add_argument("--cargo", required=True, help="Ex: vereador, prefeito")
    p_listar.add_argument("--ano", type=int, required=True)
    p_listar.add_argument("--excel", metavar="ARQUIVO.xlsx")
    p_listar.add_argument("--csv", metavar="ARQUIVO.csv")

    # rastrear
    p_rastrear = sub.add_parser("rastrear", help="Rastreia pessoa entre eleicoes")
    p_rastrear.add_argument("--nome", required=True)
    p_rastrear.add_argument("--municipio", required=True)
    p_rastrear.add_argument("--cargo", required=True)

    args = parser.parse_args()
    dispatch = {"ingest": cmd_ingest, "listar": cmd_listar, "rastrear": cmd_rastrear}
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
