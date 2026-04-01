"""
Payment Handler for Customer AI
Handles payment link creation via backend payment service
"""

import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


def _run_async_safe(coro) -> Any:
    """Run async coroutine from sync context. Works when already inside async event loop (e.g. FastAPI)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(asyncio.run, coro)
        return future.result()


# Backend payment API - URL and token from .env only (no hardcoded URLs)
PAYMENT_SERVICE_URL = (os.getenv('PAYMENT_SERVICE_URL') or '').rstrip('/')
PAYMENT_API_TOKEN = os.getenv('PAYMENT_API_TOKEN', '')


def _default_headers() -> Dict[str, str]:
    """HTTP headers including auth if configured."""
    headers: Dict[str, str] = {'Content-Type': 'application/json'}
    if PAYMENT_API_TOKEN:
        headers['Authorization'] = f'Bearer {PAYMENT_API_TOKEN}'
    return headers


class PaymentHandler:
    """Handles payment link creation via backend payment service"""

    def __init__(self, business_id: str):
        self.business_id = business_id

    def create_payment_link(
        self,
        customer_id: str,
        amount: Optional[float] = None,
        reference: Optional[str] = None,
        currency: str = "NGN",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request a payment link from the backend.

        Args:
            customer_id: Customer identifier
            amount: Optional amount to pay
            reference: Optional reference (order_id, invoice_id, etc.)
            currency: Currency code
            metadata: Optional additional context

        Returns:
            { success, payment_url, error }
        """
        try:
            return _run_async_safe(self._create_payment_link_async(
                customer_id, amount, reference, currency, metadata
            ))
        except Exception as e:
            logger.error(f"Error creating payment link: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def _create_payment_link_async(
        self,
        customer_id: str,
        amount: Optional[float],
        reference: Optional[str],
        currency: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Async implementation"""
        if not PAYMENT_SERVICE_URL:
            return {'success': False, 'error': 'PAYMENT_SERVICE_URL not configured'}
        try:
            payload = {
                "business_id": self.business_id,
                "customer_id": customer_id,
                "currency": currency,
            }
            if amount is not None:
                payload["amount"] = amount
            if reference:
                payload["reference"] = reference
            if metadata:
                payload["metadata"] = metadata

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{PAYMENT_SERVICE_URL}/api/v1/create-payment-link",
                    json=payload,
                    headers=_default_headers(),
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return {
                    'success': data.get('success', True),
                    'payment_url': data.get('payment_url'),
                    'error': data.get('error')
                }
        except httpx.HTTPStatusError as e:
            try:
                err_body = e.response.json()
                error_msg = err_body.get('detail', err_body.get('error', str(e)))
            except Exception:
                error_msg = str(e)
            logger.error(f"Payment service error: {error_msg}")
            return {'success': False, 'error': error_msg}
        except Exception as e:
            logger.error(f"Error creating payment link: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def extract_payment_details(message: str) -> Dict[str, Any]:
        """
        Extract amount and reference from customer message.
        Backend can resolve outstanding balance if not provided.
        Supports NGN (₦, naira) and USD ($, dollars).
        """
        details = {'amount': None, 'reference': None}
        message_lower = message.lower()

        # Amount patterns: NGN first (default currency), then USD
        amount_patterns = [
            r'₦\s*(\d+(?:[.,]\d{2})?)',
            r'(\d+(?:[.,]\d{2})?)\s*(?:naira|ngn)\b',
            r'\$\s*(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*(?:dollars|usd|dollars?)',
            r'(?:pay|amount of)\s*(\d+(?:\.\d{2})?)',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                try:
                    raw = match.group(1).replace(',', '.')
                    details['amount'] = float(raw)
                    break
                except (ValueError, IndexError):
                    pass

        # Reference patterns: order #123, invoice 456
        ref_patterns = [
            r'order\s*#?\s*(\w+)',
            r'invoice\s*#?\s*(\w+)',
            r'bill\s*#?\s*(\w+)',
            r'reference\s*#?\s*(\w+)',
        ]
        for pattern in ref_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                details['reference'] = match.group(1).strip()
                break

        return details


def get_payment_handler(business_id: str) -> PaymentHandler:
    """Factory function"""
    return PaymentHandler(business_id)
