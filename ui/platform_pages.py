from __future__ import annotations

import math
from collections import OrderedDict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import LEAGUES
from scout_analytics import prepare_team_stats
from ui.common import load_players, league_team_stats


PLAYER_METRICS = OrderedDict({
    "Gols & finalização": OrderedDict({
        "Gols": ("goals90", "goals_total"),
        "xG": ("xg90", "xg_total"),
        "xGOT": ("xgot90", None),
        "Finalizações": ("shots90", None),
        "Finalizações no alvo": ("shots_on_target90", None),
    }),
    "Criação": OrderedDict({
        "Assistências": ("assists90", "assists_total"),
        "xA": ("xa90", "xa_total"),
        "Chances criadas": ("key_pass90", None),
        "Grandes chances criadas": ("big_chances_created90", None),
    }),
    "Passes": OrderedDict({
        "Passes certos": ("passes90", None),
        "Bolas longas certas": ("long_balls90", None),
    }),
    "Condução & dribles": OrderedDict({
        "Dribles certos": ("dribbles90", None),
    }),
    "Defesa": OrderedDict({
        "Ações defensivas": ("defensive_actions90", None),
        "Desarmes": ("tackles90", None),
        "Interceptações": ("interceptions90", None),
        "Recuperações": ("recoveries90", None),
        "Cortes": ("clearances90", None),
        "Bloqueios": ("blocks90", None),
        "Recuperações no terço final": ("high_press_wins90", None),
    }),
    "Goleiros": OrderedDict({
        "Defesas %": ("save_pct", None),
        "Defesas": ("saves90", None),
        "Gols evitados": ("goals_prevented90", None),
        "Gols sofridos": ("goals_conceded90", None),
    }),
    "LATAMDATA": OrderedDict({
        "Impact Score": ("performance_score", None),
        "Opportunity Score": ("opportunity_score", None),
        "Value Score": ("value_score", None),
        "Finalização": ("dimension_finishing", None),
        "Criação": ("dimension_creation", None),
        "Posse": ("dimension_possession", None),
        "Defesa": ("dimension_defense", None),
    }),
})

TEAM_METRICS = OrderedDict({
    "Ataque": OrderedDict({
        "Gols": ("goals_team_match", None),
        "xG": ("expected_goals_team", None),
        "Saldo de xG": ("_xg_diff_team", None),
        "Finalizações no alvo": ("ontarget_scoring_att_team", None),
        "Grandes chances": ("big_chance_team", None),
        "Toques na área": ("touches_in_opp_box_team", None),
    }),
    "Posse & passe": OrderedDict({
        "Posse": ("possession_percentage_team", None),
        "Passes certos": ("accurate_pass_team", None),
        "Bolas longas certas": ("accurate_long_balls_team", None),
        "Cruzamentos certos": ("accurate_cross_team", None),
    }),
    "Defesa & pressão": OrderedDict({
        "xG sofrido": ("expected_goals_conceded_team", None),
        "Gols sofridos": ("goals_conceded_team_match", None),
        "Clean sheets": ("clean_sheet_team", None),
        "Desarmes": ("total_tackle_team", None),
        "Interceptações": ("interception_team", None),
        "Recuperações no terço final": ("poss_won_att_3rd_team", None),
    }),
    "LATAMDATA": OrderedDict({
        "Ataque": ("team_attack", None),
        "Controle": ("team_control", None),
        "Pressão": ("team_pressing", None),
        "Defesa": ("team_defense", None),
    }),
})

COMPARE_DEFAULTS = [
    "xg90", "xa90", "key_pass90", "dribbles90",
    "tackles90", "interceptions90", "recoveries90", "performance_score",
]

COMPARE_LABELS = {
    "xg90": "xG/90",
    "xa90": "xA/90",
    "key_pass90": "Chances criadas/90",
    "dribbles90": "Dribles/90",
    "tackles90": "Desarmes/90",
    "interceptions90": "Interceptações/90",
    "recoveries90": "Recuperações/90",
    "performance_score": "Impact Score",
    "opportunity_score": "Opportunity",
    "dimension_finishing": "Finalização",
    "dimension_creation": "Criação",
    "dimension_possession": "Posse",
    "dimension_defense": "Defesa",
    "rating": "Nota",
    "goals90": "Gols/90",
    "assists90": "Assistências/90",
    "passes90": "Passes certos/90",
    "long_balls90": "Bolas longas/90",
    "high_press_wins90": "Recup. terço final/90",
}


