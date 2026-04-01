"""
Industry configuration - single source for requirements, recommendations, and compliance.
Consolidates data from industry_classifier, playbooks, and business logic.
"""

from typing import Dict, Any, List

from .taxonomy import normalize_industry, INDUSTRIES

# Default config for industries without explicit definitions
_DEFAULT_RECOMMENDATIONS = {
    "required_data": ["business_profile", "products_services"],
    "ai_features": ["general_assistance", "information_providing"],
    "optimization_tips": ["data_quality", "response_accuracy"],
}

_DEFAULT_REQUIREMENTS = {
    "required": {"business_profile": "Basic business information"},
    "optional": {
        "products_services": "Core offerings (can be empty initially)",
        "faqs": "Frequently asked questions",
        "policies": "Business policies and procedures",
        "business_hours": "Business operating hours",
        "ai_settings": "AI configuration settings",
    },
}


# Per-industry recommendations (required_data, optional_data, ai_features, optimization_tips)
INDUSTRY_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {
    "ecommerce": {
        "required_data": ["products"],
        "optional_data": ["product_catalog", "shipping_info", "payment_details"],
        "ai_features": ["product_recommendations", "cart_management", "checkout_assistance"],
        "optimization_tips": ["inventory_tracking", "price_optimization", "customer_analytics"],
    },
    "healthcare": {
        "required_data": ["services_offered", "doctor_info", "appointment_scheduling"],
        "optional_data": ["health_education", "success_rates", "testimonials"],
        "ai_features": ["appointment_booking", "symptom_assessment", "treatment_recommendations"],
        "optimization_tips": ["patient_care_optimization", "compliance_monitoring", "resource_management"],
    },
    "real_estate": {
        "required_data": ["property_listings", "agent_contact", "viewing_schedules"],
        "optional_data": ["market_data", "virtual_tours"],
        "ai_features": ["property_matching", "market_analysis", "viewing_scheduling"],
        "optimization_tips": ["market_analysis", "portfolio_optimization", "client_management"],
    },
    "restaurants": {
        "required_data": ["menu_items", "pricing", "operating_hours"],
        "optional_data": ["reservations", "delivery_options"],
        "ai_features": ["menu_recommendations", "order_optimization", "reservation_management"],
        "optimization_tips": ["menu_optimization", "supply_chain_management", "customer_satisfaction"],
    },
    "education": {
        "required_data": ["courses", "schedules", "enrollment_info"],
        "optional_data": ["instructor_info", "materials"],
        "ai_features": ["course_recommendations", "enrollment_assistance", "schedule_help"],
        "optimization_tips": ["engagement_tracking", "completion_rates"],
    },
    "financial": {
        "required_data": ["products_services", "contact_info"],
        "optional_data": ["rates", "terms", "eligibility"],
        "ai_features": ["product_inquiry", "appointment_booking", "general_assistance"],
        "optimization_tips": ["conversion_tracking", "compliance_monitoring"],
    },
    "travel": {
        "required_data": ["destinations", "pricing", "availability"],
        "optional_data": ["itineraries", "reviews"],
        "ai_features": ["booking_assistance", "recommendations", "itinerary_help"],
        "optimization_tips": ["booking_conversion", "customer_satisfaction"],
    },
    "events": {
        "required_data": ["event_types", "pricing", "availability"],
        "optional_data": ["venue_info", "catering"],
        "ai_features": ["booking_assistance", "inquiry_handling"],
        "optimization_tips": ["conversion_tracking", "capacity_utilization"],
    },
    "logistics": {
        "required_data": ["services", "pricing", "coverage"],
        "optional_data": ["tracking", "sla_info"],
        "ai_features": ["tracking_inquiry", "booking_assistance"],
        "optimization_tips": ["delivery_metrics", "route_optimization"],
    },
    "professional_services": {
        "required_data": ["services", "consultant_info", "availability"],
        "optional_data": ["case_studies", "certifications"],
        "ai_features": ["consultation_booking", "inquiry_handling"],
        "optimization_tips": ["utilization_tracking", "client_retention"],
    },
    "beauty_wellness": {
        "required_data": ["services", "pricing", "operating_hours"],
        "optional_data": ["practitioner_info", "promotions"],
        "ai_features": ["appointment_booking", "service_recommendations"],
        "optimization_tips": ["bookings_optimization", "customer_retention"],
    },
    "telecoms": {
        "required_data": ["plans", "pricing", "coverage"],
        "optional_data": ["support_info", "promotions"],
        "ai_features": ["plan_recommendations", "support_inquiry"],
        "optimization_tips": ["churn_reduction", "upsell_opportunities"],
    },
    "banking": {
        "required_data": ["products_services", "contact_info"],
        "optional_data": ["rates", "terms", "branch_info"],
        "ai_features": ["product_inquiry", "appointment_booking"],
        "optimization_tips": ["compliance_monitoring", "cross_sell"],
    },
    "manufacturing": {
        "required_data": ["products", "capabilities", "contact_info"],
        "optional_data": ["certifications", "lead_times"],
        "ai_features": ["inquiry_handling", "quote_assistance"],
        "optimization_tips": ["lead_conversion", "capacity_utilization"],
    },
    "retail_chains": {
        "required_data": ["locations", "products_services", "operating_hours"],
        "optional_data": ["promotions", "loyalty_programs"],
        "ai_features": ["location_finder", "product_inquiry", "general_assistance"],
        "optimization_tips": ["foot_traffic", "conversion_by_location"],
    },
}


