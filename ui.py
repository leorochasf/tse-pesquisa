"""
ui.py — camada de apresentação da Ferramenta TSE.
Nenhuma lógica de negócio aqui; apenas CSS, HTML e helpers de render.
"""

from __future__ import annotations
import streamlit as st


# ─── Fontes & tokens ─────────────────────────────────────────────────────────

_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,700;"
    "1,9..144,400&"
    "family=Public+Sans:wght@400;500;600&"
    "display=swap"
)

CSS = f"""
<style>
@import url('{_FONTS_URL}');

/* ── Tokens ─────────────────────────────────────────────── */
:root {{
  --ink:      #18222E;
  --muted:    #5C6672;
  --paper:    #F6F4EE;
  --surface:  #FFFFFF;
  --primary:  #0F3B4C;
  --primary-h:#0B2C39;
  --accent:   #B8741A;
  --eleito:   #1B7A4B;
  --border:   #E3DFD4;
  --radius:   6px;
  --shadow:   0 1px 4px rgba(15,59,76,.10);
}}

/* ── Base ────────────────────────────────────────────────── */
html, body, [class*="css"] {{
  font-family: 'Public Sans', sans-serif;
  color: var(--ink);
}}

/* Esconde menu hamburger, footer e cabeçalho do Streamlit */
#MainMenu, footer, header {{ visibility: hidden; }}

/* Remove padding padrão excessivo no topo */
.block-container {{
  padding-top: 1.5rem !important;
  max-width: 860px;
}}

/* ── Header institucional ────────────────────────────────── */
.tse-header {{
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 0 1.25rem 0;
  border-bottom: 2px solid var(--primary);
  margin-bottom: 1.5rem;
}}
.tse-header-icon {{
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  background: var(--primary);
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
}}
.tse-header-icon svg {{
  color: #fff;
}}
.tse-header-text h1 {{
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.55rem;
  font-weight: 700;
  line-height: 1.1;
  margin: 0;
  color: var(--primary);
  letter-spacing: -.01em;
}}
.tse-header-text p {{
  font-size: .78rem;
  color: var(--muted);
  margin: 2px 0 0 0;
  font-weight: 500;
  letter-spacing: .02em;
  text-transform: uppercase;
}}

/* ── Cards de métrica ────────────────────────────────────── */
.tse-metrics {{
  display: flex;
  gap: 12px;
  margin-bottom: 1.25rem;
}}
.tse-metric {{
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  box-shadow: var(--shadow);
}}
.tse-metric-value {{
  font-family: 'Public Sans', sans-serif;
  font-feature-settings: "tnum";
  font-size: 2rem;
  font-weight: 600;
  line-height: 1;
  color: var(--ink);
}}
.tse-metric-value.eleito {{ color: var(--eleito); }}
.tse-metric-label {{
  font-size: .72rem;
  font-weight: 600;
  letter-spacing: .05em;
  text-transform: uppercase;
  color: var(--muted);
  margin-top: 4px;
}}

/* ── Badges ──────────────────────────────────────────────── */
.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: .72rem;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
}}
.badge-eleito {{
  background: #D1F5E0;
  color: var(--eleito);
  border: 1px solid #A8E6C1;
}}
.badge-suplente {{
  background: #EFF3F6;
  color: #4A5568;
  border: 1px solid var(--border);
}}
.badge-naoel {{
  background: #FEF3E6;
  color: #8B4500;
  border: 1px solid #F5CBА8;
}}
.badge-reeleicao {{
  background: #FEF3E6;
  color: var(--accent);
  border: 1px solid #F5D59A;
}}

/* ── Linha do tempo de mandatos ──────────────────────────── */
.tse-timeline {{
  position: relative;
  padding-left: 36px;
  margin: .5rem 0 1rem;
}}
.tse-timeline::before {{
  content: '';
  position: absolute;
  left: 14px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: var(--border);
}}
.tse-tl-item {{
  position: relative;
  margin-bottom: 16px;
}}
.tse-tl-item::before {{
  content: '';
  position: absolute;
  left: -26px;
  top: 10px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--primary);
  border: 2px solid var(--paper);
  box-shadow: 0 0 0 2px var(--primary);
}}
.tse-tl-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  box-shadow: var(--shadow);
}}
.tse-tl-ano {{
  font-family: 'Fraunces', serif;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 6px;
}}
.tse-tl-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: .82rem;
  color: var(--muted);
}}
.tse-tl-periodo {{
  font-feature-settings: "tnum";
  font-weight: 500;
  color: var(--ink);
}}
.tse-tl-partido {{
  background: #EFF3F6;
  color: var(--ink);
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: 600;
  font-size: .72rem;
  letter-spacing: .04em;
  text-transform: uppercase;
  border: 1px solid var(--border);
}}

/* ── Callouts ────────────────────────────────────────────── */
.tse-callout {{
  padding: 12px 14px;
  border-radius: var(--radius);
  font-size: .85rem;
  margin: .75rem 0;
}}
.tse-callout-warn {{
  background: #FEF3E6;
  border-left: 3px solid var(--accent);
  color: #7A4000;
}}
.tse-callout-info {{
  background: #EFF6FF;
  border-left: 3px solid #3B82F6;
  color: #1E3A5F;
}}

/* ── Rodapé ──────────────────────────────────────────────── */
.tse-footer {{
  margin-top: 2.5rem;
  padding-top: .75rem;
  border-top: 1px solid var(--border);
  font-size: .72rem;
  color: var(--muted);
  text-align: center;
  line-height: 1.6;
}}

/* ── Abas: estilo segmented control ──────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
  gap: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 3px;
  width: fit-content;
  box-shadow: var(--shadow);
}}
.stTabs [data-baseweb="tab"] {{
  border-radius: 4px;
  padding: 7px 20px;
  font-size: .82rem;
  font-weight: 600;
  letter-spacing: .03em;
  color: var(--muted);
  background: transparent;
  border: none;
}}
.stTabs [aria-selected="true"] {{
  background: var(--primary) !important;
  color: #fff !important;
}}
.stTabs [data-baseweb="tab-border"] {{
  display: none;
}}

/* Botão primário */
.stButton > button[kind="primary"] {{
  background: var(--primary) !important;
  border: none !important;
  font-weight: 600 !important;
  letter-spacing: .02em !important;
  border-radius: var(--radius) !important;
}}
.stButton > button[kind="primary"]:hover {{
  background: var(--primary-h) !important;
}}

/* Download button */
.stDownloadButton > button {{
  border-color: var(--primary) !important;
  color: var(--primary) !important;
  font-weight: 600 !important;
  border-radius: var(--radius) !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
  border-right: 1px solid var(--border);
}}
[data-testid="stSidebar"] .tse-sidebar-title {{
  font-family: 'Fraunces', serif;
  font-size: .95rem;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: .5rem;
  letter-spacing: .01em;
}}
</style>
"""

