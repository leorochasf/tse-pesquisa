"""
Integração com IA via OpenRouter — parecer de triagem e chat.

A chave é secreta: lida de OPENROUTER_API_KEY (env var; fallback em
.streamlit/secrets.toml para dev). Modelo configurável por OPENROUTER_MODEL.
Tudo sob demanda. O contexto enviado é só o que a ferramenta coletou.
"""

import json
import os
import tomllib
import urllib.request
import urllib.error

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODEL_PADRAO = "openai/gpt-4o-mini"

_SISTEMA = (
    "Você é um assistente de triagem do Ministério Público (área de improbidade "
    "administrativa e patrimônio público). Analise ESTRITAMENTE com base nos dados "
    "fornecidos abaixo. NÃO invente fatos, dispositivos legais ou jurisprudência além "
    "do que está nos dados. Trate a prescrição informada como ESTIMATIVA a confirmar. "
    "Use [VERIFICAR] em qualquer afirmação que dependa de dado não fornecido. Seja "
    "conciso, objetivo e em português."
)


def _get_secret(nome: str) -> str | None:
    valor = os.environ.get(nome)
    if valor:
        return valor
    caminho = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "secrets.toml")
    try:
        with open(caminho, "rb") as f:
            return tomllib.load(f).get(nome)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def chamar_openrouter(mensagens: list[dict], model: str | None = None) -> str:
    chave = _get_secret("OPENROUTER_API_KEY")
    if not chave:
        raise ValueError("IA indisponível: OPENROUTER_API_KEY não configurada.")
    model = model or _get_secret("OPENROUTER_MODEL") or _MODEL_PADRAO

    corpo = json.dumps({"model": model, "messages": mensagens}).encode("utf-8")
    req = urllib.request.Request(
        _OPENROUTER_URL,
        data=corpo,
        method="POST",
        headers={
            "Authorization": f"Bearer {chave}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://tse-pesquisa.vercel.app",
            "X-Title": "Ferramenta TSE - MPGO",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.load(resp)
    except urllib.error.HTTPError as e:
        raise ValueError(f"IA indisponível (erro {e.code}). Verifique a chave/saldo no OpenRouter.")
    except Exception:
        raise ValueError("IA indisponível: falha ao contatar o OpenRouter. Tente novamente.")

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise ValueError("IA indisponível: resposta inesperada do OpenRouter.")


def _fmt_brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {v:,.0f}".replace(",", ".")


def montar_contexto_pessoa(nome: str, municipio: str, cargo: str) -> dict:
    """
    Reúne os dados que a ferramenta tem sobre a pessoa (histórico, prescrição,
    patrimônio, restrições) num texto estruturado para alimentar a IA.
    Retorna {"contexto": texto, "nome": ...} ou levanta ValueError se nada achado.
    """
    import dataclasses
    from .consulta import rastrear
    from .mandato import inferir_mandatos
    from .tse_api import buscar_ficha

    inf = inferir_mandatos(rastrear(nome, municipio, cargo))
    mandatos = [dataclasses.asdict(m) for m in inf["mandatos"]]
    if not mandatos and not inf["suplencias"] and not inf["sem_eleicao"]:
        raise ValueError(f"Nenhum registro encontrado para {nome} em {municipio}/{cargo}.")

    linhas = [
        f"Pessoa: {nome.upper()}",
        f"CPF: {inf.get('cpf') or 'não disponível'}",
        f"Município/Cargo: {inf['municipio']} / {inf['cargo']}",
        "",
        "MANDATOS (eleito):",
    ]
    for m in mandatos:
        p = m.get("prescricao") or {}
        presc = {
            "prescrito": f"prescrição provável (≈{p.get('ref_ano')})",
            "no_prazo": f"no prazo (≈{p.get('ref_ano')})",
            "verificar": "verificar (nova LIA)",
        }.get(p.get("status"), "—")
        reel = " [reeleição]" if m["reeleicao"] else ""
        linhas.append(f"  - Eleito {m['ano_eleicao']} ({m['partido']}), mandato {m['inicio']}-{m['fim']}{reel}; prescrição: {presc}")

    if inf["suplencias"]:
        linhas.append("SUPLÊNCIAS: " + ", ".join(f"{s['ano']} ({s['partido']})" for s in inf["suplencias"]))

    if inf["sem_eleicao"]:
        linhas.append("OUTRAS CANDIDATURAS (não eleito / restrição):")
        for s in inf["sem_eleicao"]:
            linhas.append(f"  - {s['ano']}: {s['situacao']} ({s.get('partido') or '—'})")

    # Patrimônio + restrições (ficha de cada candidatura)
    cands = {}
    for grupo in (mandatos, inf["suplencias"], inf["sem_eleicao"]):
        for it in grupo:
            ano = it.get("ano_eleicao") or it.get("ano")
            sq, mun = it.get("sq_candidato"), it.get("cd_municipio")
            if sq and mun:
                cands[(ano, sq, mun)] = True

    linhas.append("")
    linhas.append("PATRIMÔNIO DECLARADO E SITUAÇÃO (por eleição):")
    for (ano, sq, mun) in sorted(cands):
        try:
            f = buscar_ficha(ano, mun, sq)
        except Exception:
            continue
        restr = ""
        if f.get("motivos"):
            restr = f" | situação: {f.get('situacao_registro')} — motivos: {'; '.join(f['motivos'])}"
        elif f.get("situacao_registro") and f["situacao_registro"] != "Deferido":
            restr = f" | situação: {f['situacao_registro']}"
        linhas.append(f"  - {ano}: bens {_fmt_brl(f.get('total_bens'))}{restr}")

    return {"contexto": "\n".join(linhas), "nome": nome}
