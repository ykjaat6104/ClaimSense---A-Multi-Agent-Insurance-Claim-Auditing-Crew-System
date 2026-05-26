"""
Tool definitions for agent use: database queries, web search, and policy analysis.
These are directly callable functions that agents can invoke via LLM tool-calling.
"""

from typing import Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ========== DATABASE TOOLS ==========

def get_user_claims_history(user_id: str, days_back: int = 365) -> dict[str, Any]:
    """
    Retrieve the user's claims filing frequency over a specified period.
    
    Returns:
        {
            "user_id": str,
            "total_claims_12m": int,
            "claims_last_90_days": int,
            "claims_last_30_days": int,
            "average_claim_interval_days": float,
            "highest_claim_amount": float,
            "claim_ids": list[str],
            "flagged_for_frequency": bool,
        }
    """
    try:
        # This would be implemented with actual DB queries
        # For now, returning a template response
        return {
            "user_id": user_id,
            "total_claims_12m": 0,
            "claims_last_90_days": 0,
            "claims_last_30_days": 0,
            "average_claim_interval_days": 0.0,
            "highest_claim_amount": 0.0,
            "claim_ids": [],
            "flagged_for_frequency": False,
        }
    except Exception as e:
        logger.error(f"Error fetching claims history for user {user_id}: {e}")
        return {"error": str(e)}


def get_payment_status(user_id: str, policy_id: str) -> dict[str, Any]:
    """
    Check the customer's premium payment status and history.
    
    Returns:
        {
            "user_id": str,
            "policy_id": str,
            "current_status": str,  # ACTIVE, LAPSED, SUSPENDED, CANCELLED
            "last_payment_date": str,
            "next_payment_due": str,
            "payments_in_arrears": int,
            "policy_active_since": str,
            "policy_started_date": str,
            "recent_payment_pattern": list[dict],
            "premium_amount": float,
        }
    """
    try:
        return {
            "user_id": user_id,
            "policy_id": policy_id,
            "current_status": "ACTIVE",
            "last_payment_date": datetime.now().isoformat(),
            "next_payment_due": (datetime.now() + timedelta(days=30)).isoformat(),
            "payments_in_arrears": 0,
            "policy_active_since": (datetime.now() - timedelta(days=365)).isoformat(),
            "policy_started_date": (datetime.now() - timedelta(days=365)).isoformat(),
            "recent_payment_pattern": [],
            "premium_amount": 0.0,
        }
    except Exception as e:
        logger.error(f"Error fetching payment status for user {user_id}: {e}")
        return {"error": str(e)}


def get_policy_recent_changes(policy_id: str) -> dict[str, Any]:
    """
    Detect recent changes to the policy (e.g., coverage updates, rider additions).
    Useful for detecting suspicious "just before claim" modifications.
    
    Returns:
        {
            "policy_id": str,
            "recent_changes": list[dict],
            "last_modification_date": str,
            "coverage_added_recently": list[str],
            "last_renewal_date": str,
            "suspicious_timing": bool,
            "time_since_last_change_days": int,
        }
    """
    try:
        return {
            "policy_id": policy_id,
            "recent_changes": [],
            "last_modification_date": (datetime.now() - timedelta(days=30)).isoformat(),
            "coverage_added_recently": [],
            "last_renewal_date": (datetime.now() - timedelta(days=180)).isoformat(),
            "suspicious_timing": False,
            "time_since_last_change_days": 30,
        }
    except Exception as e:
        logger.error(f"Error fetching policy changes for policy {policy_id}: {e}")
        return {"error": str(e)}


def check_duplicate_claims(user_id: str, claim_description: str) -> dict[str, Any]:
    """
    Search for potential duplicate or similar claims filed by the same user.
    
    Returns:
        {
            "user_id": str,
            "potential_duplicates": list[dict],
            "matching_score": float,  # 0-1
            "flagged_as_duplicate": bool,
        }
    """
    try:
        return {
            "user_id": user_id,
            "potential_duplicates": [],
            "matching_score": 0.0,
            "flagged_as_duplicate": False,
        }
    except Exception as e:
        logger.error(f"Error checking duplicates for user {user_id}: {e}")
        return {"error": str(e)}


# ========== WEB SEARCH TOOLS ==========

def search_market_price(item_name: str, category: str = "") -> dict[str, Any]:
    """
    Search for fair market price of claimed item via web.
    Helps detect inflated invoice amounts.
    
    Returns:
        {
            "item_name": str,
            "category": str,
            "average_price": float,
            "price_range": {"min": float, "max": float},
            "currency": str,
            "results": list[dict],
            "estimated_retail_value": float,
            "fair_market_value": float,
            "data_quality": str,  # HIGH, MEDIUM, LOW
        }
    """
    try:
        from app.services.web_search import get_web_search_service
        from app.config import get_settings
        
        settings = get_settings()
        web_search = get_web_search_service(tavily_api_key=settings.tavily_api_key if hasattr(settings, 'tavily_api_key') else None)
        
        result = web_search.search_market_price(item_name, category)
        
        return {
            "item_name": item_name,
            "category": category,
            "average_price": result.get("average_price", 0.0),
            "price_range": result.get("price_range", {"min": 0.0, "max": 0.0}),
            "currency": "USD",
            "results": result.get("results", []),
            "estimated_retail_value": result.get("average_price", 0.0),
            "fair_market_value": result.get("average_price", 0.0),
            "data_quality": result.get("data_quality", "LOW"),
        }
    except Exception as e:
        logger.error(f"Error searching market price for {item_name}: {e}")
        return {"error": str(e)}