# Per-industry data requirements (for validation)
INDUSTRY_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "ecommerce": {
        "required": {
            "products": {
                "name": "Product name",
                "description": "Product description (50-500 characters)",
                "price": "Price in numeric format",
                "availability": "Stock status (boolean)",
            }
        },
        "optional": {
            "product_catalog": "Product catalog (legacy format)",
            "shipping_info": "Shipping information (can be in policies.shipping_policy)",
            "payment_details": "Payment details (can be in policies.payment_methods)",
            "reviews": "Customer reviews and ratings",
            "promotions": "Current promotions and discounts",
        },
    },
    "healthcare": {
        "required": {
            "services_offered": {
                "consultations": "Available consultation types",
                "treatments": "Treatment procedures offered",
                "specialties": "Medical specialties",
            },
            "doctor_info": {
                "names": "Doctor names and credentials",
                "specialties": "Medical specialties",
                "experience": "Years of experience",
            },
            "appointment_scheduling": {
                "availability": "Available appointment slots",
                "booking_process": "How to book appointments",
                "cancellation_policy": "Cancellation and rescheduling policy",
            },
        },
        "optional": {
            "health_education": "Health education content",
            "success_rates": "Treatment success rates",
            "testimonials": "Patient testimonials",
        },
    },
}

# Compliance flags (for future enforcement)
INDUSTRY_COMPLIANCE: Dict[str, Dict[str, Any]] = {
    "healthcare": {"requires_phi_protection": True, "audit_required": True, "notes": "HIPAA; never provide medical advice"},
    "financial": {"requires_phi_protection": False, "audit_required": True, "notes": "Audit trails; regulated advice"},
    "banking": {"requires_phi_protection": False, "audit_required": True, "notes": "SOX; audit; KYC awareness"},
    "ecommerce": {"requires_phi_protection": False, "audit_required": False, "notes": "PCI-DSS awareness; no card storage"},
    "real_estate": {"requires_phi_protection": False, "audit_required": False, "notes": "Data privacy; fair housing"},
    "restaurants": {"requires_phi_protection": False, "audit_required": False, "notes": "Food safety; dietary restrictions"},
    "education": {"requires_phi_protection": False, "audit_required": False, "notes": "FERPA-like; no grade disclosure"},
    "telecoms": {"requires_phi_protection": False, "audit_required": False, "notes": "Regulated; SLA"},
    "professional_services": {"requires_phi_protection": False, "audit_required": False, "notes": "Licensing; conflict checks"},
}

