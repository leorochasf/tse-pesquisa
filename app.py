"""
Ferramenta TSE — app web (Streamlit).
"""

import os
import tempfile
from pathlib import Path

import streamlit as st

import ui
from tse_core.consulta import listar, listar_anos, listar_municipios
from tse_core.export import gerar_excel


# ─── Boot: sincroniza sqlite do Supabase Storage ──────────────────────────────

def _storage_configured() -> bool:
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        return False
    return "PREENCHA" not in st.secrets["SUPABASE_KEY"]


@st.cache_resource
def _init_db() -> str | None:
    if not _storage_configured():
        return None
    try:
        from supabase import create_client
        client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        data = client.storage.from_("tse-data").download("tse.sqlite")
        db_path = str(Path(tempfile.gettempdir()) / "tse.sqlite")
        with open(db_path, "wb") as f:
            f.write(data)
        os.environ["TSE_DB_PATH"] = db_path
        return db_path
    except Exception as e:
        st.warning(f"Storage indisponível, usando banco local. ({e})")
        return None


# ─── Configuração de página ───────────────────────────────────────────────────

st.set_page_config(page_title="Ferramenta TSE", page_icon="🗳️", layout="centered")

ui.inject_css()
_init_db()

# ─── Sidebar admin ────────────────────────────────────────────────────────────

def _supabase_client():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


with st.sidebar:
    st.markdown('<div class="tse-sidebar-title">Administração</div>', unsafe_allow_html=True)
    if not _storage_configured():
        st.caption("Storage não configurado. Preencha `SUPABASE_KEY` em secrets.toml.")
    senha = st.text_input("Senha de acesso", type="password", key="admin_senha")
    admin_ok = (
        _storage_configured()
        and "ADMIN_PASSWORD" in st.secrets
        and senha == st.secrets["ADMIN_PASSWORD"]
    )
    if senha and not admin_ok:
        st.error("Senha incorreta ou Storage não configurado.")
    if admin_ok:
        st.success("Autenticado")
        ano_upd = st.number_input(
            "Ano para importar", min_value=2000, max_value=2030, value=2024, step=4
        )
        if st.button("Atualizar dados do TSE", type="primary"):
            db_path = os.environ.get("TSE_DB_PATH") or None
            with st.spinner(f"Importando {ano_upd}/GO do TSE..."):
                from tse_core.ingest import importar
                total = importar(int(ano_upd), uf="GO", db_path=db_path)
            st.sidebar.success(f"{total} registros importados.")
            with st.spinner("Enviando ao Storage..."):
                try:
                    path = db_path or str(
                        Path(__file__).parent / "tse_core" / "dados" / "tse.sqlite"
                    )
                    data = Path(path).read_bytes()
                    _supabase_client().storage.from_("tse-data").upload(
                        "tse.sqlite",
                        data,
                        {"upsert": "true", "content-type": "application/octet-stream"},
                    )
                    st.sidebar.success("Storage atualizado.")
                    _init_db.clear()
                except Exception as e:
                    st.sidebar.error(f"Erro no upload: {e}")

# ─── Header ───────────────────────────────────────────────────────────────────

ui.header()

# ─── Abas ─────────────────────────────────────────────────────────────────────

tab_listar, tab_rastrear = st.tabs(["Listar candidatos", "Rastrear mandatos"])


# ─── Aba: Listar ──────────────────────────────────────────────────────────────

