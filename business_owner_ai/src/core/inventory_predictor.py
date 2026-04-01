"""
Inventory Prediction AI
Predicts inventory needs from conversation patterns
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)


class InventoryPredictor:
    """Predicts inventory needs based on customer conversations and demand patterns"""
    
    def __init__(self, business_id: str):
        self.business_id = business_id
    
    def predict_demand(
        self,
        conversations: List[Dict[str, Any]],
        current_inventory: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """Predict product demand from conversations"""
        try:
            # Analyze product mentions in conversations
            product_mentions = self._extract_product_mentions(conversations)
            
            # Calculate demand score
            demand_predictions = self._calculate_demand_predictions(product_mentions)
            
            # Generate restocking recommendations
            restocking_recommendations = self._generate_restocking_recommendations(
                demand_predictions,
                current_inventory
            )
            
            # Identify trends
            trends = self._identify_demand_trends(conversations, product_mentions)
            
            return {
                'demand_predictions': demand_predictions,
                'restocking_recommendations': restocking_recommendations,
                'trends': trends,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error predicting demand: {str(e)}")
            return {'error': str(e)}
    
    def _extract_product_mentions(self, conversations) -> Counter:
        """Extract product mentions from conversations"""
        mentions = Counter()
        for conv in conversations:
            for msg in conv.get('messages', []):
                if msg.get('role') == 'customer':
                    content = msg.get('content', '').lower()
                    # Simple keyword matching - would be enhanced with NER
                    mentions.update([content])
        return mentions
    
    def _calculate_demand_predictions(self, product_mentions) -> List[Dict[str, Any]]:
        """Calculate demand predictions"""
        predictions = []
        for product, count in product_mentions.most_common(20):
            predictions.append({
                'product': product,
                'mention_count': count,
                'demand_level': 'high' if count > 10 else 'medium' if count > 5 else 'low',
                'predicted_weekly_demand': count * 1.5  # Simple multiplier
            })
        return predictions
    
    def _generate_restocking_recommendations(self, predictions, current_inventory) -> List[Dict]:
        """Generate restocking recommendations"""
        recommendations = []
        for pred in predictions:
            if pred['demand_level'] in ['high', 'medium']:
                recommendations.append({
                    'product': pred['product'],
                    'action': 'restock',
                    'urgency': pred['demand_level'],
                    'suggested_quantity': int(pred['predicted_weekly_demand'] * 4)  # Monthly
                })
        return recommendations[:10]
    
    def _identify_demand_trends(self, conversations, product_mentions) -> Dict[str, str]:
        """Identify demand trends"""
        return {
            'overall_trend': 'increasing' if len(product_mentions) > 50 else 'stable',
            'top_category': 'general',
            'seasonal_pattern': 'analyzing'
        }


def get_inventory_predictor(business_id: str) -> InventoryPredictor:
    """Factory function"""
    return InventoryPredictor(business_id)

