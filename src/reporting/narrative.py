"""
Turns the numbers into an executive summary. Wording is deliberately non-causal.
"""

import pandas as pd

from src.analysis.run_eda import md_table
from src.ml.segmentation import PREDICTION_NOTICE
from src.reporting.settings import CURRENCY, MIN_SEGMENT_SIZE, SEGMENT_DIMENSIONS



EXTRA_LABELS = {"internet_service": "internet service", "payment_method": "payment method"}


def _money(v) -> str:
    return f"{CURRENCY}{v:,.0f}"


def _extremes(table, col):
    return table.loc[table["churn_rate_pct"].idxmin()], table.loc[table["churn_rate_pct"].idxmax()]


def _range_text(label, table, col) -> str:
    lo, hi = _extremes(table, col)
    return (f"**{label}.** Observed churn ranges from {lo['churn_rate_pct']:.1f}% ({lo[col]}, "
            f"n={int(lo['customers']):,}) to {hi['churn_rate_pct']:.1f}% ({hi[col]}, n={int(hi['customers']):,}).")


def kpi_rows(k: dict) -> list:
    high = k["high_band_name"]
    return [
        ("Total customers", f"{k['total_customers']:,}"),
        ("Churned (observed to date)", f"{k['churned_customers']:,} ({k['churn_rate_pct']:.1f}%)"),
        ("Retained (active)", f"{k['retained_customers']:,}"),
        ("Active customers with a current score", f"{k['active_scored']:,}"),
        (f"In the {high} risk band", f"{k['high_band_customers']:,} ({k['high_band_pct']:.1f}% of scored)"),
        ("Flagged for review", f"{k['flagged_for_review']:,}"),
        (f"Monthly billing in the {high} band", _money(k["high_band_monthly_billing"])),
        ("Expected annual revenue at risk", _money(k["expected_revenue_at_risk"])),
        ("Monthly billing of churned customers",
         f"{_money(k['churned_monthly_billing'])} ({k['churned_billing_share_pct']:.1f}% of total)"),
    ]