with tab_listar:
    anos = listar_anos("GO")
    if not anos:
        ui.callout(
            "Nenhum dado importado. Rode <code>python cli.py ingest --anos 2024 --uf GO</code> primeiro.",
            kind="warn",
        )
        st.stop()

    col1, col2, col3 = st.columns(3)
    with col1:
        ano = st.selectbox("Ano", anos, index=len(anos) - 1)
    with col2:
        municipios = listar_municipios("GO", ano)
        municipio = st.selectbox("Município", municipios)
    with col3:
        cargo = st.selectbox("Cargo", ["Vereador", "Prefeito"])

    if st.button("Pesquisar", type="primary"):
        try:
            candidatos = listar(ano, municipio, cargo)
        except ValueError as e:
            st.error(str(e))
            st.stop()

        eleitos = [c for c in candidatos if c["eleito"]]
        nao_eleitos = [c for c in candidatos if not c["eleito"]]

        ui.metric_cards(len(eleitos), len(nao_eleitos))

        import pandas as pd

        def _df(lista):
            return pd.DataFrame([
                {
                    "Nome": c["nome"],
                    "Urna": c["urna"] or "",
                    "Partido": c["partido"] or "",
                    "Situação": c["situacao"],
                }
                for c in lista
            ])

        if eleitos:
            st.subheader("Eleitos")
            st.dataframe(_df(eleitos), use_container_width=True, hide_index=True)

        if nao_eleitos:
            with st.expander(f"Demais candidatos ({len(nao_eleitos)})"):
                st.dataframe(_df(nao_eleitos), use_container_width=True, hide_index=True)

        st.download_button(
            label="Baixar Excel",
            data=gerar_excel(candidatos),
            file_name=f"TSE_{ano}_{municipio}_{cargo}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ─── Aba: Rastrear ────────────────────────────────────────────────────────────

with tab_rastrear:
    import pandas as pd
    from tse_core.consulta import rastrear
    from tse_core.mandato import inferir_mandatos

    municipios_todos = listar_municipios("GO")
    if not municipios_todos:
        ui.callout(
            "Nenhum dado importado. Rode <code>python cli.py ingest --anos 2024 --uf GO</code> primeiro.",
            kind="warn",
        )
        st.stop()

    with st.form("rastrear_form"):
        col1, col2 = st.columns(2)
        with col1:
            municipio_r = st.selectbox("Município", municipios_todos, key="mun_r")
        with col2:
            cargo_r = st.selectbox("Cargo", ["Prefeito", "Vereador"], key="cargo_r")
        nome_r = st.text_input(
            "Nome do candidato", placeholder="Ex: CLAUDIO HENRIQUE (parcial ou completo)"
        )
        submitted = st.form_submit_button("Rastrear", type="primary")

    if submitted:
        if not nome_r.strip():
            ui.callout("Informe ao menos parte do nome.", kind="warn")
            st.stop()

        try:
            resultado = rastrear(nome_r.strip(), municipio_r, cargo_r)
        except ValueError as e:
            st.error(str(e))
            st.stop()

        if resultado["homonimos"]:
            nomes = "<br>".join(f"&bull; {n}" for n in resultado["homonimos"])
            ui.callout(
                f"<strong>Múltiplos candidatos encontrados</strong> — use o nome completo "
                f"para refinar:<br><br>{nomes}",
                kind="warn",
            )

        if not resultado["anos"]:
            ui.callout(
                f"Nenhum registro encontrado para <strong>{nome_r}</strong> "
                f"em {municipio_r} / {cargo_r}.",
                kind="info",
            )
            st.stop()

        inf = inferir_mandatos(resultado)

        st.subheader("Linha do tempo de mandatos")
        ui.timeline(inf["mandatos"])

        if inf["suplencias"]:
            with st.expander(f"Suplências ({len(inf['suplencias'])})"):
                st.dataframe(
                    pd.DataFrame(inf["suplencias"]).rename(
                        columns={"ano": "Ano", "partido": "Partido"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

        if inf["sem_eleicao"]:
            with st.expander(f"Não eleito ({len(inf['sem_eleicao'])})"):
                st.dataframe(
                    pd.DataFrame(inf["sem_eleicao"]).rename(
                        columns={"ano": "Ano", "situacao": "Situação", "partido": "Partido"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )


# ─── Rodapé ───────────────────────────────────────────────────────────────────

anos_disponiveis = listar_anos("GO")
ui.footer(anos_disponiveis if anos_disponiveis else None)
