"""
Appointment Booking Handler for Customer AI — DEPRECATED.

This module is no longer used by the LangGraph agent. Appointment availability
and booking are now handled via the backend AI Tools gateway (AI_TOOLS_URL):
tools check_availability and book_appointment in agent_tools.py call the
backend directly. APPOINTMENT_BOOKING_URL and BOOKINGS_API_TOKEN are unused.

Kept for reference or for non-agent use cases only. Do not wire into new code.
"""

import asyncio
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)

_UNSET = object()  # Sentinel for "not yet computed"


def _run_async_safe(coro) -> Any:
    """Run async coroutine from sync context."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(asyncio.run, coro)
        return future.result()


# Backend bookings API - URL and token from .env only (no hardcoded URLs)
BOOKINGS_BASE_URL = (os.getenv('APPOINTMENT_BOOKING_URL') or '').rstrip('/')
BOOKINGS_API_TOKEN = os.getenv('BOOKINGS_API_TOKEN', '')


def _get_backend_business_id(business_id: str) -> Optional[int]:
    """Resolve Customer AI business_id (string) to backend business (integer)."""
    try:
        return int(business_id)
    except (ValueError, TypeError):
        pass
    map_json = os.getenv('BOOKINGS_BUSINESS_ID_MAP', '{}')
    try:
        mapping = json.loads(map_json)
        return mapping.get(business_id)
    except (json.JSONDecodeError, TypeError):
        return None


def _default_headers() -> Dict[str, str]:
    """HTTP headers including auth if configured."""
    headers = {'Content-Type': 'application/json'}
    if BOOKINGS_API_TOKEN:
        headers['Authorization'] = f'Bearer {BOOKINGS_API_TOKEN}'
    return headers


def _ensure_iso_datetime(dt_str: str) -> str:
    """Ensure datetime string is ISO 8601 with timezone (append Z if absent)."""
    s = dt_str.strip()
    if not s:
        return s
    if s[-1] not in ('Z', 'z') and '+' not in s and len(s) > 10:
        return s + 'Z'
    return s


def _parse_time_to_minutes(time_str: str) -> int:
    """Parse HH:MM, HH:MM:SS, or '10am'/'10:30pm' to minutes since midnight."""
    raw = time_str.strip().lower()
    is_pm = 'pm' in raw
    s = raw.replace('am', '').replace('pm', '').strip()
    parts = s.split(':')
    try:
        if len(parts) >= 2:
            h = int(parts[0] or 0)
            m = int((parts[1] or '0').split()[0])
        else:
            h = int(s.split()[0])
            m = 0
    except (ValueError, IndexError, TypeError):
        return 0
    if is_pm and h != 12:
        h += 12
    elif not is_pm and h == 12:
        h = 0
    return h * 60 + m


def _minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to HH:MM:SS."""
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}:00"


