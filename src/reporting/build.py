"""
Build the executive reports: dashboard, summary, tables, CSV exports, top customer reports.
"""

import argparse
import html
import json
import re
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select

from src.analysis.charts import churn_bar, contract_tenure_heatmap
from src.analysis.prep import TENURE_LABELS
from src.analysis.stats import churn_by
from src.campaigns.analysis import analyse
from src.campaigns.report import campaign_overview
from src.config import REPORTS_DIR
from src.db.models import RetentionCampaign
from src.db.session import Base, SessionLocal, engine
from src.ml import segmentation as seg
from src.reporting import charts as ch, metrics as m, narrative as nar
from src.reporting.customer_report import write_customer_reports
from src.reporting.data import load_history, load_model_meta, load_portfolio
from src.reporting.exports import ReportFilter, apply_filters, write_export
from src.reporting.settings import CUSTOMER_DIR, EXEC_DIR, EXPORT_DIR, SEGMENT_DIMENSIONS, SYNTHETIC_PREFIX, TOP_CUSTOMER_REPORTS



CSS = """
:root{--bg:#f5f6f8;--fg:#1c2430;--muted:#5b6675;--card:#fff;--line:#e2e6ec;--accent:#1f5fbf}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.5}
main{max-width:1200px;margin:0 auto;padding:20px 16px 48px}
h1{margin:0 0 4px;font-size:1.6rem} h2{margin:32px 0 6px;font-size:1.2rem;border-bottom:2px solid var(--line);padding-bottom:4px}
.muted{color:var(--muted);font-size:.9rem} code{background:#eef1f5;padding:1px 4px;border-radius:3px}
.notice{background:#fff7e0;border:1px solid #f0d98c;padding:8px 12px;border-radius:6px;font-size:.9rem}
.note{background:#eef4ff;border:1px solid #c6d8f5;padding:6px 12px;border-radius:6px;font-size:.88rem;margin:6px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.card .lbl{font-size:.8rem;color:var(--muted)} .card .val{font-size:1.25rem;font-weight:650;margin-top:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px;margin-top:10px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px;overflow-x:auto}
.panel.wide{grid-column:1/-1;padding:12px}
.summary{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 18px 14px}
.tbl{border-collapse:collapse;font-size:.85rem;width:100%} .tbl th,.tbl td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right}
.tbl th:first-child,.tbl td:first-child{text-align:left} .tbl th{background:#f0f2f6}
@media (max-width:600px){.grid{grid-template-columns:1fr}}
"""


def _inline(text) -> str:
    s = html.escape(str(text))
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def _table(df: pd.DataFrame) -> str:
    if df is None or len(df) == 0:
        return "<p class='muted'>Nothing to show yet.</p>"
    return df.to_html(index=False, escape=True, border=0, classes="tbl", na_rep="")


def _panel(inner: str) -> str:
    return f'<div class="panel wide">{inner}</div>'


def _list(items, ordered=True) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + f"</{tag}>"


def render_dashboard(meta, cards, summary, notes, sections) -> str:
    state = {"first": True}

    def fig_html(fig):
        out = fig.to_html(full_html=False, include_plotlyjs="cdn" if state["first"] else False,
                          config={"displaylogo": False, "responsive": True})
        state["first"] = False
        return f'<div class="panel">{out}</div>'

    cards_html = "".join(f'<div class="card"><div class="lbl">{html.escape(l)}</div>'
                         f'<div class="val">{html.escape(v)}</div></div>' for l, v in cards)
    notes_html = "".join(f'<div class="note">{_inline(n)}</div>' for n in notes)
    body = ""
    
    for title, intro, items in sections:
        inner = "".join(i if isinstance(i, str) else fig_html(i) for i in items)
        body += (f"<section><h2>{html.escape(title)}</h2><p class='muted'>{_inline(intro)}</p>"
                 f"<div class='grid'>{inner}</div></section>")
    
    return f"""
        <!doctype html>
        <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Customer Intelligence Dashboard</title><style>{CSS}</style></head>
        <body><main>
        <header><h1>Customer Intelligence: Executive Dashboard</h1>
        <p class="muted">Data as of {html.escape(meta['as_of'])} | model {html.escape(meta['model_name'])}
        ({html.escape(meta['model_version'])}) | generated {html.escape(meta['generated_at'])}</p>
        <p class="notice">{html.escape(nar.PREDICTION_NOTICE)}</p>{notes_html}</header>
        <div class="cards">{cards_html}</div>
        <section><h2>Executive summary</h2><div class="summary">
        <p><strong>{_inline(summary['headline'])}</strong></p>
        <h3>Key findings</h3>{_list(summary['findings'])}
        <h3>Recommended areas for investigation</h3><p class="muted">Questions raised by the data, not conclusions.</p>
        {_list(summary['investigate'])}
        <h3>Caveats</h3>{_list(summary['caveats'], ordered=False)}</div></section>
        {body}
        </main></body></html>
    """