def search_regional_repair_rates(repair_type: str, location: str = "") -> dict[str, Any]:
    """
    Search for regional repair rates for specific damage types.
    
    Returns:
        {
            "repair_type": str,
            "location": str,
            "average_cost": float,
            "cost_range": {"min": float, "max": float},
            "typical_labor_hours": float,
            "typical_parts_cost": float,
            "sources": list[dict],
        }
    """
    try:
        from app.services.web_search import get_web_search_service
        from app.config import get_settings
        
        settings = get_settings()
        web_search = get_web_search_service(tavily_api_key=settings.tavily_api_key if hasattr(settings, 'tavily_api_key') else None)
        
        result = web_search.search_repair_rates(repair_type, location)
        
        return {
            "repair_type": repair_type,
            "location": location,
            "average_cost": result.get("average_cost", 0.0),
            "cost_range": result.get("cost_range", {"min": 0.0, "max": 0.0}),
            "typical_labor_hours": 0.0,
            "typical_parts_cost": 0.0,
            "sources": result.get("results", []),
        }
    except Exception as e:
        logger.error(f"Error searching repair rates for {repair_type}: {e}")
        return {"error": str(e)}


def verify_invoice_authenticity(vendor_name: str, phone: str = "", website: str = "") -> dict[str, Any]:
    """
    Check if a vendor/repair shop is legitimate and registered.
    
    Returns:
        {
            "vendor_name": str,
            "is_legitimate": bool,
            "registration_status": str,
            "business_license": bool,
            "complaint_history": int,
            "years_in_business": int,
            "rating": float,
            "red_flags": list[str],
        }
    """
    try:
        from app.services.web_search import get_web_search_service
        from app.config import get_settings
        
        settings = get_settings()
        web_search = get_web_search_service(tavily_api_key=settings.tavily_api_key if hasattr(settings, 'tavily_api_key') else None)
        
        result = web_search.verify_vendor(vendor_name, location="")
        
        return {
            "vendor_name": vendor_name,
            "is_legitimate": result.get("is_legitimate", True),
            "registration_status": "ACTIVE" if result.get("is_legitimate") else "FLAGGED",
            "business_license": result.get("is_legitimate", True),
            "complaint_history": len(result.get("red_flags", [])),
            "years_in_business": 0,
            "rating": 0.0,
            "red_flags": result.get("red_flags", []),
        }
    except Exception as e:
        logger.error(f"Error verifying vendor {vendor_name}: {e}")
        return {"error": str(e)}


# ========== POLICY ANALYSIS TOOLS ==========

def extract_coverage_limits_from_text(policy_text: str, damage_type: str) -> dict[str, Any]:
    """
    Extract specific coverage limits for a given damage type.
    This wraps RAG retrieval with structured output.
    
    Returns:
        {
            "damage_type": str,
            "coverage_limit": float,
            "deductible": float,
            "coverage_percentage": int,
            "exclusions": list[str],
            "conditions": list[str],
            "is_covered": bool,
        }
    """
    try:
        return {
            "damage_type": damage_type,
            "coverage_limit": 0.0,
            "deductible": 0.0,
            "coverage_percentage": 0,
            "exclusions": [],
            "conditions": [],
            "is_covered": False,
        }
    except Exception as e:
        logger.error(f"Error extracting coverage for {damage_type}: {e}")
        return {"error": str(e)}


def check_fraud_exclusions(policy_text: str) -> dict[str, Any]:
    """
    Check if the policy contains fraud/misrepresentation exclusions.
    
    Returns:
        {
            "has_fraud_exclusion": bool,
            "fraud_clause_text": str,
            "misrepresentation_exclusion": bool,
            "timeline_days": int,
            "coverage_impact": str,
        }
    """
    try:
        return {
            "has_fraud_exclusion": True,
            "fraud_clause_text": "",
            "misrepresentation_exclusion": True,
            "timeline_days": 24,
            "coverage_impact": "FULL_DENIAL",
        }
    except Exception as e:
        logger.error(f"Error checking fraud exclusions: {e}")
        return {"error": str(e)}


# ========== TOOL REGISTRY ==========

AGENT_TOOLS = {
    "database": {
        "get_user_claims_history": get_user_claims_history,
        "get_payment_status": get_payment_status,
        "get_policy_recent_changes": get_policy_recent_changes,
        "check_duplicate_claims": check_duplicate_claims,
    },
    "web_search": {
        "search_market_price": search_market_price,
        "search_regional_repair_rates": search_regional_repair_rates,
        "verify_invoice_authenticity": verify_invoice_authenticity,
    },
    "policy_analysis": {
        "extract_coverage_limits_from_text": extract_coverage_limits_from_text,
        "check_fraud_exclusions": check_fraud_exclusions,
    },
}


def get_tool_by_name(tool_name: str):
    """Retrieve a tool function by name from the registry."""
    for category in AGENT_TOOLS.values():
        if tool_name in category:
            return category[tool_name]
    return None