# ─── SVG: ícone de coluna/urna ────────────────────────────────────────────────

_ICON_SVG = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none"
  stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="11" width="18" height="11" rx="2"/>
  <path d="M3 11V7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4"/>
  <line x1="12" y1="3" x2="12" y2="7"/>
  <line x1="8" y1="5" x2="8" y2="7"/>
  <line x1="16" y1="5" x2="16" y2="7"/>
</svg>"""


# ─── API pública ──────────────────────────────────────────────────────────────

def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header() -> None:
    st.markdown(
        f"""
        <div class="tse-header">
          <div class="tse-header-icon">{_ICON_SVG}</div>
          <div class="tse-header-text">
            <h1>Ferramenta TSE</h1>
            <p>Consulta de eleitos e mandatos &middot; Goi&aacute;s &middot; MPGO</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_cards(n_eleitos: int, n_demais: int) -> None:
    total = n_eleitos + n_demais
    st.markdown(
        f"""
        <div class="tse-metrics">
          <div class="tse-metric">
            <div class="tse-metric-value eleito">{n_eleitos}</div>
            <div class="tse-metric-label">Eleito(s)</div>
          </div>
          <div class="tse-metric">
            <div class="tse-metric-value">{n_demais}</div>
            <div class="tse-metric-label">N&atilde;o eleito(s) / Suplente(s)</div>
          </div>
          <div class="tse-metric">
            <div class="tse-metric-value">{total}</div>
            <div class="tse-metric-label">Total de candidatos</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "suplente") -> str:
    cls = {
        "eleito": "badge-eleito",
        "suplente": "badge-suplente",
        "naoel": "badge-naoel",
        "reeleicao": "badge-reeleicao",
    }.get(kind, "badge-suplente")
    return f'<span class="badge {cls}">{text}</span>'


def timeline(mandatos: list) -> None:
    """Renderiza linha do tempo de mandatos em HTML."""
    if not mandatos:
        st.markdown(
            '<div class="tse-callout tse-callout-info">Nenhum mandato registrado.</div>',
            unsafe_allow_html=True,
        )
        return

    items = []
    for m in mandatos:
        reeleicao_html = (
            f'&nbsp;{badge("Reeleição", "reeleicao")}' if m.reeleicao else ""
        )
        partido_html = (
            f'<span class="tse-tl-partido">{m.partido}</span>' if m.partido else ""
        )
        items.append(
            f'<div class="tse-tl-item">'
            f'<div class="tse-tl-card">'
            f'<div class="tse-tl-ano">Eleição {m.ano_eleicao}{reeleicao_html}</div>'
            f'<div class="tse-tl-row">{partido_html}'
            f'<span class="tse-tl-periodo">{m.inicio}&ndash;{m.fim}</span>'
            f'</div></div></div>'
        )

    st.markdown(
        f'<div class="tse-timeline">{"".join(items)}</div>',
        unsafe_allow_html=True,
    )


def callout(text: str, kind: str = "info") -> None:
    cls = "tse-callout-warn" if kind == "warn" else "tse-callout-info"
    st.markdown(
        f'<div class="tse-callout {cls}">{text}</div>',
        unsafe_allow_html=True,
    )


def footer(anos: list | None = None) -> None:
    anos_str = ", ".join(str(a) for a in anos) if anos else ""
    cobertura = f"Eleições cobertas: {anos_str} &nbsp;&middot;&nbsp;" if anos_str else ""
    st.markdown(
        f"""
        <div class="tse-footer">
          {cobertura}Fonte: TSE Dados Abertos &mdash; consulta_cand
        </div>
        """,
        unsafe_allow_html=True,
    )
