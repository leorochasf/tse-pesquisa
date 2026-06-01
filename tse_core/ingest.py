"""
Etapa 1 — Ingest do CSV oficial do TSE (consulta_cand).

Baixa o ZIP do ano pedido (com cache local), extrai o CSV da UF e
popula a tabela candidatura no SQLite. Idempotente: limpa o ano+uf
antes de reinserir.
"""

import csv
import io
import os
import urllib.request
import zipfile

from .db import conectar, criar_schema

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
    "NM_CANDIDATO":       "nm_candidato",
    "NM_URNA_CANDIDATO":  "nm_urna",
    "SG_PARTIDO":         "sg_partido",
    "DS_SIT_TOT_TURNO":   "situacao_turno",
}

_INSERT = """
    INSERT INTO candidatura
        (ano, uf, cd_municipio, nm_municipio, cd_cargo, ds_cargo,
         nr_cpf, nm_candidato, nm_urna, sg_partido, situacao_turno)
    VALUES
        (:ano, :uf, :cd_municipio, :nm_municipio, :cd_cargo, :ds_cargo,
         :nr_cpf, :nm_candidato, :nm_urna, :sg_partido, :situacao_turno)
"""


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