# Escalation triggers per industry (keywords/signals that warrant escalation)
INDUSTRY_ESCALATION_TRIGGERS: Dict[str, Dict[str, List[str]]] = {
    "ecommerce": {
        "critical": ["fraud", "scam", "stolen", "lawsuit", "police"],
        "high": ["refund", "money back", "terrible", "worst", "complaint", "payment failed"],
        "medium": ["problem", "issue", "wrong", "disappointed", "not working"],
    },
    "healthcare": {
        "critical": ["emergency", "chest pain", "can't breathe", "severe pain", "medical advice", "diagnosis"],
        "high": ["complaint", "dissatisfied", "refund", "lawsuit", "report"],
        "medium": ["billing dispute", "insurance", "waiting", "reschedule"],
    },
    "real_estate": {"critical": ["legal", "contract", "lawsuit"], "high": ["fraud", "scam", "refund"], "medium": ["negotiation", "dispute"]},
    "restaurants": {"critical": ["allergy", "emergency", "food poisoning"], "high": ["complaint", "refund"], "medium": ["wrong order", "reservation"]},
    "education": {"critical": ["legal", "academic dispute"], "high": ["grade", "complaint", "refund"], "medium": ["schedule", "enrollment"]},
    "financial": {"critical": ["fraud", "scam", "stolen"], "high": ["dispute", "refund", "licensed advice"], "medium": ["complaint", "billing"]},
    "travel": {"critical": ["emergency", "stranded"], "high": ["refund", "complaint", "cancel"], "medium": ["change", "delay"]},
    "events": {"critical": ["cancel", "emergency"], "high": ["refund", "complaint"], "medium": ["change", "contract"]},
    "logistics": {"critical": ["lost", "damaged", "claims"], "high": ["refund", "complaint"], "medium": ["delay", "dispute"]},
    "professional_services": {"critical": ["legal advice", "conflict"], "high": ["complaint", "refund"], "medium": ["billing", "dispute"]},
    "beauty_wellness": {"critical": ["medical treatment", "injury"], "high": ["complaint", "refund"], "medium": ["allergy", "reschedule"]},
    "telecoms": {"critical": ["fraud", "unauthorized"], "high": ["billing dispute", "cancel"], "medium": ["network issue", "complaint"]},
    "banking": {"critical": ["fraud", "unauthorized", "stolen"], "high": ["dispute", "refund"], "medium": ["complaint", "billing"]},
    "manufacturing": {"critical": ["contract", "quality dispute"], "high": ["refund", "complaint"], "medium": ["delay", "quote"]},
    "retail_chains": {"critical": ["fraud"], "high": ["refund", "complaint", "complex return"], "medium": ["loyalty", "issue"]},
}

