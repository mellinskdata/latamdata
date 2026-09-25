from __future__ import annotations

import streamlit as st

from config import APP_NAME
from ui.common import render_match_center
from ui.match_pages import teams_page, games_page
from ui.scout_pages import scout_page
from ui.platform_pages import home_v2, ranking_v2, compare_v2

BUILD = "2026.09.24-r2"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --latam-bg:#0d0f14;
        --latam-panel:#15171d;
        --latam-border:rgba(255,255,255,.08);
        --latam-muted:#9ea2aa;
        --latam-accent:#e6bb52;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 85% -10%, rgba(111,58,157,.10), transparent 28rem),
            var(--latam-bg);
    }
    [data-testid="stHeader"] {background:transparent;}
    [data-testid="stSidebar"] {display:none;}
    .block-container {padding-top:1rem;max-width:1450px;}
    .latam-topbar {
        display:flex;align-items:center;justify-content:space-between;gap:1rem;
        border-bottom:1px solid var(--latam-border);
        padding:.35rem 0 .8rem 0;margin-bottom:.25rem;
    }
    .latam-brand {font-weight:800;letter-spacing:.08em;font-size:1.05rem;}
    .latam-build {color:var(--latam-muted);font-size:.72rem;}
    .latam-hero {
        min-height:325px;border:1px solid var(--latam-border);border-radius:20px;
        padding:3.2rem;margin:.7rem 0 1.2rem 0;
        background:
          radial-gradient(circle at 76% 15%, rgba(215,56,155,.23), transparent 22rem),
          radial-gradient(circle at 95% 80%, rgba(78,74,205,.20), transparent 22rem),
          linear-gradient(120deg,#151820,#111318 70%);
        box-shadow:0 18px 55px rgba(0,0,0,.20);
    }
    .latam-hero h1 {
        max-width:850px;font-size:3.15rem;line-height:1.03;
        margin:.45rem 0 1rem 0;letter-spacing:-.045em;
    }
    .latam-hero p {
        max-width:730px;color:var(--latam-muted);font-size:1.08rem;line-height:1.55;
    }
    .latam-eyebrow {
        display:inline-block;color:var(--latam-accent);font-weight:750;
        letter-spacing:.12em;font-size:.74rem;
    }
    [data-testid="stMetric"] {
        border:1px solid var(--latam-border);border-radius:14px;
        padding:.65rem .8rem;background:var(--latam-panel);
    }
    [data-testid="stMetricValue"] {font-size:1.45rem;}
    [data-testid="stDataFrame"] {
        border:1px solid var(--latam-border);border-radius:14px;overflow:hidden;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color:var(--latam-border)!important;
        background:var(--latam-panel);border-radius:14px!important;
    }
    .latam-value {
        font-size:1.18rem;font-weight:800;text-align:right;color:#b66cff;
    }
    .stTabs [data-baseweb="tab-list"] {gap:.35rem;}
    .stTabs [data-baseweb="tab"] {border-radius:9px 9px 0 0;}
    div[data-testid="stRadio"] > div {gap:.2rem;}
    div[data-testid="stRadio"] label {border-radius:8px;padding:.42rem .68rem;}
    div[data-testid="stSegmentedControl"] button {border-radius:9px;}
    h1,h2,h3 {letter-spacing:-.025em;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="latam-topbar">
      <div class="latam-brand">◩ LATAMDATA</div>
      <div class="latam-build">Build {BUILD}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

nav_col, season_col = st.columns([7,1.2], vertical_alignment="center")
with nav_col:
    page = st.radio(
        "Navegação",
        ["Home","Ranking","Comparar","Scout","Times","Jogos","Dados"],
        horizontal=True,
        label_visibility="collapsed",
        key="top_navigation",
    )
with season_col:
    season = int(st.selectbox("Temporada",[2026,2025,2024,2023],index=0,key="season_top"))

if render_match_center():
    st.stop()

if page == "Home":
    home_v2(season)
elif page == "Ranking":
    ranking_v2(season)
elif page == "Comparar":
    compare_v2(season)
elif page == "Scout":
    scout_page(season)
elif page == "Times":
    teams_page(season)
elif page == "Jogos":
    games_page(season)
else:
    st.title("Dados & fontes")
    st.markdown(
        """
        ### Arquitetura

        **Jogadores:** snapshots reais de temporada são atualizados automaticamente
        por GitHub Actions a partir da integração FotMob e servidos localmente pelo app.

        **Jogos:** calendário, placares e central da partida usam a camada ESPN.

        **LATAMDATA:** percentis por posição, Impact Score, Opportunity Score,
        Value Score, Reliability Score, dimensões de jogo, arquétipos,
        similaridade estatística e Tactical Fingerprints são calculados pela plataforma.

        ### Transparência

        FotMob e ESPN são integrações web não oficiais e podem mudar. O projeto
        mantém provedores desacoplados e snapshots para estabilidade.
        Não existe fallback sintético para jogadores.
        """
    )
