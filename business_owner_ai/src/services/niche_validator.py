"""
Niche Validator Service
Validates if queries are within business scope (niche)

Prevents hallucination by rejecting out-of-scope questions directly
"""

import logging
from typing import Dict, Tuple
import json
import os

logger = logging.getLogger(__name__)


class NicheValidator:
    """Validates if queries are within business niche"""
    
    # Industry-specific keyword definitions
    INDUSTRY_KEYWORDS = {
        'beauty_wellness': {
            'in_scope': [
                'facial', 'massage', 'skincare', 'wellness', 'appointment', 'customer',
                'treatment', 'spa', 'beauty', 'hair', 'makeup', 'skin', 'relax',
                'therapy', 'service', 'booking', 'pricing', 'package', 'session',
                'consultation', 'product', 'staff', 'therapist', 'appointment',
                'reservation', 'schedule'
            ],
            'out_of_scope_keywords': [
                'restaurant', 'food', 'menu', 'recipe', 'delivery', 'order',
                'hotel', 'hotel rooms', 'nursing', 'hospital', 'surgery',
                'medication', 'prescription', 'pharmacy', 'manufacturing',
                'retail store', 'inventory shipping'
            ],
            'out_of_scope_response': (
                "I can only help with questions about beauty, wellness, spa services, "
                "appointments, and customer management. Your question appears to be "
                "outside this scope. Please ask about beauty treatments, wellness services, "
                "appointments, or customer information."
            )
        },
        'restaurants': {
            'in_scope': [
                'menu', 'food', 'order', 'delivery', 'reservation', 'restaurant',
                'dish', 'meal', 'customer', 'dining', 'table', 'booking', 'recipe',
                'ingredient', 'price', 'payment', 'kitchen', 'chef', 'staff',
                'service', 'seating', 'hours', 'location', 'cuisine', 'review'
            ],
            'out_of_scope_keywords': [
                'beauty', 'spa', 'wellness', 'massage', 'facial', 'salon',
                'hotel', 'rooms', 'accommodation', 'clinic', 'hospital',
                'pharmacy', 'manufacturing', 'retail', 'clothing', 'electronics'
            ],
            'out_of_scope_response': (
                "I can only help with questions about your restaurant, menu, orders, "
                "reservations, customers, and operations. Your question appears to be "
                "outside this scope. Please ask about food, menu items, orders, or service."
            )
        }
    }
    
    def __init__(self, business_id: str, industry: str):
        self.business_id = business_id
        self.industry = industry
        self.keywords = self.INDUSTRY_KEYWORDS.get(industry, self.INDUSTRY_KEYWORDS['restaurants'])
    
    def validate_niche_scope(self, query: str) -> Tuple[bool, str, str]:
        """
        Validate if query is within business niche.
        
        Returns:
            (is_in_scope: bool, category: str, message: str)
            - is_in_scope: True if query is in scope
            - category: 'in_scope', 'out_of_scope', or 'unclear'
            - message: Reason for classification
        """
        query_lower = query.lower()
        
        # Check for out-of-scope keywords first
        for keyword in self.keywords.get('out_of_scope_keywords', []):
            if keyword in query_lower:
                logger.warning(f"Query detected as out-of-scope: {keyword} in {query}")
                return (False, 'out_of_scope', self.keywords['out_of_scope_response'])
        
        # Check for in-scope keywords
        in_scope_count = sum(1 for keyword in self.keywords.get('in_scope', []) if keyword in query_lower)
        
        if in_scope_count > 0:
            logger.debug(f"Query detected as in-scope with {in_scope_count} keyword matches")
            return (True, 'in_scope', 'Query is within business scope')
        
        # If no keywords match, it's unclear
        logger.debug(f"Query detected as unclear - no keywords matched: {query}")
        return (False, 'unclear', (
            "I'm not sure if your question is about this business. "
            "Could you please clarify what you'd like to know about?"
        ))
    
    def is_clarification_needed(self, query: str) -> Tuple[bool, str]:
        """
        Check if query needs clarification before processing.
        
        Returns:
            (needs_clarification: bool, suggested_clarification: str)
        """
        query_lower = query.lower()
        
        # Ambiguous queries that need clarification
        ambiguous_patterns = {
            'how am i doing': 'Are you asking about sales performance, customer satisfaction, or operational efficiency?',
            'tell me about my business': 'Would you like to know about sales, customers, inventory, or something else?',
            'what should i do': 'This depends on your business goals. Can you be more specific?',
            'what\'s the status': 'What would you like the status on? (sales, inventory, customers, etc.)',
            'show me everything': 'That\'s a lot! What specific area would you like to focus on? (sales, customers, inventory, etc.)',
            'help me': 'I\'d be happy to help! What would you like to know about?',
        }
        
        for pattern, clarification in ambiguous_patterns.items():
            if pattern in query_lower:
                logger.debug(f"Query detected as ambiguous - {pattern}: {query}")
                return (True, clarification)
        
        # Check for very short/vague queries
        if len(query.split()) < 2:
            logger.debug(f"Query detected as too vague: {query}")
            return (True, "Your question is a bit vague. Could you provide more details?")
        
        return (False, "")
    
    def get_niche_boundaries(self) -> Dict[str, list]:
        """Get the niche boundaries for this industry"""
        return {
            'in_scope': self.keywords.get('in_scope', []),
            'out_of_scope': self.keywords.get('out_of_scope_keywords', [])
        }


def get_niche_validator(business_id: str, industry: str) -> NicheValidator:
    """Factory function to get niche validator instance"""
    return NicheValidator(business_id, industry)
