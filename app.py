from __future__ import annotations

import streamlit as st

from config import DEFAULT_SEASON, APP_NAME, APP_TAGLINE
from ui.common import render_match_center
from ui.match_pages import home_page, teams_page, games_page
from ui.scout_pages import scout_page, compare_page

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.1rem; max-width: 1500px;}
    [data-testid="stMetricValue"] {font-size: 1.55rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title(f"⚽ {APP_NAME}")
st.sidebar.caption(APP_TAGLINE)

page = st.sidebar.radio(
    "Navegação",
    [
        "Início",
        "Times",
        "Jogos",
        "Scout de jogadores",
        "Comparar jogadores",
        "Dados & fontes",
    ],
)

season = int(
    st.sidebar.number_input(
        "Temporada",
        min_value=2018,
        max_value=2030,
        value=DEFAULT_SEASON,
        step=1,
    )
)

st.sidebar.caption(
    "Jogos e times: ESPN. Jogadores: estatísticas reais de temporada via SofaScore."
)

if render_match_center():
    st.stop()

if page == "Início":
    home_page(season)
elif page == "Times":
    teams_page(season)
elif page == "Jogos":
    games_page(season)
elif page == "Scout de jogadores":
    scout_page(season)
elif page == "Comparar jogadores":
    compare_page(season)
else:
    st.title("Dados & fontes")
    st.markdown(
        """
        ### O que é real

        **Times e jogos:** dados consumidos de endpoints JSON públicos usados pela ESPN.

        **Jogadores:** estatísticas reais de temporada consumidas de endpoints web públicos usados pelo SofaScore. A cobertura inclui, quando a fonte disponibiliza, gols, assistências, xG, xA, passes-chave, ações defensivas, duelos, dribles, finalizações, minutos, nota média e mapa de calor.

        ### O que o LATAMDATA calcula

        Percentis por posição, Performance Score, pontos fortes e fracos, similaridade estatística e um Value Score experimental quando existe valor de mercado disponível.

        ### Limitação importante

        A integração com SofaScore é **não oficial** e não equivale a um dataset open-source/CC0 nem a uma API contratada. Se essa fonte falhar ou mudar, o app mostra indisponibilidade em vez de inventar dados.

        O antigo conjunto sintético de jogadores foi removido do fluxo e do repositório.
        """
    )
