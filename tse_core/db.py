import sqlite3
import os

_DB_DEFAULT = os.path.join(os.path.dirname(__file__), "dados", "tse.sqlite")


def _resolve_db_path(db_path: str | None) -> str:
    if db_path is not None:
        return db_path
    return os.environ.get("TSE_DB_PATH") or _DB_DEFAULT


def conectar(db_path: str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_resolve_db_path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def criar_schema(db_path: str = None) -> None:
    with conectar(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS candidatura (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ano           INTEGER NOT NULL,
                uf            TEXT    NOT NULL,
                cd_municipio  TEXT    NOT NULL,
                nm_municipio  TEXT    NOT NULL,
                cd_cargo      TEXT    NOT NULL,
                ds_cargo      TEXT    NOT NULL,
                nr_cpf        TEXT,
                sq_candidato  TEXT,
                nm_candidato  TEXT    NOT NULL,
                nm_urna       TEXT,
                sg_partido    TEXT,
                situacao_turno TEXT,
                situacao_candidatura TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_ano_mun_cargo
                ON candidatura (ano, cd_municipio, cd_cargo);

            CREATE INDEX IF NOT EXISTS idx_nm_candidato
                ON candidatura (nm_candidato);
        """)
