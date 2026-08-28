"""HTML validation report renderer."""

from __future__ import annotations

import json
import webbrowser
from html import escape
from pathlib import Path
from typing import Mapping

import numpy as np

from algosystem.shared.errors import ValidationError


class HtmlReportRenderer:
    """ReportRenderer implementation that writes a self-contained HTML file."""

    def render(
        self,
        results: object,
        output_path: Path,
        *,
        pbo_results: object | None = None,
        wf_results: object | None = None,
        ac_diagnostic: object | None = None,
        robustness: Mapping[str, object] | None = None,
        title: str = "Overfitting Detection Report",
        open_browser: bool = False,
    ) -> Path:
        """Render the report and return the written path."""
        return generate_overfit_dashboard(
            results,
            pbo_results=pbo_results,
            wf_results=wf_results,
            ac_diagnostic=ac_diagnostic,
            robustness=robustness,
            output_path=output_path,
            open_browser=open_browser,
            title=title,
        )


def generate_overfit_dashboard(
    results,
    pbo_results=None,
    wf_results=None,
    ac_diagnostic=None,
    robustness: Mapping[str, object] | None = None,
    output_path: str | Path | None = None,
    open_browser: bool = False,
    title: str = "Overfitting Detection Report",
) -> Path:
    """
    Generate a self-contained HTML overfitting detection dashboard.

    The generated HTML references Plotly through a CDN script tag, so opening
    the report with charts requires network access.
    """
    if output_path is None:
        raise ValidationError("output_path is required for validation reports")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = _build_data(results, pbo_results, wf_results, ac_diagnostic, robustness)
    output.write_text(_build_html(data, title), encoding="utf-8")

    if open_browser:
        webbrowser.open(output.resolve().as_uri())
    return output


def _safe_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    numeric = float(value)
    if not np.isfinite(numeric):
        return default
    return round(numeric, 6)


def _build_data(results, pbo_results, wf_results, ac_diagnostic, robustness):
    data: dict[str, object] = {
        "best_sharpe": _safe_float(results.best_sharpe),
        "unbiased_pvalue": _safe_float(results.unbiased_pvalue),
        "prob_overfit": _safe_float(results.prob_overfit),
        "deflated_sharpe": _safe_float(results.deflated_sharpe),
        "n_params": int(results.n_params),
        "n_reps": int(results.n_reps),
        "shuffle_method": str(results.shuffle_method),
        "best_params": str(results.param_list[results.best_param_index]),
        "null_sharpes": [_safe_float(value) for value in results.null_best_sharpes],
    }

    n_show = min(results.n_params, 30)
    data["pvalue_ranks"] = list(range(1, n_show + 1))
    data["solo_pvals"] = [
        _safe_float(results.solo_pvalues[results.sort_indices[index]]) for index in range(n_show)
    ]
    data["unbiased_pvals"] = [
        _safe_float(results.unbiased_pvalues[index]) for index in range(n_show)
    ]

    surface = results.surface_analysis()
    data["plateau_score"] = _safe_float(surface["plateau_score"])
    data["robustness_ratio"] = _safe_float(surface["robustness_ratio"])
    data["frac_positive"] = _safe_float(surface["frac_positive"])

    param_keys = sorted({key for params in results.param_list for key in params})
    if len(param_keys) >= 2:
        param_x, param_y = param_keys[0], param_keys[1]
        data["heatmap"] = _heatmap_payload(results, param_x, param_y)

    if pbo_results is not None:
        data["pbo"] = _safe_float(pbo_results.pbo)
        finite_logits = pbo_results.logits[np.isfinite(pbo_results.logits)]
        data["pbo_logits"] = [_safe_float(value) for value in finite_logits]

    if wf_results is not None:
        data["wfe"] = _safe_float(wf_results.wfe)
        data["wf_is"] = [_safe_float(value) for value in wf_results.is_sharpes]
        data["wf_oos"] = [_safe_float(value) for value in wf_results.oos_sharpes]
        data["wf_vetoed"] = bool(wf_results.vetoed)

    if ac_diagnostic is not None:
        data["acf_values"] = [_safe_float(value) for value in ac_diagnostic.acf_values]
        data["acf_has_ac"] = bool(ac_diagnostic.has_autocorrelation)
        data["acf_recommended"] = ac_diagnostic.recommended_shuffle
        data["acf_lb_pvalue"] = _safe_float(ac_diagnostic.ljung_box_pvalue)

    if robustness:
        _add_robustness(data, robustness)

    if results.returns is not None:
        try:
            analytical = results.analytical_deflated_sharpe()
        except ValidationError:
            analytical = None
        if analytical:
            data["adsr"] = _safe_float(analytical["dsr"])
            data["sr0"] = _safe_float(analytical["sr0"])
            data["min_trl"] = _safe_float(analytical["min_trl"])

    return data


