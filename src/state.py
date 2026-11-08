"""LangGraph Workflow State Definition for Customer Support Ticket Triage."""

from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AuditLogEntry(TypedDict):
    """Structured record of an agent decision, tool invocation, or state change."""
    step: str
    agent: str
    action: str
    details: Dict[str, Any]
    timestamp: str
    duration_ms: float
    status: str


class ExtractedEntities(TypedDict, total=False):
    """Entities parsed from the support ticket."""
    order_id: Optional[str]
    refund_amount: Optional[float]
    tracking_number: Optional[str]
    device_info: Optional[str]
    subscription_plan: Optional[str]
    urgency_keywords: List[str]


class RetrievedPolicyChunk(TypedDict):
    """Knowledge base policy snippet matching customer inquiry."""
    policy_id: str
    title: str
    relevance_score: float
    excerpt: str
    autonomous_limit: Optional[float]
    consequential_trigger: Optional[str]


class SupportTicketState(TypedDict, total=False):
    """Global workflow state passed across all LangGraph nodes."""
    
    # 1. Ingestion / Ticket Metadata
    ticket_id: str
    customer_id: str
    customer_email: str
    subject: str
    description: str
    channel: str
    timestamp: str

    # 2. Classification State
    category: str
    urgency: str
    sentiment: str
    intent: str
    extracted_entities: ExtractedEntities
    classification_confidence: float

    # 3. Context & Knowledge Retrieval State
    customer_profile: Optional[Dict[str, Any]]
    retrieved_policies: List[RetrievedPolicyChunk]
    retrieval_query: str

    # 4. Draft Resolution & Proposed Action
    draft_response: str
    proposed_action: str
    action_payload: Dict[str, Any]
    resolution_notes: str

    # 5. Escalation & Safety Gate State
    risk_score: float
    requires_human_approval: bool
    approval_reason: str
    safety_violations: List[str]

    # 6. Human Supervisor Interaction State
    human_decision: str  # "PENDING", "APPROVED", "REJECTED", "MODIFIED"
    human_feedback: str
    supervisor_id: Optional[str]
    approval_timestamp: Optional[str]

    # 7. Action Execution & Outcome
    executed_action: Optional[str]
    execution_status: str  # "PENDING", "SUCCESS", "FAILED", "SKIPPED", "BLOCKED"
    execution_result: Optional[Dict[str, Any]]
    final_response: str

    # 8. Observability, Logs & Telemetry
    audit_trail: List[AuditLogEntry]
    errors: List[str]
    current_step: str
    completed: bool


# Pydantic models for structured agent outputs and validation
class ClassificationOutput(BaseModel):
    category: str = Field(description="Support category from approved taxonomy")
    urgency: str = Field(description="Low, Medium, High, or Critical")
    sentiment: str = Field(description="Detected customer emotional state")
    intent: str = Field(description="Core customer intent")
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence score")


class ResolutionOutput(BaseModel):
    draft_response: str = Field(description="Empathetic, policy-compliant response")
    proposed_action: str = Field(description="Action identifier to execute")
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    resolution_notes: str = Field(description="Internal reasoning for resolution")


class EscalationOutput(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0, description="Assessed operational risk")
    requires_human_approval: bool = Field(description="True if consequential action")
    approval_reason: str = Field(description="Explicit policy rationale for escalation")
    safety_violations: List[str] = Field(default_factory=list)
