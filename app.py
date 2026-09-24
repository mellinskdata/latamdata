from __future__ import annotations

import streamlit as st

from config import DEFAULT_SEASON, APP_NAME, APP_TAGLINE
from ui.common import render_match_center
from ui.match_pages import home_page, teams_page, games_page
from ui.scout_pages import scout_page, compare_page, rankings_page

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.1rem; max-width: 1520px;}
    [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.20);
        border-radius: 14px;
        padding: .65rem .8rem;
        background: rgba(128,128,128,.055);
    }
    [data-testid="stMetricValue"] {font-size: 1.55rem;}
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(128,128,128,.15);
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab-list"] {gap: .35rem;}
    .stTabs [data-baseweb="tab"] {
        border-radius: 9px 9px 0 0;
        padding-left: .9rem;
        padding-right: .9rem;
    }
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
        "Rankings & oportunidades",
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
    "Jogadores: FotMob · Jogos: ESPN · Índices: LATAMDATA"
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
elif page == "Rankings & oportunidades":
    rankings_page(season)
elif page == "Comparar jogadores":
    compare_page(season)
else:
    st.title("Dados & fontes")
    st.markdown(
        """
        ### Camadas de dados

        **Jogadores e scouting:** o LATAMDATA usa dados reais de temporada obtidos
        por uma integração web não oficial com o FotMob. A base inclui, quando
        disponíveis, minutos, nota, gols, assistências, xG, xA, xGOT,
        finalizações, criação, passe, drible, ações defensivas, goleiros,
        elenco, idade, altura, nacionalidade e valor de mercado.

        **Times e partidas:** calendário, placares e a central da partida continuam
        usando endpoints JSON públicos utilizados pela ESPN.

        ### Inteligência LATAMDATA

        Os seguintes campos são calculados pela própria plataforma e não são
        notas oficiais das fontes:

        - percentis por posição;
        - **Impact Score** ponderado pela função do jogador;
        - dimensões de Finalização, Criação, Posse e Defesa;
        - **Reliability Score** baseado no tamanho da amostra de minutos;
        - **Value Score** para custo-benefício quando há valor de mercado;
        - **Opportunity Score** combinando impacto, idade, preço e amostra;
        - arquétipo de jogo;
        - pontos fortes e fracos;
        - sinais de gols vs xG e assistências vs xA;
        - similaridade entre atletas.

        ### Transparência

        As integrações web com FotMob e ESPN não são APIs contratadas do
        LATAMDATA e podem mudar. Elas ficam isoladas em adaptadores próprios
        para podermos trocar de fornecedor sem reescrever a aplicação.

        **Não existe fallback para jogadores fictícios.** Se uma fonte real
        estiver indisponível, a plataforma informa a falha em vez de inventar dados.
        """
    )