class AppointmentBookingHandler:
    """Handles appointment booking via backend Bookings API."""

    def __init__(self, business_id: str):
        self.business_id = business_id
        self._backend_business_id: Any = _UNSET

    def _backend_business(self) -> Optional[int]:
        if self._backend_business_id is _UNSET:
            self._backend_business_id = _get_backend_business_id(self.business_id)
        return self._backend_business_id

    def check_availability(
        self,
        service_id: str,
        date: str,
        duration_minutes: int = 60,
        staff_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check available time slots for a date (sync wrapper)."""
        try:
            return _run_async_safe(self._check_availability_async(
                service_id, date, duration_minutes, staff_id
            ))
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {'success': False, 'error': str(e)}

    async def _check_availability_async(
        self,
        service_id: str,
        date: str,
        duration_minutes: int,
        staff_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Compute available slots using working hours and existing appointments.
        Returns: { success, available_slots: [{"start": "10:00", "end": "11:00"}, ...], error? }
        """
        if not BOOKINGS_BASE_URL:
            return {'success': False, 'error': 'APPOINTMENT_BOOKING_URL not configured'}
        bid = self._backend_business()
        if bid is None:
            return {
                'success': False,
                'error': f'Could not resolve business_id "{self.business_id}" to backend business integer. Set BOOKINGS_BUSINESS_ID_MAP env if using string IDs.'
            }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 1. Get working hours
                wh_resp = await client.get(
                    f"{BOOKINGS_BASE_URL}/api/bookings/working-hours/",
                    headers=_default_headers()
                )
                wh_resp.raise_for_status()
                working_hours = wh_resp.json()

                # 2. Get existing appointments for the date
                appointments_resp = await client.get(
                    f"{BOOKINGS_BASE_URL}/api/bookings/appointments/",
                    params={
                        'start_date': date,
                        'end_date': date,
                    },
                    headers=_default_headers()
                )
                appointments_resp.raise_for_status()
                appointments = appointments_resp.json()

            # 3. Parse date to get day_of_week (0=Monday, 6=Sunday)
            try:
                dt = datetime.strptime(date, '%Y-%m-%d')
                day_of_week = dt.weekday()  # 0=Mon, 6=Sun
            except ValueError:
                return {'success': False, 'error': f'Invalid date format: {date}'}

            # Find working hours for this day (filter by business if present in response)
            day_hours = [
                h for h in working_hours
                if (h.get('business') is None or h.get('business') == bid)
                and h.get('day_of_week') == day_of_week
                and not h.get('is_closed', False)
            ]
            if not day_hours:
                return {
                    'success': True,
                    'available_slots': [],
                    'message': 'We are closed on this day.'
                }

            # Build open ranges (minutes since midnight)
            open_ranges: List[Tuple[int, int]] = []
            for h in day_hours:
                start_min = _parse_time_to_minutes(h.get('start_time', '09:00:00'))
                end_min = _parse_time_to_minutes(h.get('end_time', '17:00:00'))
                open_ranges.append((start_min, end_min))

            # Build booked ranges from appointments (only PENDING/CONFIRMED, same business)
            booked_ranges: List[Tuple[int, int]] = []
            for apt in appointments:
                if apt.get('business') is not None and apt.get('business') != bid:
                    continue
                if apt.get('status') in ('PENDING', 'CONFIRMED'):
                    st = apt.get('start_time') or ''
                    et = apt.get('end_time') or ''
                    if st and et:
                        # Parse ISO datetime - use date part to get time
                        try:
                            start_dt = datetime.fromisoformat(st.replace('Z', '+00:00'))
                            end_dt = datetime.fromisoformat(et.replace('Z', '+00:00'))
                            # Convert to minutes (same calendar day)
                            s_min = start_dt.hour * 60 + start_dt.minute
                            e_min = end_dt.hour * 60 + end_dt.minute
                            booked_ranges.append((s_min, e_min))
                        except (ValueError, TypeError):
                            pass

            # Generate available slots: open intervals minus booked intervals
            slot_duration = duration_minutes
            available: List[Dict[str, str]] = []
            for (open_start, open_end) in open_ranges:
                cursor = open_start
                while cursor + slot_duration <= open_end:
                    slot_end = cursor + slot_duration
                    overlaps = any(
                        not (slot_end <= b_start or cursor >= b_end)
                        for b_start, b_end in booked_ranges
                    )
                    if not overlaps:
                        available.append({
                            'start': _minutes_to_time(cursor),
                            'end': _minutes_to_time(slot_end),
                        })
                    cursor += 30  # 30-min increment for next candidate

            return {
                'success': True,
                'available_slots': available,
            }
        except httpx.HTTPStatusError as e:
            msg = e.response.text
            try:
                msg = e.response.json().get('detail', msg)
            except Exception:
                pass
            logger.error(f"Backend API error checking availability: {e.response.status_code} - {msg}")
            return {'success': False, 'error': msg}
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {'success': False, 'error': str(e)}

    def is_slot_available(
        self,
        date: str,
        start_time: str,
        duration_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Check if a specific slot is available.
        start_time: "10:00" or "10:00:00"
        Returns: { available: bool, suggested_slots?: [...] }
        """
        result = self.check_availability('', date, duration_minutes)
        if not result.get('success'):
            return {'available': False, 'error': result.get('error')}

        slots = result.get('available_slots', [])
        start_min = _parse_time_to_minutes(start_time)

        for slot in slots:
            s_min = _parse_time_to_minutes(slot.get('start', ''))
            if s_min == start_min:
                return {'available': True}

        return {
            'available': False,
            'suggested_slots': slots[:5],
        }

    def book_appointment(
        self,
        customer_id: str,
        customer_name: str,
        customer_contact: str,
        service_id: str,
        service_name: str,
        appointment_datetime: str,
        duration_minutes: int = 60,
        staff_id: Optional[str] = None,
        staff_name: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Book a new appointment (sync wrapper)."""
        try:
            return _run_async_safe(self._book_appointment_async(
                customer_id, customer_name, customer_contact,
                service_id, service_name, appointment_datetime,
                duration_minutes, staff_id, staff_name, notes, metadata
            ))
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return {'success': False, 'error': str(e)}

    async def _book_appointment_async(
        self,
        customer_id: str,
        customer_name: str,
        customer_contact: str,
        service_id: str,
        service_name: str,
        appointment_datetime: str,
        duration_minutes: int,
        staff_id: Optional[str],
        staff_name: Optional[str],
        notes: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create appointment via backend POST /api/bookings/appointments/."""
        if not BOOKINGS_BASE_URL:
            return {'success': False, 'error': 'APPOINTMENT_BOOKING_URL not configured'}
        bid = self._backend_business()
        if bid is None:
            return {
                'success': False,
                'error': f'Could not resolve business_id "{self.business_id}" to backend business integer.'
            }

        try:
            # Parse start datetime and compute end
            dt_str = _ensure_iso_datetime(appointment_datetime)
            try:
                start_dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except ValueError:
                start_dt = datetime.fromisoformat(dt_str)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            start_iso = start_dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
            end_iso = end_dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

            payload = {
                'business': bid,
                'customer_id': customer_id,
                'customer_phone': customer_contact,
                'customer_name': customer_name,
                'service_type': service_name or 'Consultation',
                'start_time': start_iso,
                'end_time': end_iso,
                'notes': notes or '',
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{BOOKINGS_BASE_URL}/api/bookings/appointments/",
                    json=payload,
                    headers=_default_headers()
                )
                response.raise_for_status()
                data = response.json()

            # Normalize to format expected by business_specific_ai
            raw_id = data.get('id')  # Can be None if backend returns {'id': None}
            return {
                'success': True,
                'appointment': {
                    'appointment_id': str(raw_id) if raw_id is not None else '',
                    'id': raw_id,
                    'google_calendar_link': '',  # Backend may provide google_event_id
                    **data,
                }
            }
        except httpx.HTTPStatusError as e:
            msg = e.response.text
            try:
                body = e.response.json()
                msg = body.get('error', body.get('detail', msg))
            except Exception:
                pass
            logger.error(f"Backend API error booking: {e.response.status_code} - {msg}")
            return {'success': False, 'error': msg}
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return {'success': False, 'error': str(e)}

    def extract_booking_details(self, message: str, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract booking details from customer message and context."""
        details = {
            'service_id': None,
            'service_name': None,
            'date': None,
            'time': None,
            'duration_minutes': 60,
            'customer_name': conversation_context.get('customer_name'),
            'customer_contact': conversation_context.get('customer_contact'),
            'notes': None
        }

        message_lower = message.lower()
        business_data = conversation_context.get('business_data', {})

        if 'products_services' in business_data:
            services = business_data.get('products_services', [])
        else:
            products = business_data.get('products', [])
            services_list = business_data.get('services', [])
            services = products + services_list

        for service in services:
            service_name = service.get('name', '').lower()
            if service_name in message_lower:
                details['service_name'] = service.get('name')
                details['service_id'] = service.get('service_id') or service.get('id', f"srv_{service.get('name', '').replace(' ', '_').lower()}")
                break

        if not details['service_name']:
            service_keywords = {
                'consultation': 'Consultation',
                'appointment': 'Appointment',
                'session': 'Session',
                'treatment': 'Treatment',
                'therapy': 'Therapy'
            }
            for keyword, default_name in service_keywords.items():
                if keyword in message_lower:
                    details['service_name'] = default_name
                    details['service_id'] = f"srv_{keyword}"
                    break

        if 'today' in message_lower:
            details['date'] = datetime.now().strftime('%Y-%m-%d')
        elif 'tomorrow' in message_lower:
            details['date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'next week' in message_lower:
            details['date'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        elif 'monday' in message_lower or 'mon' in message_lower:
            today = datetime.now()
            days_until = (7 - today.weekday()) % 7 or 7
            details['date'] = (today + timedelta(days=days_until)).strftime('%Y-%m-%d')
        elif 'tuesday' in message_lower or 'tue' in message_lower:
            today = datetime.now()
            days_until = (8 - today.weekday()) % 7 or 7
            details['date'] = (today + timedelta(days=days_until)).strftime('%Y-%m-%d')

        date_pattern = r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b'
        date_match = re.search(date_pattern, message)
        if date_match:
            y, m, d = date_match.groups()
            details['date'] = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

        time_pattern = r'\b(\d{1,2}):?(\d{2})?\s*(am|pm|AM|PM)\b'
        time_match = re.search(time_pattern, message)
        if time_match:
            details['time'] = time_match.group(0).strip()

        time_24_pattern = r'\b([01]?\d|2[0-3]):([0-5]\d)\b'
        time_24_match = re.search(time_24_pattern, message)
        if time_24_match and not details.get('time'):
            h, m = time_24_match.groups()
            details['time'] = f"{h}:{m}"

        name_pattern = r'(?:my name is|i am|i\'m|call me)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)'
        name_match = re.search(name_pattern, message, re.IGNORECASE)
        if name_match:
            details['customer_name'] = name_match.group(1).title()

        phone_pattern = r'(\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
        phone_match = re.search(phone_pattern, message)
        if phone_match:
            details['customer_contact'] = phone_match.group(1)

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, message)
        if email_match:
            details['customer_contact'] = email_match.group(0)

        details['is_complete'] = all([
            details['service_id'] or details['service_name'],
            details['date'],
            details['time'],
            details['customer_name'] or details.get('customer_id'),
            details['customer_contact']
        ])
        return details


def get_appointment_booking_handler(business_id: str) -> AppointmentBookingHandler:
    return AppointmentBookingHandler(business_id)
