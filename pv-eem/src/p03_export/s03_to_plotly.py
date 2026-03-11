import plotly.graph_objects as go


def plot(results):
    """Run plot."""
    df = results.pivot(index=["time"], columns="combiner_device_id", values="p_mp")
    df = df.reset_index()

    # Create the plot
    fig = go.Figure()
    for column in df.columns[1::100]:
        fig.add_trace(
            go.Scatter(
                x=df["time"], y=df[column], mode="markers", name=column, opacity=0.5
            )
        )

    # Customize the plot
    fig.update_layout(
        title="Time Series Data",
        xaxis_title="Time",
        yaxis_title="p_mp",
        showlegend=True,
        xaxis=dict(
            tickangle=45,
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(128,128,128,0.2)",
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(128,128,128,0.2)",
        ),
    )

    fig.show()
