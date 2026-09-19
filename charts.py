import numpy as np
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt


def radar_chart(player_row, radar_metrics):
    pairs = []
    for label, metric in radar_metrics.items():
        value = player_row.get(f"pct_{metric}")
        if pd.notna(value):
            pairs.append((label, float(value)))
    if len(pairs) < 3:
        fig = go.Figure()
        fig.add_annotation(text="Dados insuficientes para radar", showarrow=False)
        fig.update_layout(height=420)
        return fig
    labels = [p[0] for p in pairs]
    values = [p[1] for p in pairs]
    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]], theta=labels + [labels[0]], fill="toself",
        hovertemplate="%{theta}: P%{r:.0f}<extra></extra>"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100], tickvals=[20,40,60,80,100])),
        showlegend=False, margin=dict(l=35,r=35,t=25,b=25), height=420
    )
    return fig


def heatmap_figure(events):
    fig, ax = plt.subplots(figsize=(10.5,6.8))
    ax.set_xlim(0,105); ax.set_ylim(0,68); ax.set_aspect("equal"); ax.axis("off")
    ax.plot([0,105,105,0,0],[0,0,68,68,0], linewidth=1.5)
    ax.plot([52.5,52.5],[0,68], linewidth=1.1)
    ax.add_patch(plt.Circle((52.5,34),9.15,fill=False,linewidth=1.1))
    ax.plot([0,16.5,16.5,0],[13.84,13.84,54.16,54.16],linewidth=1.1)
    ax.plot([105,88.5,88.5,105],[13.84,13.84,54.16,54.16],linewidth=1.1)
    ax.plot([0,5.5,5.5,0],[24.84,24.84,43.16,43.16],linewidth=1.0)
    ax.plot([105,99.5,99.5,105],[24.84,24.84,43.16,43.16],linewidth=1.0)
    if events is not None and len(events) >= 5 and {"x","y"}.issubset(events.columns):
        x = pd.to_numeric(events["x"], errors="coerce").dropna().to_numpy()
        y = pd.to_numeric(events["y"], errors="coerce").dropna().to_numpy()
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]
        if n and np.nanmax(x) <= 100.5 and np.nanmax(y) <= 100.5:
            x = x * 1.05
            y = y * 0.68
        heat, _, _ = np.histogram2d(x, y, bins=(30,20), range=[[0,105],[0,68]])
        ax.imshow(heat.T, extent=[0,105,0,68], origin="lower", interpolation="gaussian", alpha=.72, aspect="auto")
    return fig
