"""
LangGraph agent tools.
Each tool wraps an existing handler (knowledge base, booking, payment) so
the LLM can decide when to call them during the agent loop.
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

from langchain_core.tools import tool

from .knowledge_base import KnowledgeBaseManager
from .payment_handler import PaymentHandler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Factory: build the tool list for a specific business at runtime.
# We need closures over the business-specific handlers and data.
# ---------------------------------------------------------------------------

def build_tools_for_business(
    business_id: str,
    business_data: Dict[str, Any],
    knowledge_base: KnowledgeBaseManager,
    payment_handler: PaymentHandler,
) -> tuple:
    """Return (tools, product_media_ref) for one business.

    product_media_ref is a mutable list. When product_search resolves a
    product with an image_url, it appends {"name": ..., "image_url": ...}.
    The caller must clear this list before each agent invocation and read
    it afterwards to extract the latest product image for the response.
    """
    # Mutable capture — shared between the tool closure and the caller.
    # Reset this list before every invoke_agent call.
    _product_media: List[Dict[str, Any]] = []

    tools_url = (os.getenv("AI_TOOLS_URL") or "").strip()
    tools_api_key = (os.getenv("AI_SERVICE_API_KEY") or "").strip()
    backend_timeout_s = float(os.getenv("AI_TOOLS_TIMEOUT_S", "15"))

    # Validate tools_url at build time to catch SSRF-prone configurations early.
    _PRIVATE_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    if tools_url:
        _parsed = urlparse(tools_url)
        _host = (_parsed.hostname or "").lower()
        if _host in _PRIVATE_HOSTS or _host.startswith("169.254") or _host.startswith("10.") or _host == "":
            logger.warning(
                f"AI_TOOLS_URL points to a private/loopback host ({_host}). "
                "This is only acceptable in local development."
            )

    def _call_backend_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not tools_url:
            raise RuntimeError("AI_TOOLS_URL is not set")
        if not tools_api_key:
            raise RuntimeError("AI_SERVICE_API_KEY is not set")

        import httpx

        payload = {"business_id": str(business_id), "tool": tool_name, "params": params or {}}
        headers = {"X-API-Key": tools_api_key}
        resp = httpx.post(tools_url, json=payload, headers=headers, timeout=backend_timeout_s)
        try:
            data = resp.json()
        except Exception:
            data = {"success": False, "error": "invalid_json", "message": resp.text}
        if resp.status_code >= 400:
            data.setdefault("success", False)
            data.setdefault("error", f"http_{resp.status_code}")
        return data

    # ── RAG retrieval ────────────────────────────────────────────────────
    @tool
    def search_knowledge(query: str) -> str:
        """Search the business knowledge base (products, services, FAQs,
        policies, hours) for information relevant to the customer query.
        Call this whenever you need business-specific facts you don't
        already have in context."""
        try:
            try:
                threshold = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.4"))
            except ValueError:
                threshold = 0.4
            results = knowledge_base.retrieve_relevant_knowledge(
                business_id=business_id,
                query=query,
                n_results=5,
            )
            if not results.get("success") or not results.get("documents"):
                return "No relevant information found in the knowledge base."
            docs = results["documents"]
            parts = []
            for doc in docs:
                if doc.get("relevance_score", 0) > threshold:
                    parts.append(doc["content"])
            return "\n\n".join(parts) if parts else "No highly relevant results."
        except Exception as exc:
            logger.error(f"search_knowledge error: {exc}")
            return f"Knowledge search failed: {exc}"

    # ── Backend tool gateway: products ───────────────────────────────────
    @tool
    def product_search(query: str, category: str = "", max_results: int = 5) -> str:
        """Search products by name/description/SKU via backend.
        Parameters:
        - query (required)
        - category (optional)
        - max_results (optional, 1-50; default 5)
        """
        try:
            params: Dict[str, Any] = {"query": query, "max_results": max_results}
            if category:
                params["category"] = category
            result = _call_backend_tool("product_search", params)
            if not result.get("success", True):
                msg = result.get("message") or result.get("error") or "unknown error"
                return f"Product search failed: {msg}"

            data = result.get("data", result)
            products = data.get("products") if isinstance(data, dict) else None
            if not products and isinstance(data, list):
                products = data
            if not products:
                return f"No products found for '{query}'."

            lines: List[str] = []
            for p in products[: max(1, min(int(max_results), 50))]:
                if not isinstance(p, dict):
                    continue
                name = p.get("name") or "Unknown"
                pid = p.get("id") or p.get("product_id")
                price = p.get("price")
                currency = p.get("currency") or (business_data.get("payment_details", {}) or {}).get("currency") or "NGN"
                desc = p.get("description") or ""
                sku = p.get("sku") or ""
                image_url = p.get("image_url") or p.get("image") or ""
                line = f"{name}"
                if pid is not None:
                    line += f" (id={pid})"
                if sku:
                    line += f" sku={sku}"
                if price is not None:
                    line += f" — {currency} {price}"
                if desc:
                    line += f" — {desc}"
                lines.append(line)
                # Capture the first product that has an image for the API response
                if image_url and not _product_media:
                    _product_media.append({"name": name, "image_url": image_url})
            return "\n".join(lines) if lines else f"No products found for '{query}'."
        except Exception as exc:
            logger.error(f"product_search error: {exc}")
            return f"Product search failed: {exc}"

    @tool
    def get_product_by_id(product_id: int) -> str:
        """Get full details for a specific product by internal ID (backend)."""
        try:
            result = _call_backend_tool("get_product_by_id", {"product_id": int(product_id)})
            if not result.get("success", True):
                msg = result.get("message") or result.get("error") or "unknown error"
                return f"Get product failed: {msg}"

            data = result.get("data", result)
            product = data.get("product") if isinstance(data, dict) else data
            if not isinstance(product, dict):
                return json.dumps(data, ensure_ascii=False)

            currency = product.get("currency") or (business_data.get("payment_details", {}) or {}).get("currency") or "NGN"
            parts = [
                f"Name: {product.get('name') or ''}".strip(),
                f"ID: {product.get('id') or product.get('product_id') or product_id}",
            ]
            if product.get("sku"):
                parts.append(f"SKU: {product.get('sku')}")
            if product.get("price") is not None:
                parts.append(f"Price: {currency} {product.get('price')}")
            if product.get("description"):
                parts.append(f"Description: {product.get('description')}")
            if product.get("category"):
                parts.append(f"Category: {product.get('category')}")
            if product.get("availability") is not None:
                parts.append(f"Availability: {product.get('availability')}")
            return "\n".join([p for p in parts if p])
        except Exception as exc:
            logger.error(f"get_product_by_id error: {exc}")
            return f"Get product failed: {exc}"

    # ── Order total ──────────────────────────────────────────────────────
    @tool
    def calculate_order_total(items_json: str) -> str:
        """Calculate the total cost for an order.  `items_json` is a JSON
        array like [{"name": "Sausage roll", "quantity": 2}].
        Returns an itemised breakdown with a total.
        Best for small baskets (each item triggers a backend product search; large lists may be slow)."""
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            return "Could not parse items. Provide a JSON array of {name, quantity}."
        lines = []
        total = 0.0
        currency = (business_data.get("payment_details", {}) or {}).get("currency") or "NGN"
        for item in items:
            name = item.get("name", "")
            qty = int(item.get("quantity", 1))
            # Prefer live pricing via backend tool
            try:
                res = _call_backend_tool("product_search", {"query": name, "max_results": 1})
                data = res.get("data", res)
                products = data.get("products") if isinstance(data, dict) else (data if isinstance(data, list) else [])
                match = products[0] if products else None
            except Exception:
                match = None

            if not isinstance(match, dict) or match.get("price") is None:
                lines.append(f"{name}: price not found")
                continue

            price = float(match.get("price", 0))
            subtotal = price * qty
            total += subtotal
            display_name = match.get("name") or name
            lines.append(f"{qty}x {display_name}: {currency} {price:,.0f} each = {currency} {subtotal:,.0f}")
        lines.append(f"TOTAL: {currency} {total:,.0f}")
        return "\n".join(lines)

    # ── Backend tool gateway: appointments ───────────────────────────────
    @tool
    def check_availability(date: str, service_id: str = "") -> str:
        """Check available appointment slots for a given date (YYYY-MM-DD).
        Optionally filter by service_id."""
        try:
            params: Dict[str, Any] = {"date": date}
            if service_id:
                params["service_id"] = service_id
            result = _call_backend_tool("check_availability", params)
            if not result.get("success", True):
                msg = result.get("message") or result.get("error") or "unknown error"
                return f"Could not check availability: {msg}"

            data = result.get("data", result)
            slots = None
            if isinstance(data, dict):
                slots = data.get("available_slots") or data.get("slots")
            if slots is None and isinstance(data, list):
                slots = data
            if not slots:
                return f"No available slots on {date}."
            slot_strs = []
            for s in slots:
                if isinstance(s, dict) and s.get("start") and s.get("end"):
                    slot_strs.append(f"{s['start']} – {s['end']}")
                else:
                    slot_strs.append(str(s))
            return f"Available slots on {date}: " + ", ".join(slot_strs)
        except Exception as exc:
            logger.error(f"check_availability error: {exc}")
            return f"Availability check failed: {exc}"

    @tool
    def book_appointment(
        customer_phone: str,
        service_type: str,
        date: str,
        time: str,
        customer_name: str = "",
        notes: str = "",
    ) -> str:
        """Create a pending appointment booking via backend.
        Parameters:
        - customer_phone (required): WhatsApp/Phone number (e.g. +2348012345678)
        - service_type (required): Name of the service
        - date (required): YYYY-MM-DD
        - time (required): HH:MM (24-hour)
        - customer_name (optional)
        - notes (optional)
        """
        try:
            params: Dict[str, Any] = {
                "customer_phone": customer_phone,
                "service_type": service_type,
                "date": date,
                "time": time,
            }
            if customer_name:
                params["customer_name"] = customer_name
            if notes:
                params["notes"] = notes
            result = _call_backend_tool("book_appointment", params)
            if not result.get("success", True):
                msg = result.get("message") or result.get("error") or "unknown error"
                return f"Booking failed: {msg}"
            return f"Appointment request submitted for {service_type} on {date} at {time}. Status: pending confirmation."
        except Exception as exc:
            logger.error(f"book_appointment error: {exc}")
            return f"Booking failed: {exc}"

    @tool
    def get_business_hours() -> str:
        """Retrieve business hours for the week via backend."""
        try:
            result = _call_backend_tool("get_business_hours", {})
            if not result.get("success", True):
                msg = result.get("message") or result.get("error") or "unknown error"
                return f"Could not fetch business hours: {msg}"
            data = result.get("data", result)
            if isinstance(data, dict) and data.get("business_hours"):
                data = data["business_hours"]
            return json.dumps(data, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"get_business_hours error: {exc}")
            return f"Could not fetch business hours: {exc}"

    # ── Payment link (Paystack via AI Tools gateway) ─────────────────────
    @tool
    def initialize_payment(
        email: str,
        amount: float,
        description: str = "",
    ) -> str:
        """Generate a Paystack payment link for the customer.
        Call this ONLY when the customer has confirmed their purchase and
        has provided their email address.
        Parameters:
        - email (required): Customer email address (used for Paystack receipt)
        - amount (required): Amount in NGN (naira), e.g. 15000 for ₦15,000
        - description (optional): What the customer is paying for,
          e.g. "Wireless Headphones × 1"
        """
        try:
            params: Dict[str, Any] = {
                "email": email,
                "amount": float(amount),
            }
            if description:
                params["description"] = description

            # Inject vendor_id from business data if configured (enables auto payouts)
            _pay = business_data.get("payment_details") or {}
            _vendor_id = (
                business_data.get("vendor_id")
                or (_pay.get("vendor_id") if isinstance(_pay, dict) else None)
            )
            if _vendor_id:
                try:
                    params["vendor_id"] = int(_vendor_id)
                except (ValueError, TypeError):
                    pass

            result = _call_backend_tool("initialize_payment", params)
            if not result.get("success"):
                msg = result.get("message") or result.get("error") or "unknown error"
                return f"Could not create payment link: {msg}"

            # The backend returns a pre-formatted message_for_customer that
            # already contains the payment URL, reference, and instructions.
            customer_msg = result.get("message_for_customer")
            if customer_msg:
                return customer_msg

            # Fallback if backend omits message_for_customer
            return "Your payment link has been generated. Please check for the link to complete your payment."
        except Exception as exc:
            logger.error(f"initialize_payment error: {exc}")
            return f"Payment initialization failed: {exc}"

    # Allow backend to enable/disable specific tools per business.
    enabled = business_data.get("ai_settings", {}) if isinstance(business_data.get("ai_settings", {}), dict) else {}
    enabled_tools = enabled.get("enable_tools")
    if not isinstance(enabled_tools, list):
        enabled_tools = []
    enabled_tools = [str(t) for t in enabled_tools]

    always_on = [search_knowledge, calculate_order_total, initialize_payment]
    optional_map = {
        "product_search": product_search,
        "get_product_by_id": get_product_by_id,
        "check_availability": check_availability,
        "book_appointment": book_appointment,
        "get_business_hours": get_business_hours,
    }

    selected_optional = []
    if enabled_tools:
        for tname, fn in optional_map.items():
            if tname in enabled_tools:
                selected_optional.append(fn)
    else:
        selected_optional = list(optional_map.values())

    return always_on + selected_optional, _product_media
