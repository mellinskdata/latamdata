from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config import LEAGUES
from scout_analytics import (
    RADAR_METRICS,
    LABELS,
    player_signals,
    similar_players,
    strengths_weaknesses,
)
from charts import radar_chart, percentile_bars, shotmap_figure
from ui.common import load_players, player_details, source_badges


TABLE_COLUMNS = [
    "player", "club", "league", "position", "age", "minutes", "rating",
    "goals90", "assists90", "xg90", "xa90", "performance_score",
    "market_value_m", "value_score", "opportunity_score", "archetype",
]


def _safe(value, digits=1, suffix=""):
    if value is None or pd.isna(value):
        return "—"
    if isinstance(value, (int, np.integer)):
        return f"{int(value)}{suffix}"
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def _player_selector(df: pd.DataFrame, label: str, key: str | None = None):
    labels = {
        f"{row.league_key}:{int(row.player_id)}":
            f"{row.player} — {row.club} ({LEAGUES[row.league_key].name})"
        for row in df.sort_values(["player", "club"]).itertuples()
    }
    selected = st.selectbox(
        label,
        list(labels),
        format_func=lambda value: labels[value],
        key=key,
    )
    league_key, player_id = selected.split(":")
    row = df[
        (df.league_key == league_key)
        & (df.player_id.astype(str) == player_id)
    ].iloc[0].copy()
    return league_key, int(player_id), row


def _metric_rows(player: pd.Series) -> pd.DataFrame:
    metrics = [
        "goals90", "assists90", "xg90", "xa90", "xgot90",
        "shots90", "shots_on_target90",
        "key_pass90", "big_chances_created90", "passes90",
        "long_balls90", "dribbles90",
        "defensive_actions90", "tackles90", "interceptions90",
        "recoveries90", "clearances90", "blocks90", "high_press_wins90",
        "save_pct", "saves90", "goals_prevented90", "goals_conceded90",
    ]
    rows = []
    for metric in metrics:
        value = player.get(metric)
        pct = player.get(f"pct_{metric}")
        if pd.notna(value):
            rows.append(
                {
                    "Métrica": LABELS.get(metric, metric),
                    "Valor": round(float(value), 2),
                    "Percentil": np.nan if pd.isna(pct) else round(float(pct), 0),
                }
            )
    return pd.DataFrame(rows)


def _profile_view(df: pd.DataFrame):
    league_key, player_id, player = _player_selector(
        df, "Jogador", "profile_player"
    )

    season_name = None
    if pd.notna(player.get("season")):
        season_name = str(player.get("season"))

    details = {}
    try:
        with st.spinner("Carregando relatório detalhado do atleta..."):
            details = player_details(player_id, league_key, season_name)
    except Exception as exc:
        st.caption(f"Detalhamento individual indisponível: {exc}")

    image_url = details.get(
        "image_url",
        f"https://images.fotmob.com/image_resources/playerimages/{player_id}.png",
    )

    photo, identity = st.columns([1, 6])
    with photo:
        st.image(image_url, width=120)
    with identity:
        st.title(player.player)
        st.caption(
            f"{player.club} · {player.league} · {player.position_label or player.position} "
            f"· {player.nationality or '—'}"
        )
        st.markdown(f"**Arquétipo LATAMDATA:** {player.archetype}")

    kpis = st.columns(7)
    kpis[0].metric("Idade", _safe(player.age, 0))
    kpis[1].metric("Minutos", _safe(player.minutes, 0))
    kpis[2].metric("Nota", _safe(player.rating, 2))
    kpis[3].metric("Impact Score", _safe(player.performance_score, 1))
    kpis[4].metric("Confiabilidade", _safe(player.reliability_score, 0, "%"))
    kpis[5].metric(
        "Valor",
        "—" if pd.isna(player.market_value_m)
        else f"€ {player.market_value_m:.1f} mi",
    )
    kpis[6].metric("Opportunity", _safe(player.opportunity_score, 1))

    st.subheader("Perfil multidimensional")
    dimensions = st.columns(4)
    dimensions[0].metric("Finalização", _safe(player.dimension_finishing, 0))
    dimensions[1].metric("Criação", _safe(player.dimension_creation, 0))
    dimensions[2].metric("Posse", _safe(player.dimension_possession, 0))
    dimensions[3].metric("Defesa", _safe(player.dimension_defense, 0))

    left, right = st.columns([1, 1.15])
    with left:
        st.plotly_chart(
            radar_chart(player, RADAR_METRICS),
            use_container_width=True,
        )
    with right:
        metric_rows = _metric_rows(player)
        st.plotly_chart(
            percentile_bars(metric_rows),
            use_container_width=True,
        )

    signals = player_signals(player)
    if signals:
        st.subheader("Sinais do modelo")
        for signal in signals:
            st.write(f"• {signal}")

    strong, weak = strengths_weaknesses(player)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Pontos fortes")
        for name, value in strong:
            st.progress(int(value), text=f"{name} — P{value:.0f}")
    with c2:
        st.subheader("Pontos de atenção")
        for name, value in weak:
            st.progress(int(value), text=f"{name} — P{value:.0f}")

    detail_table = details.get("stats")
    shotmap = details.get("shotmap")
    if isinstance(detail_table, pd.DataFrame) and not detail_table.empty:
        st.subheader("Relatório estatístico detalhado")
        show = detail_table[
            ["group", "title", "value", "per90", "percentile"]
        ].copy()
        show.columns = ["Grupo", "Métrica", "Total", "Por 90", "Percentil FotMob"]
        st.dataframe(show, hide_index=True, use_container_width=True)

    if isinstance(shotmap, pd.DataFrame) and not shotmap.empty:
        st.subheader("Mapa de finalizações")
        st.pyplot(shotmap_figure(shotmap), use_container_width=True)
        if "xg" in shotmap:
            s1, s2, s3 = st.columns(3)
            s1.metric("Finalizações mapeadas", len(shotmap))
            s2.metric("xG no mapa", f"{shotmap['xg'].sum():.2f}")
            if "on_target" in shotmap:
                s3.metric("No alvo", int(shotmap["on_target"].fillna(False).sum()))

    st.subheader("Jogadores similares")
    similar = similar_players(
        df,
        player_id,
        league_key=league_key,
        n=10,
    )
    if similar.empty:
        st.info("Amostra insuficiente para similaridade.")
    else:
        columns = [
            "player", "club", "league", "position", "age", "minutes",
            "performance_score", "market_value_m", "opportunity_score",
            "archetype", "similarity",
        ]
        st.dataframe(
            similar[columns],
            hide_index=True,
            use_container_width=True,
        )


