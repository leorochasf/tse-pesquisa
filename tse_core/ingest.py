"""
Etapa 1 — Ingest do CSV oficial do TSE (consulta_cand).

Baixa o ZIP do ano pedido (com cache local), extrai o CSV da UF e
popula a tabela candidatura no SQLite. Idempotente: limpa o ano+uf
antes de reinserir.
"""

import csv
import io
import json
import os
import time
import urllib.request
import zipfile

from .db import conectar, criar_schema

# cdEleicao do DivulgaCandContas por ano (eleições municipais). Não confundir
# com CD_ELEICAO dos dados abertos — é o id usado na API/URL do site.
_CD_ELEICAO_DIVULGA = {2012: "1699", 2016: "2", 2020: "2030402020", 2024: "2045202024"}
_LISTA_URL = (
    "https://divulgacandcontas.tse.jus.br/divulga/rest/v1/candidatura/listar/"
    "{ano}/{municipio}/{cd_eleicao}/{cargo}/candidatos"
)

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
_URL_TEMPLATE = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/"
    "consulta_cand_{ano}.zip"
)

_COL_MAP = {
    "ANO_ELEICAO":        "ano",
    "SG_UF":              "uf",
    "SG_UE":              "cd_municipio",
    "NM_UE":              "nm_municipio",
    "CD_CARGO":           "cd_cargo",
    "DS_CARGO":           "ds_cargo",
    "NR_CPF_CANDIDATO":   "nr_cpf",
    "SQ_CANDIDATO":       "sq_candidato",
    "NM_CANDIDATO":       "nm_candidato",
    "NM_URNA_CANDIDATO":  "nm_urna",
    "SG_PARTIDO":         "sg_partido",
    "DS_SIT_TOT_TURNO":   "situacao_turno",
}

_INSERT = """
    INSERT INTO candidatura
        (ano, uf, cd_municipio, nm_municipio, cd_cargo, ds_cargo,
         nr_cpf, sq_candidato, nm_candidato, nm_urna, sg_partido, situacao_turno)
    VALUES
        (:ano, :uf, :cd_municipio, :nm_municipio, :cd_cargo, :ds_cargo,
         :nr_cpf, :sq_candidato, :nm_candidato, :nm_urna, :sg_partido, :situacao_turno)
"""


_CACHE_DIVULGA = os.path.join(_CACHE_DIR, "divulga")


def _buscar_lista(ano: int, municipio: str, cargo: str, cd_eleicao: str) -> list[dict]:
    """Lista de candidatos de um (ano/município/cargo) via API do DivulgaCandContas, com cache em disco."""
    os.makedirs(_CACHE_DIVULGA, exist_ok=True)
    cache_path = os.path.join(_CACHE_DIVULGA, f"{ano}_{municipio}_{cargo}.json")
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f).get("candidatos", [])
    url = _LISTA_URL.format(ano=ano, municipio=municipio, cd_eleicao=cd_eleicao, cargo=cargo)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    time.sleep(0.2)
    return data.get("candidatos", [])


