"""
Ferramenta TSE — função serverless Vercel.
Despacha por ?action= (anos, municipios, listar, rastrear, excel).
"""

import json
import os
import sys
import dataclasses
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Garante que tse_core é importável a partir da raiz do projeto
_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ── Download do sqlite do Supabase Storage ─────────────────────────────────────

_DB_TMP = "/tmp/tse.sqlite"


def _garantir_db() -> None:
    """Baixa tse.sqlite do Supabase Storage para /tmp se ainda não existir."""
    if os.path.exists(_DB_TMP):
        os.environ["TSE_DB_PATH"] = _DB_TMP
        return

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        # fallback: usa sqlite local (para vercel dev / testes sem Storage)
        return

    import requests  # noqa: PLC0415

    storage_url = f"{url.rstrip('/')}/storage/v1/object/tse-data/tse.sqlite"
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    resp = requests.get(storage_url, headers=headers, timeout=30)
    resp.raise_for_status()

    with open(_DB_TMP, "wb") as f:
        f.write(resp.content)

    os.environ["TSE_DB_PATH"] = _DB_TMP


# ── Actions ───────────────────────────────────────────────────────────────────

def _action_anos(params: dict) -> dict:
    from tse_core.consulta import listar_anos
    return {"anos": listar_anos("GO")}


def _action_municipios(params: dict) -> dict:
    from tse_core.consulta import listar_municipios
    ano = int(params["ano"][0]) if "ano" in params else None
    return {"municipios": listar_municipios("GO", ano)}


def _action_listar(params: dict) -> dict:
    from tse_core.consulta import listar
    ano = int(params["ano"][0])
    municipio = params["municipio"][0]
    cargo = params["cargo"][0]
    candidatos = listar(ano, municipio, cargo)
    eleitos = [c for c in candidatos if c["eleito"]]
    nao_eleitos = [c for c in candidatos if not c["eleito"]]
    return {"eleitos": eleitos, "nao_eleitos": nao_eleitos}


def _action_rastrear(params: dict) -> dict:
    from tse_core.consulta import rastrear
    from tse_core.mandato import inferir_mandatos
    nome = params["nome"][0]
    municipio = params["municipio"][0]
    cargo = params["cargo"][0]
    resultado = rastrear(nome, municipio, cargo)
    inf = inferir_mandatos(resultado)
    return {
        "municipio": inf["municipio"],
        "cargo": inf["cargo"],
        "mandatos": [dataclasses.asdict(m) for m in inf["mandatos"]],
        "suplencias": inf["suplencias"],
        "sem_eleicao": inf["sem_eleicao"],
        "homonimos": resultado["homonimos"],
        "cpf": inf["cpf"],
        "cpfs_distintos": inf["cpfs_distintos"],
    }


def _action_ficha(params: dict) -> dict:
    from tse_core.tse_api import buscar_ficha
    ano = params["ano"][0]
    municipio = params["municipio"][0]
    sq = params["sq"][0]
    return buscar_ficha(ano, municipio, sq)


def _action_ia_status(params: dict) -> dict:
    """Diagnóstico: diz se a chave/modelo chegaram à função (sem expor a chave)."""
    from tse_core.ia import _get_secret, _MODEL_PADRAO
    chave = _get_secret("OPENROUTER_API_KEY")
    return {
        "configurada": bool(chave),
        "prefixo": (chave[:7] + "…") if chave else None,
        "modelo": _get_secret("OPENROUTER_MODEL") or _MODEL_PADRAO,
    }


def _action_parecer(params: dict) -> dict:
    from tse_core.ia import montar_contexto_pessoa, chamar_openrouter, _SISTEMA
    ctx = montar_contexto_pessoa(params["nome"][0], params["municipio"][0], params["cargo"][0])
    texto = chamar_openrouter([
        {"role": "system", "content": _SISTEMA},
        {"role": "user", "content": (
            ctx["contexto"] + "\n\n---\nGere um PARECER DE TRIAGEM sucinto: (1) pontos de atenção "
            "(red flags); (2) encaminhamento sugerido (arquivar / aprofundar / instaurar), "
            "com a ressalva de que é apoio à triagem, não decisão."
        )},
    ])
    return {"parecer": texto}


def _action_excel(params: dict) -> bytes:
    from tse_core.consulta import listar
    from tse_core.export import gerar_excel
    ano = int(params["ano"][0])
    municipio = params["municipio"][0]
    cargo = params["cargo"][0]
    candidatos = listar(ano, municipio, cargo)
    return gerar_excel(candidatos)


# ── Handler ───────────────────────────────────────────────────────────────────

_EXCEL_ACTIONS = {"excel"}
_ACTIONS = {
    "anos": _action_anos,
    "municipios": _action_municipios,
    "listar": _action_listar,
    "rastrear": _action_rastrear,
    "ficha": _action_ficha,
    "parecer": _action_parecer,
    "ia_status": _action_ia_status,
}


class handler(BaseHTTPRequestHandler):  # noqa: N801

    def log_message(self, *args):  # silencia logs de request do stdlib
        pass

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        action = params.get("action", [None])[0]

        try:
            _garantir_db()
        except Exception as e:
            self._send_json(500, {"erro": f"Erro ao carregar banco de dados: {e}"})
            return

        if action in _EXCEL_ACTIONS:
            try:
                xlsx = _action_excel(params)
            except ValueError as e:
                self._send_json(400, {"erro": str(e)})
                return
            municipio = params.get("municipio", [""])[0]
            cargo = params.get("cargo", [""])[0]
            ano = params.get("ano", [""])[0]
            filename = f"TSE_{ano}_{municipio}_{cargo}.xlsx"
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(xlsx)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(xlsx)
            return

        fn = _ACTIONS.get(action)
        if fn is None:
            self._send_json(400, {"erro": f"action inválida: {action!r}"})
            return

        try:
            result = fn(params)
        except ValueError as e:
            self._send_json(400, {"erro": str(e)})
            return
        except Exception as e:
            self._send_json(500, {"erro": str(e)})
            return

        self._send_json(200, result)
