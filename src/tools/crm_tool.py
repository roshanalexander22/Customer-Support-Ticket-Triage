"""Customer CRM & Account Verification Tool."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from src.config import CRM_DATABASE_PATH


class CRMTool:
    """Provides customer profile lookups, order verification, and risk metrics."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or CRM_DATABASE_PATH
        self.data: Dict[str, Any] = {}
        self._load_database()

    def _load_database(self) -> None:
        """Load customer CRM data from JSON."""
        if self.db_path.exists():
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.data = json.load(f).get("customers", {})
        else:
            self.data = {}

    def lookup_customer(self, customer_id: Optional[str] = None, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve customer profile by ID or email address."""
        if not self.data:
            self._load_database()

        if customer_id and customer_id in self.data:
            return self.data[customer_id]

        if email:
            email_clean = email.strip().lower()
            for cust in self.data.values():
                if cust.get("email", "").strip().lower() == email_clean:
                    return cust

        return None

    def get_order_details(self, customer_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Look up order specifics for a given customer."""
        customer = self.lookup_customer(customer_id)
        if not customer:
            return None

        orders = customer.get("recent_orders", [])
        for order in orders:
            if order.get("order_id") == order_id:
                return order

        return None

    def assess_vip_status(self, customer: Dict[str, Any]) -> bool:
        """Check if customer is entitled to VIP SLA handling."""
        return customer.get("tier") == "VIP_PLATINUM" or customer.get("lifetime_value", 0) >= 1000.0


# Global singleton instance
crm_lookup_tool = CRMTool()
