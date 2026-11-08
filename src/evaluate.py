"""Evaluation Suite: Benchmark 10 Representative Support Scenarios."""

import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.graph import triage_app
from src.config import SCENARIOS_PATH, RESULTS_DIR, FIGURES_DIR


def run_evaluation() -> Dict[str, Any]:
    """Execute all 10 benchmark test scenarios, evaluate agent performance, and generate artifacts."""
    print("=" * 70)
    print("STARTING CUSTOMER SUPPORT TICKET TRIAGE BENCHMARK EVALUATION (10 SCENARIOS)")
    print("=" * 70)

    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        scenarios: List[Dict[str, Any]] = json.load(f)

    results_table: List[Dict[str, Any]] = []
    full_traces: List[Dict[str, Any]] = []

    cat_matches = 0
    urgency_matches = 0
    sentiment_matches = 0
    approval_matches = 0
    policy_matches = 0
    action_matches = 0
    total_latency_ms = 0.0

    for idx, item in enumerate(scenarios, 1):
        scenario_id = item["scenario_id"]
        name = item["name"]
        expected = item["expected"]
        print(f"\n[{idx}/10] Running {scenario_id}: {name}...")

        start_t = time.time()
        # Invoke LangGraph app with thread isolation
        final_state = triage_app.invoke(
            item,
            config={"configurable": {"thread_id": f"bench-{scenario_id.lower()}"}}
        )
        elapsed_ms = (time.time() - start_t) * 1000
        total_latency_ms += elapsed_ms

        # Extract actuals
        act_cat = final_state.get("category", "")
        act_urg = final_state.get("urgency", "")
        act_sent = final_state.get("sentiment", "")
        act_approval = final_state.get("requires_human_approval", False)
        act_action = final_state.get("proposed_action", "")
        act_status = final_state.get("execution_status", "")
        
        # Check policy match
        retrieved_policies = [p["policy_id"] for p in final_state.get("retrieved_policies", [])]
        policy_hit = expected["expected_policy_id"] in retrieved_policies

        # Boolean evaluations
        cat_ok = act_cat.lower() == expected["category"].lower()
        urg_ok = act_urg.lower() == expected["urgency"].lower()
        sent_ok = expected["sentiment"].lower() in act_sent.lower() or act_sent.lower() in expected["sentiment"].lower()
        approval_ok = act_approval == expected["requires_human_approval"]
        action_ok = act_action == expected["expected_action"]

        if cat_ok: cat_matches += 1
        if urg_ok: urgency_matches += 1
        if sent_ok: sentiment_matches += 1
        if approval_ok: approval_matches += 1
        if policy_hit: policy_matches += 1
        if action_ok: action_matches += 1

        overall_scenario_pass = cat_ok and approval_ok and action_ok

        record = {
            "scenario_id": scenario_id,
            "name": name,
            "category_actual": act_cat,
            "category_expected": expected["category"],
            "category_match": cat_ok,
            "urgency_actual": act_urg,
            "urgency_expected": expected["urgency"],
            "urgency_match": urg_ok,
            "human_approval_actual": act_approval,
            "human_approval_expected": expected["requires_human_approval"],
            "human_approval_match": approval_ok,
            "policy_retrieved": retrieved_policies[:2],
            "policy_expected": expected["expected_policy_id"],
            "policy_hit": policy_hit,
            "action_actual": act_action,
            "action_expected": expected["expected_action"],
            "action_match": action_ok,
            "execution_status": act_status,
            "risk_score": final_state.get("risk_score", 0.0),
            "latency_ms": round(elapsed_ms, 2),
            "scenario_passed": overall_scenario_pass
        }
        results_table.append(record)

        # Sanitize state for trace serialization
        serializable_state = {}
        for k, v in final_state.items():
            try:
                json.dumps(v)
                serializable_state[k] = v
            except (TypeError, OverflowError):
                serializable_state[k] = str(v)
        full_traces.append(serializable_state)

        print(f"    Category: {act_cat} ({'✓' if cat_ok else '✗'}) | "
              f"Approval: {act_approval} ({'✓' if approval_ok else '✗'}) | "
              f"Action: {act_action} ({'✓' if action_ok else '✗'}) | "
              f"Latency: {elapsed_ms:.1f}ms")

    n = len(scenarios)
    summary_metrics = {
        "total_scenarios": n,
        "scenarios_passed": sum(1 for r in results_table if r["scenario_passed"]),
        "scenario_pass_rate_pct": round((sum(1 for r in results_table if r["scenario_passed"]) / n) * 100, 1),
        "category_accuracy_pct": round((cat_matches / n) * 100, 1),
        "urgency_accuracy_pct": round((urgency_matches / n) * 100, 1),
        "sentiment_accuracy_pct": round((sentiment_matches / n) * 100, 1),
        "human_approval_gate_accuracy_pct": round((approval_matches / n) * 100, 1),
        "policy_retrieval_hit_rate_pct": round((policy_matches / n) * 100, 1),
        "action_execution_alignment_pct": round((action_matches / n) * 100, 1),
        "execution_success_rate_pct": round((sum(1 for r in results_table if r["execution_status"] == "SUCCESS") / n) * 100, 1),
        "average_latency_ms": round(total_latency_ms / n, 2)
    }

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY METRICS")
    print("=" * 70)
    for k, v in summary_metrics.items():
        print(f"  {k:35s}: {v}")

    # Save results files
    results_json_path = RESULTS_DIR / "evaluation_results.json"
    traces_json_path = RESULTS_DIR / "10_scenarios_traces.json"
    summary_md_path = RESULTS_DIR / "evaluation_summary.md"

    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump({"metrics": summary_metrics, "scenario_details": results_table}, f, indent=2)

    with open(traces_json_path, "w", encoding="utf-8") as f:
        json.dump(full_traces, f, indent=2)

    _generate_markdown_summary(summary_metrics, results_table, summary_md_path)
    _generate_evaluation_charts(results_table, summary_metrics)

    print(f"\nArtifacts successfully written to:")
    print(f"  - {results_json_path}")
    print(f"  - {traces_json_path}")
    print(f"  - {summary_md_path}")
    print(f"  - {FIGURES_DIR / 'evaluation_dashboard.png'}")

    return {"metrics": summary_metrics, "details": results_table}


