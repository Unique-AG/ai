import json
import re
from typing import Literal

from typing_extensions import override
from unique_toolkit.content.functions import upload_content_from_bytes

from unique_stock_ticker.plot.backend.base import (
    PlottingBackend,
    PlottingBackendConfig,
    PlottingBackendName,
    StockHistoryPlotPayload,
)

_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Interactive Stock Dashboard</title>
  <link rel="preconnect" href="https://cdn.plot.ly" />
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <style>
    :root{
      --bg:#ffffff;
      --text:#1f2a37;
      --muted:#6b7280;
      --accent:#2dd4bf;
      --accent-200:#b6f3ea;
      --grid:#e5e7eb;
      --positive:#2e7d32;
      --negative:#b91c1c;
      --chip:#f3f4f6;
      --shadow:0 6px 24px rgba(31,41,55,0.08);
      --radius:14px;
    }
    html,body{height:100%}
    body{
      margin:0;
      font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,"Apple Color Emoji","Segoe UI Emoji";
      color:var(--text);
      background:var(--bg);
    }
    .wrap{
      max-width:1100px;
      margin:24px auto;
      padding:0 16px 24px;
    }
    header{
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:16px;
      margin-bottom:8px;
    }
    .ticker{
      display:flex;
      flex-direction:column;
      gap:2px;
    }
    .ticker small{color:var(--muted); letter-spacing:.02em}
    .company-name{
      font-size:18px;
      font-weight:600;
    }
    .price-row{
      display:flex;
      align-items:baseline;
      gap:16px;
    }
    .price{
      font-size:48px;
      font-weight:700;
      line-height:1;
    }
    .delta{
      color:var(--positive);
      font-weight:600;
    }
    .controls{
      display:flex;
      gap:8px;
      align-items:center;
      flex-wrap:wrap;
    }
    .chip{
      border:1px solid var(--grid);
      background:var(--chip);
      padding:6px 10px;
      border-radius:999px;
      color:#111827;
      font-weight:600;
      font-size:13px;
      cursor:pointer;
      user-select:none;
    }
    .chip[aria-pressed="true"]{
      background:#111827;
      color:white;
      border-color:#111827;
    }
    .card{
      background:#fff;
      border:1px solid var(--grid);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      overflow:hidden;
    }
    #chart{
      height:420px;
    }
    .metrics{
      padding:16px 20px 8px;
      border-top:1px solid var(--grid);
    }
    details summary{
      list-style:none;
      cursor:pointer;
      display:inline-flex;
      align-items:center;
      gap:8px;
      background:var(--chip);
      border:1px solid var(--grid);
      border-radius:10px;
      padding:8px 12px;
      font-weight:700;
    }
    .grid{
      display:grid;
      grid-template-columns:repeat(3, minmax(0,1fr));
      gap:14px 28px;
      margin-top:14px;
    }
    .kv{
      display:flex;
      justify-content:space-between;
      gap:8px;
      border-bottom:1px dashed #eaecef;
      padding:8px 0;
    }
    .k{color:var(--muted)}
    .v{font-weight:600}
    footer{
      display:flex;
      justify-content:space-between;
      align-items:center;
      color:var(--muted);
      font-size:13px;
      padding:10px 4px 0;
    }
    .logo{display:flex; align-items:center; gap:8px}
    .sr-only{
      position:absolute;
      width:1px;
      height:1px;
      padding:0;
      margin:-1px;
      overflow:hidden;
      clip:rect(0,0,0,0);
      white-space:nowrap;
      border:0;
    }
    @media (max-width: 760px){
      .grid{grid-template-columns:repeat(2, minmax(0,1fr));}
      .price{font-size:36px;}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="ticker">
        <small id="ticker-label"></small>
        <div class="company-name" id="company-name"></div>
        <div class="price-row">
          <div class="price" id="price"></div>
          <div class="delta" id="delta"></div>
        </div>
      </div>
      <div class="controls" aria-label="Time ranges">
        <button class="chip" data-range="1M">1M</button>
        <button class="chip" data-range="3M">3M</button>
        <button class="chip" data-range="6M">6M</button>
        <button class="chip" data-range="1Y" aria-pressed="true">1Y</button>
        <button class="chip" data-range="YTD">YTD</button>
        <button class="chip" data-range="MAX">MAX</button>
        <button class="chip" id="toggle-ma" aria-pressed="false">MA</button>
      </div>
    </header>

    <div class="card">
      <div id="chart"></div>
      <div class="metrics">
        <details open>
          <summary>
            <span>Metrics</span>
            <span class="sr-only">Toggle metrics details</span>
          </summary>
          <div class="grid">
            <div class="kv"><span class="k">Open</span><span class="v" id="m-open">N/A</span></div>
            <div class="kv"><span class="k">Price Earnings Ratio</span><span class="v" id="m-per">N/A</span></div>
            <div class="kv"><span class="k">Dividend Yield</span><span class="v" id="m-div">N/A</span></div>

            <div class="kv"><span class="k">High</span><span class="v" id="m-high">N/A</span></div>
            <div class="kv"><span class="k">Volume</span><span class="v" id="m-vol">N/A</span></div>
            <div class="kv"><span class="k">Volatility 30D</span><span class="v" id="m-vola">N/A</span></div>

            <div class="kv"><span class="k">Close</span><span class="v" id="m-close">N/A</span></div>
            <div class="kv"><span class="k">Year High</span><span class="v" id="m-yh">N/A</span></div>
            <div class="kv"><span class="k">Year Low</span><span class="v" id="m-yl">N/A</span></div>

            <div class="kv"><span class="k">Market Cap</span><span class="v" id="m-mc">N/A</span></div>
          </div>
        </details>
      </div>
    </div>

    <footer>
      <div>Last updated: <span id="last-updated"></span></div>
      <div class="logo">DATA POWERED BY <strong id="data-source"></strong></div>
    </footer>
  </div>

  <script>
    const dashboardData = __DASHBOARD_DATA__;
    const metricMap = new Map(
      dashboardData.metrics.map((metric) => [metric.name, metric.value]),
    );
    const series = {
      x: dashboardData.priceHistory.map((item) => new Date(item.date)),
      y: dashboardData.priceHistory.map((item) => item.value),
    };

    function getCurrencyPrefix(currency) {
      const mapping = {
        USD: "US$ ",
        EUR: "EUR ",
        CHF: "CHF ",
        GBP: "GBP ",
      };
      return mapping[currency] || `${currency} `;
    }

    function formatCompact(value) {
      if (value === null || value === undefined) {
        return "N/A";
      }
      const absValue = Math.abs(value);
      const units = [
        { limit: 1_000_000_000_000, suffix: "T" },
        { limit: 1_000_000_000, suffix: "B" },
        { limit: 1_000_000, suffix: "M" },
        { limit: 1_000, suffix: "K" },
      ];

      for (const unit of units) {
        if (absValue >= unit.limit) {
          const scaled = value / unit.limit;
          const digits = Math.abs(scaled) >= 100 ? 0 : Math.abs(scaled) >= 10 ? 1 : 2;
          return `${scaled.toFixed(digits)}${unit.suffix}`;
        }
      }

      return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    function formatMoney(value, fractionDigits = 2) {
      if (value === null || value === undefined) {
        return "N/A";
      }
      return `${getCurrencyPrefix(dashboardData.info.currency)}${value.toLocaleString(undefined, {
        minimumFractionDigits: fractionDigits,
        maximumFractionDigits: fractionDigits,
      })}`;
    }

    function formatPercent(value, fractionDigits = 2) {
      if (value === null || value === undefined) {
        return "N/A";
      }
      return `${value.toFixed(fractionDigits)}%`;
    }

    function formatDecimal(value, fractionDigits = 3) {
      if (value === null || value === undefined) {
        return "N/A";
      }
      return value.toFixed(fractionDigits);
    }

    function setMetric(id, formatter, metricName) {
      document.getElementById(id).textContent = formatter(metricMap.get(metricName));
    }

    function movingAverage(values, windowSize = 12) {
      const output = new Array(values.length).fill(null);
      let sum = 0;

      for (let index = 0; index < values.length; index += 1) {
        sum += values[index];
        if (index >= windowSize) {
          sum -= values[index - windowSize];
        }
        if (index >= windowSize - 1) {
          output[index] = sum / windowSize;
        }
      }

      return output;
    }

    function setPressed(button) {
      document
        .querySelectorAll(".controls .chip[data-range]")
        .forEach((item) => item.removeAttribute("aria-pressed"));
      button.setAttribute("aria-pressed", "true");
    }

    function updateHeader() {
      const lastIndex = series.y.length - 1;
      const last = series.y[lastIndex];
      const previous = lastIndex > 0 ? series.y[lastIndex - 1] : last;
      const delta = last - previous;
      const percentage = previous ? (delta / previous) * 100 : 0;
      const isPositive = delta >= 0;
      const deltaElement = document.getElementById("delta");

      document.getElementById("price").textContent = formatMoney(last, 2);
      deltaElement.textContent = `${isPositive ? "+" : "-"}${Math.abs(percentage).toFixed(2)}%, ${Math.abs(delta).toFixed(2)}`;
      deltaElement.style.color = isPositive ? "var(--positive)" : "var(--negative)";
    }

    function getInitialRange() {
      const end = series.x[series.x.length - 1];
      const start = new Date(end);
      start.setMonth(end.getMonth() - 12);
      return [start, end];
    }

    document.getElementById("ticker-label").textContent =
      `${dashboardData.info.ticker}: ${dashboardData.info.exchange}`;
    document.getElementById("company-name").textContent =
      dashboardData.info.companyName || dashboardData.info.instrumentName;
    document.getElementById("last-updated").textContent = new Date(
      dashboardData.lastUpdated,
    ).toLocaleString();
    document.getElementById("data-source").textContent =
      String(dashboardData.dataSource || "Six").toUpperCase();
    document.title = `${dashboardData.info.ticker} Stock Dashboard`;

    setMetric("m-open", formatMoney, "Open");
    setMetric("m-per", formatDecimal, "Price Earnings Ratio");
    setMetric("m-div", (value) => formatPercent(value, 3), "Dividend Yield");
    setMetric("m-high", formatMoney, "High");
    setMetric(
      "m-vol",
      (value) => {
        if (value === null || value === undefined) {
          return "N/A";
        }
        return `${getCurrencyPrefix(dashboardData.info.currency)}${formatCompact(value)}`;
      },
      "Volume",
    );
    setMetric("m-vola", (value) => formatPercent(value, 0), "Volatility 30 Days");
    setMetric("m-close", formatMoney, "Close");
    setMetric("m-yh", formatMoney, "Year High");
    setMetric("m-yl", formatMoney, "Year Low");
    setMetric(
      "m-mc",
      (value) => {
        if (value === null || value === undefined) {
          return "N/A";
        }
        return `${getCurrencyPrefix(dashboardData.info.currency)}${formatCompact(value)}`;
      },
      "Market Cap",
    );

    updateHeader();

    const chartElement = document.getElementById("chart");
    const ma12 = movingAverage(series.y, 12);
    const priceTrace = {
      x: series.x,
      y: series.y,
      type: "scatter",
      mode: "lines",
      line: { color: "#7bd5ce", width: 3 },
      hovertemplate: "%{x|%b %d, %Y}<br><b>%{y:.2f}</b><extra></extra>",
      name: "Price",
    };
    const movingAverageTrace = {
      x: series.x,
      y: ma12,
      type: "scatter",
      mode: "lines",
      line: { color: "#0ea5a3", width: 2, dash: "dot" },
      hovertemplate: "MA %{x|%b %d, %Y}<br><b>%{y:.2f}</b><extra></extra>",
      name: "MA 12",
      visible: false,
    };
    const [initialStart, initialEnd] = getInitialRange();
    const lastValue = series.y[series.y.length - 1];

    const layout = {
      margin: { l: 56, r: 32, t: 10, b: 56 },
      showlegend: false,
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      xaxis: {
        gridcolor: "#eef2f7",
        zeroline: false,
        range: [initialStart, initialEnd],
        rangeselector: {
          buttons: [
            { count: 1, label: "1M", step: "month", stepmode: "backward" },
            { count: 3, label: "3M", step: "month", stepmode: "backward" },
            { count: 6, label: "6M", step: "month", stepmode: "backward" },
            { count: 12, label: "1Y", step: "month", stepmode: "backward" },
            { step: "all", label: "MAX" },
          ],
        },
        rangeslider: { visible: true, thickness: 0.1 },
      },
      yaxis: {
        gridcolor: "#eef2f7",
        zeroline: false,
        tickprefix: getCurrencyPrefix(dashboardData.info.currency),
      },
      shapes: [
        {
          type: "line",
          xref: "paper",
          x0: 0,
          x1: 1,
          y0: lastValue,
          y1: lastValue,
          line: { color: "#cfe9e6", width: 2, dash: "dash" },
        },
      ],
    };
    const config = {
      responsive: true,
      displaylogo: true,
      displayModeBar: true,
      modeBarButtonsToRemove: [
        "zoom3d",
        "pan3d",
        "orbitRotation",
        "table",
        "lasso2d",
        "select2d",
        "toggleSpikelines",
        "hoverCompareCartesian",
        "hoverClosestCartesian",
      ],
      modeBarButtonsToAdd: [
        "toImage",
        "zoom2d",
        "pan2d",
        "zoomIn2d",
        "zoomOut2d",
        "autoScale2d",
        "resetScale2d",
      ],
    };

    Plotly.newPlot(chartElement, [priceTrace, movingAverageTrace], layout, config);

    document.querySelectorAll(".controls .chip[data-range]").forEach((button) => {
      button.addEventListener("click", () => {
        const selectedRange = button.getAttribute("data-range");
        const now = new Date(series.x[series.x.length - 1]);
        let start = null;

        if (selectedRange === "MAX") {
          Plotly.relayout(chartElement, { "xaxis.autorange": true });
          setPressed(button);
          return;
        }

        if (selectedRange === "YTD") {
          start = new Date(now.getFullYear(), 0, 1);
        } else {
          const monthMapping = { "1M": 1, "3M": 3, "6M": 6, "1Y": 12 };
          start = new Date(now);
          start.setMonth(now.getMonth() - (monthMapping[selectedRange] || 12));
        }

        Plotly.relayout(chartElement, { "xaxis.range": [start, now] });
        setPressed(button);
      });
    });

    document.getElementById("toggle-ma").addEventListener("click", (event) => {
      const nextVisible = movingAverageTrace.visible === false;
      Plotly.restyle(chartElement, { visible: nextVisible }, [1]);
      event.currentTarget.setAttribute("aria-pressed", String(nextVisible));
      movingAverageTrace.visible = nextVisible;
    });

    window.addEventListener("resize", () => Plotly.Plots.resize(chartElement));
  </script>
</body>
</html>
""".strip()


class HtmlTickerPlotConfig(PlottingBackendConfig):
    name: Literal[PlottingBackendName.HTML] = PlottingBackendName.HTML
    filename_prefix: str = "stock_dashboard"
    render_width: int = 800
    render_height: int = 600


class HtmlPlottingBackend(PlottingBackend[HtmlTickerPlotConfig]):
    def __init__(
        self,
        config: HtmlTickerPlotConfig,
        company_id: str,
        user_id: str,
        chat_id: str,
    ):
        super().__init__(config)
        self._company_id = company_id
        self._user_id = user_id
        self._chat_id = chat_id

    @override
    def plot(
        self,
        ticker_data: list[StockHistoryPlotPayload],
    ) -> str:
        rendering_blocks: list[str] = []

        for payload in ticker_data:
            html_content = render_stock_dashboard_html(payload)
            ticker_slug = _sanitize_filename_fragment(payload.info.ticker.lower())
            filename = f"{self.config.filename_prefix}_{ticker_slug}.html"
            content = upload_content_from_bytes(
                user_id=self._user_id,
                company_id=self._company_id,
                content=html_content.encode("utf-8"),
                content_name=filename,
                mime_type="text/html",
                chat_id=self._chat_id,
                skip_ingestion=True,
                hide_in_chat=True,
            )
            rendering_blocks.append(
                _build_html_rendering_block(
                    content_id=content.id,
                    width=self.config.render_width,
                    height=self.config.render_height,
                )
            )

        return "\n\n".join(rendering_blocks)

    @classmethod
    @override
    def remove_result_from_text(cls, text: str) -> str:
        return re.sub(r"```HtmlRendering[\s\S]*?```", "", text)


def render_stock_dashboard_html(payload: StockHistoryPlotPayload) -> str:
    serialized_payload = payload.model_dump(mode="json", by_alias=True)
    embedded_payload = json.dumps(serialized_payload).replace("</", "<\\/")
    return _HTML_TEMPLATE.replace("__DASHBOARD_DATA__", embedded_payload)


def _build_html_rendering_block(content_id: str, width: int, height: int) -> str:
    return (
        "```HtmlRendering\n"
        f"{width}px\n"
        f"{height}px\n\n"
        f"unique://content/{content_id}\n\n"
        "```"
    )


def _sanitize_filename_fragment(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9]+", "_", value)
    return sanitized.strip("_") or "stock"
