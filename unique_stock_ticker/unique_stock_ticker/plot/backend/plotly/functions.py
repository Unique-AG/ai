import datetime

import plotly.graph_objects as go
from numerize.numerize import numerize
from plotly.subplots import make_subplots


def _get_figure_title(
    company_name: str,
    ticker: str,
    market_name: str,
    currency: str,
    last_price: float,
    net_change: float,
    relative_change: float,
) -> str:
    sign_change = "+" if net_change > 0 else "-"
    title = f"{company_name} ({ticker}: {market_name})"
    title += f"<br><b>{numerize(last_price)} {currency}</b></br>"
    title += f"{sign_change}{numerize(abs(net_change))} {currency} ({sign_change}{numerize(abs(relative_change))}%)"
    return title


def _get_metrics_html(metrics: dict[str, float], num_cols: int) -> str:
    metrics_html = ""
    metrics_str = {k: numerize(v) for k, v in metrics.items()}
    max_len = max(len(f"{k}: {v}") for k, v in metrics_str.items())
    items = list(metrics_str.items())

    for i in range(0, len(items), num_cols):
        row_items = items[i : i + num_cols]
        row = "\t".join(
            [f"<b>{k}</b>: {v}".ljust(max_len + 7) for k, v in row_items]
        )  # +7 for the html tags
        metrics_html += row + "<br>"

    return metrics_html


def plot_stock_price_history_plotly(
    session_dates: list[datetime.datetime | datetime.date],
    price_history: list[float],
    company_name: str,
    ticker: str,
    market_name: str,
    currency: str,
    metrics: dict[str, float] | None = None,
    metrics_num_cols: int = 3,
    num_xticks: int = 10,
    template: str = "plotly_white",
) -> go.Figure:
    if len(price_history) != len(session_dates):
        raise ValueError(
            "price_history and session_dates must be of the same length"
        )

    has_metrics = metrics is not None and len(metrics) > 0

    fig = make_subplots(
        rows=2 if has_metrics else 1,
        cols=1,
        vertical_spacing=0.2,
        specs=[
            [{"type": "scatter"}],
            [{"type": "scatter"}] if has_metrics else None,
        ],
    )

    # Prepare x-axis values and tickvals/ticktext
    x_ticks_interval = len(session_dates) // (num_xticks)
    extracted_session_dates_for_ticks = session_dates[::x_ticks_interval]
    x_axis_tickvals = [
        d.strftime("%b %d %H:%M") for d in extracted_session_dates_for_ticks
    ]
    x_axis_ticktexts = [
        d.strftime("%b %d") for d in extracted_session_dates_for_ticks
    ]
    x_axis_values = [d.strftime("%b %d %H:%M") for d in session_dates]

    net_change = price_history[-1] - price_history[0]
    relative_change = 100 * net_change / price_history[0]
    line_color = "green" if relative_change > 0 else "red"

    fig.add_trace(
        go.Scatter(
            x=x_axis_values,
            y=price_history,
            mode="lines",
            line=dict(color=line_color),
        ),
        row=1,
        col=1,
    )

    x_axis_title = "Date"
    y_axis_title = f"Price ({currency})"
    title = _get_figure_title(
        company_name,
        ticker,
        market_name,
        currency,
        price_history[-1],
        net_change,
        relative_change,
    )

    fig.update_layout(
        title=dict(
            automargin=True,
            text=title,
            yref="container",
            y=0.85,
            font=dict(size=20),
        ),
        xaxis_title=x_axis_title,
        yaxis_title=y_axis_title,
        template=template,
        xaxis=dict(
            showgrid=False,
            type="category",
            tickvals=x_axis_tickvals,
            ticktext=x_axis_ticktexts,
        ),
        yaxis=dict(showgrid=True, zeroline=False),
        margin=dict(l=40, r=40),
        font=dict(family="Courier New", size=12),
    )

    if has_metrics:
        fig.update_xaxes(visible=False, row=2, col=1)
        fig.update_yaxes(visible=False, row=2, col=1)

        metrics_html = _get_metrics_html(metrics, metrics_num_cols)  # type: ignore
        fig.add_annotation(
            dict(
                font=dict(size=15),
                showarrow=False,
                text=metrics_html,
                xanchor="center",
                yanchor="top",
            ),
            row=2,
            col=1,
        )

    return fig
