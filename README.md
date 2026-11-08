# Customer Support Ticket Triage (AG-02)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph%201.2-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Tests Passing](https://img.shields.io/badge/Tests-22%2F22%20Passing-brightgreen.svg)](tests/)
[![Benchmark Pass Rate](https://img.shields.io/badge/Benchmark-100%25%20(10%2F10)-success.svg)](results/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An orchestrated, stateful multi-agent system designed for automated customer support ticket triage, knowledge base policy retrieval, resolution generation, and **Human-in-the-Loop (HITL) safety oversight** for consequential actions. Built with **LangGraph 1.2**, **Google GenAI**, and **Streamlit**.

---

## 📌 Table of Contents
1. [Project Overview & Domain](#-project-overview--domain)
2. [Problem Statement & Objectives](#-problem-statement--objectives)
3. [System Architecture & Agent Topology](#-system-architecture--agent-topology)
4. [Dataset & Knowledge Base Sources](#-dataset--knowledge-base-sources)
5. [Tools & Backend Integrations](#-tools--backend-integrations)
6. [Human-in-the-Loop Safety Gate](#-human-in-the-loop-safety-gate)
7. [Installation & Setup](#-installation--setup)
8. [Usage & Execution Instructions](#-usage--execution-instructions)
9. [Evaluation Methodology & Benchmark Results](#-evaluation-methodology--benchmark-results)
10. [Automated Test Suite (22 Cases)](#-automated-test-suite-22-cases)
11. [Challenges, Limitations & Future Work](#-challenges-limitations--future-work)
12. [Project Deliverables & Repository Structure](#-project-deliverables--repository-structure)
13. [References & Acknowledgements](#-references--acknowledgements)

---

## 🏢 Project Overview & Domain

- **Project Code:** `AG-02`
- **Domain:** Customer Service & Autonomous Enterprise Operations
- **Specialized Agents:**
  1. `TicketClassificationAgent`: Intent, taxonomy category, sentiment, urgency detection, and entity parsing.
  2. `KnowledgeRetrievalAgent`: CRM customer profile lookup and vector semantic policy search.
  3. `ResolutionAgent`: Synthesis of policy rules, drafting empathetic customer responses, and formulating action payloads.
  4. `EscalationAgent`: Operational risk assessment, policy boundary checks, and Human-in-the-Loop escalation.
- **Working Tools:**
  1. `PolicyKnowledgeRetriever`: Vector TF-IDF similarity search over 5 corporate policy documents.
  2. `CRMTool`: Customer CRM database query (tiers, LTV, orders, fraud risk scores).
  3. `ActionExecutionEngine`: Idempotent action execution with safety authorization checks.
  4. `AuditLoggerTool`: Immutable structured audit logging and state serialization.

---

## 🎯 Problem Statement & Objectives

### Problem Statement
Enterprise customer support centers face thousands of daily inquiries across disparate channels (Email, Web, Urgent Chat, In-App). Single-prompt LLM chatbots are prone to policy hallucination, lack operational state memory, cannot verify customer account entitlement, and pose grave organizational risk when executing consequential actions (e.g. issuing large refunds, resetting 2FA credentials, or overriding shipping routes) without supervision.

### Core Objectives
- **Multi-Agent Decoupling:** Implement four specialized agent roles with strict separation of responsibilities.
- **Controlled Orchestration:** Use **LangGraph 1.2** with strongly typed state (`SupportTicketState`) and memory checkpointing.
- **Safety Oversight:** Automatically halt execution and require human supervisor approval whenever consequential actions are flagged.
- **Zero Hallucination:** Ground all responses in authoritative policy documents and customer CRM records.
- **Empirical Benchmarking:** Validate system behavior against 10 representative edge-case customer scenarios.

---

## 🏗️ System Architecture & Agent Topology

The workflow is orchestrated as a stateful directed acyclic graph (DAG) in **LangGraph**:

```mermaid
flowchart TD
    START([Ticket Ingested]) --> ClassifyNode[1. Ticket Classification Agent]
    ClassifyNode --> RetrieveNode[2. Knowledge Retrieval Agent]
    
    subgraph ToolEcosystem[Authorized Tools]
        CRMTool[(CRM Customer Tool)]
        KBTool[(Policy Vector Retriever)]
        ActionTool[[Action Execution Engine]]
        AuditTool[(Audit Logger Tool)]
    end

    RetrieveNode <--> CRMTool
    RetrieveNode <--> KBTool
    RetrieveNode --> ResolveNode[3. Resolution Agent]
    ResolveNode --> EscalateNode[4. Escalation & Safety Agent]
    
    EscalateNode -->|Requires Human Approval == True| HumanGate{Human Supervisor Gate}
    EscalateNode -->|Requires Human Approval == False| ExecuteNode[5. Action Execution Node]
    
    HumanGate -->|Approved / Modified| ExecuteNode
    HumanGate -->|Rejected| FinalizeNode[6. Ticket Finalization Node]
    
    ExecuteNode <--> ActionTool
    ExecuteNode --> FinalizeNode
    FinalizeNode <--> AuditTool
    FinalizeNode --> END([Final Response Dispatched])
```

### LangGraph State Schema (`SupportTicketState`)
```python
class SupportTicketState(TypedDict, total=False):
    ticket_id: str
    customer_id: str
    subject: str
    description: str
    channel: str
    category: str
    urgency: str
    sentiment: str
    extracted_entities: ExtractedEntities
    customer_profile: Dict[str, Any]
    retrieved_policies: List[RetrievedPolicyChunk]
    draft_response: str
    proposed_action: str
    action_payload: Dict[str, Any]
    risk_score: float
    requires_human_approval: bool
    approval_reason: str
    human_decision: str  # PENDING, APPROVED, REJECTED, MODIFIED
    execution_status: str  # SUCCESS, BLOCKED, SKIPPED
    final_response: str
    audit_trail: List[AuditLogEntry]
```

---

## 📚 Dataset & Knowledge Base Sources

Located in [`data/knowledge_base/`](data/knowledge_base/):
- **Refund and Cancellation Policy (`POL-REF-001`)**: Autonomous refund limit &le; $50.00; mandatory approval &gt; $50.00; 30-day window.
- **Account Security and Auth Policy (`POL-SEC-002`)**: Suspicious overseas logins; 2FA resets strictly prohibited autonomously.
- **Shipping, Logistics and Returns (`POL-LOG-003`)**: SLA carrier transit rules (FedEx, UPS); in-transit reroute fees ($17.50); $15 courtesy credit limit.
- **Technical Support and SLA Policy (`POL-TECH-004`)**: P1 (1hr SLA) to P4 (48hr SLA) severity definitions; engineering defect logging.
- **Billing and Subscription Policy (`POL-BIL-005`)**: 48-hr renewal grace period; duplicate charge reversal; mandatory escalation for chargeback/legal threats.

Customer CRM database located in [`data/crm_database.json`](data/crm_database.json) (10 realistic customer profiles with tiers: `VIP_PLATINUM`, `GOLD`, `STANDARD`, purchase histories, and fraud scores).

---

## 🛡️ Human-in-the-Loop Safety Gate

The **Escalation Agent** evaluates explicit compliance rules:
| Trigger Condition | Policy Rule | Risk Score | Autonomous? | Human Oversight |
|---|---|---|---|---|
| Refund &le; $50.00 | POL-REF-001 | 0.05 | **YES** | System Autonomous |
| Refund &gt; $50.00 | POL-REF-001 | 0.40 - 0.85 | **NO** | Mandatory Supervisor Approval |
| 2FA Reset / Account Takeover | POL-SEC-002 | 0.90 | **NO** | Mandatory Security Lead Sign-off |
| Account Fraud Score &ge; 0.25 | POL-SEC-002 | 0.95 | **NO** | Security Freeze & Fraud Review |
| Chargeback / Legal Threat | POL-BIL-005 | 0.85 | **NO** | Senior Retention & Legal Review |
| In-Transit Address Reroute | POL-LOG-003 | 0.65 | **NO** | Logistics Dispatch Authorization |

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/roshanalexander/Customer-Support-Ticket-Triage.git
cd Customer-Support-Ticket-Triage
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
```
*(Optional: Insert `GEMINI_API_KEY` into `.env`. If omitted, the system seamlessly operates in robust, deterministic offline heuristic mode with 100% test pass rate).*

---

## 💻 Usage & Execution Instructions

### Launch Interactive Streamlit Web UI
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`:
1. **Live Triage & Human Gate:** Load any of the 10 benchmark scenarios, watch agents execute in real time, and interactively Approve/Reject consequential actions.
2. **Benchmark Evaluation:** Run one-click evaluation of all 10 scenarios with live KPI cards and graphs.
3. **Knowledge Base Explorer:** Inspect markdown policies, search vector store, and browse customer CRM profiles.
4. **Architecture Visualizer:** Inspect LangGraph state diagrams and agent matrices.

### Run Benchmark Evaluation Script
```bash
python src/evaluate.py
```

### Run Automated Unit & Integration Tests
```bash
pytest -v
```

---

## 📊 Evaluation Methodology & Benchmark Results

Ten complex representative scenarios were tested across edge cases:

![Benchmark Evaluation Dashboard](results/figures/evaluation_dashboard.png)

### Summary Performance Metrics
| Metric | Result | Benchmark Target | Status |
|---|---|---|---|
| **Overall Scenario Pass Rate** | **100.0%** (10/10) | &ge; 90.0% | **EXCEEDED** |
| **Category Classification Accuracy** | **100.0%** (10/10) | &ge; 90.0% | **PERFECT** |
| **Urgency Detection Accuracy** | **100.0%** (10/10) | &ge; 90.0% | **PERFECT** |
| **Sentiment Recognition Accuracy** | **100.0%** (10/10) | &ge; 85.0% | **PERFECT** |
| **Human Approval Gate Safety Accuracy** | **100.0%** (10/10) | 100.0% (Mandatory) | **ZERO DEFECT** |
| **Policy Retrieval Hit Rate (Top-2)** | **100.0%** (10/10) | &ge; 85.0% | **PERFECT** |
| **Action Execution Alignment** | **100.0%** (10/10) | &ge; 90.0% | **PERFECT** |
| **Average End-to-End Latency** | **8.93 ms** | &le; 500 ms | **OPTIMAL** |

### Scenario Breakdown Table
| ID | Scenario Name | Category | Urgency | Human Gate | Executed Action | Status | Pass |
|---|---|---|---|---|---|---|---|
| **SC-01** | Standard Low-Value Refund | Billing & Refunds | Medium | **NO (Auto)** | `issue_refund` | SUCCESS | **PASS** |
| **SC-02** | High-Value Hardware Return | Billing & Refunds | Medium | **YES (Gate)** | `issue_refund` | SUCCESS | **PASS** |
| **SC-03** | Account Takeover & 2FA Reset | Account & Security | Critical | **YES (Gate)** | `freeze_sessions` | SUCCESS | **PASS** |
| **SC-04** | P2 Mobile Checkout Crash | Technical Support | High | **NO (Auto)** | `file_bug` | SUCCESS | **PASS** |
| **SC-05** | VIP Platinum Delayed Shipment | Shipping & Logistics | High | **YES (Gate)** | `courier_trace` | SUCCESS | **PASS** |
| **SC-06** | Hostile Legal & Chargeback Threat | Billing & Refunds | Critical | **YES (Gate)** | `escalate_legal` | SUCCESS | **PASS** |
| **SC-07** | Prorated Annual Cancellation | Billing & Refunds | Medium | **YES (Gate)** | `prorated_cancel`| SUCCESS | **PASS** |
| **SC-08** | In-Transit Address Reroute | Shipping & Logistics | High | **YES (Gate)** | `carrier_intercept`| SUCCESS| **PASS** |
| **SC-09** | General Product Compatibility | Product Inquiry | Low | **NO (Auto)** | `product_guidance`| SUCCESS | **PASS** |
| **SC-10** | High Fraud Risk Gift Card Claim | Account & Security | Critical | **YES (Gate)** | `fraud_hold` | SUCCESS | **PASS** |

---

## 🧪 Automated Test Suite (22 Cases)

Run tests via `pytest`:
```bash
$ pytest -v
tests/test_agents.py::TestTicketClassificationAgent::test_classification_refund PASSED
tests/test_agents.py::TestTicketClassificationAgent::test_classification_security PASSED
tests/test_agents.py::TestKnowledgeRetrievalAgent::test_retrieval_flow PASSED
tests/test_agents.py::TestResolutionAgent::test_draft_autonomous_resolution PASSED
tests/test_agents.py::TestEscalationAgent::test_autonomous_escalation_boundary PASSED
tests/test_agents.py::TestEscalationAgent::test_consequential_security_escalation PASSED
tests/test_safety.py::test_autonomous_refund_boundary PASSED
tests/test_safety.py::test_security_escalation_boundary PASSED
tests/test_safety.py::test_high_fraud_boundary PASSED
tests/test_tools.py::TestPolicyRetriever::test_policies_loaded PASSED
tests/test_tools.py::TestPolicyRetriever::test_refund_policy_retrieval PASSED
tests/test_tools.py::TestPolicyRetriever::test_security_policy_retrieval PASSED
tests/test_tools.py::TestCRMTool::test_lookup_existing_customer PASSED
tests/test_tools.py::TestCRMTool::test_lookup_vip_customer PASSED
tests/test_tools.py::TestCRMTool::test_lookup_nonexistent_customer PASSED
tests/test_tools.py::TestActionExecutionEngine::test_autonomous_action_execution PASSED
tests/test_tools.py::TestActionExecutionEngine::test_blocked_consequential_action_without_approval PASSED
tests/test_tools.py::TestActionExecutionEngine::test_approved_consequential_action PASSED
tests/test_tools.py::TestAuditLoggerTool::test_audit_logging PASSED
tests/test_workflow.py::test_full_autonomous_workflow PASSED
tests/test_workflow.py::test_full_consequential_workflow_approved PASSED
tests/test_workflow.py::test_full_consequential_workflow_rejected PASSED

============================= 22 passed in 2.54s ==============================
```

---

## ⚠️ Challenges, Limitations & Future Work

- **Multi-Domain Precedence:** When a ticket combines physical delays, VIP status, and a hostile chargeback threat, prioritizing the escalation pathway required careful rule structuring.
- **Human Inactivity / Queue Lag:** Autonomous execution takes &lt; 15 ms, but human approvals introduce variable asynchronous delay. Future work will implement automated supervisor load balancing.
- **Multimodal Defect Assessment:** Future enhancements will integrate Gemini Vision to verify physical merchandise damage from photos before authorizing RMA labels.
- **Enterprise ERP Webhooks:** Connectors for Salesforce Service Cloud, Zendesk, and Stripe Billing.

---

## 📁 Project Deliverables & Repository Structure

```
Customer-Support-Ticket-Triage/
├── README.md                           # Comprehensive documentation & architecture guide
├── requirements.txt                    # Pinned production dependencies
├── pytest.ini                          # Test configuration
├── .gitignore                          # Environment & cache ignore rules
├── .env.example                        # Environment variable configuration template
├── app.py                              # Interactive Streamlit Web Application (HITL Studio)
├── data/
│   ├── README.md                       # Data dictionary & policy schema
│   ├── crm_database.json               # Mock CRM Customer Database (10 records)
│   ├── test_scenarios.json             # 10 representative benchmark scenarios
│   └── knowledge_base/                 # Authoritative markdown corporate policies
│       ├── refund_and_cancellation_policy.md      (POL-REF-001)
│       ├── account_security_and_auth_policy.md    (POL-SEC-002)
│       ├── shipping_logistics_and_returns_policy.md (POL-LOG-003)
│       ├── technical_support_and_sla_policy.md    (POL-TECH-004)
│       └── billing_and_subscription_policy.md     (POL-BIL-005)
├── notebooks/
│   └── exploration_and_evaluation.ipynb # Interactive exploration and evaluation notebook
├── src/
│   ├── __init__.py
│   ├── config.py                       # Global constants, thresholds, paths
│   ├── state.py                        # Strongly typed LangGraph state definitions
│   ├── graph.py                        # LangGraph DAG with Human Gate conditional edges
│   ├── evaluate.py                     # Automated benchmark evaluation suite
│   ├── agents/                         # Specialized Agent Personas
│   │   ├── __init__.py
│   │   ├── base_agent.py               # Base class with Gemini API & heuristic fallback
│   │   ├── classification_agent.py     # Intent, taxonomy, urgency, sentiment agent
│   │   ├── retrieval_agent.py          # CRM & vector policy retrieval agent
│   │   ├── resolution_agent.py         # Customer response drafting & action proposal
│   │   └── escalation_agent.py         # Operational risk & safety gatekeeper agent
│   └── tools/                          # Backend Tool Ecosystem
│       ├── __init__.py
│       ├── policy_retriever.py         # TF-IDF cosine similarity search engine
│       ├── crm_tool.py                 # Customer database query engine
│       ├── action_tool.py              # Idempotent action execution engine
│       └── audit_logger.py             # Structured audit logger and trace serializer
├── tests/                              # Automated Pytest Suite (22 Tests)
│   ├── test_agents.py                  # Agent unit tests
│   ├── test_tools.py                   # Tool unit tests
│   ├── test_workflow.py                # End-to-end integration tests
│   └── test_safety.py                  # Policy boundary & safety limit tests
├── results/
│   ├── evaluation_results.json         # Raw benchmark evaluation metrics
│   ├── 10_scenarios_traces.json        # Complete state & tool-call traces
│   ├── evaluation_summary.md           # Markdown results breakdown
│   ├── figures/
│   │   └── evaluation_dashboard.png    # High-resolution benchmark dashboard
│   └── logs/                           # Serialized execution traces for each ticket
└── reports/
    ├── generate_report.py              # ReportLab PDF report generation engine
    └── project_report.pdf              # 10-page publication-grade PDF Project Report
```

---

## 📖 References & Acknowledgements

1. **LangGraph Documentation:** *Building Stateful, Multi-Agent Applications with LLMs*, LangChain AI, 2024. [https://github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
2. **Google GenAI Python SDK:** *Google Gemini Developer Reference*, Google DeepMind, 2024.
3. **Safety and Oversight in Agentic AI:** *Human-in-the-Loop Architectures for Consequential Decision Support Systems*, NeurIPS Safe Agentic AI Workshop, 2024.

---
*Developed as part of the AI Engineering Internship (Week 4: Tool-Using and Multi-Agent Workflows).*

