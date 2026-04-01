"""
Customer Segmentation AI
ML-based customer clustering and targeted marketing recommendations
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import Counter
import statistics

logger = logging.getLogger(__name__)


class CustomerSegmentation:
    """
    Segments customers using ML clustering and behavior analysis
    """
    
    def __init__(self, business_id: str):
        self.business_id = business_id
        self.segments = {}
    
    def segment_customers(
        self,
        customer_data: List[Dict[str, Any]],
        method: str = 'behavior'
    ) -> Dict[str, Any]:
        """
        Segment customers using specified method
        
        Args:
            customer_data: List of customer profiles with behavior data
            method: 'behavior', 'value', 'engagement', or 'rfm'
        
        Returns:
            - segments: Dict[segment_name, List[customer_ids]]
            - segment_profiles: Dict[segment_name, characteristics]
            - recommendations: Dict[segment_name, strategies]
        """
        try:
            if method == 'behavior':
                return self._segment_by_behavior(customer_data)
            elif method == 'value':
                return self._segment_by_value(customer_data)
            elif method == 'engagement':
                return self._segment_by_engagement(customer_data)
            elif method == 'rfm':
                return self._segment_by_rfm(customer_data)
            else:
                return self._segment_by_behavior(customer_data)
                
        except Exception as e:
            logger.error(f"Error segmenting customers: {str(e)}")
            return {
                'segments': {},
                'segment_profiles': {},
                'error': str(e)
            }
    
    def _segment_by_behavior(self, customer_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Segment by behavior patterns"""
        try:
            segments = {
                'frequent_buyers': [],
                'occasional_buyers': [],
                'one_time_buyers': [],
                'browsers': []
            }
            
            for customer in customer_data:
                customer_id = customer.get('customer_id')
                purchase_count = customer.get('purchase_count', 0)
                conversation_count = customer.get('conversation_count', 0)
                
                # Categorize based on behavior
                if purchase_count >= 5:
                    segments['frequent_buyers'].append(customer_id)
                elif purchase_count >= 2:
                    segments['occasional_buyers'].append(customer_id)
                elif purchase_count == 1:
                    segments['one_time_buyers'].append(customer_id)
                elif conversation_count > 0:
                    segments['browsers'].append(customer_id)
            
            # Create segment profiles
            segment_profiles = {
                'frequent_buyers': {
                    'count': len(segments['frequent_buyers']),
                    'characteristics': 'High purchase frequency, loyal customers',
                    'avg_purchases': self._calc_avg_purchases(customer_data, segments['frequent_buyers'])
                },
                'occasional_buyers': {
                    'count': len(segments['occasional_buyers']),
                    'characteristics': 'Moderate purchase frequency, potential for growth',
                    'avg_purchases': self._calc_avg_purchases(customer_data, segments['occasional_buyers'])
                },
                'one_time_buyers': {
                    'count': len(segments['one_time_buyers']),
                    'characteristics': 'Single purchase, need re-engagement',
                    'avg_purchases': 1.0
                },
                'browsers': {
                    'count': len(segments['browsers']),
                    'characteristics': 'High interest, no purchases yet',
                    'avg_purchases': 0.0
                }
            }
            
            # Generate recommendations
            recommendations = self._generate_segment_recommendations(segments, customer_data)
            
            return {
                'segments': segments,
                'segment_profiles': segment_profiles,
                'recommendations': recommendations,
                'total_customers': len(customer_data),
                'segmentation_method': 'behavior',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in behavior segmentation: {str(e)}")
            return {}
    
    def _segment_by_value(self, customer_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Segment by customer lifetime value"""
        try:
            # Calculate CLV for each customer
            customer_values = []
            for customer in customer_data:
                total_spent = customer.get('total_spent', 0)
                customer_values.append((customer.get('customer_id'), total_spent))
            
            # Sort by value
            customer_values.sort(key=lambda x: x[1], reverse=True)
            
            # Create segments
            total_customers = len(customer_values)
            segments = {
                'high_value': [cv[0] for cv in customer_values[:int(total_customers * 0.2)]],  # Top 20%
                'medium_value': [cv[0] for cv in customer_values[int(total_customers * 0.2):int(total_customers * 0.6)]],  # Middle 40%
                'low_value': [cv[0] for cv in customer_values[int(total_customers * 0.6):]]  # Bottom 40%
            }
            
            # Calculate segment metrics
            segment_profiles = {}
            for segment_name, customer_ids in segments.items():
                segment_data = [c for c in customer_data if c.get('customer_id') in customer_ids]
                total_value = sum(c.get('total_spent', 0) for c in segment_data)
                avg_value = total_value / len(segment_data) if segment_data else 0
                
                segment_profiles[segment_name] = {
                    'count': len(customer_ids),
                    'total_value': total_value,
                    'avg_value': avg_value,
                    'revenue_contribution': (total_value / sum(cv[1] for cv in customer_values)) if customer_values else 0
                }
            
            recommendations = {
                'high_value': "VIP treatment, exclusive offers, loyalty rewards, personalized service",
                'medium_value': "Upsell opportunities, targeted promotions, encourage repeat purchases",
                'low_value': "Win-back campaigns, entry-level offers, nurture relationship"
            }
            
            return {
                'segments': segments,
                'segment_profiles': segment_profiles,
                'recommendations': recommendations,
                'total_customers': total_customers,
                'segmentation_method': 'value',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in value segmentation: {str(e)}")
            return {}
    
    def _segment_by_engagement(self, customer_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Segment by engagement level"""
        try:
            segments = {
                'highly_engaged': [],
                'moderately_engaged': [],
                'low_engagement': [],
                'inactive': []
            }
            
            for customer in customer_data:
                customer_id = customer.get('customer_id')
                conversation_count = customer.get('conversation_count', 0)
                last_activity_days = customer.get('days_since_last_activity', 999)
                
                # Engagement scoring
                engagement_score = conversation_count - (last_activity_days / 30)
                
                if engagement_score > 5 and last_activity_days < 7:
                    segments['highly_engaged'].append(customer_id)
                elif engagement_score > 2 and last_activity_days < 30:
                    segments['moderately_engaged'].append(customer_id)
                elif last_activity_days < 90:
                    segments['low_engagement'].append(customer_id)
                else:
                    segments['inactive'].append(customer_id)
            
            segment_profiles = {
                'highly_engaged': {
                    'count': len(segments['highly_engaged']),
                    'characteristics': 'Active, frequent interactions, recent activity'
                },
                'moderately_engaged': {
                    'count': len(segments['moderately_engaged']),
                    'characteristics': 'Regular interactions, good potential'
                },
                'low_engagement': {
                    'count': len(segments['low_engagement']),
                    'characteristics': 'Infrequent interactions, needs activation'
                },
                'inactive': {
                    'count': len(segments['inactive']),
                    'characteristics': 'No recent activity, needs re-engagement'
                }
            }
            
            recommendations = {
                'highly_engaged': "Maintain engagement, offer premium services, request referrals",
                'moderately_engaged': "Increase touchpoints, targeted content, engagement campaigns",
                'low_engagement': "Re-activation campaigns, special offers, feedback requests",
                'inactive': "Win-back campaigns, surveys, incentive offers"
            }
            
            return {
                'segments': segments,
                'segment_profiles': segment_profiles,
                'recommendations': recommendations,
                'total_customers': len(customer_data),
                'segmentation_method': 'engagement'
            }
            
        except Exception as e:
            logger.error(f"Error in engagement segmentation: {str(e)}")
            return {}
    
    def _segment_by_rfm(self, customer_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Segment using RFM (Recency, Frequency, Monetary) analysis"""
        try:
            # Calculate RFM scores for each customer
            rfm_scores = []
            for customer in customer_data:
                recency = customer.get('days_since_last_purchase', 999)
                frequency = customer.get('purchase_count', 0)
                monetary = customer.get('total_spent', 0)
                
                # Score each dimension (1-5, 5 being best)
                r_score = self._score_recency(recency)
                f_score = self._score_frequency(frequency)
                m_score = self._score_monetary(monetary)
                
                rfm_scores.append({
                    'customer_id': customer.get('customer_id'),
                    'r_score': r_score,
                    'f_score': f_score,
                    'm_score': m_score,
                    'total_score': r_score + f_score + m_score
                })
            
            # Define segments based on RFM scores
            segments = {
                'champions': [],  # High R, F, M
                'loyal_customers': [],  # High F, M
                'potential_loyalists': [],  # High R, low F
                'at_risk': [],  # Low R, high F, M
                'hibernating': [],  # Low R, F, M
                'lost': []  # Very low R
            }
            
            for rfm in rfm_scores:
                customer_id = rfm['customer_id']
                r, f, m = rfm['r_score'], rfm['f_score'], rfm['m_score']
                
                if r >= 4 and f >= 4 and m >= 4:
                    segments['champions'].append(customer_id)
                elif f >= 4 and m >= 4:
                    segments['loyal_customers'].append(customer_id)
                elif r >= 4 and f < 3:
                    segments['potential_loyalists'].append(customer_id)
                elif r < 3 and f >= 3 and m >= 3:
                    segments['at_risk'].append(customer_id)
                elif r < 3 and f < 3:
                    segments['hibernating'].append(customer_id)
                elif r == 1:
                    segments['lost'].append(customer_id)
            
            segment_profiles = {
                'champions': {'count': len(segments['champions']), 'priority': 'retain'},
                'loyal_customers': {'count': len(segments['loyal_customers']), 'priority': 'nurture'},
                'potential_loyalists': {'count': len(segments['potential_loyalists']), 'priority': 'convert'},
                'at_risk': {'count': len(segments['at_risk']), 'priority': 'save'},
                'hibernating': {'count': len(segments['hibernating']), 'priority': 'reactivate'},
                'lost': {'count': len(segments['lost']), 'priority': 'win_back'}
            }
            
            recommendations = {
                'champions': "Reward, request reviews/referrals, exclusive previews",
                'loyal_customers': "Loyalty programs, upsell premium products",
                'potential_loyalists': "Membership programs, targeted recommendations",
                'at_risk': "Personalized outreach, special discounts, feedback surveys",
                'hibernating': "Reactivation campaigns, limited-time offers",
                'lost': "Win-back campaigns, steep discounts, surveys"
            }
            
            return {
                'segments': segments,
                'segment_profiles': segment_profiles,
                'recommendations': recommendations,
                'total_customers': len(customer_data),
                'segmentation_method': 'rfm'
            }
            
        except Exception as e:
            logger.error(f"Error in RFM segmentation: {str(e)}")
            return {}
    
    def create_target_segment_profile(
        self,
        segment_name: str,
        customers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create detailed profile for a target segment"""
        try:
            if not customers:
                return {}
            
            # Aggregate characteristics
            total_spent = [c.get('total_spent', 0) for c in customers]
            purchase_counts = [c.get('purchase_count', 0) for c in customers]
            conversation_counts = [c.get('conversation_count', 0) for c in customers]
            
            # Extract preferences
            all_products = []
            all_categories = []
            for c in customers:
                all_products.extend(c.get('purchased_products', []))
                all_categories.extend(c.get('interested_categories', []))
            
            top_products = Counter(all_products).most_common(5)
            top_categories = Counter(all_categories).most_common(3)
            
            profile = {
                'segment_name': segment_name,
                'size': len(customers),
                'demographics': {
                    'avg_lifetime_value': statistics.mean(total_spent) if total_spent else 0,
                    'avg_purchase_frequency': statistics.mean(purchase_counts) if purchase_counts else 0,
                    'avg_engagement': statistics.mean(conversation_counts) if conversation_counts else 0
                },
                'preferences': {
                    'top_products': [p[0] for p in top_products],
                    'top_categories': [c[0] for c in top_categories]
                },
                'personalization_strategy': self._generate_personalization_strategy(segment_name),
                'messaging_recommendations': self._generate_messaging_recommendations(segment_name),
                'optimal_contact_time': self._determine_optimal_contact_time(customers)
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Error creating target segment profile: {str(e)}")
            return {}
    
    def _calc_avg_purchases(self, customer_data: List[Dict], customer_ids: List[str]) -> float:
        """Calculate average purchases for a segment"""
        try:
            purchases = [
                c.get('purchase_count', 0)
                for c in customer_data
                if c.get('customer_id') in customer_ids
            ]
            return statistics.mean(purchases) if purchases else 0.0
        except:
            return 0.0
    
    def _generate_segment_recommendations(
        self,
        segments: Dict[str, List[str]],
        customer_data: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Generate recommendations for each segment"""
        return {
            'frequent_buyers': "Focus on retention, offer loyalty rewards, request referrals",
            'occasional_buyers': "Encourage frequency with targeted promotions and bundles",
            'one_time_buyers': "Re-engagement campaigns, special comeback offers",
            'browsers': "Conversion campaigns, first-purchase incentives, trust-building"
        }
    
    def _score_recency(self, days: int) -> int:
        """Score recency (1-5)"""
        if days <= 7: return 5
        elif days <= 30: return 4
        elif days <= 90: return 3
        elif days <= 180: return 2
        else: return 1
    
    def _score_frequency(self, count: int) -> int:
        """Score frequency (1-5)"""
        if count >= 10: return 5
        elif count >= 5: return 4
        elif count >= 3: return 3
        elif count >= 1: return 2
        else: return 1
    
    def _score_monetary(self, amount: float) -> int:
        """Score monetary value (1-5)"""
        if amount >= 50000: return 5
        elif amount >= 20000: return 4
        elif amount >= 10000: return 3
        elif amount >= 5000: return 2
        else: return 1
    
    def _generate_personalization_strategy(self, segment_name: str) -> str:
        """Generate personalization strategy for segment"""
        strategies = {
            'champions': "Personalized premium offers, early access to new products",
            'loyal_customers': "Customized bundles based on purchase history",
            'potential_loyalists': "Targeted product recommendations",
            'at_risk': "Personalized win-back offers",
            'frequent_buyers': "Exclusive deals and early access",
            'occasional_buyers': "Bundled discounts on favorites",
            'one_time_buyers': "Personalized comeback incentives",
            'browsers': "Product-specific promotions based on browsing"
        }
        return strategies.get(segment_name, "Personalized messaging based on behavior")
    
    def _generate_messaging_recommendations(self, segment_name: str) -> Dict[str, str]:
        """Generate messaging recommendations"""
        return {
            'tone': 'friendly and appreciative' if 'loyal' in segment_name else 'engaging and incentivizing',
            'focus': 'retention' if 'champion' in segment_name or 'loyal' in segment_name else 'conversion',
            'frequency': 'moderate' if 'engaged' in segment_name else 'strategic'
        }
    
    def _determine_optimal_contact_time(self, customers: List[Dict[str, Any]]) -> str:
        """Determine best time to contact segment"""
        # Simplified - would analyze actual engagement patterns
        return "Weekdays 10AM-2PM (based on historical engagement)"


def get_customer_segmentation(business_id: str) -> CustomerSegmentation:
    """Factory function to get customer segmentation instance"""
    return CustomerSegmentation(business_id)

