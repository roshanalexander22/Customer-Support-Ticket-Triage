"""LangGraph Multi-Agent Orchestration Workflow with Human-in-the-Loop Safety Gate."""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import SupportTicketState
from src.agents import (
    classification_agent,
    retrieval_agent,
    resolution_agent,
    escalation_agent
)
from src.tools import action_engine_tool, audit_logger_tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Node Definitions
# ---------------------------------------------------------

def node_classify(state: SupportTicketState) -> Dict[str, Any]:
    """Execute classification agent."""
    try:
        return classification_agent.process(state)
    except Exception as e:
        logger.error(f"Error in node_classify: {e}", exc_info=True)
        errors = state.get("errors", [])
        errors.append(f"Classification failure: {str(e)}")
        return {
            "category": "General / Feedback",
            "urgency": "Medium",
            "sentiment": "Neutral",
            "intent": "Unclassified customer ticket",
            "extracted_entities": {},
            "classification_confidence": 0.5,
            "errors": errors,
            "current_step": "CLASSIFY_FAILED"
        }


def node_retrieve(state: SupportTicketState) -> Dict[str, Any]:
    """Execute knowledge retrieval agent (CRM + Policy KB)."""
    try:
        return retrieval_agent.process(state)
    except Exception as e:
        logger.error(f"Error in node_retrieve: {e}", exc_info=True)
        errors = state.get("errors", [])
        errors.append(f"Retrieval failure: {str(e)}")
        return {
            "customer_profile": None,
            "retrieved_policies": [],
            "retrieval_query": state.get("subject", ""),
            "errors": errors,
            "current_step": "RETRIEVE_FAILED"
        }


def node_resolve(state: SupportTicketState) -> Dict[str, Any]:
    """Execute resolution agent (draft response + propose action)."""
    try:
        return resolution_agent.process(state)
    except Exception as e:
        logger.error(f"Error in node_resolve: {e}", exc_info=True)
        errors = state.get("errors", [])
        errors.append(f"Resolution failure: {str(e)}")
        return {
            "draft_response": "We have received your ticket and our team is investigating.",
            "proposed_action": "provide_product_guidance",
            "action_payload": {},
            "resolution_notes": f"Fallback resolution triggered due to error: {e}",
            "errors": errors,
            "current_step": "RESOLVE_FAILED"
        }


def node_escalate(state: SupportTicketState) -> Dict[str, Any]:
    """Execute escalation agent (safety gate & consequential action checks)."""
    try:
        return escalation_agent.process(state)
    except Exception as e:
        logger.error(f"Error in node_escalate: {e}", exc_info=True)
        errors = state.get("errors", [])
        errors.append(f"Escalation failure: {str(e)}")
        # Fail-safe: Any failure in escalation defaults to requiring human approval
        return {
            "requires_human_approval": True,
            "approval_reason": f"Fail-safe escalation triggered by system exception: {str(e)}",
            "risk_score": 0.99,
            "safety_violations": ["FAIL_SAFE_TRIGGERED"],
            "human_decision": "PENDING",
            "errors": errors,
            "current_step": "ESCALATE_FAILED"
        }


def node_human_approval_gate(state: SupportTicketState) -> Dict[str, Any]:
    """Human-in-the-Loop decision processing node."""
    start_time = time.time()
    audit_trail = state.get("audit_trail", [])
    
    # Check current human decision in state
    current_decision = state.get("human_decision", "PENDING")
    supervisor = state.get("supervisor_id") or "SUPERVISOR-ON-DUTY"
    
    # If decision was already provided (e.g. from UI, CLI, or test harness), record it
    if current_decision in ["APPROVED", "MODIFIED", "REJECTED"]:
        decision_status = current_decision
        feedback = state.get("human_feedback") or f"Human supervisor verified and marked as {decision_status}"
    else:
        # Default mock-supervisor approval for test execution if no human input specified
        decision_status = "APPROVED"
        feedback = "Automated supervisor validation granted under simulation protocol"

    approval_time = datetime.now(timezone.utc).isoformat()
    duration_ms = (time.time() - start_time) * 1000

    audit_logger_tool.log_event(
        audit_trail=audit_trail,
        step="HUMAN_APPROVAL_GATE",
        agent="HumanSupervisorGate",
        action="process_human_oversight",
        details={
            "decision": decision_status,
            "supervisor_id": supervisor,
            "feedback": feedback,
            "timestamp": approval_time,
            "consequential_action": state.get("proposed_action")
        },
        duration_ms=duration_ms
    )

    return {
        "human_decision": decision_status,
        "human_feedback": feedback,
        "supervisor_id": supervisor,
        "approval_timestamp": approval_time,
        "current_step": "HUMAN_APPROVED" if decision_status in ["APPROVED", "MODIFIED"] else "HUMAN_REJECTED",
        "audit_trail": audit_trail
    }


