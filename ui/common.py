from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

from config import LEAGUES
from data.espn_client import (
    ESPNClient,
    normalize_scoreboard,
    normalize_teams,
    teams_from_matches,
    match_team_stats,
    match_lineups,
    match_events,
    match_header,
)
from data.fotmob_provider import FotMobProvider
from scout_analytics import prepare_players


@st.cache_resource
def espn_client():
    return ESPNClient()


@st.cache_resource
def fotmob_provider():
    return FotMobProvider()


@st.cache_data(ttl=900, show_spinner=False)
def league_matches(league_key: str, season: int):
    league = LEAGUES[league_key]
    return normalize_scoreboard(
        espn_client().scoreboard(league.espn_slug, season),
        league_key,
        league.name,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def league_teams(league_key: str, season: int):
    league = LEAGUES[league_key]
    try:
        df = normalize_teams(
            espn_client().teams_endpoint(league.espn_slug),
            league_key,
            league.name,
        )
        if not df.empty:
            return df
    except Exception:
        pass
    return teams_from_matches(league_matches(league_key, season))


@st.cache_data(ttl=900, show_spinner=False)
def match_summary(league_key: str, event_id: str):
    return espn_client().summary(LEAGUES[league_key].espn_slug, event_id)


@st.cache_data(ttl=21600, show_spinner=False)
def league_players(league_key: str, season: int):
    snapshot = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "snapshots"
        / f"{league_key}_{season}.csv"
    )
    if snapshot.exists():
        cached = pd.read_csv(snapshot)
        if not cached.empty:
            return cached

    try:
        frame = fotmob_provider().league_players(league_key, season)
        if not frame.empty:
            try:
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                frame.to_csv(snapshot, index=False)
            except OSError:
                pass
            return frame
    except Exception as live_error:
        raise RuntimeError(
            f"Falha na fonte FotMob e não existe snapshot local para "
            f"{LEAGUES[league_key].name} {season}: {live_error}"
        ) from live_error

    return pd.DataFrame()


@st.cache_data(ttl=21600, show_spinner=False)
def league_team_stats(league_key: str, season: int):
    snapshot = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "snapshots"
        / f"team_{league_key}_{season}.csv"
    )
    if snapshot.exists():
        cached = pd.read_csv(snapshot)
        if not cached.empty:
            return cached
    return fotmob_provider().league_team_stats(league_key, season)


@st.cache_data(ttl=21600, show_spinner=False)
def player_details(player_id: int, league_key: str, season_name: str | None = None):
    return fotmob_provider().player_details(
        int(player_id),
        league_key,
        season_name=season_name,
    )


def load_players(league_keys: list[str], season: int):
    frames, errors = [], []
    for key in league_keys:
        try:
            df = league_players(key, season)
            if not df.empty:
                frames.append(df)
        except Exception as exc:
            errors.append((key, str(exc)))
    if not frames:
        return pd.DataFrame(), errors
    return prepare_players(pd.concat(frames, ignore_index=True)), errors


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode().lower()
    return "".join(c for c in value if c.isalnum())


def format_date(value) -> str:
    try:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts.tz_convert("America/Sao_Paulo").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value or "")


def score_text(row) -> str:
    if pd.notna(row.home_score) and pd.notna(row.away_score):
        return f"{int(row.home_score)} x {int(row.away_score)}"
    return "x"


def source_badges():
    st.caption(
        "Jogadores: snapshots reais atualizados automaticamente a partir do FotMob. "
        "Jogos e central da partida: ESPN. Índices e percentis: LATAMDATA."
    )


def match_list(df, prefix: str = ""):
    if df.empty:
        st.info("Nenhuma partida encontrada.")
        return
    for row in df.itertuples():
        a, b, c, d, e = st.columns([1.4, 3, 1.2, 3, .8])
        a.caption(format_date(row.date))
        b.write(f"**{row.home}**")
        c.markdown(f"### {score_text(row)}")
        d.write(f"**{row.away}**")
        with e:
            if st.button("Abrir", key=f"{prefix}{row.league_key}_{row.event_id}"):
                st.session_state.match = (row.league_key, str(row.event_id))
                st.rerun()


def render_match_center():
    state = st.session_state.get("match")
    if not state:
        return False

    league_key, event_id = state
    st.title("Central da partida")
    if st.button("Voltar"):
        del st.session_state.match
        st.rerun()

    try:
        data = match_summary(league_key, event_id)
        header = match_header(data)

        left, center, right = st.columns([2, 1, 2])
        with left:
            if header["home_logo"]:
                st.image(header["home_logo"], width=70)
            st.subheader(header["home"])
        with center:
            hs = "-" if header["home_score"] in (None, "") else header["home_score"]
            aws = "-" if header["away_score"] in (None, "") else header["away_score"]
            st.markdown(f"## {hs} x {aws}")
        with right:
            if header["away_logo"]:
                st.image(header["away_logo"], width=70)
            st.subheader(header["away"])

        st.caption(
            f"{format_date(header['date'])} · {header['venue']} · {header['status']}"
        )
        tab_stats, tab_lineups, tab_events = st.tabs(
            ["Estatísticas", "Escalações", "Eventos"]
        )
        with tab_stats:
            frame = match_team_stats(data)
            if frame.empty:
                st.info("Sem estatísticas detalhadas para esta partida.")
            else:
                st.dataframe(frame.T, use_container_width=True)
        with tab_lineups:
            frame = match_lineups(data)
            if frame.empty:
                st.info("Escalações indisponíveis.")
            else:
                st.dataframe(frame, hide_index=True, use_container_width=True)
        with tab_events:
            frame = match_events(data)
            if frame.empty:
                st.info("Eventos indisponíveis.")
            else:
                st.dataframe(frame, hide_index=True, use_container_width=True)
    except Exception as exc:
        st.error(str(exc))
    return True