def enriquecer_situacao(uf: str = "GO", db_path: str = None) -> int:
    """
    Completa candidaturas sem resultado de totalização (situacao_turno nulo/#NULO)
    com dados da API do DivulgaCandContas:
      - Se a API tem o resultado real da votação (Eleito/Não eleito/Suplente),
        corrige `situacao_turno` (assim eleito/mandato/ordenação ficam corretos).
      - Caso contrário (Indeferido/Renúncia/Cancelado/...), grava o motivo em
        `situacao_candidatura`.
    Idempotente: só processa linhas ainda #NULO e sem situacao_candidatura.
    """
    conn = conectar(db_path) if db_path else conectar()

    combos = conn.execute(
        """
        SELECT DISTINCT ano, cd_municipio, cd_cargo
        FROM candidatura
        WHERE uf = ? AND cd_cargo IN ('11', '13')
          AND (situacao_turno IS NULL OR situacao_turno LIKE '#%')
          AND situacao_candidatura IS NULL
        """,
        (uf.upper(),),
    ).fetchall()

    print(f"[enriquecer] {len(combos)} combinações (ano/município/cargo) a consultar...")
    atualizados = 0
    for i, c in enumerate(combos, 1):
        ano, municipio, cargo = c["ano"], c["cd_municipio"], c["cd_cargo"]
        cd_eleicao = _CD_ELEICAO_DIVULGA.get(ano)
        if not cd_eleicao:
            continue
        try:
            candidatos = _buscar_lista(ano, municipio, cargo, cd_eleicao)
        except Exception as e:
            print(f"  [{i}/{len(combos)}] {ano}/{municipio}/{cargo}: ERRO {e}")
            continue

        with conn:
            for cand in candidatos:
                sq = str(cand.get("id"))
                totalizacao = (cand.get("descricaoTotalizacao") or "").strip()
                registro = (cand.get("descricaoSituacao") or "").strip()
                cond = "WHERE uf = ? AND ano = ? AND sq_candidato = ? AND (situacao_turno IS NULL OR situacao_turno LIKE '#%')"
                if totalizacao and totalizacao.upper() != "CONCORRENDO":
                    # Resultado real existe na API — corrige a totalização.
                    cur = conn.execute(
                        f"UPDATE candidatura SET situacao_turno = ? {cond}",
                        (totalizacao.upper(), uf.upper(), ano, sq),
                    )
                elif registro:
                    # Sem resultado de votação — registra o motivo (Indeferido/Renúncia/...).
                    cur = conn.execute(
                        f"UPDATE candidatura SET situacao_candidatura = ? {cond}",
                        (registro, uf.upper(), ano, sq),
                    )
                else:
                    continue
                atualizados += cur.rowcount
        if i % 50 == 0:
            print(f"  [{i}/{len(combos)}] ... {atualizados} linhas atualizadas")

    print(f"[enriquecer] concluído: {atualizados} linhas atualizadas.")
    return atualizados


def _zip_path(ano: int) -> str:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    return os.path.join(_CACHE_DIR, f"consulta_cand_{ano}.zip")


def _baixar(ano: int) -> str:
    path = _zip_path(ano)
    if os.path.exists(path):
        print(f"  ZIP já em cache: {path}")
        return path
    url = _URL_TEMPLATE.format(ano=ano)
    print(f"  Baixando {url} ...")
    urllib.request.urlretrieve(url, path)
    size_mb = os.path.getsize(path) / 1e6
    print(f"  Baixado: {size_mb:.1f} MB -> {path}")
    return path


def _csv_nome(ano: int, uf: str) -> str:
    return f"consulta_cand_{ano}_{uf.upper()}.csv"


def _ler_registros(zip_path: str, ano: int, uf: str) -> list[dict]:
    nome = _csv_nome(ano, uf)
    with zipfile.ZipFile(zip_path) as zf:
        if nome not in zf.namelist():
            raise FileNotFoundError(
                f"Arquivo {nome} não encontrado no ZIP. "
                f"Arquivos disponíveis: {zf.namelist()}"
            )
        with zf.open(nome) as f:
            texto = f.read().decode("latin-1")

    reader = csv.DictReader(
        io.StringIO(texto),
        delimiter=";",
        quotechar='"',
    )
    # Strip quotes dos nomes de coluna (alguns anos vêm com aspas extras)
    reader.fieldnames = [c.strip('"').strip() for c in reader.fieldnames]

    registros = []
    for row in reader:
        rec = {}
        for csv_col, db_col in _COL_MAP.items():
            valor = row.get(csv_col, "").strip().strip('"')
            # Normaliza valores nulos do TSE
            if valor in ("#NULO", "#NE", "-1", "-3", "-4", ""):
                valor = None
            rec[db_col] = valor
        registros.append(rec)
    return registros


def importar(ano: int, uf: str = "GO", db_path: str = None) -> int:
    """
    Importa candidatos de `uf` no `ano` para o SQLite.
    Retorna a quantidade de registros inseridos.
    """
    criar_schema(db_path) if db_path else criar_schema()
    conn = conectar(db_path) if db_path else conectar()

    print(f"\n[ingest] Importando {ano}/{uf.upper()} ...")
    zip_path = _baixar(ano)
    registros = _ler_registros(zip_path, ano, uf)
    print(f"  Registros lidos do CSV: {len(registros)}")

    with conn:
        conn.execute(
            "DELETE FROM candidatura WHERE ano = ? AND uf = ?",
            (ano, uf.upper()),
        )
        conn.executemany(_INSERT, registros)

    total = conn.execute(
        "SELECT COUNT(*) FROM candidatura WHERE ano = ? AND uf = ?",
        (ano, uf.upper()),
    ).fetchone()[0]
    print(f"  Registros no banco após ingest: {total}")
    return total