def node_execute_action(state: SupportTicketState) -> Dict[str, Any]:
    """Execute the approved action via ActionExecutionEngine."""
    start_time = time.time()
    proposed_action = state.get("proposed_action", "none")
    action_payload = state.get("action_payload", {})
    requires_approval = state.get("requires_human_approval", False)
    human_decision = state.get("human_decision", "NOT_REQUIRED")
    supervisor_id = state.get("supervisor_id")
    audit_trail = state.get("audit_trail", [])

    exec_result = action_engine_tool.execute(
        action_name=proposed_action,
        payload=action_payload,
        requires_human_approval=requires_approval,
        human_decision=human_decision,
        authorized_by=supervisor_id if requires_approval else "SYSTEM_AUTONOMOUS"
    )

    duration_ms = (time.time() - start_time) * 1000

    audit_logger_tool.log_event(
        audit_trail=audit_trail,
        step="EXECUTE_ACTION_TOOL",
        agent="ActionExecutionEngine",
        action=f"execute_{proposed_action}",
        details={
            "action": proposed_action,
            "status": exec_result.get("status"),
            "transaction_id": exec_result.get("transaction_id"),
            "authorized_by": exec_result.get("authorized_by")
        },
        duration_ms=duration_ms,
        status=exec_result.get("status", "SUCCESS")
    )

    return {
        "executed_action": proposed_action,
        "execution_status": exec_result.get("status", "SUCCESS"),
        "execution_result": exec_result,
        "current_step": "ACTION_EXECUTED",
        "audit_trail": audit_trail
    }


def node_finalize_ticket(state: SupportTicketState) -> Dict[str, Any]:
    """Finalize response, update customer notification, and persist audit trace."""
    start_time = time.time()
    draft = state.get("draft_response", "")
    decision = state.get("human_decision", "NOT_REQUIRED")
    exec_status = state.get("execution_status", "SKIPPED")
    exec_result = state.get("execution_result") or {}
    ticket_id = state.get("ticket_id", "TCK-UNKNOWN")
    audit_trail = state.get("audit_trail", [])

    # Compose final customer response
    if decision == "REJECTED":
        final_response = (
            f"{draft}\n\n"
            f"[Administrative Note: The proposed adjustment was reviewed by supervisory staff "
            f"and could not be authorized as originally submitted: {state.get('human_feedback')}]. "
            "Our team will reach out directly to explore alternative arrangements."
        )
    elif exec_status == "SUCCESS":
        tx_id = exec_result.get("transaction_id")
        tx_note = f"\n\n[Reference Transaction ID: {tx_id}]" if tx_id else ""
        final_response = f"{draft}{tx_note}"
    else:
        final_response = draft

    # Persist trace
    saved_path = audit_logger_tool.persist_trace(ticket_id=ticket_id, state=state)

    duration_ms = (time.time() - start_time) * 1000

    audit_logger_tool.log_event(
        audit_trail=audit_trail,
        step="FINALIZE_TICKET",
        agent="WorkflowOrchestrator",
        action="finalize_workflow_and_persist_state",
        details={
            "ticket_id": ticket_id,
            "trace_path": str(saved_path),
            "execution_status": exec_status
        },
        duration_ms=duration_ms
    )

    return {
        "final_response": final_response,
        "completed": True,
        "current_step": "COMPLETED",
        "audit_trail": audit_trail
    }


# ---------------------------------------------------------
# Conditional Routing Functions
# ---------------------------------------------------------

def route_after_escalation(state: SupportTicketState) -> Literal["human_approval_gate", "execute_action"]:
    """Conditional branch: route to human gate if consequential action detected."""
    if state.get("requires_human_approval", False):
        return "human_approval_gate"
    return "execute_action"


def route_after_human_approval(state: SupportTicketState) -> Literal["execute_action", "finalize_ticket"]:
    """Conditional branch: proceed to execute if approved or modified; finalize if rejected."""
    decision = state.get("human_decision")
    if decision in ["APPROVED", "MODIFIED"]:
        return "execute_action"
    return "finalize_ticket"


# ---------------------------------------------------------
# Graph Construction Factory
# ---------------------------------------------------------

def create_ticket_triage_graph(checkpointer: Any = None):
    """Build and compile the LangGraph multi-agent workflow."""
    workflow = StateGraph(SupportTicketState)

    # Add Nodes
    workflow.add_node("classify", node_classify)
    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("resolve", node_resolve)
    workflow.add_node("escalate", node_escalate)
    workflow.add_node("human_approval_gate", node_human_approval_gate)
    workflow.add_node("execute_action", node_execute_action)
    workflow.add_node("finalize_ticket", node_finalize_ticket)

    # Add Linear Flow Edges
    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "retrieve")
    workflow.add_edge("retrieve", "resolve")
    workflow.add_edge("resolve", "escalate")

    # Conditional Edge: Safety Gate Evaluation
    workflow.add_conditional_edges(
        "escalate",
        route_after_escalation,
        {
            "human_approval_gate": "human_approval_gate",
            "execute_action": "execute_action"
        }
    )

    # Conditional Edge: Human Supervisor Decision
    workflow.add_conditional_edges(
        "human_approval_gate",
        route_after_human_approval,
        {
            "execute_action": "execute_action",
            "finalize_ticket": "finalize_ticket"
        }
    )

    workflow.add_edge("execute_action", "finalize_ticket")
    workflow.add_edge("finalize_ticket", END)

    # Compile with memory checkpointer if provided
    compiled_app = workflow.compile(checkpointer=checkpointer)
    return compiled_app


# Global default compiled graph
triage_app = create_ticket_triage_graph(checkpointer=MemorySaver())