def _filtered_market(df: pd.DataFrame):
    query = st.text_input("Pesquisar jogador ou clube")
    f1, f2, f3, f4 = st.columns(4)

    positions = sorted(df.position.dropna().unique())
    positions_selected = f1.multiselect(
        "Posição",
        positions,
        default=positions,
    )

    ages = pd.to_numeric(df.age, errors="coerce").dropna()
    min_age = int(ages.min()) if not ages.empty else 16
    max_age = int(ages.max()) if not ages.empty else 40
    age_range = f2.slider(
        "Idade",
        min_age,
        max_age,
        (min_age, min(max_age, 29)),
    )

    max_minutes = int(max(900, df.minutes.fillna(0).max()))
    min_minutes = f3.slider(
        "Minutos mínimos",
        0,
        max_minutes,
        min(450, max_minutes),
        90,
    )

    sort_by = f4.selectbox(
        "Ordenar por",
        [
            "performance_score",
            "opportunity_score",
            "value_score",
            "rating",
            "xg90",
            "xa90",
            "minutes",
        ],
    )

    filtered = df[
        df.position.isin(positions_selected)
        & (df.minutes.fillna(0) >= min_minutes)
        & (
            df.age.isna()
            | df.age.between(age_range[0], age_range[1])
        )
    ].copy()

    if query:
        filtered = filtered[
            filtered.player.str.contains(query, case=False, na=False)
            | filtered.club.str.contains(query, case=False, na=False)
        ]

    return filtered.sort_values(sort_by, ascending=False, na_position="last")


def scout_page(season: int):
    st.title("Scout de jogadores")
    source_badges()

    selected = st.multiselect(
        "Campeonatos carregados",
        list(LEAGUES),
        default=["bra_a"],
        format_func=lambda key: LEAGUES[key].name,
    )
    if not selected:
        return

    with st.spinner("Construindo base estatística real..."):
        df, errors = load_players(selected, season)

    for key, error in errors:
        st.warning(f"{LEAGUES[key].name}: {error}")

    if df.empty:
        st.error(
            "Não foi possível carregar a base real de atletas. "
            "O LATAMDATA não preenche a tela com jogadores fictícios."
        )
        return

    st.caption(f"{len(df)} atletas reais · temporada {season}")
    tab_market, tab_profile = st.tabs(["Mercado", "Relatório do atleta"])

    with tab_market:
        filtered = _filtered_market(df)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Atletas encontrados", len(filtered))
        k2.metric(
            "Impact mediano",
            "—" if filtered.empty else f"{filtered.performance_score.median():.1f}",
        )
        u23 = filtered[filtered.age.fillna(99) <= 23]
        k3.metric("Sub-23", len(u23))
        k4.metric(
            "Maior Opportunity",
            "—" if filtered.empty else f"{filtered.opportunity_score.max():.1f}",
        )

        show = filtered[TABLE_COLUMNS].copy()
        show.columns = [
            "Jogador", "Clube", "Liga", "Pos.", "Idade", "Minutos", "Nota",
            "Gols/90", "Ast/90", "xG/90", "xA/90", "Impact",
            "Valor € mi", "Value", "Opportunity", "Arquétipo",
        ]
        st.dataframe(
            show.head(400),
            hide_index=True,
            use_container_width=True,
        )

        if not filtered.empty:
            st.subheader("Mapa de mercado")
            x_axis = (
                "market_value_m"
                if filtered.market_value_m.notna().sum() >= 8
                else "rating"
            )
            plot_df = filtered[
                filtered[x_axis].notna()
                & filtered.performance_score.notna()
            ].copy()
            if not plot_df.empty:
                st.plotly_chart(
                    px.scatter(
                        plot_df,
                        x=x_axis,
                        y="performance_score",
                        size="minutes",
                        color="position",
                        hover_name="player",
                        hover_data=[
                            "club", "age", "archetype",
                            "xg90", "xa90", "opportunity_score",
                        ],
                        labels={
                            "performance_score": "Impact Score",
                            "market_value_m": "Valor de mercado (€ mi)",
                            "rating": "Nota FotMob",
                        },
                    ),
                    use_container_width=True,
                )

        st.download_button(
            "Exportar tabela filtrada CSV",
            filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"latamdata_scout_{season}.csv",
            mime="text/csv",
        )

    with tab_profile:
        _profile_view(df)


