import numpy as np
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt


def radar_chart(player_row, radar_metrics):
    pairs = []
    for label, metric in radar_metrics.items():
        if metric in player_row.index and pd.notna(player_row.get(metric)):
            value = player_row.get(metric)
        else:
            value = player_row.get(f"pct_{metric}")
        if pd.notna(value):
            pairs.append((label, float(value)))

    if len(pairs) < 3:
        fig = go.Figure()
        fig.add_annotation(text="Dados insuficientes para radar", showarrow=False)
        fig.update_layout(height=420)
        return fig

    labels = [item[0] for item in pairs]
    values = [item[1] for item in pairs]
    fig = go.Figure(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            hovertemplate="%{theta}: %{r:.0f}/100<extra></extra>",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[20, 40, 60, 80, 100],
            )
        ),
        showlegend=False,
        margin=dict(l=35, r=35, t=25, b=25),
        height=430,
    )
    return fig


def percentile_bars(rows: pd.DataFrame):
    if rows is None or rows.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem percentis disponíveis", showarrow=False)
        return fig

    frame = rows.dropna(subset=["Percentil"]).copy().sort_values("Percentil")
    fig = go.Figure(
        go.Bar(
            x=frame["Percentil"],
            y=frame["Métrica"],
            orientation="h",
            text=frame["Percentil"].map(lambda value: f"P{value:.0f}"),
            textposition="outside",
            customdata=frame[["Valor"]].to_numpy(),
            hovertemplate="%{y}<br>Valor: %{customdata[0]}<br>Percentil: %{x:.0f}<extra></extra>",
        )
    )
    fig.update_xaxes(range=[0, 105], title="Percentil na posição")
    fig.update_layout(
        height=max(360, 31 * len(frame)),
        margin=dict(l=10, r=35, t=20, b=25),
        yaxis_title="",
        showlegend=False,
    )
    return fig


def _draw_pitch(ax):
    ax.set_xlim(0, 105)
    ax.set_ylim(0, 68)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.plot([0, 105, 105, 0, 0], [0, 0, 68, 68, 0], linewidth=1.5)
    ax.plot([52.5, 52.5], [0, 68], linewidth=1.1)
    ax.add_patch(plt.Circle((52.5, 34), 9.15, fill=False, linewidth=1.1))
    ax.plot([0, 16.5, 16.5, 0], [13.84, 13.84, 54.16, 54.16], linewidth=1.1)
    ax.plot([105, 88.5, 88.5, 105], [13.84, 13.84, 54.16, 54.16], linewidth=1.1)
    ax.plot([0, 5.5, 5.5, 0], [24.84, 24.84, 43.16, 43.16], linewidth=1.0)
    ax.plot([105, 99.5, 99.5, 105], [24.84, 24.84, 43.16, 43.16], linewidth=1.0)


def shotmap_figure(shots: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    _draw_pitch(ax)

    if shots is None or shots.empty or not {"x", "y"}.issubset(shots.columns):
        return fig

    frame = shots.copy()
    frame["x"] = pd.to_numeric(frame["x"], errors="coerce")
    frame["y"] = pd.to_numeric(frame["y"], errors="coerce")
    frame["xg"] = pd.to_numeric(frame.get("xg", 0), errors="coerce").fillna(0)
    frame = frame.dropna(subset=["x", "y"])

    if frame.empty:
        return fig

    sizes = 35 + frame["xg"].clip(lower=0, upper=1) * 300
    ax.scatter(
        frame["x"],
        frame["y"],
        s=sizes,
        alpha=.58,
        edgecolors="black",
        linewidths=.45,
    )
    return fig


def heatmap_figure(events):
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    _draw_pitch(ax)

    if events is not None and len(events) >= 5 and {"x", "y"}.issubset(events.columns):
        frame = events[["x", "y"]].apply(pd.to_numeric, errors="coerce").dropna()
        if not frame.empty:
            x = frame["x"].to_numpy()
            y = frame["y"].to_numpy()
            if np.nanmax(x) <= 100.5 and np.nanmax(y) <= 100.5:
                x = x * 1.05
                y = y * .68
            heat, _, _ = np.histogram2d(
                x,
                y,
                bins=(30, 20),
                range=[[0, 105], [0, 68]],
            )
            ax.imshow(
                heat.T,
                extent=[0, 105, 0, 68],
                origin="lower",
                interpolation="gaussian",
                alpha=.72,
                aspect="auto",
            )
    return fig
