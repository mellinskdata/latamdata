
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt

def radar_chart(player_row, radar_metrics):
    labels = list(radar_metrics.keys())
    values = [float(player_row[f"pct_{m}"]) for m in radar_metrics.values()]
    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=labels_closed,
        fill="toself",
        name=player_row["player"],
        hovertemplate="%{theta}: %{r:.0f}º percentil<extra></extra>"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,100], tickvals=[20,40,60,80,100])),
        showlegend=False,
        margin=dict(l=40,r=40,t=40,b=40),
        height=430
    )
    return fig

def heatmap_figure(events):
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    ax.set_xlim(0,105)
    ax.set_ylim(0,68)
    ax.set_aspect("equal")
    ax.axis("off")

    # Pitch
    ax.plot([0,105,105,0,0], [0,0,68,68,0], linewidth=1.6)
    ax.plot([52.5,52.5], [0,68], linewidth=1.2)
    center = plt.Circle((52.5,34), 9.15, fill=False, linewidth=1.2)
    ax.add_patch(center)
    ax.plot(52.5,34,"o",markersize=3)

    # Penalty areas
    ax.plot([0,16.5,16.5,0], [13.84,13.84,54.16,54.16], linewidth=1.2)
    ax.plot([105,88.5,88.5,105], [13.84,13.84,54.16,54.16], linewidth=1.2)
    ax.plot([0,5.5,5.5,0], [24.84,24.84,43.16,43.16], linewidth=1.2)
    ax.plot([105,99.5,99.5,105], [24.84,24.84,43.16,43.16], linewidth=1.2)

    if len(events) >= 5:
        x = events["x"].to_numpy()
        y = events["y"].to_numpy()
        heat, xedges, yedges = np.histogram2d(x, y, bins=(30,20), range=[[0,105],[0,68]])
        ax.imshow(
            heat.T,
            extent=[0,105,0,68],
            origin="lower",
            interpolation="gaussian",
            alpha=0.72,
            aspect="auto"
        )
        ax.scatter(x, y, s=5, alpha=0.08)

    return fig