def _heatmap_payload(results, param_x: str, param_y: str) -> dict[str, object]:
    xvalues = sorted({params[param_x] for params in results.param_list})
    yvalues = sorted({params[param_y] for params in results.param_list})
    grid: list[list[float | None]] = [[None] * len(xvalues) for _ in yvalues]
    counts = [[0] * len(xvalues) for _ in yvalues]
    for index, params in enumerate(results.param_list):
        x_index = xvalues.index(params[param_x])
        y_index = yvalues.index(params[param_y])
        if grid[y_index][x_index] is None:
            grid[y_index][x_index] = 0.0
        grid[y_index][x_index] += float(results.original_sharpes[index])
        counts[y_index][x_index] += 1
    for y_index in range(len(yvalues)):
        for x_index in range(len(xvalues)):
            if counts[y_index][x_index] > 0 and grid[y_index][x_index] is not None:
                grid[y_index][x_index] = round(
                    grid[y_index][x_index] / counts[y_index][x_index],
                    4,
                )
    return {
        "z": grid,
        "x": [str(value) for value in xvalues],
        "y": [str(value) for value in yvalues],
        "xlabel": param_x,
        "ylabel": param_y,
    }


def _add_robustness(data: dict[str, object], robustness: Mapping[str, object]) -> None:
    if "sharpe_ci" in robustness:
        ci = robustness["sharpe_ci"]
        data["ci_lower"] = _safe_float(ci.ci_lower)
        data["ci_upper"] = _safe_float(ci.ci_upper)
        data["ci_includes_zero"] = bool(ci.ci_includes_zero)
    if "kelly" in robustness:
        kelly = robustness["kelly"]
        data["kelly_fraction"] = _safe_float(kelly.kelly_fraction)
        data["kelly_edge"] = _safe_float(kelly.edge)
        data["kelly_has_edge"] = bool(kelly.has_edge)
        data["kelly_win_rate"] = _safe_float(kelly.win_rate)