def build_summary(ctx: dict) -> dict:
    k, h = ctx["kpis"], ctx["kpis"]["horizon_months"]
    high, overall = k["high_band_name"], k["churn_rate_pct"]
    findings, investigate = [], []

    band = ctx["by_band"].iloc[-1]
    headline = (f"{overall:.1f}% of customers in the data have churned ({k['churned_customers']:,} of "
                f"{k['total_customers']:,}). Among the {k['active_scored']:,} active customers with a current score, "
                f"{k['high_band_pct']:.1f}% sit in the {high} risk band and carry {band['expected_pct']:.1f}% of an "
                f"expected {_money(k['expected_revenue_at_risk'])} annual revenue at risk.")

    findings.append(f"**Portfolio.** {k['total_customers']:,} customers: {k['retained_customers']:,} retained and "
                    f"{k['churned_customers']:,} churned ({overall:.1f}%). Churned customers accounted for "
                    f"{_money(k['churned_monthly_billing'])} of monthly billing ({k['churned_billing_share_pct']:.1f}% "
                    "of the total).")
    
    findings.append(_range_text("Contract type", ctx["contract"], "contract_type"))
    findings.append(_range_text("Tenure (months)", ctx["tenure"], "tenure_bucket"))

    annual = k["active_annual_billing"]
    pct_of_annual = 100 * k["expected_revenue_at_risk"] / annual if annual else 0.0
    findings.append(f"**Revenue at risk.** Among active customers with a current score, expected annual revenue at "
                    f"risk is {_money(k['expected_revenue_at_risk'])} (churn probability x {h} months of charges; "
                    f"about {pct_of_annual:.0f}% of their annual billing). The {band['risk_level']} band holds "
                    f"{band['customers_pct']:.1f}% of those customers but {band['expected_pct']:.1f}% of that amount.")

    conc = ctx["concentration"]
    if conc.get("top10") is not None:
        findings.append(f"**Concentration.** The 10% of active customers with the highest expected loss hold "
                        f"{100 * conc['top10']:.0f}% of the expected revenue at risk; the top 20% hold "
                        f"{100 * conc['top20']:.0f}%.")

    pr = ctx["priority"]
    if not pr.empty:
        top = pr[pr["priority_rank"] == pr["priority_rank"].min()]
        findings.append(f"**Top-priority segment.** {int(top['customers'].sum()):,} customers are in the highest "
                        f"review-priority tier ({', '.join(top['priority_segment'])}); together they pay "
                        f"{_money(top['monthly_billing'].sum())} per month.")

    cands = []
    for col, t in ctx["risk_tables"].items():
        for _, r in t.iterrows():
            if r["customers"] >= MIN_SEGMENT_SIZE:
                cands.append((r["pct_high_risk"], SEGMENT_DIMENSIONS.get(col, col), r[col], int(r["customers"])))
    cands.sort(reverse=True)
    if cands:
        findings.append(f"**Where elevated risk concentrates.** Highest shares of active customers in the {high} band: "
                        + "; ".join(f"{lab} = {val}: {pct:.1f}% (n={n:,})" for pct, lab, val, n in cands[:3])
                        + ". Segments overlap, so these are not independent groups.")

    t = ctx["trend"]
    if t is not None and len(t) >= 2:
        a, b = t.iloc[0], t.iloc[-1]
        s = (f"**Trend over time.** Average predicted churn probability moved from {a['avg_probability']:.1%} "
             f"({a['scored_on']:%Y-%m-%d}, {int(a['customers']):,} customers scored) to {b['avg_probability']:.1%} "
             f"({b['scored_on']:%Y-%m-%d}, {int(b['customers']):,} scored); the share at or above the {high} cutoff "
             f"moved from {a['pct_high']:.1f}% to {b['pct_high']:.1f}%.")
        if t["model_version"].nunique() > 1:
            s += " The model version changed between runs, so part of the movement may reflect the model."
        if ctx.get("includes_synthetic"):
            s = "SYNTHETIC DEMO HISTORY: " + s
        findings.append(s)
        mv = ctx.get("movers")
        if mv:
            findings.append(f"**Movement since the previous run.** Of {mv['customers_compared']:,} customers scored in "
                            f"both runs, {mv['rose']:,} rose by {mv['min_change'] * 100:.0f}+ points and "
                            f"{mv['fell']:,} fell by {mv['min_change'] * 100:.0f}+ points.")
    else:
        findings.append("**Trend over time.** Not yet available: it needs at least two stored scoring runs. Run "
                        "`python -m src.ml.segment_run` on a regular schedule (for example monthly).")

    camp = ctx.get("campaigns")
    if camp is not None and not camp.empty:
        real = camp[~camp["synthetic"].astype(bool)]
        n_synth = len(camp) - len(real)
    else:
        real, n_synth = pd.DataFrame(), 0
    if real.empty:
        msg = "**Retention campaigns.** No real campaigns have been recorded yet."
        if n_synth:
            msg += f" ({n_synth} synthetic demo campaign(s) are excluded from this summary.)"
        findings.append(msg)
    else:
        statuses = ", ".join(f"{c} {s}" for s, c in real["status"].value_counts().items())
        findings.append(f"**Retention campaigns.** {len(real)} campaign(s) recorded ({statuses}); "
                        f"{int(real['enrolled'].sum()):,} customers enrolled.")
    for name, claim in ctx.get("campaign_claims", []):
        findings.append(f"**Campaign result: {name}.** {claim}")

    # ---- areas to investigate (questions, not conclusions) ----
    lo, hi = _extremes(ctx["contract"], "contract_type")
    if hi["churn_rate_pct"] - lo["churn_rate_pct"] >= 10:
        investigate.append(
            f"Why is observed churn higher on {hi['contract_type']} contracts ({hi['churn_rate_pct']:.1f}%) than on "
            f"{lo['contract_type']} contracts ({lo['churn_rate_pct']:.1f}%)? Contract type, tenure and price overlap, so "
            "a randomised test (for example, offering a contract upgrade to a random half of eligible customers) would "
            "be needed to learn whether changing the contract changes retention.")
    
    first = ctx["tenure"].iloc[0]
    if overall > 0 and first["churn_rate_pct"] >= 1.5 * overall:
        investigate.append(
            f"What happens in the first year? Customers with {first['tenure_bucket']} months of tenure show "
            f"{first['churn_rate_pct']:.1f}% observed churn against {overall:.1f}% overall. Review onboarding, early "
            "billing experience and first-year offers, and check how many of these customers are also on "
            "month-to-month contracts.")
    
    for col, label in EXTRA_LABELS.items():
        t2 = ctx["extra_churn"][col]
        big = t2[t2["customers"] >= 100]
        if big.empty:
            continue
        r = big.loc[big["churn_rate_pct"].idxmax()]
        if r["churn_rate_pct"] - overall >= 5:
            investigate.append(
                f"Why do customers with {label} = {r[col]} show higher observed churn ({r['churn_rate_pct']:.1f}% vs "
                f"{overall:.1f}% overall, n={int(r['customers']):,})? Price, service quality and customer mix are all "
                "possible explanations; this data cannot separate them.")
    
    if conc.get("top10") is not None and conc["top10"] >= 0.30:
        investigate.append(
            f"A small group of customers holds a large share of expected revenue at risk (top 10% = "
            f"{100 * conc['top10']:.0f}%). Check whether account-level review of these customers is practical before "
            "planning broad outreach.")
   
    if not ctx.get("campaign_claims"):
        investigate.append("Run the next retention campaign with a randomised holdout group, so its effect on retention "
                           "can be measured. Without one, results can only be described.")
    investigate.append("Once later customer-status data exists, compare earlier predictions with what customers actually "
                       "did, to check that the model's probabilities still match reality.")

    caveats = [
        PREDICTION_NOTICE,
        "Observed churn is the share of customers in the dataset who have already left (a single snapshot). It is not a "
        "rate per month or quarter, and the data holds no churn dates, so observed churn cannot be tracked over time. "
        "The trend shown is the trend in predicted risk across scoring runs.",
        f"Expected revenue at risk = churn probability x {h} months of current monthly charges. It assumes a lost customer "
        "is not replaced and ignores discounting. The probabilities come from a model trained on this same customer "
        "base, so scores for customers that were in the training data are somewhat optimistic.",
        "Segment comparisons are descriptive. Segments overlap (for example contract type and tenure), and none of these "
        "differences shows what would happen if a customer's contract, price or service changed.",
        "If the customer data is a public or synthetic sample, results illustrate the platform and may not generalise to "
        "a real business.",
    ]

    return {"headline": headline, "findings": findings, "investigate": investigate, "caveats": caveats}


def to_markdown(summary: dict, kpis: dict, notes: list, meta: dict) -> str:
    L = ["# Executive Summary: Customer Churn and Retention", "",
         f"*Data as of {meta['as_of']} | model {meta['model_name']} ({meta['model_version']}) | "
         f"generated {meta['generated_at']}*", "", f"> {PREDICTION_NOTICE}", "",
         "## At a glance", "", summary["headline"], "",
         md_table(pd.DataFrame(kpi_rows(kpis), columns=["measure", "value"])), ""]
    
    if notes:
        L += ["## Data notes", ""] + [f"- {n}" for n in notes] + [""]
    
    L += ["## Key findings", ""] + [f"{i}. {t}" for i, t in enumerate(summary["findings"], 1)]
    L += ["", "## Recommended areas for investigation", "",
          "These are questions raised by the data, not conclusions.", ""]
    L += [f"{i}. {t}" for i, t in enumerate(summary["investigate"], 1)]
    L += ["", "## Caveats", ""] + [f"- {t}" for t in summary["caveats"]]
    
    return "\n".join(L)

