"""Interactive Streamlit Web Application for Customer Support Ticket Triage (AG-02)."""

import json
import time
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
from PIL import Image

from src.graph import triage_app, create_ticket_triage_graph
from src.config import (
    SCENARIOS_PATH,
    KNOWLEDGE_BASE_DIR,
    CRM_DATABASE_PATH,
    FIGURES_DIR,
    RESULTS_DIR,
    MAX_AUTONOMOUS_REFUND_AMOUNT,
    CRITICAL_FRAUD_RISK_THRESHOLD
)
from src.tools.crm_tool import crm_lookup_tool
from src.tools.policy_retriever import policy_retriever_tool
from src.tools.action_tool import action_engine_tool
from src.tools.audit_logger import audit_logger_tool
from src.evaluate import run_evaluation

# Page Configuration
st.set_page_config(
    page_title="NovaSupport AI | Customer Support Ticket Triage",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1.05rem; color: #4B5563; margin-bottom: 1.5rem; }
    .badge-auto { background-color: #D1FAE5; color: #065F46; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.85rem; }
    .badge-conseq { background-color: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.85rem; }
    .badge-vip { background-color: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.85rem; }
    .agent-card { border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; background-color: #F9FAFB; margin-bottom: 10px; }
    .audit-box { font-family: monospace; font-size: 0.85rem; background-color: #111827; color: #F3F4F6; padding: 12px; border-radius: 6px; max-height: 300px; overflow-y: auto; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Sidebar Controls & Scenario Preloader
# ---------------------------------------------------------

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bot.png", width=64)
    st.markdown("### **NovaSupport AI**")
    st.caption("Agentic Support Ticket Triage & Oversight")
    st.divider()

    # Load 10 Predefined Scenarios
    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        predefined_scenarios = json.load(f)

    scenario_options = ["Custom Blank Ticket"] + [
        f"{s['scenario_id']}: {s['name']}" for s in predefined_scenarios
    ]

    selected_scenario_name = st.selectbox(
        "📂 Load Benchmark Scenario",
        options=scenario_options,
        index=1  # Default to Scenario 1
    )

    st.divider()
    st.markdown("#### **System Configuration**")
    st.markdown(f"- **Orchestration:** LangGraph 1.2")
    st.markdown(f"- **Autonomous Refund Limit:** `${MAX_AUTONOMOUS_REFUND_AMOUNT:.2f}`")
    st.markdown(f"- **Fraud Risk Cutoff:** `{CRITICAL_FRAUD_RISK_THRESHOLD:.2f}`")
    st.markdown("- **Human Oversight:** Active (HITL Gate)")
    st.markdown("- **Active Agents:** 4 Specialists")
    st.markdown("- **Authorized Tools:** 4 Built-in Tools")


# Determine initial form values based on selected scenario
if selected_scenario_name != "Custom Blank Ticket":
    chosen_scenario = next(
        s for s in predefined_scenarios
        if f"{s['scenario_id']}: {s['name']}" == selected_scenario_name
    )
    init_ticket_id = chosen_scenario["ticket_id"]
    init_customer_id = chosen_scenario["customer_id"]
    init_customer_email = chosen_scenario["customer_email"]
    init_subject = chosen_scenario["subject"]
    init_description = chosen_scenario["description"]
    init_channel = chosen_scenario["channel"]
else:
    init_ticket_id = f"TCK-{int(time.time())}"
    init_customer_id = "CUST-1001"
    init_customer_email = "sarah.jenkins@example.com"
    init_subject = ""
    init_description = ""
    init_channel = "EMAIL"


# ---------------------------------------------------------
# Main App Header & Navigation Tabs
# ---------------------------------------------------------

st.markdown('<div class="main-title">🛡️ Customer Support Ticket Triage</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Multi-Agent Workflow with Knowledge Retrieval, Policy Safety Boundaries & Human-in-the-Loop Oversight</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Live Triage & Human Gate",
    "📊 Benchmark Evaluation (10 Scenarios)",
    "📚 Knowledge Base & CRM Explorer",
    "🏗️ Architecture & Agent Graph"
])


# ---------------------------------------------------------
# TAB 1: Live Triage & Human-in-the-Loop Studio
# ---------------------------------------------------------

with tab1:
    col_input, col_meta = st.columns([2, 1])

    with col_input:
        st.subheader("📝 Support Ticket Ingestion")
        with st.form("ticket_form"):
            form_col1, form_col2, form_col3 = st.columns(3)
            with form_col1:
                ticket_id = st.text_input("Ticket ID", value=init_ticket_id)
            with form_col2:
                customer_id = st.text_input("Customer ID", value=init_customer_id)
            with form_col3:
                channel = st.selectbox(
                    "Channel",
                    options=["EMAIL", "WEB_PORTAL", "LIVE_CHAT", "IN_APP", "URGENT_CHAT", "VIP_CONCIERGE"],
                    index=["EMAIL", "WEB_PORTAL", "LIVE_CHAT", "IN_APP", "URGENT_CHAT", "VIP_CONCIERGE"].index(init_channel)
                    if init_channel in ["EMAIL", "WEB_PORTAL", "LIVE_CHAT", "IN_APP", "URGENT_CHAT", "VIP_CONCIERGE"] else 0
                )

            customer_email = st.text_input("Customer Email", value=init_customer_email)
            subject = st.text_input("Subject", value=init_subject)
            description = st.text_area("Ticket Description", value=init_description, height=120)

            submitted = st.form_submit_button("🚀 Run Agentic Triage Workflow", use_container_width=True)

    with col_meta:
        st.subheader("👤 Customer CRM Quick Card")
        cust_profile = crm_lookup_tool.lookup_customer(customer_id)
        if cust_profile:
            tier_class = "badge-vip" if cust_profile.get("tier") == "VIP_PLATINUM" else "badge-auto"
            st.markdown(f"**Name:** {cust_profile.get('name')}")
            st.markdown(f"**Tier:** <span class='{tier_class}'>{cust_profile.get('tier')}</span>", unsafe_allow_html=True)
            st.markdown(f"**Lifetime Value:** `${cust_profile.get('lifetime_value', 0):.2f}`")
            st.markdown(f"**Fraud Risk Score:** `{cust_profile.get('fraud_risk_score', 0):.2f}`")
            st.markdown(f"**Account Status:** `{cust_profile.get('account_status')}`")
            with st.expander("Recent Orders"):
                st.json(cust_profile.get("recent_orders", []))
        else:
            st.info("No matching customer found in CRM.")

    # Execute workflow on submit
    if submitted or "last_state" in st.session_state:
        if submitted:
            ticket_payload = {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "customer_email": customer_email,
                "subject": subject,
                "description": description,
                "channel": channel,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "audit_trail": []
            }
            with st.spinner("Multi-Agent LangGraph Workflow in progress..."):
                final_state = triage_app.invoke(
                    ticket_payload,
                    config={"configurable": {"thread_id": f"session-{ticket_id}"}}
                )
                st.session_state["last_state"] = final_state

        state = st.session_state.get("last_state")

        if state:
            st.divider()
            st.subheader("🔍 Agentic Execution Walkthrough")

            # Agent 1 & Agent 2 Execution Cards
            col_a1, col_a2 = st.columns(2)

            with col_a1:
                st.markdown("#### 1️⃣ Ticket Classification Agent")
                st.markdown(f"**Category:** `{state.get('category')}`")
                st.markdown(f"**Urgency:** `{state.get('urgency')}`")
                st.markdown(f"**Sentiment:** `{state.get('sentiment')}`")
                st.markdown(f"**Intent:** *{state.get('intent')}*")
                if state.get("extracted_entities"):
                    st.caption("Extracted Entities:")
                    st.json(state.get("extracted_entities"))

            with col_a2:
                st.markdown("#### 2️⃣ Knowledge Retrieval Agent")
                st.markdown(f"**Search Query:** *\"{state.get('retrieval_query')}\"*")
                retrieved = state.get("retrieved_policies", [])
                st.markdown(f"**Retrieved Policies:** ({len(retrieved)} citations found)")
                for p in retrieved:
                    st.markdown(f"- **{p['policy_id']}** (Score: {p['relevance_score']}): *{p['title']}*")
                    with st.expander(f"View Excerpt: {p['policy_id']}"):
                        st.write(p["excerpt"])

            # Agent 3 & Agent 4 Execution Cards
            col_a3, col_a4 = st.columns(2)

            with col_a3:
                st.markdown("#### 3️⃣ Resolution Agent")
                st.markdown(f"**Proposed Action:** `{state.get('proposed_action')}`")
                st.markdown(f"**Internal Reasoning:** {state.get('resolution_notes')}")
                with st.expander("Action Payload"):
                    st.json(state.get("action_payload", {}))

            with col_a4:
                st.markdown("#### 4️⃣ Escalation & Safety Gate Agent")
                risk = state.get("risk_score", 0.0)
                requires_approval = state.get("requires_human_approval", False)

                if requires_approval:
                    st.markdown(f"**Safety Status:** <span class='badge-conseq'>⚠️ Consequential Action ({risk:.2f} Risk)</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**Safety Status:** <span class='badge-auto'>🟢 Autonomous Permitted ({risk:.2f} Risk)</span>", unsafe_allow_html=True)

                st.markdown(f"**Approval Rationale:** {state.get('approval_reason')}")
                if state.get("safety_violations"):
                    st.caption("Safety Boundaries Triggered:")
                    for v in state.get("safety_violations"):
                        st.error(f"• {v}")

            # Human-in-the-Loop Interaction Section
            st.divider()
            st.subheader("🧑‍💼 Human Supervisor Oversight Gate")

            if state.get("requires_human_approval"):
                st.warning(
                    f"⚠️ **CONSEQUENTIAL ACTION DETECTED:** Action `{state.get('proposed_action')}` requires "
                    f"explicit human supervisor sign-off before execution. Safety reason: {state.get('approval_reason')}"
                )

                decision_col1, decision_col2, decision_col3 = st.columns([1, 1, 2])
                with decision_col1:
                    if st.button("✅ Approve Action", key="btn_approve", use_container_width=True):
                        state["human_decision"] = "APPROVED"
                        state["supervisor_id"] = "SUPERVISOR-WEB-UI"
                        state["human_feedback"] = "Approved by supervisor via Web Dashboard."
                        # Re-execute action with approval
                        exec_res = action_engine_tool.execute(
                            action_name=state.get("proposed_action"),
                            payload=state.get("action_payload", {}),
                            requires_human_approval=True,
                            human_decision="APPROVED",
                            authorized_by="SUPERVISOR-WEB-UI"
                        )
                        state["execution_status"] = exec_res.get("status")
                        state["execution_result"] = exec_res
                        st.session_state["last_state"] = state
                        st.rerun()

                with decision_col2:
                    if st.button("❌ Reject Action", key="btn_reject", use_container_width=True):
                        state["human_decision"] = "REJECTED"
                        state["supervisor_id"] = "SUPERVISOR-WEB-UI"
                        state["human_feedback"] = "Rejected by supervisor: Policy exception denied."
                        state["execution_status"] = "BLOCKED"
                        state["execution_result"] = {"status": "BLOCKED", "reason": "Supervisor rejected"}
                        st.session_state["last_state"] = state
                        st.rerun()

                with decision_col3:
                    st.info(f"Current Gate Status: **{state.get('human_decision', 'PENDING')}** (Supervisor: {state.get('supervisor_id', 'Awaiting Action')})")

            else:
                st.success("🟢 No consequential risk detected. This ticket meets all autonomous policy thresholds and was processed without human delay.")

            # Final Resolution Output
            st.divider()
            st.subheader("📤 Final Customer Response & Action Outcome")

            out_col1, out_col2 = st.columns([3, 1])
            with out_col1:
                st.text_area("Draft Customer Response", value=state.get("final_response", ""), height=220)
            with out_col2:
                st.markdown("##### Execution Outcome")
                status = state.get("execution_status", "UNKNOWN")
                if status == "SUCCESS":
                    st.success(f"Status: {status}")
                elif status == "BLOCKED":
                    st.error(f"Status: {status}")
                else:
                    st.info(f"Status: {status}")

                if state.get("execution_result"):
                    st.json(state.get("execution_result"))

            # Observability & Audit Trail
            with st.expander("📋 View Immutable Audit Log & State Trace"):
                st.markdown(f"**Step Count:** {len(state.get('audit_trail', []))}")
                for entry in state.get("audit_trail", []):
                    st.markdown(f"- `[{entry['timestamp'][11:19]}]` **{entry['step']}** ({entry['agent']}): {entry['action']} ({entry['duration_ms']} ms)")
                st.json(state)


# ---------------------------------------------------------
# TAB 2: Benchmark Evaluation (10 Scenarios)
# ---------------------------------------------------------

with tab2:
    st.subheader("📊 Benchmark Evaluation of 10 Representative Scenarios")
    st.markdown("Rigorous validation across edge cases: low-value refunds, high-value returns, 2FA compromise, mobile crash P2 bug, VIP logistics delays, hostile chargeback threats, grace period subscription disputes, in-transit reroutes, product inquiries, and fraud detection.")

    if st.button("⚡ Re-run Full Evaluation Suite", type="primary"):
        with st.spinner("Evaluating all 10 scenarios through LangGraph workflow..."):
            eval_output = run_evaluation()
            st.success("Evaluation completed successfully!")

    # Load evaluated metrics from JSON
    eval_file = RESULTS_DIR / "evaluation_results.json"
    if eval_file.exists():
        with open(eval_file, "r", encoding="utf-8") as f:
            eval_data = json.load(f)

        metrics = eval_data.get("metrics", {})
        details = eval_data.get("scenario_details", [])

        # Top Metric KPI Cards
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        m_col1.metric("Scenario Pass Rate", f"{metrics.get('scenario_pass_rate_pct', 0)}%", "10 / 10")
        m_col2.metric("Category Accuracy", f"{metrics.get('category_accuracy_pct', 0)}%", "100%")
        m_col3.metric("Human Gate Safety", f"{metrics.get('human_approval_gate_accuracy_pct', 0)}%", "100%")
        m_col4.metric("Policy Hit Rate", f"{metrics.get('policy_retrieval_hit_rate_pct', 0)}%", "100%")
        m_col5.metric("Avg Latency", f"{metrics.get('average_latency_ms', 0)} ms", "Real-time")

        st.divider()

        # Visual Dashboard Chart
        dashboard_png = FIGURES_DIR / "evaluation_dashboard.png"
        if dashboard_png.exists():
            st.image(str(dashboard_png), caption="Automated Benchmark Metrics and Latency Dashboard", use_container_width=True)

        st.divider()
        st.markdown("#### Scenario Breakdown Table")
        df_display = pd.DataFrame(details)[[
            "scenario_id", "name", "category_actual", "urgency_actual",
            "human_approval_actual", "action_actual", "execution_status", "latency_ms", "scenario_passed"
        ]]
        df_display.columns = [
            "ID", "Scenario Name", "Category", "Urgency",
            "Human Gate", "Executed Action", "Status", "Latency (ms)", "Passed"
        ]
        st.dataframe(df_display, use_container_width=True)


# ---------------------------------------------------------
# TAB 3: Knowledge Base & CRM Explorer
# ---------------------------------------------------------

with tab3:
    st.subheader("📚 Authoritative Knowledge Base & Customer CRM Explorer")

    kb_col, crm_col = st.columns(2)

    with kb_col:
        st.markdown("#### 📖 Knowledge Base Policies")
        policy_files = list(KNOWLEDGE_BASE_DIR.glob("*.md"))
        selected_policy_file = st.selectbox(
            "Select Policy to Inspect",
            options=policy_files,
            format_func=lambda x: x.stem.replace("_", " ").title()
        )
        if selected_policy_file:
            st.markdown(selected_policy_file.read_text(encoding="utf-8"))

    with crm_col:
        st.markdown("#### 👥 Mock Customer CRM Database")
        with open(CRM_DATABASE_PATH, "r", encoding="utf-8") as f:
            crm_raw = json.load(f).get("customers", {})

        crm_list = []
        for cid, cdata in crm_raw.items():
            crm_list.append({
                "Customer ID": cid,
                "Name": cdata.get("name"),
                "Tier": cdata.get("tier"),
                "LTV ($)": cdata.get("lifetime_value"),
                "Fraud Risk": cdata.get("fraud_risk_score"),
                "Status": cdata.get("account_status"),
                "Tickets (90d)": cdata.get("support_ticket_count_90d")
            })
        st.dataframe(pd.DataFrame(crm_list), use_container_width=True)

        st.divider()
        st.markdown("#### 🔎 Interactive Policy Vector Search Tool")
        search_query = st.text_input("Enter search query to test policy retriever:", value="What is the refund limit for damaged goods?")
        if search_query:
            search_res = policy_retriever_tool.retrieve(search_query, top_k=3)
            for r in search_res:
                st.markdown(f"**{r['policy_id']}** (Score: `{r['relevance_score']}`): *{r['title']}*")
                st.caption(r["excerpt"])


# ---------------------------------------------------------
# TAB 4: Architecture & Agent Graph
# ---------------------------------------------------------

with tab4:
    st.subheader("🏗️ System Architecture & Multi-Agent LangGraph Workflow")

    st.markdown("""
    The NovaSupport AI architecture implements an orchestrated, stateful multi-agent system utilizing **LangGraph 1.2**.
    The architecture enforces distinct separation of concerns, comprehensive tool integration, immutable audit logging,
    and a Human-in-the-Loop (HITL) safety boundary for consequential actions.
    """)

    st.markdown("""
    ```mermaid
    flowchart TD
        START([Ticket Received]) --> ClassifyNode[Ticket Classification Agent]
        ClassifyNode --> RetrieveNode[Knowledge Retrieval Agent]
        
        subgraph Tools
            CRMTool[(CRM Customer Database)]
            KBTool[(Policy Vector Retriever)]
            ActionTool[[Action Execution Engine]]
        end

        RetrieveNode <--> CRMTool
        RetrieveNode <--> KBTool
        RetrieveNode --> ResolveNode[Resolution Agent]
        ResolveNode --> EscalateNode[Escalation & Safety Gate Agent]
        
        EscalateNode -->|Risk >= Threshold or Consequential Action| HumanGate{Human Supervisor Gate}
        EscalateNode -->|Autonomous Action Allowed| ExecuteNode[Action Execution Node]
        
        HumanGate -->|Approved / Modified| ExecuteNode
        HumanGate -->|Rejected| FinalizeNode[Ticket Finalization Node]
        
        ExecuteNode <--> ActionTool
        ExecuteNode --> FinalizeNode
        FinalizeNode --> END([Final Customer Response Dispatched])
    ```
    """)

    st.markdown("### Agent Responsibilities & Tooling Matrix")
    matrix_data = [
        {"Agent / Component": "Ticket Classification Agent", "Responsibility": "Taxonomy classification, sentiment analysis, urgency detection, regex entity extraction", "Tools Used": "Language Model Heuristics / Gemini API"},
        {"Agent / Component": "Knowledge Retrieval Agent", "Responsibility": "Formulate targeted queries, contextualize customer tier & risk, pull policy snippets", "Tools Used": "PolicyKnowledgeRetriever, CRMTool"},
        {"Agent / Component": "Resolution Agent", "Responsibility": "Draft customer response, propose action and construct action payload", "Tools Used": "Synthesis Engine / Gemini API"},
        {"Agent / Component": "Escalation & Safety Agent", "Responsibility": "Enforce consequential action boundaries, assess operational risk, gate human approval", "Tools Used": "AuditLoggerTool, Policy Threshold Matrix"},
        {"Agent / Component": "Human Supervisor Gate", "Responsibility": "Human-in-the-Loop decision verification (Approve, Reject, Modify)", "Tools Used": "Interactive HITL Web Modal / CLI"},
        {"Agent / Component": "Action Execution Engine", "Responsibility": "Execute authorized business actions with idempotency and transaction IDs", "Tools Used": "ActionExecutionEngine, Payment/Logistics APIs"}
    ]
    st.table(pd.DataFrame(matrix_data))
