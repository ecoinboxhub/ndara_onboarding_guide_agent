"""
Business Intelligence Orchestrator
Main coordinator for Business Owner AI system
"""

import logging
import re
import os
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx

from .prompts import get_prompts
from .sales_analyzer import get_sales_analyzer
from .customer_segmentation import get_customer_segmentation
from .competitive_intelligence import get_competitive_intelligence
from .inventory_predictor import get_inventory_predictor
from .template_optimizer import get_template_optimizer
from .nl_inventory import get_nl_inventory
from .broadcast_composer import get_broadcast_composer
from ..services.openai_service import get_openai_service

logger = logging.getLogger(__name__)

# Appointment booking service URL
APPOINTMENT_BOOKING_URL = os.getenv(
    'APPOINTMENT_BOOKING_URL',
    'http://localhost:8006'
)


class BusinessIntelligence:
    """Main orchestrator for Business Owner AI"""
    
    def __init__(self, business_id: str, industry: str):
        self.business_id = business_id
        self.industry = industry
        self.prompts = get_prompts()
        
        # Initialize AI modules
        self.sales_analyzer = get_sales_analyzer(business_id)
        self.customer_segmentation = get_customer_segmentation(business_id)
        self.competitive_intelligence = get_competitive_intelligence(business_id, industry)
        self.inventory_predictor = get_inventory_predictor(business_id)
        self.template_optimizer = get_template_optimizer(business_id)
        self.nl_inventory = get_nl_inventory(business_id)
        self.broadcast_composer = get_broadcast_composer(business_id)
        
        # Initialize OpenAI service for conversational responses
        self.openai_service = get_openai_service()
        
        # Invoice generation moved to separate service (invoice_generator)
        # Can be called via HTTP API if needed
    
    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process business owner query using appropriate AI module"""
        try:
            # Classify query intent
            intent = self._classify_query_intent(query)
            
            # Route to appropriate handler
            if intent == 'sales_analysis':
                return self._handle_sales_query(query, context)
            elif intent == 'customer_segmentation':
                return self._handle_segmentation_query(query, context)
            elif intent == 'inventory':
                return self._handle_inventory_query(query, context)
            elif intent == 'invoice':
                return self._handle_invoice_query(query, context)
            elif intent == 'appointment':
                return await self._handle_appointment_query(query, context)
            elif intent == 'broadcast':
                return self._handle_broadcast_query(query, context)
            else:
                return self._handle_general_query(query, context)
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }
    
    def _classify_query_intent(self, query: str) -> str:
        """Classify business owner query intent"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['sales', 'revenue', 'performance']):
            return 'sales_analysis'
        elif any(word in query_lower for word in ['segment', 'customer group', 'target']):
            return 'customer_segmentation'
        elif any(word in query_lower for word in ['inventory', 'stock', 'restock']):
            return 'inventory'
        elif any(word in query_lower for word in ['invoice', 'bill', 'receipt', 'find invoice', 'show invoice', 'unpaid invoice', 'overdue invoice']):
            return 'invoice'
        elif any(word in query_lower for word in ['appointment', 'booking', 'schedule', 'reschedule', 'cancel appointment', 'my appointments', 'show appointments', 'do i have']):
            return 'appointment'
        elif any(word in query_lower for word in ['broadcast', 'message', 'announce']):
            return 'broadcast'
        else:
            return 'general'
    
    def _handle_sales_query(self, query, context) -> Dict[str, Any]:
        """Handle sales-related queries"""
        conversations = context.get('conversations', [])
        sales_data = context.get('sales_data', [])
        
        analysis = self.sales_analyzer.analyze_sales_performance(conversations, sales_data)
        
        return {
            'success': True,
            'intent': 'sales_analysis',
            'analysis': analysis,
            'query': query
        }
    
    def _handle_segmentation_query(self, query, context) -> Dict[str, Any]:
        """Handle customer segmentation queries"""
        customer_data = context.get('customer_data', [])
        method = context.get('method', 'behavior')
        
        segmentation = self.customer_segmentation.segment_customers(customer_data, method)
        
        return {
            'success': True,
            'intent': 'customer_segmentation',
            'segmentation': segmentation,
            'query': query
        }
    
    def _handle_inventory_query(self, query, context) -> Dict[str, Any]:
        """
        Handle inventory retrieval/search queries using natural language processing
        
        Inventory management operations are handled automatically by backend when sales close or stock changes.
        This method helps business owners search and retrieve inventory information.
        """
        try:
            # Parse natural language query to extract search criteria
            parsed_query = self._parse_inventory_query(query)
            
            # Extract search filters
            search_filters = parsed_query.get('filters', {})
            
            # Generate guidance for backend to execute the search
            guidance = self._generate_inventory_search_guidance(parsed_query)
            
            # Optional: Include demand prediction if requested
            if context.get('predict_demand'):
                conversations = context.get('conversations', [])
                prediction = self.inventory_predictor.predict_demand(conversations)
                parsed_query['prediction'] = prediction
            
            return {
                'success': True,
                'intent': 'inventory_retrieval',
                'parsed_query': parsed_query,
                'search_filters': search_filters,
                'guidance': guidance,
                'query': query,
                'message': f"I'll help you {parsed_query.get('action', 'search')} inventory. {guidance}"
            }
        except Exception as e:
            logger.error(f"Error handling inventory query: {str(e)}")
            return {
                'success': False,
                'intent': 'inventory_retrieval',
                'error': str(e),
            'query': query
        }
    
    def _handle_invoice_query(self, query, context) -> Dict[str, Any]:
        """
        Handle invoice retrieval/search queries using natural language processing
        
        Invoice generation is handled automatically by backend when sales close.
        This method helps business owners search and retrieve invoices.
        """
        try:
            # Parse natural language query to extract search criteria
            parsed_query = self._parse_invoice_query(query)
            
            # Extract search filters
            search_filters = parsed_query.get('filters', {})
            
            # Generate guidance for backend to execute the search
            guidance = self._generate_invoice_search_guidance(parsed_query)
            
            return {
                'success': True,
                'intent': 'invoice_retrieval',
                'parsed_query': parsed_query,
                'search_filters': search_filters,
                'guidance': guidance,
                'query': query,
                'message': f"I'll help you {parsed_query.get('action', 'search')} invoices. {guidance}"
            }
        except Exception as e:
            logger.error(f"Error handling invoice query: {str(e)}")
            return {
                'success': False,
                'intent': 'invoice_retrieval',
                'error': str(e),
            'query': query
        }
    
    def _parse_invoice_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language invoice query to extract search criteria"""
        query_lower = query.lower()
        
        parsed = {
            'action': 'search',  # search, find, show, list
            'filters': {},
            'sort_by': None,
            'limit': None
        }
        
        # Detect action
        if 'find' in query_lower or 'get' in query_lower:
            parsed['action'] = 'find'
        elif 'show' in query_lower or 'list' in query_lower or 'display' in query_lower:
            parsed['action'] = 'list'
        
        # Extract invoice number (if specified)
        invoice_num_match = re.search(r'inv[-\s]?(\d{8}[-\s]?\d+)', query_lower)
        if invoice_num_match:
            parsed['filters']['invoice_number'] = invoice_num_match.group(0).upper().replace(' ', '-')
        
        # Extract payment status
        if any(word in query_lower for word in ['unpaid', 'not paid', 'outstanding', 'pending']):
            parsed['filters']['payment_status'] = 'pending'
        elif any(word in query_lower for word in ['paid', 'completed']):
            parsed['filters']['payment_status'] = 'paid'
        elif any(word in query_lower for word in ['overdue', 'past due', 'late']):
            parsed['filters']['overdue'] = True
        elif 'refund' in query_lower:
            parsed['filters']['payment_status'] = 'refunded'
        
        # Extract date range
        if 'today' in query_lower:
            parsed['filters']['date_range'] = 'today'
        elif 'yesterday' in query_lower:
            parsed['filters']['date_range'] = 'yesterday'
        elif 'last week' in query_lower:
            parsed['filters']['date_range'] = 'last_7_days'
        elif 'last month' in query_lower or 'past month' in query_lower:
            parsed['filters']['date_range'] = 'last_30_days'
        elif 'this month' in query_lower:
            parsed['filters']['date_range'] = 'this_month'
        elif 'this year' in query_lower:
            parsed['filters']['date_range'] = 'this_year'
        
        # Extract customer name (simple extraction - can be enhanced with NLP)
        # Look for patterns like "for customer X" or "customer X"
        # Use case-insensitive matching to handle any capitalization
        customer_match = re.search(r'(?:for|customer|client)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)', query, re.IGNORECASE)
        if customer_match:
            # Title case the extracted name for consistency
            parsed['filters']['customer_name'] = customer_match.group(1).title()
        
        # Extract amount range
        amount_match = re.search(r'(?:over|above|more than|greater than)\s*([₦$]?)(\d+(?:[.,]\d+)?)', query_lower)
        if amount_match:
            parsed['filters']['amount_min'] = float(amount_match.group(2).replace(',', ''))
        
        amount_match = re.search(r'(?:under|below|less than|under)\s*([₦$]?)(\d+(?:[.,]\d+)?)', query_lower)
        if amount_match:
            parsed['filters']['amount_max'] = float(amount_match.group(2).replace(',', ''))
        
        # Extract sort preferences
        if 'latest' in query_lower or 'recent' in query_lower or 'newest' in query_lower:
            parsed['sort_by'] = 'date_desc'
        elif 'oldest' in query_lower:
            parsed['sort_by'] = 'date_asc'
        elif 'highest' in query_lower or 'largest' in query_lower:
            parsed['sort_by'] = 'amount_desc'
        elif 'lowest' in query_lower or 'smallest' in query_lower:
            parsed['sort_by'] = 'amount_asc'
        
        # Extract limit
        limit_match = re.search(r'(?:first|top|last)\s*(\d+)', query_lower)
        if limit_match:
            parsed['limit'] = int(limit_match.group(1))
        elif 'all' in query_lower:
            parsed['limit'] = None  # No limit
        
        return parsed
    
    def _generate_invoice_search_guidance(self, parsed_query: Dict[str, Any]) -> str:
        """Generate guidance for backend to execute invoice search"""
        filters = parsed_query.get('filters', {})
        action = parsed_query.get('action', 'search')
        
        guidance_parts = []
        
        if action == 'find' and filters.get('invoice_number'):
            guidance_parts.append(f"Search for invoice with number: {filters['invoice_number']}")
        else:
            guidance_parts.append(f"Retrieve invoices")
        
        if filters.get('payment_status'):
            status = filters['payment_status'].upper()
            guidance_parts.append(f"with payment status: {status}")
        
        if filters.get('overdue'):
            guidance_parts.append("that are overdue (past due date)")
        
        if filters.get('date_range'):
            date_map = {
                'today': 'created today',
                'yesterday': 'created yesterday',
                'last_7_days': 'created in the last 7 days',
                'last_30_days': 'created in the last 30 days',
                'this_month': 'created this month',
                'this_year': 'created this year'
            }
            guidance_parts.append(date_map.get(filters['date_range'], filters['date_range']))
        
        if filters.get('customer_name'):
            guidance_parts.append(f"for customer: {filters['customer_name']}")
        
        if filters.get('amount_min'):
            guidance_parts.append(f"with amount >= ₦{filters['amount_min']:,.2f}")
        
        if filters.get('amount_max'):
            guidance_parts.append(f"with amount <= ₦{filters['amount_max']:,.2f}")
        
        if parsed_query.get('sort_by'):
            sort_map = {
                'date_desc': 'sorted by date (newest first)',
                'date_asc': 'sorted by date (oldest first)',
                'amount_desc': 'sorted by amount (highest first)',
                'amount_asc': 'sorted by amount (lowest first)'
            }
            guidance_parts.append(sort_map.get(parsed_query['sort_by'], ''))
        
        if parsed_query.get('limit'):
            guidance_parts.append(f"limit results to {parsed_query['limit']} invoices")
        
        return ". ".join(guidance_parts) + "." if guidance_parts else "Retrieve all invoices."
    
    def _parse_inventory_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language inventory query to extract search criteria"""
        query_lower = query.lower()
        
        parsed = {
            'action': 'search',  # search, find, show, list
            'filters': {},
            'sort_by': None,
            'limit': None
        }
        
        # Detect action
        if 'find' in query_lower or 'get' in query_lower:
            parsed['action'] = 'find'
        elif 'show' in query_lower or 'list' in query_lower or 'display' in query_lower:
            parsed['action'] = 'list'
        
        # Extract product/service name or ID
        product_match = re.search(r'(?:product|item|service)\s+([A-Za-z0-9\s-]+)', query_lower)
        if product_match:
            parsed['filters']['product_name'] = product_match.group(1).strip()
        
        # Extract stock level filters
        if any(word in query_lower for word in ['low stock', 'running low', 'low inventory']):
            parsed['filters']['stock_level'] = 'low'
        elif any(word in query_lower for word in ['out of stock', 'no stock', 'zero stock']):
            parsed['filters']['stock_level'] = 'zero'
        elif any(word in query_lower for word in ['high stock', 'overstocked', 'excess stock']):
            parsed['filters']['stock_level'] = 'high'
        
        # Extract category
        categories = ['electronics', 'clothing', 'food', 'furniture', 'accessories', 'beauty', 'healthcare', 'services']
        for cat in categories:
            if cat in query_lower:
                parsed['filters']['category'] = cat
                break
        
        # Extract price range
        price_match = re.search(r'(?:over|above|more than|greater than)\s*([₦$]?)(\d+(?:[.,]\d+)?)', query_lower)
        if price_match:
            parsed['filters']['price_min'] = float(price_match.group(2).replace(',', ''))
        
        price_match = re.search(r'(?:under|below|less than)\s*([₦$]?)(\d+(?:[.,]\d+)?)', query_lower)
        if price_match:
            parsed['filters']['price_max'] = float(price_match.group(2).replace(',', ''))
        
        # Extract date range for service availability
        if 'today' in query_lower:
            parsed['filters']['date_range'] = 'today'
        elif 'tomorrow' in query_lower:
            parsed['filters']['date_range'] = 'tomorrow'
        elif 'next week' in query_lower:
            parsed['filters']['date_range'] = 'next_7_days'
        elif 'this week' in query_lower:
            parsed['filters']['date_range'] = 'this_week'
        
        # Extract staff/service provider for service inventory
        # Use case-insensitive matching to handle any capitalization
        staff_match = re.search(r'(?:staff|provider|therapist|doctor|instructor)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)', query, re.IGNORECASE)
        if staff_match:
            # Title case the extracted name for consistency
            parsed['filters']['staff_name'] = staff_match.group(1).title()
        
        # Extract resource type for service inventory
        if any(word in query_lower for word in ['room', 'facility', 'space']):
            parsed['filters']['resource_type'] = 'room'
        elif any(word in query_lower for word in ['equipment', 'tool', 'machine']):
            parsed['filters']['resource_type'] = 'equipment'
        
        # Extract sort preferences
        if 'most popular' in query_lower or 'best selling' in query_lower:
            parsed['sort_by'] = 'sales_desc'
        elif 'least popular' in query_lower:
            parsed['sort_by'] = 'sales_asc'
        elif 'highest price' in query_lower or 'most expensive' in query_lower:
            parsed['sort_by'] = 'price_desc'
        elif 'lowest price' in query_lower or 'cheapest' in query_lower:
            parsed['sort_by'] = 'price_asc'
        elif 'newest' in query_lower or 'latest' in query_lower:
            parsed['sort_by'] = 'date_desc'
        elif 'oldest' in query_lower:
            parsed['sort_by'] = 'date_asc'
        
        # Extract limit
        limit_match = re.search(r'(?:first|top|last)\s*(\d+)', query_lower)
        if limit_match:
            parsed['limit'] = int(limit_match.group(1))
        elif 'all' in query_lower:
            parsed['limit'] = None  # No limit
        
        return parsed
    
    def _generate_inventory_search_guidance(self, parsed_query: Dict[str, Any]) -> str:
        """Generate guidance for backend to execute inventory search"""
        filters = parsed_query.get('filters', {})
        action = parsed_query.get('action', 'search')
        
        guidance_parts = []
        
        if action == 'find' and filters.get('product_name'):
            guidance_parts.append(f"Search for inventory item: {filters['product_name']}")
        else:
            guidance_parts.append(f"Retrieve inventory items")
        
        if filters.get('stock_level'):
            level_map = {
                'low': 'with low stock (below reorder point)',
                'zero': 'that are out of stock',
                'high': 'with high stock (above reorder point)'
            }
            guidance_parts.append(level_map.get(filters['stock_level'], ''))
        
        if filters.get('category'):
            guidance_parts.append(f"in category: {filters['category']}")
        
        if filters.get('price_min'):
            guidance_parts.append(f"with price >= ₦{filters['price_min']:,.2f}")
        
        if filters.get('price_max'):
            guidance_parts.append(f"with price <= ₦{filters['price_max']:,.2f}")
        
        if filters.get('date_range'):
            date_map = {
                'today': 'available today',
                'tomorrow': 'available tomorrow',
                'next_7_days': 'available in the next 7 days',
                'this_week': 'available this week'
            }
            guidance_parts.append(date_map.get(filters['date_range'], filters['date_range']))
        
        if filters.get('staff_name'):
            guidance_parts.append(f"for staff/provider: {filters['staff_name']}")
        
        if filters.get('resource_type'):
            guidance_parts.append(f"with resource type: {filters['resource_type']}")
        
        if parsed_query.get('sort_by'):
            sort_map = {
                'sales_desc': 'sorted by sales (highest first)',
                'sales_asc': 'sorted by sales (lowest first)',
                'price_desc': 'sorted by price (highest first)',
                'price_asc': 'sorted by price (lowest first)',
                'date_desc': 'sorted by date (newest first)',
                'date_asc': 'sorted by date (oldest first)'
            }
            guidance_parts.append(sort_map.get(parsed_query['sort_by'], ''))
        
        if parsed_query.get('limit'):
            guidance_parts.append(f"limit results to {parsed_query['limit']} items")
        
        return ". ".join(guidance_parts) + "." if guidance_parts else "Retrieve all inventory items."
    
    def _handle_broadcast_query(self, query, context) -> Dict[str, Any]:
        """Handle broadcast message queries"""
        intent = context.get('message_intent', 'promotion')
        segment = context.get('target_segment', 'all_customers')
        business_data = context.get('business_data', {})
        
        broadcast = self.broadcast_composer.compose_broadcast(intent, segment, business_data)
        
        return {
            'success': True,
            'intent': 'broadcast',
            'broadcast': broadcast,
            'query': query
        }
    
    async def _handle_appointment_query(self, query, context) -> Dict[str, Any]:
        """
        Handle appointment retrieval/search/rescheduling queries using natural language processing
        
        Appointment booking operations are handled automatically by Customer AI.
        This method helps business owners search, retrieve, reschedule, and cancel appointments.
        """
        try:
            query_lower = query.lower()
            
            # Check if it's a rescheduling request
            if any(word in query_lower for word in ['reschedule', 'move', 'change time', 'change date']):
                return await self._handle_appointment_reschedule(query, context)
            # Check if it's a cancellation request
            if any(word in query_lower for word in ['cancel', 'cancel appointment']):
                return await self._handle_appointment_cancellation(query, context)
            
            # Otherwise, it's a retrieval/search query
            parsed_query = self._parse_appointment_query(query)
            search_filters = parsed_query.get('filters', {})
            guidance = self._generate_appointment_search_guidance(parsed_query)
            
            # Try to get appointments from appointment service
            try:
                appointments_result = await self._call_appointment_service_get_appointments(search_filters)
                
                if appointments_result.get('success'):
                    appointments = appointments_result.get('appointments', [])
                    
                    # Generate natural language response
                    natural_response = self._format_appointments_natural_language(appointments, parsed_query)
                    
                    return {
                        'success': True,
                        'intent': 'appointment_retrieval',
                        'parsed_query': parsed_query,
                        'search_filters': search_filters,
                        'guidance': guidance,
                        'appointments': appointments,
                        'count': len(appointments),
                        'query': query,
                        'response': natural_response,
                        'message': natural_response
                    }
            except Exception as e:
                logger.error(f"Error retrieving appointments from service: {str(e)}")
            
            # Fallback to guidance-only response
            return {
                'success': True,
                'intent': 'appointment_retrieval',
                'parsed_query': parsed_query,
                'search_filters': search_filters,
                'guidance': guidance,
                'query': query,
                'response': f"I'll help you {parsed_query.get('action', 'search')} appointments. {guidance}",
                'message': f"I'll help you {parsed_query.get('action', 'search')} appointments. {guidance}"
            }
        except Exception as e:
            logger.error(f"Error handling appointment query: {str(e)}")
            return {
                'success': False,
                'intent': 'appointment_retrieval',
                'error': str(e),
                'query': query
            }
    
    async def _call_appointment_service_get_appointments(
        self,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call appointment booking service to get appointments"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{APPOINTMENT_BOOKING_URL}/api/v1/get-appointments",
                    params={"business_id": self.business_id},
                    json={
                        "start_date": filters.get('start_date'),
                        "end_date": filters.get('end_date'),
                        "customer_id": filters.get('customer_id'),
                        "staff_id": filters.get('staff_id'),
                        "status": filters.get('status'),
                        "limit": filters.get('limit')
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error calling appointment service: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_appointment_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language appointment query into structured format"""
        query_lower = query.lower()
        parsed = {
            'action': 'list',
            'filters': {},
            'sort_by': 'date_asc',  # Default: chronological order
            'limit': None
        }
        
        # Determine action
        if any(word in query_lower for word in ['find', 'search', 'show', 'get', 'list']):
            parsed['action'] = 'list'
        elif any(word in query_lower for word in ['count', 'how many']):
            parsed['action'] = 'count'
        
        # Extract date filters
        if 'today' in query_lower:
            parsed['filters']['start_date'] = datetime.now().strftime('%Y-%m-%d')
            parsed['filters']['end_date'] = datetime.now().strftime('%Y-%m-%d')
        elif 'tomorrow' in query_lower:
            from datetime import timedelta
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            parsed['filters']['start_date'] = tomorrow
            parsed['filters']['end_date'] = tomorrow
        elif 'this week' in query_lower:
            from datetime import timedelta
            today = datetime.now()
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            parsed['filters']['start_date'] = start.strftime('%Y-%m-%d')
            parsed['filters']['end_date'] = end.strftime('%Y-%m-%d')
        elif 'next week' in query_lower:
            from datetime import timedelta
            today = datetime.now()
            start = today - timedelta(days=today.weekday()) + timedelta(days=7)
            end = start + timedelta(days=6)
            parsed['filters']['start_date'] = start.strftime('%Y-%m-%d')
            parsed['filters']['end_date'] = end.strftime('%Y-%m-%d')
        elif 'this month' in query_lower:
            from datetime import timedelta
            today = datetime.now()
            start = today.replace(day=1)
            next_month = (start.replace(month=start.month+1) if start.month < 12 
                         else start.replace(year=start.year+1, month=1))
            end = next_month - timedelta(days=1)
            parsed['filters']['start_date'] = start.strftime('%Y-%m-%d')
            parsed['filters']['end_date'] = end.strftime('%Y-%m-%d')
        
        # Extract customer name
        customer_match = re.search(r'(?:for|customer|with)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)', query, re.IGNORECASE)
        if customer_match:
            parsed['filters']['customer_name'] = customer_match.group(1).title()
        
        # Extract staff/provider name
        staff_match = re.search(r'(?:staff|provider|therapist|doctor|with)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)', query, re.IGNORECASE)
        if staff_match:
            parsed['filters']['staff_name'] = staff_match.group(1).title()
        
        # Extract status
        if any(word in query_lower for word in ['confirmed', 'scheduled']):
            parsed['filters']['status'] = 'confirmed'
        elif 'cancelled' in query_lower:
            parsed['filters']['status'] = 'cancelled'
        elif 'completed' in query_lower:
            parsed['filters']['status'] = 'completed'
        elif 'pending' in query_lower:
            parsed['filters']['status'] = 'pending'
        
        # Extract sort preferences
        if 'earliest' in query_lower or 'soonest' in query_lower:
            parsed['sort_by'] = 'date_asc'
        elif 'latest' in query_lower or 'recent' in query_lower:
            parsed['sort_by'] = 'date_desc'
        
        # Extract limit
        limit_match = re.search(r'(?:first|next|last)\s*(\d+)', query_lower)
        if limit_match:
            parsed['limit'] = int(limit_match.group(1))
        elif 'all' in query_lower:
            parsed['limit'] = None
        
        return parsed
    
    def _generate_appointment_search_guidance(self, parsed_query: Dict[str, Any]) -> str:
        """Generate guidance for backend to execute appointment search"""
        filters = parsed_query.get('filters', {})
        action = parsed_query.get('action', 'list')
        
        guidance_parts = []
        
        if action == 'count':
            guidance_parts.append("Count appointments")
        else:
            guidance_parts.append("Retrieve appointments")
        
        if filters.get('start_date') and filters.get('end_date'):
            if filters['start_date'] == filters['end_date']:
                guidance_parts.append(f"on {filters['start_date']}")
            else:
                guidance_parts.append(f"between {filters['start_date']} and {filters['end_date']}")
        elif filters.get('start_date'):
            guidance_parts.append(f"from {filters['start_date']}")
        
        if filters.get('customer_name'):
            guidance_parts.append(f"for customer: {filters['customer_name']}")
        
        if filters.get('staff_name'):
            guidance_parts.append(f"with staff/provider: {filters['staff_name']}")
        
        if filters.get('status'):
            guidance_parts.append(f"with status: {filters['status'].upper()}")
        
        if parsed_query.get('sort_by'):
            sort_map = {
                'date_asc': 'sorted by date (earliest first)',
                'date_desc': 'sorted by date (latest first)'
            }
            guidance_parts.append(sort_map.get(parsed_query['sort_by'], ''))
        
        if parsed_query.get('limit'):
            guidance_parts.append(f"limit results to {parsed_query['limit']} appointments")
        
        return ". ".join(guidance_parts) + "." if guidance_parts else "Retrieve all appointments."
    
    async def _handle_appointment_reschedule(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment rescheduling request"""
        try:
            # Extract appointment identifier and new datetime from query
            parsed = self._parse_reschedule_query(query)
            
            appointment_id = parsed.get('appointment_id')
            new_datetime = parsed.get('new_datetime')
            
            # If we have appointment ID and new datetime, call appointment service
            if appointment_id and new_datetime:
                try:
                    # Call appointment booking service to reschedule
                    reschedule_result = await self._call_appointment_service_reschedule(
                        appointment_id,
                        new_datetime,
                        parsed.get('reason'),
                        context
                    )
                    
                    if reschedule_result.get('success'):
                        appointment = reschedule_result.get('appointment', {})
                        customer_name = appointment.get('customer_name', 'the customer')
                        service_name = appointment.get('service_name', 'service')
                        old_datetime = reschedule_result.get('reschedule', {}).get('old_datetime', '')
                        new_datetime_formatted = self._format_datetime_natural(new_datetime)
                        old_datetime_formatted = self._format_datetime_natural(old_datetime) if old_datetime else 'the previous time'
                        
                        natural_response = f"Done! I've successfully rescheduled {customer_name}'s {service_name} appointment. It was moved from {old_datetime_formatted} to {new_datetime_formatted}. The customer has been notified automatically, so they'll receive a message about the change right away. The appointment reference is {appointment_id}."
                        
                        return {
                            'success': True,
                            'intent': 'appointment_reschedule',
                            'parsed_query': parsed,
                            'query': query,
                            'response': natural_response,
                            'message': natural_response,
                            'reschedule_result': reschedule_result,
                            'appointment': appointment
                        }
                    else:
                        error_msg = reschedule_result.get('error', 'Failed to reschedule')
                        natural_error = f"I'm sorry, but I couldn't reschedule the appointment. {error_msg}. Please check the appointment ID and try again, or contact support if the issue persists."
                        
                        return {
                            'success': False,
                            'intent': 'appointment_reschedule',
                            'response': natural_error,
                            'message': natural_error,
                            'error': error_msg,
                            'query': query
                        }
                except Exception as e:
                    logger.error(f"Error calling appointment service: {str(e)}")
                    # Fall back to guidance response
                    return {
                        'success': True,
                        'intent': 'appointment_reschedule',
                        'parsed_query': parsed,
                        'query': query,
                        'message': f"I'll help you reschedule the appointment. Backend should call appointment service with appointment_id={appointment_id} and new_datetime={new_datetime}",
                        'requires_backend_action': True,
                        'action': 'reschedule_appointment',
                        'appointment_id': appointment_id,
                        'new_datetime': new_datetime,
                        'reason': parsed.get('reason'),
                        'notify_customer': True
                    }
            else:
                # Missing information - return guidance
                return {
                    'success': True,
                    'intent': 'appointment_reschedule',
                    'parsed_query': parsed,
                    'query': query,
                    'message': f"I'll help you reschedule the appointment. Please provide the appointment ID and new date/time.",
                    'requires_backend_action': True,
                    'action': 'reschedule_appointment',
                    'appointment_id': parsed.get('appointment_id'),
                    'new_datetime': parsed.get('new_datetime'),
                    'reason': parsed.get('reason'),
                    'notify_customer': True
                }
        except Exception as e:
            logger.error(f"Error handling appointment reschedule: {str(e)}")
            return {
                'success': False,
                'intent': 'appointment_reschedule',
                'error': str(e),
                'query': query
            }
    
    async def _call_appointment_service_reschedule(
        self,
        appointment_id: str,
        new_datetime: str,
        reason: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call appointment booking service to reschedule"""
        try:
            # Get appointment details first to get google_calendar_event_id
            async with httpx.AsyncClient() as client:
                # First get appointment to retrieve metadata
                get_response = await client.post(
                    f"{APPOINTMENT_BOOKING_URL}/api/v1/get-appointments",
                    params={"business_id": self.business_id},
                    json={
                        "limit": 100  # Get recent appointments
                    },
                    timeout=10.0
                )
                
                if get_response.status_code == 200:
                    appointments_data = get_response.json()
                    appointments = appointments_data.get('appointments', [])
                    
                    # Find the appointment
                    appointment = next((apt for apt in appointments if apt.get('appointment_id') == appointment_id), None)
                    
                    if appointment:
                        metadata = {
                            'google_calendar_event_id': appointment.get('google_calendar_event_id'),
                            'duration_minutes': appointment.get('duration_minutes', 60)
                        }
                    else:
                        metadata = {}
                else:
                    metadata = {}
                
                # Call reschedule endpoint
                reschedule_response = await client.post(
                    f"{APPOINTMENT_BOOKING_URL}/api/v1/reschedule-appointment",
                    params={"business_id": self.business_id},
                    json={
                        "appointment_id": appointment_id,
                        "new_datetime": new_datetime,
                        "reason": reason or "Business owner reschedule request",
                        "notify_customer": True,
                        "metadata": metadata
                    },
                    timeout=10.0
                )
                reschedule_response.raise_for_status()
                return reschedule_response.json()
        except Exception as e:
            logger.error(f"Error calling appointment service: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_reschedule_query(self, query: str) -> Dict[str, Any]:
        """Parse reschedule query to extract appointment ID and new datetime"""
        parsed = {
            'appointment_id': None,
            'new_datetime': None,
            'reason': None
        }
        
        # Extract appointment ID (format: APT_xxx or appointment ID mentioned)
        apt_match = re.search(r'APT[_\-]?([A-Z0-9]+)', query, re.IGNORECASE)
        if apt_match:
            parsed['appointment_id'] = f"APT_{apt_match.group(1)}"
        
        # Extract new datetime (simplified - in production use NLP)
        query_lower = query.lower()
        if 'tomorrow' in query_lower:
            from datetime import datetime, timedelta
            parsed['new_datetime'] = (datetime.now() + timedelta(days=1)).isoformat()
        elif 'next week' in query_lower:
            from datetime import datetime, timedelta
            parsed['new_datetime'] = (datetime.now() + timedelta(days=7)).isoformat()
        
        return parsed
    
    async def _handle_appointment_cancellation(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment cancellation request"""
        try:
            # Extract appointment identifier from query
            parsed = self._parse_cancellation_query(query)
            
            appointment_id = parsed.get('appointment_id')
            
            # If we have appointment ID, call appointment service
            if appointment_id:
                try:
                    # Call appointment booking service to cancel
                    cancel_result = await self._call_appointment_service_cancel(
                        appointment_id,
                        parsed.get('reason'),
                        context
                    )
                    
                    if cancel_result.get('success'):
                        appointment = cancel_result.get('appointment', {})
                        customer_name = appointment.get('customer_name', 'the customer')
                        service_name = appointment.get('service_name', 'service')
                        appointment_datetime = appointment.get('appointment_datetime', '')
                        datetime_formatted = self._format_datetime_natural(appointment_datetime) if appointment_datetime else 'their scheduled time'
                        reason = parsed.get('reason', 'business request')
                        
                        natural_response = f"All set! I've cancelled {customer_name}'s {service_name} appointment that was scheduled for {datetime_formatted}. The cancellation reason has been recorded as: {reason}. The customer has been automatically notified about this cancellation, and they'll receive a message letting them know. They can reach out to reschedule if they'd like. The appointment reference was {appointment_id}."
                        
                        return {
                            'success': True,
                            'intent': 'appointment_cancellation',
                            'parsed_query': parsed,
                            'query': query,
                            'response': natural_response,
                            'message': natural_response,
                            'cancellation_result': cancel_result,
                            'appointment': appointment
                        }
                    else:
                        error_msg = cancel_result.get('error', 'Failed to cancel')
                        natural_error = f"I'm sorry, but I couldn't cancel the appointment. {error_msg}. Please check the appointment ID and try again, or contact support if the issue persists."
                        
                        return {
                            'success': False,
                            'intent': 'appointment_cancellation',
                            'response': natural_error,
                            'message': natural_error,
                            'error': error_msg,
                            'query': query
                        }
                except Exception as e:
                    logger.error(f"Error calling appointment service: {str(e)}")
                    # Fall back to guidance response
                    return {
                        'success': True,
                        'intent': 'appointment_cancellation',
                        'parsed_query': parsed,
                        'query': query,
                        'message': f"I'll help you cancel the appointment. Backend should call appointment service with appointment_id={appointment_id}",
                        'requires_backend_action': True,
                        'action': 'cancel_appointment',
                        'appointment_id': appointment_id,
                        'reason': parsed.get('reason'),
                        'cancelled_by': 'business_owner',
                        'notify_customer': True
                    }
            else:
                # Missing appointment ID - return guidance
                return {
                    'success': True,
                    'intent': 'appointment_cancellation',
                    'parsed_query': parsed,
                    'query': query,
                    'message': f"I'll help you cancel the appointment. Please provide the appointment ID.",
                    'requires_backend_action': True,
                    'action': 'cancel_appointment',
                    'appointment_id': parsed.get('appointment_id'),
                    'reason': parsed.get('reason'),
                    'cancelled_by': 'business_owner',
                    'notify_customer': True
                }
        except Exception as e:
            logger.error(f"Error handling appointment cancellation: {str(e)}")
            return {
                'success': False,
                'intent': 'appointment_cancellation',
                'error': str(e),
                'query': query
            }
    
    async def _call_appointment_service_cancel(
        self,
        appointment_id: str,
        reason: Optional[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call appointment booking service to cancel"""
        try:
            # Get appointment details first to get google_calendar_event_id
            async with httpx.AsyncClient() as client:
                # First get appointment to retrieve metadata
                get_response = await client.post(
                    f"{APPOINTMENT_BOOKING_URL}/api/v1/get-appointments",
                    params={"business_id": self.business_id},
                    json={
                        "limit": 100  # Get recent appointments
                    },
                    timeout=10.0
                )
                
                if get_response.status_code == 200:
                    appointments_data = get_response.json()
                    appointments = appointments_data.get('appointments', [])
                    
                    # Find the appointment
                    appointment = next((apt for apt in appointments if apt.get('appointment_id') == appointment_id), None)
                    
                    if appointment:
                        metadata = {
                            'google_calendar_event_id': appointment.get('google_calendar_event_id')
                        }
                    else:
                        metadata = {}
                else:
                    metadata = {}
                
                # Call cancel endpoint
                cancel_response = await client.post(
                    f"{APPOINTMENT_BOOKING_URL}/api/v1/cancel-appointment",
                    params={"business_id": self.business_id},
                    json={
                        "appointment_id": appointment_id,
                        "reason": reason or "Business owner cancellation request",
                        "cancelled_by": "business_owner",
                        "notify_customer": True,
                        "metadata": metadata
                    },
                    timeout=10.0
                )
                cancel_response.raise_for_status()
                return cancel_response.json()
        except Exception as e:
            logger.error(f"Error calling appointment service: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _parse_cancellation_query(self, query: str) -> Dict[str, Any]:
        """Parse cancellation query to extract appointment ID and reason"""
        parsed = {
            'appointment_id': None,
            'reason': None
        }
        
        # Extract appointment ID
        apt_match = re.search(r'APT[_\-]?([A-Z0-9]+)', query, re.IGNORECASE)
        if apt_match:
            parsed['appointment_id'] = f"APT_{apt_match.group(1)}"
        
        # Extract reason (simplified)
        query_lower = query.lower()
        if 'conflict' in query_lower or 'unavailable' in query_lower:
            parsed['reason'] = 'business_unavailable'
        elif 'emergency' in query_lower:
            parsed['reason'] = 'emergency'
        else:
            parsed['reason'] = 'business_request'
        
        return parsed
    
    def _format_appointments_natural_language(self, appointments: List[Dict[str, Any]], parsed_query: Dict[str, Any]) -> str:
        """Format appointment list into natural language response"""
        try:
            if not appointments:
                date_info = ""
                if parsed_query.get('filters', {}).get('start_date'):
                    date_info = f" for {parsed_query['filters']['start_date']}"
                return f"You don't have any appointments{date_info}. Your schedule is clear!"
            
            count = len(appointments)
            if count == 1:
                apt = appointments[0]
                customer_name = apt.get('customer_name', 'A customer')
                service_name = apt.get('service_name', 'service')
                datetime_formatted = self._format_datetime_natural(apt.get('appointment_datetime', ''))
                status = apt.get('status', 'confirmed')
                
                response = f"You have 1 appointment: {customer_name} has a {service_name} appointment on {datetime_formatted} (Status: {status.capitalize()})."
                
                if apt.get('notes'):
                    response += f" Note: {apt['notes']}"
                
                return response
            
            else:
                response = f"You have {count} appointments:\n\n"
                
                for idx, apt in enumerate(appointments[:10], 1):  # Limit to first 10 for readability
                    customer_name = apt.get('customer_name', 'A customer')
                    service_name = apt.get('service_name', 'service')
                    datetime_formatted = self._format_datetime_natural(apt.get('appointment_datetime', ''))
                    status = apt.get('status', 'confirmed')
                    
                    response += f"{idx}. {customer_name} - {service_name} on {datetime_formatted} ({status.capitalize()})"
                    
                    if apt.get('staff_name'):
                        response += f" with {apt['staff_name']}"
                    
                    response += f". Reference: {apt.get('appointment_id', 'N/A')}\n"
                
                if count > 10:
                    response += f"\n... and {count - 10} more appointment(s)."
                
                return response
        except Exception as e:
            logger.error(f"Error formatting appointments: {str(e)}")
            return f"You have {len(appointments)} appointment(s)."
    
    def _format_datetime_natural(self, datetime_str: str) -> str:
        """Format datetime string into natural language (e.g., 'Monday, January 15th at 2:00 PM')"""
        try:
            from datetime import datetime
            # Parse ISO format
            if 'T' in datetime_str:
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(datetime_str)
            
            # Format date
            day_name = dt.strftime('%A')
            month_name = dt.strftime('%B')
            day = dt.day
            year = dt.year
            
            # Add ordinal suffix
            if 10 <= day % 100 <= 20:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            
            # Format time (12-hour format)
            hour = dt.hour
            minute = dt.minute
            am_pm = 'AM' if hour < 12 else 'PM'
            hour_12 = hour if hour <= 12 else hour - 12
            if hour_12 == 0:
                hour_12 = 12
            
            time_str = f"{hour_12}:{minute:02d} {am_pm}"
            
            return f"{day_name}, {month_name} {day}{suffix}, {year} at {time_str}"
        except Exception:
            return datetime_str  # Return original if parsing fails
    
    def _handle_general_query(self, query, context) -> Dict[str, Any]:
        """Handle general business intelligence queries using OpenAI for conversational responses"""
        try:
            # Use OpenAI service to generate a natural, conversational response
            openai_result = self.openai_service.generate_general_response(query)
            
            if openai_result.get('success'):
                return {
                    'success': True,
                    'intent': 'general',
                    'response': openai_result.get('response', ''),
                    'query': query,
                    'tokens_used': openai_result.get('tokens_used', {})
                }
            else:
                # Fallback if OpenAI fails
                logger.warning(f"OpenAI service failed for general query: {openai_result.get('error')}")
                return {
                    'success': True,
                    'intent': 'general',
                    'response': "I can help with sales analysis, customer segmentation, inventory retrieval/search, invoice retrieval/search, appointment retrieval/rescheduling, and broadcast messages. What would you like to know?",
                    'query': query
                }
        except Exception as e:
            logger.error(f"Error handling general query with OpenAI: {str(e)}")
            # Fallback response if there's an error
            return {
                'success': True,
                'intent': 'general',
                'response': "I can help with sales analysis, customer segmentation, inventory retrieval/search, invoice retrieval/search, appointment retrieval/rescheduling, and broadcast messages. What would you like to know?",
                'query': query
            }


def get_business_intelligence(business_id: str, industry: str) -> BusinessIntelligence:
    """Factory function to get business intelligence instance"""
    return BusinessIntelligence(business_id, industry)