def _fmt(value: float, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    if abs(float(value)) >= 100:
        return f"{float(value):,.0f}".replace(",", ".")
    return f"{float(value):.{digits}f}"


def _all_players(season: int) -> pd.DataFrame:
    df, errors = load_players(list(LEAGUES), season)
    for key, error in errors:
        st.caption(f"{LEAGUES[key].name}: {error}")
    return df


def _metric_total(frame: pd.DataFrame, per90_col: str, explicit_total: str | None) -> pd.Series:
    if explicit_total and explicit_total in frame:
        return pd.to_numeric(frame[explicit_total], errors="coerce")
    values = pd.to_numeric(frame.get(per90_col), errors="coerce")
    minutes = pd.to_numeric(frame.get("minutes"), errors="coerce")
    return values * minutes / 90.0


def _rank_cards(frame: pd.DataFrame, value_col: str, value_label: str, top_n: int = 60):
    if frame.empty:
        st.info("Nenhum resultado para esses filtros.")
        return

    show = frame.head(top_n).copy()
    for pos, row in enumerate(show.itertuples(), start=1):
        with st.container(border=True):
            rank, identity, meta, value = st.columns([.6, 5.4, 3, 1.2], vertical_alignment="center")
            rank.markdown(f"### {pos}")
            identity.markdown(f"**{row.player}**")
            identity.caption(f"{row.club} · {row.league}")
            age = "—" if pd.isna(row.age) else f"{int(row.age)} anos"
            meta.caption(f"{row.position} · {age} · {int(row.minutes) if pd.notna(row.minutes) else 0} min")
            metric_value = getattr(row, value_col)
            value.markdown(f"<div class='latam-value'>{_fmt(metric_value)}</div>", unsafe_allow_html=True)
            value.caption(value_label)


def home_v2(season: int):
    players = _all_players(season)

    st.markdown(
        """
        <section class="latam-hero">
          <div class="latam-eyebrow">FOOTBALL INTELLIGENCE · SOUTH AMERICA</div>
          <h1>Dados para encontrar o próximo jogador antes do mercado.</h1>
          <p>Scouting, rankings, comparação, contexto de mercado e análise de times em uma única plataforma.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Busca global",
        placeholder="Buscar jogador ou clube...",
        label_visibility="collapsed",
        key="home_global_search",
    )

    if not players.empty and query:
        mask = (
            players.player.str.contains(query, case=False, na=False)
            | players.club.str.contains(query, case=False, na=False)
        )
        result = players[mask].sort_values("performance_score", ascending=False).head(12)
        with st.container(border=True):
            st.subheader("Resultados")
            st.dataframe(
                result[
                    [
                        "player", "club", "league", "position", "age", "minutes",
                        "rating", "performance_score", "opportunity_score",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
            )

    if players.empty:
        st.warning("Base de jogadores indisponível.")
        return

    qualified = players[players.minutes.fillna(0) >= 600].copy()
    a, b, c, d = st.columns(4)
    a.metric("Jogadores", f"{len(players):,}".replace(",", "."))
    b.metric("Clubes", int(players.club.nunique()))
    c.metric("Ligas", int(players.league.nunique()))
    d.metric("Sub-23", int((players.age.fillna(99) <= 23).sum()))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Ranking de impacto")
        cols = [
            "player", "club", "position", "age", "minutes",
            "performance_score", "archetype",
        ]
        st.dataframe(
            qualified.sort_values("performance_score", ascending=False)[cols].head(10),
            hide_index=True,
            use_container_width=True,
        )
    with right:
        st.subheader("Oportunidades Sub-23")
        u23 = qualified[qualified.age.fillna(99) <= 23]
        cols = [
            "player", "club", "position", "age", "minutes",
            "opportunity_score", "market_value_m", "archetype",
        ]
        st.dataframe(
            u23.sort_values("opportunity_score", ascending=False)[cols].head(10),
            hide_index=True,
            use_container_width=True,
        )


def ranking_v2(season: int):
    st.title("Ranking")
    entity = st.segmented_control(
        "Tipo",
        ["Jogadores", "Equipes"],
        default="Jogadores",
        key="ranking_entity",
    )

    if entity == "Equipes":
        _team_ranking(season)
        return

    leagues = st.multiselect(
        "Liga",
        list(LEAGUES),
        default=list(LEAGUES),
        format_func=lambda key: LEAGUES[key].name,
        key="rank_v2_leagues",
    )
    if not leagues:
        return

    df, errors = load_players(leagues, season)
    for key, error in errors:
        st.warning(f"{LEAGUES[key].name}: {error}")
    if df.empty:
        st.error("Não foi possível carregar jogadores.")
        return

    c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
    category = c1.selectbox("Categoria", list(PLAYER_METRICS), key="rank_category")
    metric_name = c2.selectbox("Indicador", list(PLAYER_METRICS[category]), key="rank_metric")
    mode = c3.segmented_control("Formato", ["Por 90", "Total"], default="Por 90")
    min_minutes = c4.number_input("Min. minutos", min_value=0, max_value=5000, value=450, step=90)

    m1, m2, m3, m4 = st.columns([1.2, 1.2, 1.2, 2])
    positions = sorted(df.position.dropna().unique())
    pos = m1.multiselect("Posições", positions, default=positions)
    ages = pd.to_numeric(df.age, errors="coerce").dropna()
    age_min = int(ages.min()) if not ages.empty else 16
    age_max = int(ages.max()) if not ages.empty else 45
    age_range = m2.slider("Idade", age_min, age_max, (age_min, age_max))
    min_impact = m3.slider("Impact mínimo", 0, 100, 0)
    search = m4.text_input("Buscar jogador ou clube", placeholder="Nome...")

    per90_col, total_col = PLAYER_METRICS[category][metric_name]
    working = df[
        df.position.isin(pos)
        & (df.minutes.fillna(0) >= min_minutes)
        & (df.performance_score.fillna(0) >= min_impact)
        & (df.age.isna() | df.age.between(age_range[0], age_range[1]))
    ].copy()

    if search:
        working = working[
            working.player.str.contains(search, case=False, na=False)
            | working.club.str.contains(search, case=False, na=False)
        ]

    if mode == "Total" and category != "LATAMDATA" and metric_name != "Defesas %":
        working["ranking_value"] = _metric_total(working, per90_col, total_col)
    else:
        working["ranking_value"] = pd.to_numeric(working.get(per90_col), errors="coerce")

    ascending = per90_col in {"goals_conceded90"}
    working = working.dropna(subset=["ranking_value"]).sort_values(
        "ranking_value", ascending=ascending
    )

    st.caption(f"{len(working)} atletas no recorte · {metric_name} · {mode}")
    _rank_cards(working, "ranking_value", f"{metric_name} · {mode}")


def _team_ranking(season: int):
    league_key = st.selectbox(
        "Liga",
        list(LEAGUES),
        format_func=lambda key: LEAGUES[key].name,
        key="team_rank_league",
    )
    raw = league_team_stats(league_key, season)
    df = prepare_team_stats(raw)
    if df.empty:
        st.warning("Estatísticas de equipes indisponíveis.")
        return

    c1, c2, c3 = st.columns([1.5, 1.5, 2])
    category = c1.selectbox("Categoria", list(TEAM_METRICS), key="team_rank_category")
    metric_name = c2.selectbox("Indicador", list(TEAM_METRICS[category]), key="team_rank_metric")
    search = c3.text_input("Buscar equipe", key="team_rank_search")

    metric, _ = TEAM_METRICS[category][metric_name]
    work = df.copy()
    if search:
        work = work[work.team.str.contains(search, case=False, na=False)]
    lower = metric in {"goals_conceded_team_match", "expected_goals_conceded_team"}
    work = work.dropna(subset=[metric]).sort_values(metric, ascending=lower)

    for pos, row in enumerate(work.itertuples(), start=1):
        with st.container(border=True):
            a, b, c, d = st.columns([.6, 5, 3, 1.2], vertical_alignment="center")
            a.markdown(f"### {pos}")
            b.markdown(f"**{row.team}**")
            b.caption(row.league)
            c.caption(getattr(row, "tactical_style", ""))
            d.markdown(
                f"<div class='latam-value'>{_fmt(getattr(row, metric))}</div>",
                unsafe_allow_html=True,
            )
            d.caption(metric_name)


def _compare_radar(rows: pd.DataFrame, metrics: list[str]) -> go.Figure:
    labels = [COMPARE_LABELS.get(m, m) for m in metrics]
    fig = go.Figure()

    for _, row in rows.iterrows():
        values = []
        for metric in metrics:
            if metric in {"performance_score", "opportunity_score", "dimension_finishing", "dimension_creation", "dimension_possession", "dimension_defense"}:
                value = row.get(metric)
            else:
                value = row.get(f"pct_{metric}")
            values.append(0 if pd.isna(value) else float(value))
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name=row["player"],
                opacity=.55,
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=620,
        margin=dict(l=45, r=45, t=40, b=35),
        legend=dict(orientation="h", y=1.08),
    )
    return fig


def compare_v2(season: int):
    st.title("Comparar")
    entity = st.segmented_control(
        "Tipo",
        ["Jogadores", "Equipes"],
        default="Jogadores",
        key="compare_entity_v2",
    )
    if entity == "Equipes":
        _compare_teams(season)
        return

    players = _all_players(season)
    if players.empty:
        st.warning("Base de jogadores indisponível.")
        return

    label_by_key = {
        f"{row.league_key}:{int(row.player_id)}": f"{row.player} — {row.club}"
        for row in players.sort_values("player").itertuples()
    }
    options = list(label_by_key)
    chosen = st.multiselect(
        "Comparando",
        options,
        max_selections=4,
        format_func=lambda key: label_by_key[key],
        placeholder="Selecione de 2 a 4 jogadores",
    )

    available = list(COMPARE_LABELS)
    indicators = st.multiselect(
        "Indicadores",
        available,
        default=COMPARE_DEFAULTS,
        format_func=lambda metric: COMPARE_LABELS[metric],
        max_selections=12,
    )

    if len(chosen) < 2:
        st.info("Selecione pelo menos 2 jogadores para comparar.")
        return

    mask = pd.Series(False, index=players.index)
    for key in chosen:
        league_key, player_id = key.split(":")
        mask |= (players.league_key == league_key) & (players.player_id.astype(str) == player_id)
    rows = players[mask].copy()

    if indicators:
        st.plotly_chart(_compare_radar(rows, indicators), use_container_width=True)

    table = []
    for metric in indicators:
        item = {"Indicador": COMPARE_LABELS.get(metric, metric)}
        for _, row in rows.iterrows():
            item[row.player] = row.get(metric)
        table.append(item)
    if table:
        st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)


def _compare_teams(season: int):
    league_key = st.selectbox(
        "Liga",
        list(LEAGUES),
        format_func=lambda key: LEAGUES[key].name,
        key="compare_team_league",
    )
    df = prepare_team_stats(league_team_stats(league_key, season))
    if df.empty:
        st.warning("Dados de equipes indisponíveis.")
        return

    names = sorted(df.team.dropna().unique())
    chosen = st.multiselect("Comparando", names, max_selections=4)
    if len(chosen) < 2:
        st.info("Selecione pelo menos 2 equipes.")
        return

    rows = df[df.team.isin(chosen)]
    metrics = [
        ("Ataque", "team_attack"),
        ("Controle", "team_control"),
        ("Pressão", "team_pressing"),
        ("Defesa", "team_defense"),
    ]
    fig = go.Figure()
    labels = [label for label, _ in metrics]
    for row in rows.itertuples():
        values = [float(getattr(row, metric) or 0) for _, metric in metrics]
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name=row.team,
                opacity=.55,
            )
        )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=600,
        legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig, use_container_width=True)

    cols = ["team", "tactical_style", "team_attack", "team_control", "team_pressing", "team_defense"]
    st.dataframe(rows[cols], hide_index=True, use_container_width=True)