def _generate_markdown_summary(metrics: Dict[str, Any], details: List[Dict[str, Any]], out_path: Path) -> None:
    """Generate Markdown report table."""
    md = "# Benchmark Evaluation Results (10 Representative Scenarios)\n\n"
    md += f"**Overall Scenario Pass Rate:** {metrics['scenario_pass_rate_pct']}%\n"
    md += f"**Category Classification Accuracy:** {metrics['category_accuracy_pct']}%\n"
    md += f"**Human Approval Gate Safety Accuracy:** {metrics['human_approval_gate_accuracy_pct']}%\n"
    md += f"**Policy Retrieval Hit Rate:** {metrics['policy_retrieval_hit_rate_pct']}%\n"
    md += f"**Average End-to-End Latency:** {metrics['average_latency_ms']} ms\n\n"

    md += "### Detailed Scenario Breakdown\n\n"
    md += "| Scenario ID | Name | Category (Act/Exp) | Urgency | Human Gate | Action | Status | Pass |\n"
    md += "|---|---|---|---|---|---|---|---|\n"

    for r in details:
        cat_str = f"{r['category_actual']}"
        gate_str = f"{'YES' if r['human_approval_actual'] else 'NO'}"
        pass_str = "PASS" if r["scenario_passed"] else "FAIL"
        md += f"| {r['scenario_id']} | {r['name']} | {cat_str} | {r['urgency_actual']} | {gate_str} | `{r['action_actual']}` | {r['execution_status']} | **{pass_str}** |\n"

    out_path.write_text(md, encoding="utf-8")


def _generate_evaluation_charts(details: List[Dict[str, Any]], metrics: Dict[str, Any]) -> None:
    """Generate publication-ready evaluation charts and dashboard."""
    df = pd.DataFrame(details)

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Performance Metrics Bar Chart
    metric_keys = [
        "Category Acc",
        "Urgency Acc",
        "Approval Gate",
        "Policy Retrieval",
        "Action Match",
        "Exec Success"
    ]
    metric_vals = [
        metrics["category_accuracy_pct"],
        metrics["urgency_accuracy_pct"],
        metrics["human_approval_gate_accuracy_pct"],
        metrics["policy_retrieval_hit_rate_pct"],
        metrics["action_execution_alignment_pct"],
        metrics["execution_success_rate_pct"]
    ]
    colors = ["#2b5c8f", "#3c8dbc", "#00a65a", "#f39c12", "#605ca8", "#00c0ef"]
    bars = axes[0, 0].bar(metric_keys, metric_vals, color=colors, width=0.6)
    axes[0, 0].set_ylim(0, 115)
    axes[0, 0].set_ylabel("Accuracy / Alignment (%)")
    axes[0, 0].set_title("Agent Capability Benchmark Scores", fontsize=12, fontweight="bold")
    for bar in bars:
        h = bar.get_height()
        axes[0, 0].text(bar.get_x() + bar.get_width()/2., h + 2, f"{h:.1f}%", ha='center', va='bottom', fontsize=9, fontweight="bold")
    axes[0, 0].tick_params(axis='x', rotation=25)

    # 2. Risk Score by Scenario
    risk_colors = ["#00a65a" if not r else "#dd4b39" for r in df["human_approval_actual"]]
    axes[0, 1].barh(df["scenario_id"], df["risk_score"], color=risk_colors, height=0.6)
    axes[0, 1].axvline(0.25, color="orange", linestyle="--", label="Low/Med Risk Threshold (0.25)")
    axes[0, 1].axvline(0.50, color="red", linestyle="--", label="High Consequential Threshold (0.50)")
    axes[0, 1].set_xlim(0, 1.05)
    axes[0, 1].set_xlabel("Assessed Operational Risk Score (0.0 - 1.0)")
    axes[0, 1].set_title("Risk Score & Human Approval Gate Triggers", fontsize=12, fontweight="bold")
    axes[0, 1].legend(loc="lower right", fontsize=8)

    # 3. Category Distribution
    cat_counts = df["category_actual"].value_counts()
    axes[1, 0].pie(cat_counts, labels=cat_counts.index, autopct="%1.1f%%", startangle=140, colors=sns.color_palette("Blues_r", len(cat_counts)))
    axes[1, 0].set_title("Distribution of Support Ticket Categories", fontsize=12, fontweight="bold")

    # 4. Latency Distribution per Scenario
    axes[1, 1].plot(df["scenario_id"], df["latency_ms"], marker='o', color="#2b5c8f", linewidth=2, markersize=7)
    axes[1, 1].axhline(metrics["average_latency_ms"], color="red", linestyle=":", label=f"Avg: {metrics['average_latency_ms']}ms")
    axes[1, 1].set_ylabel("Processing Latency (ms)")
    axes[1, 1].set_title("End-to-End Orchestrated Workflow Latency", fontsize=12, fontweight="bold")
    axes[1, 1].tick_params(axis='x', rotation=45)
    axes[1, 1].legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    chart_path = FIGURES_DIR / "evaluation_dashboard.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()


if __name__ == "__main__":
    run_evaluation()
