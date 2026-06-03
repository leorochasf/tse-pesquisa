"""
Etapa 4 — Inferência de mandatos a partir do resultado de rastrear().

Regras municipais:
- Mandato = 4 anos; posse em 1/jan do ano seguinte à eleição.
- Eleito em X -> mandato X+1 a X+4.
- Reeleição: eleito em eleições consecutivas (ex: 2016 e 2020).
- Suplentes: sinalizados, sem mandato inferido.
"""

from dataclasses import dataclass


@dataclass
class Mandato:
    ano_eleicao: int
    inicio: int       # ano de início (ano_eleicao + 1)
    fim: int          # ano de fim (ano_eleicao + 4)
    reeleicao: bool
    partido: str | None
    sq_candidato: str | None
    cd_municipio: str | None


def inferir_mandatos(resultado_rastrear: dict, duracao: int = 4) -> dict:
    """
    Recebe o dict retornado por rastrear() e retorna:
    {
        'municipio': ...,
        'cargo': ...,
        'mandatos': [Mandato, ...],
        'suplencias': [{'ano': ..., 'partido': ...}, ...],
        'sem_eleicao': [{'ano': ..., 'situacao': ..., 'partido': ...}, ...],
    }
    """
    anos_eleitos: list[dict] = []
    suplencias: list[dict] = []
    sem_eleicao: list[dict] = []

    for item in resultado_rastrear["anos"]:
        if item["eleito"]:
            anos_eleitos.append(item)
        elif item["situacao"] == "SUPLENTE":
            suplencias.append({"ano": item["ano"], "partido": item["partido"]})
        else:
            sem_eleicao.append({
                "ano": item["ano"],
                "situacao": item["situacao"],
                "partido": item["partido"],
            })

    anos_eleitos.sort(key=lambda x: x["ano"])
    anos_vitorias = [e["ano"] for e in anos_eleitos]

    mandatos: list[Mandato] = []
    for i, item in enumerate(anos_eleitos):
        ano = item["ano"]
        reeleicao = i > 0 and anos_vitorias[i - 1] == ano - 4
        mandatos.append(Mandato(
            ano_eleicao=ano,
            inicio=ano + 1,
            fim=ano + duracao,
            reeleicao=reeleicao,
            partido=item["partido"],
            sq_candidato=item.get("sq_candidato"),
            cd_municipio=item.get("cd_municipio"),
        ))

    return {
        "municipio": resultado_rastrear["municipio"],
        "cargo": resultado_rastrear["cargo"],
        "mandatos": mandatos,
        "suplencias": suplencias,
        "sem_eleicao": sem_eleicao,
    }


def formatar_linha_do_tempo(resultado_mandatos: dict, nome: str) -> str:
    """Retorna string formatada da linha do tempo para exibição no terminal."""
    linhas = [
        f"Candidato : {nome}",
        f"Municipio : {resultado_mandatos['municipio']}",
        f"Cargo     : {resultado_mandatos['cargo']}",
        "",
    ]

    mandatos = resultado_mandatos["mandatos"]
    if mandatos:
        linhas.append("Mandatos:")
        for m in mandatos:
            tag = " [REELEICAO]" if m.reeleicao else ""
            linhas.append(
                f"  Eleito {m.ano_eleicao} ({m.partido}) -> "
                f"mandato {m.inicio}-{m.fim}{tag}"
            )
    else:
        linhas.append("Sem mandatos registrados.")

    suplencias = resultado_mandatos["suplencias"]
    if suplencias:
        linhas.append("")
        linhas.append("Suplencias:")
        for s in suplencias:
            linhas.append(f"  {s['ano']} ({s['partido']})")

    sem = resultado_mandatos["sem_eleicao"]
    if sem:
        linhas.append("")
        linhas.append("Nao eleito:")
        for s in sem:
            linhas.append(f"  {s['ano']} - {s['situacao']} ({s['partido']})")

    return "\n".join(linhas)
