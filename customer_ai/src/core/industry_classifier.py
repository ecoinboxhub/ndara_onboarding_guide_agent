"""
Industry Classification System for Customer AI
Automatically identifies business industry and routes to appropriate AI engine
Uses canonical industry taxonomy from domain layer.
"""

import logging
from typing import Dict, List, Any, Optional
import re

from ..domain.industries.taxonomy import normalize_industry
from ..domain.industries.config import get_recommendations, get_requirements

logger = logging.getLogger(__name__)


class IndustryClassifier:
    """
    Classifies businesses into industry categories for AI routing
    """
    
    def __init__(self):
        self.industry_keywords = {
            'ecommerce': [
                'online store', 'ecommerce', 'retail', 'shopping', 'products', 'inventory',
                'shipping', 'delivery', 'payment', 'checkout', 'cart', 'store'
            ],
            'healthcare': [
                'doctor', 'medical', 'healthcare', 'clinic', 'hospital', 'patient',
                'appointment', 'treatment', 'medicine', 'health', 'medical', 'surgery'
            ],
            'real_estate': [
                'property', 'real estate', 'house', 'apartment', 'rental', 'sale',
                'agent', 'realtor', 'listing', 'property', 'home', 'mortgage'
            ],
            'restaurants': [
                'restaurant', 'food', 'menu', 'dining', 'cafe', 'kitchen', 'chef',
                'meal', 'cuisine', 'dining', 'food service', 'catering'
            ],
            'education': [
                'school', 'education', 'course', 'training', 'learning', 'student',
                'teacher', 'academy', 'institute', 'university', 'college'
            ],
            'financial': [
                'bank', 'financial', 'loan', 'investment', 'insurance', 'money',
                'credit', 'finance', 'accounting', 'tax', 'financial services'
            ],
            'travel': [
                'travel', 'hotel', 'tourism', 'vacation', 'booking', 'flight',
                'trip', 'destination', 'travel agency', 'accommodation'
            ],
            'events': [
                'event', 'party', 'wedding', 'celebration', 'entertainment',
                'venue', 'planning', 'conference', 'meeting'
            ],
            'logistics': [
                'delivery', 'shipping', 'logistics', 'transport', 'freight',
                'warehouse', 'supply chain', 'distribution'
            ],
            'professional_services': [
                'consulting', 'legal', 'accounting', 'marketing', 'advertising',
                'consultant', 'professional services', 'business services'
            ],
            'beauty_wellness': [
                'beauty', 'salon', 'spa', 'wellness', 'fitness', 'gym',
                'massage', 'cosmetic', 'skincare', 'hair', 'nails'
            ],
            'telecoms': [
                'telecom', 'internet', 'phone', 'communication', 'network',
                'telecommunications', 'broadband', 'mobile', 'wireless'
            ],
            'banking': [
                'banking', 'bank', 'financial institution', 'credit union',
                'investment bank', 'commercial bank', 'retail banking'
            ],
            'manufacturing': [
                'manufacturing', 'production', 'factory', 'industrial',
                'machinery', 'equipment', 'assembly', 'production line'
            ],
            'retail_chains': [
                'retail chain', 'franchise', 'chain store', 'multi-location',
                'retail network', 'store chain', 'brand stores'
            ]
        }
        
        self.industry_weights = {
            'ecommerce': 1.0,
            'healthcare': 1.0,
            'real_estate': 1.0,
            'restaurants': 1.0,
            'education': 1.0,
            'financial': 1.0,
            'travel': 1.0,
            'events': 1.0,
            'logistics': 1.0,
            'professional_services': 1.0,
            'beauty_wellness': 1.0,
            'telecoms': 1.0,
            'banking': 1.0,
            'manufacturing': 1.0,
            'retail_chains': 1.0
        }
    
    def classify_business(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify business into industry category
        """
        try:
            # Extract text data for analysis
            text_data = self._extract_text_data(business_data)
            
            # Calculate industry scores
            industry_scores = self._calculate_industry_scores(text_data)
            
            # Get top industry (ensure canonical key via taxonomy)
            top_industry = max(industry_scores.items(), key=lambda x: x[1])
            canonical_industry = normalize_industry(top_industry[0])
            
            # Get confidence score
            confidence = self._calculate_confidence(industry_scores, top_industry[1])
            
            return {
                'success': True,
                'industry': canonical_industry,
                'confidence': confidence,
                'scores': industry_scores,
                'recommendations': self._get_industry_recommendations(canonical_industry)
            }
            
        except Exception as e:
            logger.error(f"Error classifying business: {str(e)}")
            return {
                'success': False,
                'error': f"Error classifying business: {str(e)}"
            }
    
    def _extract_text_data(self, business_data: Dict[str, Any]) -> str:
        """
        Extract all text data from business information
        Supports both new knowledge_data format and legacy business_data format
        """
        text_parts = []
        
        # Handle new knowledge_data structure
        if 'business_info' in business_data:
            business_info = business_data['business_info']
            if 'name' in business_info:
                text_parts.append(business_info['name'])
            if 'description' in business_info:
                text_parts.append(business_info['description'])
        
        # Handle legacy business_profile structure
        elif 'business_profile' in business_data:
            profile = business_data['business_profile']
            if 'business_name' in profile:
                text_parts.append(profile['business_name'])
            if 'description' in profile:
                text_parts.append(profile['description'])
            if 'industry' in profile:
                text_parts.append(profile['industry'])
        
        # Products (new structure)
        if 'products' in business_data:
            for item in business_data['products']:
                if 'name' in item:
                    text_parts.append(item['name'])
                if 'description' in item:
                    text_parts.append(item['description'])
                if 'category' in item:
                    text_parts.append(item['category'])
        
        # Services (new structure)
        if 'services' in business_data:
            for item in business_data['services']:
                if 'name' in item:
                    text_parts.append(item['name'])
                if 'description' in item:
                    text_parts.append(item['description'])
                if 'category' in item:
                    text_parts.append(item['category'])
        
        # Products/services (legacy structure)
        if 'products_services' in business_data:
            for item in business_data['products_services']:
                if 'name' in item:
                    text_parts.append(item['name'])
                if 'description' in item:
                    text_parts.append(item['description'])
                if 'category' in item:
                    text_parts.append(item['category'])
        
        # FAQs (same in both structures)
        if 'faqs' in business_data:
            for faq in business_data['faqs']:
                if 'question' in faq:
                    text_parts.append(faq['question'])
                if 'answer' in faq:
                    text_parts.append(faq['answer'])
        
        return ' '.join(text_parts).lower()
    
    def _calculate_industry_scores(self, text_data: str) -> Dict[str, float]:
        """
        Calculate industry scores based on keyword matching
        """
        scores = {}
        
        for industry, keywords in self.industry_keywords.items():
            score = 0
            total_keywords = len(keywords)
            
            for keyword in keywords:
                # Count keyword occurrences
                count = text_data.count(keyword.lower())
                if count > 0:
                    score += count
            
            # Normalize score
            if total_keywords > 0:
                scores[industry] = (score / total_keywords) * self.industry_weights.get(industry, 1.0)
            else:
                scores[industry] = 0
        
        return scores
    
    def _calculate_confidence(self, scores: Dict[str, float], top_score: float) -> float:
        """
        Calculate confidence score for classification
        """
        if top_score == 0:
            return 0.0
        
        # Get second highest score
        sorted_scores = sorted(scores.values(), reverse=True)
        second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0
        
        # Calculate confidence as ratio of top score to second score
        if second_score > 0:
            confidence = top_score / (top_score + second_score)
        else:
            confidence = 1.0
        
        return min(confidence, 1.0)
    
    def _get_industry_recommendations(self, industry: str) -> Dict[str, Any]:
        """Get recommendations for specific industry from domain config."""
        return get_recommendations(industry)
    
    def get_industry_specific_requirements(self, industry: str) -> Dict[str, Any]:
        """Get data requirements for specific industry from domain config."""
        return get_requirements(industry)
    
    def validate_industry_data(self, industry: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against industry requirements
        Supports both new knowledge_data format and legacy format
        """
        requirements = self.get_industry_specific_requirements(industry)
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'missing_optional': []
        }
        
        # Check required fields with format flexibility
        for field, description in requirements.get('required', {}).items():
            # Handle field mapping for new vs legacy formats
            field_found = False
            
            # Check direct field
            if field in data:
                field_found = True
            # Map business_profile <-> business_info (new format)
            elif field == 'business_profile' and 'business_info' in data:
                field_found = True
            elif field == 'business_info' and 'business_profile' in data:
                field_found = True
            # Map products_services <-> products + services (new format)
            elif field == 'products_services':
                # Check legacy format
                if 'products_services' in data:
                    field_found = True
                # Check new format: products + services arrays (empty arrays are valid)
                elif 'products' in data or 'services' in data:
                    # If either products or services field exists (even if empty), it's valid
                    field_found = True
                # Check product_catalog (legacy format)
                elif 'product_catalog' in data:
                    catalog = data.get('product_catalog', {})
                    if isinstance(catalog, dict):
                        # product_catalog exists, even if products array is empty
                        field_found = True
            # Check for products field (ecommerce industry)
            elif field == 'products':
                # Check direct field
                if isinstance(data.get('products'), list):
                    field_found = True
                # Check legacy field names
                elif 'product_catalog' in data:
                    field_found = True
                elif 'products_services' in data:
                    field_found = True
                # Check services array (some industries use services instead of products)
                elif isinstance(data.get('services'), list) and len(data.get('services', [])) > 0:
                    field_found = True
            
            if not field_found:
                validation_result['missing_required'].append(field)
                validation_result['errors'].append(f"Missing required field: {field}")
                validation_result['is_valid'] = False
        
        # Check optional fields
        # Catalog (products_services) is provided via backend AI Tools in knowledge_data format; do not warn when absent
        catalog_from_tools = (
            'business_info' in data
            or data.get('_original_structure') == 'knowledge_data'
            or 'collection_name' in data
        )
        for field, description in requirements.get('optional', {}).items():
            if field not in data:
                if field == 'products_services' and catalog_from_tools:
                    continue  # Catalog from AI Tools, not onboarding
                validation_result['missing_optional'].append(field)
                validation_result['warnings'].append(f"Missing optional field: {field}")
        
        return validation_result