# Recommended actions per industry and severity (for escalation endpoint)
INDUSTRY_ESCALATION_RECOMMENDATIONS: Dict[str, Dict[str, str]] = {
    "ecommerce": {
        "critical": "Connect with payment/security team immediately",
        "high": "Connect with customer relations manager within 1 hour",
        "medium": "Route to support team for same-day resolution",
    },
    "healthcare": {
        "critical": "Immediate escalation to clinician; if emergency, advise caller to call 911",
        "high": "Connect with medical director or practice manager within 1 hour",
        "medium": "Route to front desk or billing for same-day follow-up",
    },
    "real_estate": {
        "critical": "Connect with managing broker or legal immediately",
        "high": "Connect with senior agent within 2 hours",
        "medium": "Route to assigned agent for same-day callback",
    },
    "restaurants": {
        "critical": "Connect with manager immediately; advise medical emergency protocols if allergy",
        "high": "Connect with manager within 30 minutes",
        "medium": "Route to host/manager for same-day resolution",
    },
    "education": {
        "critical": "Connect with academic director immediately",
        "high": "Connect with student services within 2 hours",
        "medium": "Route to enrollment advisor for same-day callback",
    },
    "financial": {
        "critical": "Connect with compliance/fraud team immediately",
        "high": "Connect with relationship manager within 1 hour",
        "medium": "Route to advisor for same-day callback",
    },
    "travel": {
        "critical": "Connect with emergency travel desk immediately",
        "high": "Connect with customer relations within 2 hours",
        "medium": "Route to booking team for same-day resolution",
    },
    "events": {
        "critical": "Connect with event manager immediately",
        "high": "Connect with event coordinator within 2 hours",
        "medium": "Route to sales for same-day callback",
    },
    "logistics": {
        "critical": "Connect with claims team immediately",
        "high": "Connect with customer service lead within 2 hours",
        "medium": "Route to account manager for same-day resolution",
    },
    "professional_services": {
        "critical": "Connect with partner or compliance immediately",
        "high": "Connect with senior consultant within 2 hours",
        "medium": "Route to project lead for same-day callback",
    },
    "beauty_wellness": {
        "critical": "Connect with owner/manager immediately; medical emergency protocols if injury",
        "high": "Connect with manager within 1 hour",
        "medium": "Route to front desk for same-day resolution",
    },
    "telecoms": {
        "critical": "Connect with fraud/security team immediately",
        "high": "Connect with retention/support lead within 1 hour",
        "medium": "Route to technical support for same-day resolution",
    },
    "banking": {
        "critical": "Connect with fraud team immediately",
        "high": "Connect with branch manager or relationship manager within 1 hour",
        "medium": "Route to customer service for same-day callback",
    },
    "manufacturing": {
        "critical": "Connect with sales director or quality lead immediately",
        "high": "Connect with account manager within 2 hours",
        "medium": "Route to sales for same-day quote/callback",
    },
    "retail_chains": {
        "critical": "Connect with store manager or loss prevention immediately",
        "high": "Connect with customer relations within 1 hour",
        "medium": "Route to store for same-day resolution",
    },
}

_DEFAULT_ESCALATION_RECOMMENDATION = "Connect with customer relations manager within 1 hour"


def get_recommendations(industry: str) -> Dict[str, Any]:
    """Get recommendations for an industry. Uses canonical key via taxonomy."""
    canonical = normalize_industry(industry)
    rec = INDUSTRY_RECOMMENDATIONS.get(canonical)
    if rec:
        return rec
    return _DEFAULT_RECOMMENDATIONS.copy()


def get_requirements(industry: str) -> Dict[str, Any]:
    """Get data requirements for an industry. Uses canonical key via taxonomy."""
    canonical = normalize_industry(industry)
    req = INDUSTRY_REQUIREMENTS.get(canonical)
    if req:
        return req
    return _DEFAULT_REQUIREMENTS.copy()


def get_compliance(industry: str) -> Dict[str, Any]:
    """Get compliance flags for an industry."""
    canonical = normalize_industry(industry)
    return INDUSTRY_COMPLIANCE.get(canonical, {"requires_phi_protection": False, "audit_required": False, "notes": ""})


def get_escalation_triggers(industry: str) -> Dict[str, List[str]]:
    """Get escalation trigger keywords per severity for an industry."""
    canonical = normalize_industry(industry)
    return INDUSTRY_ESCALATION_TRIGGERS.get(canonical, {
        "critical": ["fraud", "emergency", "lawsuit"],
        "high": ["refund", "complaint", "terrible"],
        "medium": ["problem", "issue", "disappointed"],
    })


def get_escalation_recommendation(industry: str, severity: str) -> str:
    """Get recommended action for escalation by industry and severity."""
    canonical = normalize_industry(industry)
    recs = INDUSTRY_ESCALATION_RECOMMENDATIONS.get(canonical, {})
    severity_key = severity.lower() if severity else "high"
    return recs.get(severity_key) or recs.get("high") or _DEFAULT_ESCALATION_RECOMMENDATION