def _campaign_claims(db):
    out = []
    stmt = select(RetentionCampaign).where(RetentionCampaign.status == "completed",
                                           RetentionCampaign.is_synthetic.is_(False))
    for camp in db.scalars(stmt).all():
        out.append((camp.campaign_name, analyse(db, camp.campaign_id)["comparison"]["claim"]))
    return out


def main(include_synthetic: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    cfg = seg.load_config()
    risk_order = seg.ordered_names(cfg["risk_bands"])
    value_order = seg.ordered_names(cfg["value_tiers"])
    high = risk_order[-1]
    model_meta = load_model_meta()
    horizon = model_meta["business_assumptions"]["horizon_months"]

    with SessionLocal() as db:
        raw = load_portfolio(db)
        if raw.empty:
            raise SystemExit("No customers in the database. Run: python -m src.ingestion.pipeline")
        
        pf, active, scored = m.split_portfolio(raw, horizon)
        if scored.empty:
            raise SystemExit("No stored predictions for active customers. Run: python -m src.ml.segment_run")
        
        hist = load_history(db, include_synthetic)
        campaigns = campaign_overview(db)
        claims = _campaign_claims(db)
        top_ids = scored.sort_values("expected_revenue_at_risk", ascending=False)["customer_id"].head(
            TOP_CUSTOMER_REPORTS).tolist()
        n_customer_reports = write_customer_reports(db, top_ids, CUSTOMER_DIR)

    # ---------------- numbers ----------------
    kpis = m.headline_kpis(pf, active, scored, risk_order, horizon)
    overall = kpis["churn_rate_pct"]
    contract, tenure = churn_by(pf, "contract_type"), churn_by(pf, "tenure_bucket")
    extra = {c: churn_by(pf, c) for c in ("internet_service", "payment_method")}
    dims = {c: m.risk_by_segment(scored, c, risk_order) for c in SEGMENT_DIMENSIONS}
    by_band, priority = m.revenue_by_band(scored, risk_order), m.priority_table(scored)
    curve = m.concentration_curve(scored)
    conc = {"top10": m.top_share(curve, 0.10), "top20": m.top_share(curve, 0.20)}
    trend = m.risk_trend(hist, cfg["risk_bands"][high], horizon)
    movers = m.risk_movers(hist)
    has_synth = bool(include_synthetic and hist["batch_id"].astype(str).str.startswith(SYNTHETIC_PREFIX).any())
    notes = m.data_notes(active, scored, risk_order, has_synth)

    ctx = {
        "kpis": kpis, 
        "contract": contract, 
        "tenure": tenure, 
        "extra_churn": extra, 
        "risk_tables": dims,
        "by_band": by_band, 
        "priority": priority, 
        "concentration": conc, 
        "trend": trend, 
        "movers": movers,
        "campaigns": campaigns, 
        "campaign_claims": claims, 
        "risk_order": risk_order, 
        "includes_synthetic": has_synth
    }

    summary = nar.build_summary(ctx)

    as_of = scored["prediction_date"].max()
    meta = {
        "as_of": f"{as_of:%Y-%m-%d}" if pd.notna(as_of) else "unknown",
        "model_name": model_meta["model_name"], 
        "model_version": model_meta["model_version"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    }

    # ---------------- dashboard sections ----------------
    orders = {
        "tenure_bucket": list(TENURE_LABELS), 
        "value_tier": value_order,
        "contract_type": ["Month-to-month", "One year", "Two year"]
    }

    trend_items = []
    if len(trend) >= 2:
        trend_items.append(ch.trend_fig(trend, high))
        disp = trend[["scored_on", "customers", "avg_probability", "pct_high", "expected_revenue_at_risk", "model_version"]].copy()
        disp["scored_on"] = disp["scored_on"].dt.strftime("%Y-%m-%d")
        trend_items.append(_panel(_table(disp)))
        
        if movers:
            trend_items.append(_panel(f"<p class='muted'>Largest increases between the last two runs "
                                      f"({html.escape(str(movers['previous_batch']))} to "
                                      f"{html.escape(str(movers['latest_batch']))}):</p>" + _table(movers["top_increases"])))
    else:
        trend_items.append(_panel("<p>Needs at least two stored scoring runs. Run <code>python -m src.ml.segment_run</code> "
                                  "regularly (for example monthly), or create fake demo history with "
                                  "<code>python -m src.reporting.demo_history</code>.</p>"))

    camp_items = [_panel(_table(campaigns))]
    for name, claim in claims:
        camp_items.append(_panel(f"<strong>{html.escape(name)}</strong><br>{_inline(claim)}"))

    sections = [
        ("1. Observed churn: who has already left",
         "Share of all customers in the data who have left, with 95% confidence intervals. Associations only.",
         [ch.style(churn_bar(pf, "contract_type", "Churn rate by contract type", overall)),
          ch.style(churn_bar(pf, "tenure_bucket", "Churn rate by tenure (months)", overall)),
          ch.style(contract_tenure_heatmap(pf))]),
        ("2. Risk levels across customer segments",
         f"Share of active, scored customers in each risk band. {high} = highest band.",
         [ch.risk_mix_fig(scored, c, risk_order, f"Risk mix by {lab.lower()}", orders.get(c))
          for c, lab in SEGMENT_DIMENSIONS.items()]),
        ("3. Revenue at risk",
         f"Expected annual revenue at risk = churn probability x {horizon} months of charges. "
         "Billing shown is current monthly billing, which is exposure and not an expected loss.",
         [ch.revenue_band_fig(by_band, risk_order), ch.priority_fig(priority), ch.concentration_fig(curve),
          _panel(_table(by_band))]),
        ("4. Trend in predicted risk",
         "Observed churn has no dates in this data, so the trend is in the model's predicted risk across scoring runs.",
         trend_items),
        ("5. Retention campaigns",
         "All campaigns, including synthetic demos (marked in the table). Results are described in the summary only "
         "for real, completed campaigns.", camp_items),
    ]

    cards = nar.kpi_rows(kpis)

    # ---------------- write files ----------------
    EXEC_DIR.mkdir(parents=True, exist_ok=True)
    (EXEC_DIR / "tables").mkdir(exist_ok=True)
    (REPORTS_DIR / "executive_dashboard.html").write_text(
        render_dashboard(meta, cards, summary, notes, sections), encoding="utf-8"
    )
    (REPORTS_DIR / "executive_summary.md").write_text(
        nar.to_markdown(summary, kpis, notes, meta), encoding="utf-8"
    )
    (EXEC_DIR / "kpis.json").write_text(json.dumps(kpis, indent=2))
    
    tables = {
        "churn_by_contract": contract, 
        "churn_by_tenure": tenure, 
        "revenue_by_band": by_band,
        "priority_segments": priority, 
        "risk_trend": trend,
        **{f"risk_by_{c}": t for c, t in dims.items()}, 
        **{f"churn_by_{c}": t for c, t in extra.items()}
    }

    for name, t in tables.items():
        if t is not None and len(t):
            t.to_csv(EXEC_DIR / "tables" / f"{name}.csv", index=False)

    jobs = {
        "customer_predictions_all_active.csv": ReportFilter(),
        "high_value_at_risk_priority_1_2.csv": ReportFilter(priority_ranks=[1, 2]),
        f"month_to_month_{high.lower()}_risk.csv": ReportFilter(
            risk_levels=[high], contract_types=["Month-to-month"]
        )
    }
    for fname, flt in jobs.items():
        flt.validate(risk_order, value_order)
        d = apply_filters(pf, flt)
        if len(d):
            info = write_export(d, EXPORT_DIR / fname, flt)
            print(f"Export: {info['rows']:>6,} rows -> {info['path']}")

    print(f"\n{kpis['total_customers']:,} customers | churn {overall}% | {kpis['active_scored']:,} active scored | "
          f"{kpis['high_band_pct']}% in the {high} band | expected revenue at risk {kpis['expected_revenue_at_risk']:,.0f}")
    print(f"Dashboard: {REPORTS_DIR / 'executive_dashboard.html'}")
    print(f"Summary:   {REPORTS_DIR / 'executive_summary.md'}")
    print(f"{n_customer_reports} customer report(s) in {CUSTOMER_DIR}")
    
    for n in notes:
        print("NOTE:", n)




if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-synthetic", action="store_true",
                    help="show FAKE demo history (created by demo_history.py) in the trend section")
    main(ap.parse_args().include_synthetic)

