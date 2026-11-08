"""Configuration constants and environment settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
CRM_DATABASE_PATH = DATA_DIR / "crm_database.json"
SCENARIOS_PATH = DATA_DIR / "test_scenarios.json"
RESULTS_DIR = BASE_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
LOGS_DIR = RESULTS_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"

# Ensure runtime directories exist
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Consequential Action Policy Thresholds
MAX_AUTONOMOUS_REFUND_AMOUNT = float(os.getenv("MAX_AUTONOMOUS_REFUND_AMOUNT", "50.00"))
MAX_AUTONOMOUS_COURTESY_CREDIT = float(os.getenv("MAX_AUTONOMOUS_COURTESY_CREDIT", "15.00"))
CRITICAL_FRAUD_RISK_THRESHOLD = float(os.getenv("CRITICAL_FRAUD_RISK_THRESHOLD", "0.25"))
VIP_LTV_THRESHOLD = float(os.getenv("VIP_LTV_THRESHOLD", "1000.00"))

# Checkpointer settings
ENABLE_CHECKPOINTER = os.getenv("ENABLE_CHECKPOINTER", "true").lower() == "true"
CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints.sqlite"

# Logging & Telemetry
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SAVE_AUDIT_LOGS = os.getenv("SAVE_AUDIT_LOGS", "true").lower() == "true"

# SLA Thresholds (Hours)
SLA_HOURS = {
    "Critical": 1,
    "High": 4,
    "Medium": 24,
    "Low": 48
}

# Categories
SUPPORT_CATEGORIES = [
    "Billing & Refunds",
    "Technical Support",
    "Account & Security",
    "Shipping & Logistics",
    "Product Inquiry",
    "General / Feedback"
]

# Urgency Levels
URGENCY_LEVELS = ["Low", "Medium", "High", "Critical"]

# Human Decision Types
DECISION_APPROVED = "APPROVED"
DECISION_REJECTED = "REJECTED"
DECISION_MODIFIED = "MODIFIED"
