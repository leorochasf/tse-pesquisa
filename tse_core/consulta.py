"""
Etapas 2 e 4 — Consultas: listar() e rastrear().
"""

import unicodedata
from .db import conectar
from .dados.cargos import resolver_cargo

_SITUACOES_ELEITO = {"ELEITO", "ELEITO POR QP", "ELEITO POR MEDIA", "ELEITO POR MÉDIA"}


def _normalizar(texto: str) -> str:
    """Remove acentos e converte para maiúsculo para comparação."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.upper())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _resolver_municipio(conn, municipio: str, ano: int, uf: str) -> list[dict]:
    """Busca municípios que correspondam ao texto, sem acento e case-insensitive."""
    rows = conn.execute(
        "SELECT DISTINCT cd_municipio, nm_municipio FROM candidatura "
        "WHERE ano = ? AND uf = ?",
        (ano, uf.upper()),
    ).fetchall()
    alvo = _normalizar(municipio)
    return [r for r in rows if alvo in _normalizar(r["nm_municipio"])]


def listar_anos(uf: str) -> list[int]:
    """Retorna os anos disponíveis na base para a UF, em ordem crescente."""
    conn = conectar()
    rows = conn.execute(
        "SELECT DISTINCT ano FROM candidatura WHERE uf = ? ORDER BY ano",
        (uf.upper(),),
    ).fetchall()
    return [r["ano"] for r in rows]


def listar_municipios(uf: str, ano: int = None) -> list[str]:
    """Retorna municípios disponíveis para a UF (e opcionalmente ano), em ordem alfabética."""
    conn = conectar()
    if ano is not None:
        rows = conn.execute(
            "SELECT DISTINCT nm_municipio FROM candidatura WHERE uf = ? AND ano = ? ORDER BY nm_municipio",
            (uf.upper(), ano),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT DISTINCT nm_municipio FROM candidatura WHERE uf = ? ORDER BY nm_municipio",
            (uf.upper(),),
        ).fetchall()
    return [r["nm_municipio"] for r in rows]


def listar(
    ano: int,
    municipio: str,
    cargo: str,
    uf: str = "GO",
    db_path: str = None,
) -> list[dict]:
    """
    Retorna candidatos para municipio+cargo+ano, ordenados por situação e nome.
    Raises ValueError se municipio ou cargo não forem encontrados.
    """
    conn = conectar(db_path) if db_path else conectar()

    cd_cargo = resolver_cargo(cargo)
    if cd_cargo is None:
        raise ValueError(f"Cargo nao reconhecido: '{cargo}'. Use: prefeito, vereador, etc.")

    municipios = _resolver_municipio(conn, municipio, ano, uf)
    if not municipios:
        raise ValueError(f"Municipio '{municipio}' nao encontrado para {ano}/{uf.upper()}.")
    if len(municipios) > 1:
        nomes = ", ".join(r["nm_municipio"] for r in municipios)
        raise ValueError(f"Municipio ambiguo — encontrados: {nomes}. Seja mais especifico.")

    cd_municipio = municipios[0]["cd_municipio"]
    nm_municipio = municipios[0]["nm_municipio"]

    rows = conn.execute(
        """
        SELECT nm_candidato, nm_urna, sg_partido, situacao_turno, ds_cargo, sq_candidato
        FROM candidatura
        WHERE ano = ? AND uf = ? AND cd_municipio = ? AND cd_cargo = ?
        ORDER BY
            CASE situacao_turno
                WHEN 'ELEITO'           THEN 1
                WHEN 'ELEITO POR QP'    THEN 2
                WHEN 'ELEITO POR MEDIA' THEN 3
                WHEN 'ELEITO POR MÉDIA' THEN 3
                WHEN 'SUPLENTE'         THEN 4
                WHEN 'NAO ELEITO'       THEN 5
                WHEN 'NÃO ELEITO'       THEN 5
                ELSE 6
            END,
            nm_candidato
        """,
        (ano, uf.upper(), cd_municipio, cd_cargo),
    ).fetchall()

    return [
        {
            "ano": ano,
            "municipio": nm_municipio,
            "cd_municipio": cd_municipio,
            "cargo": dict(row)["ds_cargo"],
            "nome": row["nm_candidato"],
            "urna": row["nm_urna"],
            "partido": row["sg_partido"],
            "situacao": row["situacao_turno"] or "SEM INFO",
            "eleito": (row["situacao_turno"] or "") in _SITUACOES_ELEITO
                      or _normalizar(row["situacao_turno"] or "").startswith("ELEITO"),
            "sq_candidato": row["sq_candidato"],
        }
        for row in rows
    ]


def rastrear(
    nome: str,
    municipio: str,
    cargo: str,
    uf: str = "GO",
    anos: list[int] | None = None,
    db_path: str = None,
) -> dict:
    """
    Rastreia uma pessoa pelo nome ao longo de várias eleições.
    Retorna dict com chave 'anos' (lista de resultados por ano) e 'homônimos'
    (lista de nomes distintos encontrados, para desambiguação se > 1).
    """
    conn = conectar(db_path) if db_path else conectar()

    cd_cargo = resolver_cargo(cargo)
    if cd_cargo is None:
        raise ValueError(f"Cargo nao reconhecido: '{cargo}'.")

    municipios = _resolver_municipio(conn, municipio, anos[0] if anos else 2024, uf)
    if not municipios:
        # Tenta em qualquer ano disponível
        rows_mun = conn.execute(
            "SELECT DISTINCT cd_municipio, nm_municipio FROM candidatura WHERE uf = ?",
            (uf.upper(),)
        ).fetchall()
        alvo = _normalizar(municipio)
        municipios = [r for r in rows_mun if alvo in _normalizar(r["nm_municipio"])]
    if not municipios:
        raise ValueError(f"Municipio '{municipio}' nao encontrado.")
    if len(municipios) > 1:
        nomes = ", ".join(r["nm_municipio"] for r in municipios)
        raise ValueError(f"Municipio ambiguo: {nomes}")

    cd_municipio = municipios[0]["cd_municipio"]
    nm_municipio = municipios[0]["nm_municipio"]

    # Anos disponíveis para esse município+cargo
    anos_disponiveis = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT ano FROM candidatura "
            "WHERE uf = ? AND cd_municipio = ? AND cd_cargo = ? ORDER BY ano",
            (uf.upper(), cd_municipio, cd_cargo),
        ).fetchall()
    ]
    anos_busca = [a for a in anos_disponiveis if a in anos] if anos else anos_disponiveis

    alvo_nome = _normalizar(nome)
    resultados = []
    nomes_encontrados = set()

    for ano in anos_busca:
        rows = conn.execute(
            "SELECT nm_candidato, nm_urna, sg_partido, situacao_turno, sq_candidato "
            "FROM candidatura "
            "WHERE ano = ? AND uf = ? AND cd_municipio = ? AND cd_cargo = ?",
            (ano, uf.upper(), cd_municipio, cd_cargo),
        ).fetchall()

        for row in rows:
            nm = _normalizar(row["nm_candidato"] or "")
            nu = _normalizar(row["nm_urna"] or "")
            if alvo_nome in nm or alvo_nome in nu or nm in alvo_nome:
                nomes_encontrados.add(row["nm_candidato"])
                resultados.append({
                    "ano": ano,
                    "nome": row["nm_candidato"],
                    "urna": row["nm_urna"],
                    "partido": row["sg_partido"],
                    "situacao": row["situacao_turno"] or "SEM INFO",
                    "eleito": (row["situacao_turno"] or "") in _SITUACOES_ELEITO
                              or _normalizar(row["situacao_turno"] or "").startswith("ELEITO"),
                    "sq_candidato": row["sq_candidato"],
                    "cd_municipio": cd_municipio,
                })

    return {
        "municipio": nm_municipio,
        "cargo": cargo.upper(),
        "anos_pesquisados": anos_busca,
        "anos": resultados,
        "homonimos": sorted(nomes_encontrados) if len({_normalizar(n) for n in nomes_encontrados}) > 1 else [],
    }