def _build_html(data: dict[str, object], title: str) -> str:
    data_json = json.dumps(data, default=str)
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root {{
  color-scheme: dark;
  --bg: #10131a;
  --panel: #181d27;
  --panel-2: #202735;
  --line: #30394b;
  --text: #edf2f7;
  --muted: #96a0b3;
  --green: #34d399;
  --red: #f87171;
  --amber: #fbbf24;
  --blue: #7aa2ff;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.45;
}}
header {{
  padding: 28px 36px 18px;
  border-bottom: 1px solid var(--line);
  background: #151a24;
}}
h1 {{ font-size: 22px; margin: 0 0 8px; font-weight: 650; }}
.subtitle {{ color: var(--muted); font-size: 13px; }}
main {{ padding: 26px 36px 42px; max-width: 1460px; margin: 0 auto; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 18px 0 24px; }}
.metric {{ border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 14px 16px; }}
.metric .label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
.metric .value {{ font-size: 20px; font-weight: 700; margin-top: 4px; }}
.grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
.card {{ border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 18px; }}
.card h2 {{ font-size: 13px; color: var(--muted); margin: 0 0 12px; text-transform: uppercase; letter-spacing: .06em; }}
.chart {{ width: 100%; height: 390px; }}
.wide {{ grid-column: 1 / -1; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
td {{ padding: 8px 0; border-bottom: 1px solid var(--line); }}
td:last-child {{ text-align: right; color: var(--text); font-weight: 600; }}
.green {{ color: var(--green); }}
.red {{ color: var(--red); }}
.amber {{ color: var(--amber); }}
.blue {{ color: var(--blue); }}
footer {{ color: var(--muted); font-size: 11px; padding: 22px 36px; border-top: 1px solid var(--line); }}
@media (max-width: 900px) {{
  header, main, footer {{ padding-left: 18px; padding-right: 18px; }}
  .grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<header>
  <h1>{safe_title}</h1>
  <div class="subtitle" id="subtitle"></div>
</header>
<main>
  <section class="metrics" id="metrics"></section>
  <section class="grid">
    <div class="card"><h2>Null Distribution</h2><div id="null-dist" class="chart"></div></div>
    <div class="card"><h2>Parameter Surface</h2><div id="heatmap" class="chart"></div></div>
    <div class="card"><h2>P-Value Comparison</h2><div id="pvalues" class="chart"></div></div>
    <div class="card" id="pbo-card" style="display:none"><h2>PBO Distribution</h2><div id="pbo-dist" class="chart"></div></div>
    <div class="card wide" id="wf-card" style="display:none"><h2>Walk-Forward IS vs OOS</h2><div id="wf-scatter" class="chart"></div></div>
    <div class="card wide"><h2>Core Statistics</h2><table id="stats"></table></div>
  </section>
</main>
<footer>Generated by AlgoSystem validation. Charts load Plotly from a CDN and require network access.</footer>
<script>
const D = {data_json};
const layout = {{
  paper_bgcolor: "#181d27",
  plot_bgcolor: "#181d27",
  font: {{ color: "#96a0b3", size: 11 }},
  margin: {{ t: 24, r: 18, b: 54, l: 58 }},
  xaxis: {{ gridcolor: "#30394b", zerolinecolor: "#30394b" }},
  yaxis: {{ gridcolor: "#30394b", zerolinecolor: "#30394b" }}
}};
const config = {{ responsive: true, displayModeBar: false }};

document.getElementById("subtitle").textContent =
  `${{D.n_params}} parameter combinations · ${{D.n_reps}} permutations · shuffle = ${{D.shuffle_method}} · best params = ${{D.best_params}}`;

function colorForP(value) {{
  if (value < 0.05) return "green";
  if (value < 0.10) return "amber";
  return "red";
}}
function metric(label, value, cls) {{
  document.getElementById("metrics").insertAdjacentHTML("beforeend",
    `<div class="metric"><div class="label">${{label}}</div><div class="value ${{cls || ""}}">${{value}}</div></div>`);
}}
metric("Unbiased p-value", D.unbiased_pvalue.toFixed(4), colorForP(D.unbiased_pvalue));
metric("Best Sharpe", D.best_sharpe.toFixed(3), "blue");
metric("Deflated Sharpe", D.deflated_sharpe.toFixed(3), D.deflated_sharpe > 0 ? "green" : "red");
metric("Probability Overfit", (D.prob_overfit * 100).toFixed(1) + "%", D.prob_overfit < 0.3 ? "green" : "red");
metric("Plateau Score", D.plateau_score.toFixed(3), D.plateau_score > 0.2 ? "green" : D.plateau_score > 0.05 ? "amber" : "red");
if (D.pbo !== undefined) metric("PBO", D.pbo.toFixed(4), D.pbo < 0.3 ? "green" : "red");

Plotly.newPlot("null-dist", [{{
  x: D.null_sharpes,
  type: "histogram",
  nbinsx: 50,
  marker: {{ color: "rgba(122,162,255,.65)", line: {{ color: "#7aa2ff", width: .5 }} }},
  hovertemplate: "Sharpe: %{{x:.3f}}<br>Count: %{{y}}<extra></extra>"
}}], {{
  ...layout,
  shapes: [{{ type: "line", x0: D.best_sharpe, x1: D.best_sharpe, y0: 0, y1: 1, yref: "paper", line: {{ color: "#f87171", width: 2, dash: "dash" }} }}],
  xaxis: {{ ...layout.xaxis, title: "Best Sharpe under permutation" }},
  yaxis: {{ ...layout.yaxis, title: "Frequency" }}
}}, config);

if (D.heatmap) {{
  Plotly.newPlot("heatmap", [{{
    z: D.heatmap.z,
    x: D.heatmap.x,
    y: D.heatmap.y,
    type: "heatmap",
    zmid: 0,
    colorscale: [[0, "#991b1b"], [.4, "#f59e0b"], [.5, "#202735"], [.75, "#10b981"], [1, "#065f46"]],
    colorbar: {{ title: "Sharpe" }},
    hovertemplate: `${{D.heatmap.xlabel}}: %{{x}}<br>${{D.heatmap.ylabel}}: %{{y}}<br>Sharpe: %{{z:.4f}}<extra></extra>`
  }}], {{
    ...layout,
    xaxis: {{ ...layout.xaxis, title: D.heatmap.xlabel }},
    yaxis: {{ ...layout.yaxis, title: D.heatmap.ylabel }}
  }}, config);
}}

Plotly.newPlot("pvalues", [
  {{ x: D.pvalue_ranks, y: D.solo_pvals, mode: "markers", marker: {{ color: "#7aa2ff", size: 8 }}, name: "Solo" }},
  {{ x: D.pvalue_ranks, y: D.unbiased_pvals, mode: "markers", marker: {{ color: "#f87171", size: 8, symbol: "diamond" }}, name: "Unbiased" }}
], {{
  ...layout,
  xaxis: {{ ...layout.xaxis, title: "Parameter rank" }},
  yaxis: {{ ...layout.yaxis, title: "P-value", range: [-.03, 1.06] }},
  shapes: [{{ type: "line", x0: 0, x1: D.pvalue_ranks.length + 1, y0: .05, y1: .05, line: {{ color: "#34d399", width: 1, dash: "dash" }} }}]
}}, config);

if (D.pbo_logits) {{
  document.getElementById("pbo-card").style.display = "";
  Plotly.newPlot("pbo-dist", [
    {{ x: D.pbo_logits.filter(v => v < 0), type: "histogram", marker: {{ color: "rgba(248,113,113,.7)" }}, name: "Overfit" }},
    {{ x: D.pbo_logits.filter(v => v >= 0), type: "histogram", marker: {{ color: "rgba(52,211,153,.7)" }}, name: "Genuine" }}
  ], {{ ...layout, barmode: "stack", xaxis: {{ ...layout.xaxis, title: "Logit(OOS rank)" }} }}, config);
}}

if (D.wf_is) {{
  document.getElementById("wf-card").style.display = "";
  const values = D.wf_is.concat(D.wf_oos);
  const lo = Math.min(...values) - .5;
  const hi = Math.max(...values) + .5;
  Plotly.newPlot("wf-scatter", [
    {{ x: D.wf_is, y: D.wf_oos, mode: "markers+text", text: D.wf_is.map((_, i) => "F" + (i + 1)), textposition: "top right", marker: {{ color: "#7aa2ff", size: 12, line: {{ color: "#edf2f7", width: 1 }} }}, name: "Folds" }},
    {{ x: [lo, hi], y: [lo, hi], mode: "lines", line: {{ color: "#96a0b3", dash: "dash" }}, name: "IS = OOS" }}
  ], {{
    ...layout,
    xaxis: {{ ...layout.xaxis, title: "In-sample Sharpe", range: [lo, hi] }},
    yaxis: {{ ...layout.yaxis, title: "Out-of-sample Sharpe", range: [lo, hi] }}
  }}, config);
}}

function row(label, value, cls) {{
  document.getElementById("stats").insertAdjacentHTML("beforeend",
    `<tr><td>${{label}}</td><td class="${{cls || ""}}">${{value}}</td></tr>`);
}}
row("Best Sharpe", D.best_sharpe.toFixed(4), "blue");
row("Unbiased p-value", D.unbiased_pvalue.toFixed(6), colorForP(D.unbiased_pvalue));
row("Probability overfit", (D.prob_overfit * 100).toFixed(2) + "%", D.prob_overfit < .3 ? "green" : "red");
row("Deflated Sharpe", D.deflated_sharpe.toFixed(4), D.deflated_sharpe > 0 ? "green" : "red");
row("Robustness ratio", D.robustness_ratio.toFixed(4));
row("Fraction positive", (D.frac_positive * 100).toFixed(1) + "%");
if (D.adsr !== undefined) row("Analytical DSR", D.adsr.toFixed(6), D.adsr > .95 ? "green" : "amber");
if (D.min_trl !== undefined) row("Minimum track record", Math.round(D.min_trl) + " observations");
</script>
</body>
</html>
"""


__all__ = ["HtmlReportRenderer", "generate_overfit_dashboard"]
