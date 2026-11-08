"""Quick CLI Demonstration for Customer Support Ticket Triage (AG-02)."""

import json
from src.graph import triage_app

def run_demo():
    print("=" * 70)
    print("  CUSTOMER SUPPORT TICKET TRIAGE (AG-02) — CLI DEMONSTRATION")
    print("=" * 70)

    with open("data/test_scenarios.json", "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    # 1. Autonomous Flow: Scenario 1
    print("\n>>> DEMO 1: SCENARIO 01 — Autonomous Low-Value Refund ($28.50)")
    res1 = triage_app.invoke(scenarios[0], config={"configurable": {"thread_id": "cli-demo-1"}})
    cust1 = res1.get("customer_profile") or {}
    print(f"Customer: {cust1.get('name')} | Tier: {cust1.get('tier')} | LTV: ${cust1.get('lifetime_value')}")
    print(f"Category: {res1.get('category')} | Urgency: {res1.get('urgency')} | Sentiment: {res1.get('sentiment')}")
    policies1 = res1.get("retrieved_policies", [])
    if policies1:
        print(f"Policy Retrieved: {policies1[0]['policy_id']} — {policies1[0]['title']}")
    print(f"Proposed Action: {res1.get('proposed_action')} (${res1.get('action_payload', {}).get('amount')})")
    print(f"Requires Human Approval: {res1.get('requires_human_approval')} (Operational Risk: {res1.get('risk_score')})")
    print(f"Execution Status: {res1.get('execution_status')} | TxID: {res1.get('execution_result', {}).get('transaction_id')}")
    print("\n--- Dispatched Customer Response ---")
    print(res1.get("final_response"))

    # 2. Consequential Flow: Scenario 3 (Critical 2FA Security Breach)
    print("\n" + "=" * 70)
    print("\n>>> DEMO 2: SCENARIO 03 — Consequential 2FA Lockout & Security Freeze")
    res3 = triage_app.invoke(scenarios[2], config={"configurable": {"thread_id": "cli-demo-3"}})
    cust3 = res3.get("customer_profile") or {}
    print(f"Customer: {cust3.get('name')} | Tier: {cust3.get('tier')} | Fraud Risk: {cust3.get('fraud_risk_score')}")
    print(f"Category: {res3.get('category')} | Urgency: {res3.get('urgency')} | Sentiment: {res3.get('sentiment')}")
    print(f"Proposed Action: {res3.get('proposed_action')}")
    print(f"Requires Human Approval: {res3.get('requires_human_approval')} (Operational Risk: {res3.get('risk_score')})")
    print(f"Approval Rationale: {res3.get('approval_reason')}")
    print(f"Human Supervisor Decision: {res3.get('human_decision')} by {res3.get('supervisor_id')}")
    print(f"Execution Status: {res3.get('execution_status')} | TxID: {res3.get('execution_result', {}).get('transaction_id')}")
    print("\n--- Dispatched Customer Response ---")
    print(res3.get("final_response"))
    print("\n" + "=" * 70)

if __name__ == "__main__":
    run_demo()
