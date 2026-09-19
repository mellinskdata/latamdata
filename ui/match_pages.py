from __future__ import annotations

import pandas as pd
import streamlit as st

from config import LEAGUES
from scout_analytics import team_form, team_summary, prepare_players
from ui.common import (
    league_matches, league_teams, league_players, match_list, normalize_name,
)


def home_page(season: int):
    st.title("LATAMDATA")
    st.subheader("Football intelligence for South America")
    st.success("Times, jogos e atletas reais. Não há fallback para jogadores fictícios.")

    frames = []
    for key in LEAGUES:
        try:
            frames.append(league_matches(key, season))
        except Exception:
            pass

    if not frames:
        st.warning("Não foi possível carregar partidas agora.")
        return

    df = pd.concat(frames, ignore_index=True)
    now = pd.Timestamp.now(tz="UTC")
    left, right = st.columns(2)
    with left:
        st.subheader("Últimos jogos")
        match_list(
            df[df.date <= now].sort_values("date", ascending=False).head(6),
            "home_last_",
        )
    with right:
        st.subheader("Próximos jogos")
        match_list(
            df[df.date > now].sort_values("date").head(6),
            "home_next_",
        )


def teams_page(season: int):
    st.title("Times")
    key = st.selectbox(
        "Campeonato",
        list(LEAGUES),
        format_func=lambda x: LEAGUES[x].name,
    )

    try:
        teams = league_teams(key, season).sort_values("team")
        query = st.text_input("Pesquisar time")
        if query:
            teams = teams[teams.team.str.contains(query, case=False, na=False)]
        if teams.empty:
            st.info("Nenhum time encontrado.")
            return

        labels = {row.team_id: row.team for row in teams.itertuples()}
        team_id = st.selectbox(
            "Time",
            teams.team_id.tolist(),
            format_func=lambda x: labels[x],
        )
        team = teams[teams.team_id.astype(str) == str(team_id)].iloc[0]

        if team.logo:
            st.image(team.logo, width=80)
        st.header(team.team)

        matches = league_matches(key, season)
        summary = team_summary(matches, team_id)
        cols = st.columns(5)
        metrics = [
            ("Jogos", summary["games"]),
            ("Vitórias", summary["wins"]),
            ("Empates", summary["draws"]),
            ("Derrotas", summary["losses"]),
            ("Pts/jogo", summary["ppg"]),
        ]
        for col, (label, value) in zip(cols, metrics):
            col.metric(label, value)

        form = team_form(matches, team_id, 10)
        if not form.empty:
            st.write("Forma recente: " + " ".join(form.result.astype(str)))

        tab_games, tab_players = st.tabs(["Partidas", "Jogadores"])
        with tab_games:
            club_matches = matches[
                (matches.home_id.astype(str) == str(team_id))
                | (matches.away_id.astype(str) == str(team_id))
            ]
            match_list(
                club_matches.sort_values("date", ascending=False).head(30),
                "team_",
            )

        with tab_players:
            with st.spinner("Carregando elenco estatístico real..."):
                players = prepare_players(league_players(key, season))
            club_norm = normalize_name(team.team)
            names = players.club.fillna("").map(normalize_name)
            players = players[
                names.map(
                    lambda value: value == club_norm
                    or club_norm in value
                    or value in club_norm
                )
            ]
            if players.empty:
                st.info("Não consegui casar o nome do clube entre as duas fontes.")
            else:
                columns = [
                    "player", "position", "minutes", "rating",
                    "goals90", "assists90", "xg90", "xa90",
                    "performance_score",
                ]
                st.dataframe(
                    players[columns].sort_values("minutes", ascending=False),
                    hide_index=True,
                    use_container_width=True,
                )
    except Exception as exc:
        st.error(str(exc))


def games_page(season: int):
    st.title("Jogos")
    selected = st.multiselect(
        "Campeonatos",
        list(LEAGUES),
        default=list(LEAGUES),
        format_func=lambda x: LEAGUES[x].name,
    )

    frames = []
    for key in selected:
        try:
            frames.append(league_matches(key, season))
        except Exception as exc:
            st.warning(f"{LEAGUES[key].name}: {exc}")

    if not frames:
        st.info("Nenhuma partida disponível.")
        return

    df = pd.concat(frames, ignore_index=True)
    query = st.text_input("Buscar time")
    if query:
        df = df[
            df.home.str.contains(query, case=False, na=False)
            | df.away.str.contains(query, case=False, na=False)
        ]

    mode = st.radio(
        "Mostrar",
        ["Recentes", "Próximos", "Todos"],
        horizontal=True,
    )
    now = pd.Timestamp.now(tz="UTC")
    if mode == "Recentes":
        df = df[df.date <= now].sort_values("date", ascending=False).head(80)
    elif mode == "Próximos":
        df = df[df.date > now].sort_values("date").head(80)
    else:
        df = df.sort_values("date", ascending=False)

    match_list(df, "games_")