def compare_page(season: int):
    st.title("Comparar jogadores")
    source_badges()

    selected = st.multiselect(
        "Campeonatos",
        list(LEAGUES),
        default=["bra_a"],
        format_func=lambda key: LEAGUES[key].name,
        key="compare_leagues",
    )
    if not selected:
        return

    with st.spinner("Carregando base de comparação..."):
        df, errors = load_players(selected, season)

    for key, error in errors:
        st.warning(f"{LEAGUES[key].name}: {error}")
    if df.empty:
        st.error("A base real de jogadores está indisponível.")
        return

    a, b = st.columns(2)
    with a:
        _, _, p1 = _player_selector(df, "Jogador A", "compare_a")
    with b:
        _, _, p2 = _player_selector(df, "Jogador B", "compare_b")

    with a:
        st.subheader(p1.player)
        st.caption(f"{p1.club} · {p1.archetype}")
        st.plotly_chart(radar_chart(p1, RADAR_METRICS), use_container_width=True)
    with b:
        st.subheader(p2.player)
        st.caption(f"{p2.club} · {p2.archetype}")
        st.plotly_chart(radar_chart(p2, RADAR_METRICS), use_container_width=True)

    metrics = [
        ("Impact Score", "performance_score"),
        ("Opportunity", "opportunity_score"),
        ("Confiabilidade", "reliability_score"),
        ("Nota", "rating"),
        ("Gols/90", "goals90"),
        ("Assistências/90", "assists90"),
        ("xG/90", "xg90"),
        ("xA/90", "xa90"),
        ("xGOT/90", "xgot90"),
        ("Chances criadas/90", "key_pass90"),
        ("Dribles/90", "dribbles90"),
        ("Desarmes/90", "tackles90"),
        ("Interceptações/90", "interceptions90"),
        ("Recuperações/90", "recoveries90"),
        ("Minutos", "minutes"),
        ("Valor € mi", "market_value_m"),
    ]
    comparison = pd.DataFrame(
        {
            "Métrica": [item[0] for item in metrics],
            p1.player: [p1.get(item[1]) for item in metrics],
            p2.player: [p2.get(item[1]) for item in metrics],
        }
    )
    st.dataframe(comparison, hide_index=True, use_container_width=True)


def rankings_page(season: int):
    st.title("Rankings & oportunidades")
    source_badges()

    selected = st.multiselect(
        "Campeonatos",
        list(LEAGUES),
        default=["bra_a"],
        format_func=lambda key: LEAGUES[key].name,
        key="rank_leagues",
    )
    if not selected:
        return

    with st.spinner("Montando rankings..."):
        df, errors = load_players(selected, season)

    for key, error in errors:
        st.warning(f"{LEAGUES[key].name}: {error}")
    if df.empty:
        st.error("Não foi possível carregar os rankings.")
        return

    minimum = st.slider("Minutos mínimos", 0, int(max(900, df.minutes.max())), 600, 90)
    pool = df[df.minutes.fillna(0) >= minimum].copy()

    tabs = st.tabs([
        "Impacto",
        "Sub-23",
        "Criação",
        "Finalização",
        "Defesa",
        "Custo-benefício",
    ])

    specs = [
        ("performance_score", pool),
        ("opportunity_score", pool[pool.age.fillna(99) <= 23]),
        ("dimension_creation", pool),
        ("dimension_finishing", pool),
        ("dimension_defense", pool),
        ("value_score", pool[pool.value_score.notna()]),
    ]

    for tab, (metric, frame) in zip(tabs, specs):
        with tab:
            if frame.empty:
                st.info("Sem atletas suficientes nesse recorte.")
                continue
            columns = [
                "player", "club", "league", "position", "age", "minutes",
                metric, "rating", "market_value_m", "archetype",
            ]
            st.dataframe(
                frame.sort_values(metric, ascending=False)[columns].head(40),
                hide_index=True,
                use_container_width=True,
            )
