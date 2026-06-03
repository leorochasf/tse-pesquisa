"""
Acesso à API do DivulgaCandContas (TSE) — não-oficial.

Centraliza o mapa de cdEleicao, a lista de candidatos por município/cargo
(usada no enriquecimento de situação) e a ficha individual do candidato
(usada para bens declarados / patrimônio). Todas as funções cacheiam em disco.
"""

import json
import os
import tempfile
import time
import urllib.request

# cdEleicao do DivulgaCandContas por ano (eleições municipais). Não confundir
# com CD_ELEICAO dos dados abertos — é o id usado na API/URL do site.
CD_ELEICAO_DIVULGA = {2012: "1699", 2016: "2", 2020: "2030402020", 2024: "2045202024"}

_BASE = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1/candidatura"
_LISTA_URL = _BASE + "/listar/{ano}/{municipio}/{cd_eleicao}/{cargo}/candidatos"
_FICHA_URL = _BASE + "/buscar/{ano}/{municipio}/{cd_eleicao}/candidato/{sq}"

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
_CACHE_LISTA = os.path.join(_CACHE_DIR, "divulga")
# Ficha é consultada em runtime (inclusive na Vercel, onde só /tmp é gravável).
_CACHE_FICHA = os.path.join(tempfile.gettempdir(), "tse_ficha")


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def buscar_lista(ano: int, municipio: str, cargo: str, cd_eleicao: str) -> list[dict]:
    """Lista de candidatos de um (ano/município/cargo), com cache em disco."""
    os.makedirs(_CACHE_LISTA, exist_ok=True)
    cache_path = os.path.join(_CACHE_LISTA, f"{ano}_{municipio}_{cargo}.json")
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f).get("candidatos", [])
    data = _get_json(_LISTA_URL.format(ano=ano, municipio=municipio, cd_eleicao=cd_eleicao, cargo=cargo))
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    time.sleep(0.2)
    return data.get("candidatos", [])


def buscar_ficha(ano: int, municipio: str, sq: str) -> dict:
    """
    Ficha individual do candidato — patrimônio declarado.
    Retorna payload enxuto: {ano, total_bens (R$), bens [{descricao,tipo,valor}], divulga_bens}.
    Cache em disco. `ano` pode vir como str.
    """
    ano = int(ano)
    cd_eleicao = CD_ELEICAO_DIVULGA.get(ano)
    if not cd_eleicao:
        return {"ano": ano, "total_bens": None, "bens": [], "divulga_bens": False}

    cache_path = os.path.join(_CACHE_FICHA, f"{ano}_{municipio}_{sq}.json")
    d = None
    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = None
    if d is None:
        d = _get_json(_FICHA_URL.format(ano=ano, municipio=municipio, cd_eleicao=cd_eleicao, sq=sq))
        try:  # cache best-effort — disco pode ser só-leitura (serverless)
            os.makedirs(_CACHE_FICHA, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(d, f)
        except OSError:
            pass

    bens = [
        {
            "descricao": b.get("descricao"),
            "tipo": b.get("descricaoDeTipoDeBem"),
            "valor": b.get("valor"),
        }
        for b in (d.get("bens") or [])
    ]
    return {
        "ano": ano,
        "total_bens": d.get("totalDeBens"),
        "bens": bens,
        "divulga_bens": bool(d.get("st_DIVULGA_BENS")),
    }
