
import pandas as pd
import streamlit as st
import plotly.express as px
from analytics import add_percentiles, add_value_score, similar_players, player_strengths_weaknesses, RADAR_METRICS
from charts import radar_chart, heatmap_figure

st.set_page_config(
    page_title="ScoutLATAM",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_data():
    players = pd.read_csv("players.csv")
    events = pd.read_csv("events.csv")
    players = add_percentiles(players)
    players = add_value_score(players)
    return players, events

df, events = load_data()

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
[data-testid="stMetricValue"] {font-size: 1.65rem;}
.small-muted {opacity: .7; font-size: .88rem;}
.hero {
    padding: 1rem 1.2rem; border: 1px solid rgba(128,128,128,.25);
    border-radius: 14px; margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("⚽ ScoutLATAM")
st.sidebar.caption("Recruitment analytics para Brasil e América do Sul")

page = st.sidebar.radio(
    "Navegação",
    ["Descobrir jogadores", "Perfil do atleta", "Comparar", "Metodologia"]
)

if page == "Descobrir jogadores":
    st.title("Descobrir jogadores")
    st.caption("Filtre o mercado e encontre atletas que combinam desempenho, perfil e valor.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        leagues = st.multiselect("Ligas", sorted(df["league"].unique()), default=sorted(df["league"].unique()))
    with c2:
        positions = st.multiselect("Posições", sorted(df["position"].unique()), default=sorted(df["position"].unique()))
    with c3:
        age = st.slider("Idade", int(df.age.min()), int(df.age.max()), (18,25))
    with c4:
        max_value = st.slider("Valor máximo (€ mi)", 0.5, float(max(15, df.market_value_m.quantile(.95))), 6.0, 0.5)

    c5, c6, c7 = st.columns(3)
    with c5:
        min_minutes = st.slider("Minutos mínimos", 0, 3000, 900, 100)
    with c6:
        min_perf = st.slider("Performance mínima", 35, 95, 60)
    with c7:
        sort_by = st.selectbox("Ordenar por", ["value_score","performance_score","market_value_m","age"])

    filtered = df[
        df["league"].isin(leagues) &
        df["position"].isin(positions) &
        df["age"].between(*age) &
        (df["market_value_m"] <= max_value) &
        (df["minutes"] >= min_minutes) &
        (df["performance_score"] >= min_perf)
    ].copy()

    ascending = sort_by in ["market_value_m","age"]
    filtered = filtered.sort_values(sort_by, ascending=ascending)

    a,b,c,d = st.columns(4)
    a.metric("Jogadores encontrados", len(filtered))
    b.metric("Valor mediano", f"€ {filtered.market_value_m.median():.1f} mi" if len(filtered) else "—")
    c.metric("Score médio", f"{filtered.performance_score.mean():.1f}" if len(filtered) else "—")
    d.metric("Melhor Value Score", f"{filtered.value_score.max():.1f}" if len(filtered) else "—")

    display_cols = [
        "player","club","league","age","position","minutes",
        "market_value_m","performance_score","value_score"
    ]
    st.dataframe(
        filtered[display_cols].rename(columns={
            "player":"Jogador","club":"Clube","league":"Liga","age":"Idade",
            "position":"Pos.","minutes":"Minutos","market_value_m":"Valor € mi",
            "performance_score":"Performance","value_score":"Custo-benefício"
        }),
        use_container_width=True,
        hide_index=True
    )

    if len(filtered):
        st.subheader("Mapa de mercado")
        fig = px.scatter(
            filtered, x="market_value_m", y="performance_score",
            size="minutes", color="position", hover_name="player",
            hover_data=["club","league","age","value_score"],
            labels={
                "market_value_m":"Valor de mercado (€ mi)",
                "performance_score":"Performance Score",
                "position":"Posição"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

elif page == "Perfil do atleta":
    st.title("Perfil do atleta")
    options = df.sort_values("player")[["player_id","player","club","position"]]
    labels = {
        r.player_id: f"{r.player} — {r.club} ({r.position})"
        for r in options.itertuples()
    }
    player_id = st.selectbox(
        "Jogador",
        options.player_id.tolist(),
        format_func=lambda x: labels[x]
    )
    p = df[df.player_id == player_id].iloc[0]

    st.markdown(
        f"""<div class="hero">
        <h2 style="margin:0">{p['player']}</h2>
        <div class="small-muted">{p['club']} · {p['league']} · {p['nationality']} · {p['position']}</div>
        </div>""",
        unsafe_allow_html=True
    )

    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Idade", int(p.age))
    m2.metric("Minutos", f"{int(p.minutes):,}".replace(",","."))
    m3.metric("Valor", f"€ {p.market_value_m:.2f} mi")
    m4.metric("Performance", f"{p.performance_score:.1f}")
    m5.metric("Custo-benefício", f"{p.value_score:.1f}")
    m6.metric("Pé", p.foot)

    left, right = st.columns([1.05, 1])
    with left:
        st.subheader("Perfil estatístico")
        st.plotly_chart(radar_chart(p, RADAR_METRICS), use_container_width=True)
    with right:
        st.subheader("Mapa de calor médio")
        player_events = events[events.player_id == player_id]
        st.pyplot(heatmap_figure(player_events), use_container_width=True)

    st.subheader("Principais métricas")
    metric_rows = pd.DataFrame([
        ["Gols / 90", p.goals90, p.pct_goals90],
        ["Assistências / 90", p.assists90, p.pct_assists90],
        ["xG / 90", p.xg90, p.pct_xg90],
        ["xA / 90", p.xa90, p.pct_xa90],
        ["Passes progressivos / 90", p.prog_pass90, p.pct_prog_pass90],
        ["Conduções progressivas / 90", p.prog_carry90, p.pct_prog_carry90],
        ["Passes-chave / 90", p.key_pass90, p.pct_key_pass90],
        ["Interceptações / 90", p.interceptions90, p.pct_interceptions90],
        ["Recuperações / 90", p.recoveries90, p.pct_recoveries90],
        ["Duelos vencidos %", p.duel_win_pct, p.pct_duel_win_pct],
        ["Pressões / 90", p.pressures90, p.pct_pressures90],
    ], columns=["Métrica","Valor","Percentil na posição"])
    st.dataframe(metric_rows, use_container_width=True, hide_index=True)

    strengths, weaknesses = player_strengths_weaknesses(p)
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Pontos fortes")
        for name, pct in strengths:
            st.progress(int(pct), text=f"{name} — P{pct:.0f}")
    with c2:
        st.subheader("Pontos a desenvolver")
        for name, pct in weaknesses:
            st.progress(int(pct), text=f"{name} — P{pct:.0f}")

    st.subheader("Jogadores similares")
    sim = similar_players(df, player_id, n=8)
    if not sim.empty:
        st.dataframe(
            sim[["player","club","league","age","market_value_m","performance_score","value_score","similarity"]]
            .rename(columns={
                "player":"Jogador","club":"Clube","league":"Liga","age":"Idade",
                "market_value_m":"Valor € mi","performance_score":"Performance",
                "value_score":"Custo-benefício","similarity":"Similaridade %"
            }),
            use_container_width=True, hide_index=True
        )

elif page == "Comparar":
    st.title("Comparar jogadores")
    col1, col2 = st.columns(2)
    labels = {r.player_id: f"{r.player} — {r.club} ({r.position})" for r in df.itertuples()}
    ids = df.player_id.tolist()

    with col1:
        p1_id = st.selectbox("Jogador A", ids, index=0, format_func=lambda x: labels[x])
    with col2:
        p2_id = st.selectbox("Jogador B", ids, index=1, format_func=lambda x: labels[x])

    p1 = df[df.player_id == p1_id].iloc[0]
    p2 = df[df.player_id == p2_id].iloc[0]

    c1,c2 = st.columns(2)
    with c1:
        st.subheader(p1.player)
        st.plotly_chart(radar_chart(p1, RADAR_METRICS), use_container_width=True)
    with c2:
        st.subheader(p2.player)
        st.plotly_chart(radar_chart(p2, RADAR_METRICS), use_container_width=True)

    metrics = [
        ("Performance","performance_score"),
        ("Custo-benefício","value_score"),
        ("Valor € mi","market_value_m"),
        ("xG / 90","xg90"),
        ("xA / 90","xa90"),
        ("Passes prog. / 90","prog_pass90"),
        ("Conduções prog. / 90","prog_carry90"),
        ("Interceptações / 90","interceptions90"),
        ("Duelos %","duel_win_pct"),
        ("Pressões / 90","pressures90")
    ]
    comp = pd.DataFrame({
        "Métrica":[x[0] for x in metrics],
        p1.player:[p1[x[1]] for x in metrics],
        p2.player:[p2[x[1]] for x in metrics],
    })
    st.dataframe(comp, use_container_width=True, hide_index=True)

else:
    st.title("Metodologia")
    st.markdown("""
### O que este MVP faz

O **ScoutLATAM** usa uma base demonstrativa sintética para permitir que toda a aplicação funcione sem depender de APIs pagas ou scraping.

**Performance Score** é um índice demonstrativo já presente na base de exemplo. Em uma versão real, ele deve ser recalculado por posição, função, liga, idade e contexto da equipe.

**Percentis** são calculados apenas contra jogadores da mesma posição. Isso evita comparar, por exemplo, volume ofensivo de um zagueiro com o de um centroavante.

**Custo-benefício** combina performance ajustada por liga e idade com o valor de mercado:

`valor_score ∝ performance_ajustada / sqrt(valor_de_mercado)`

Depois, o resultado é normalizado de 0 a 100.

**Similaridade** padroniza métricas por jogador e usa distância de cosseno dentro da mesma posição. É uma baseline interpretável; depois pode ser substituída por PCA, UMAP, clustering ou embeddings.

**Heatmap** usa eventos espaciais `x, y`. No dataset demonstrativo esses eventos são sintéticos; em produção, devem vir de event data real.

### Para transformar em produto real

1. Substitua `players.csv` por dados reais.
2. Substitua `events.csv` por event data com coordenadas.
3. Adicione histórico por temporada e partida.
4. Modele força de liga e contexto de equipe.
5. Treine um modelo de valuation com transferências reais.
6. Adicione contratos, salário estimado, pé, altura e elegibilidade.
7. Inclua filtros por função: progressor, criador, marcador, finalizador etc.
8. Salve shortlists e relatórios em banco PostgreSQL.
    """)

st.sidebar.divider()
st.sidebar.caption("Dataset atual: demonstração sintética. Arquitetura pronta para dados reais.")
