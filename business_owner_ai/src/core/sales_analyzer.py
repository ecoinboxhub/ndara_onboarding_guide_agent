"""
Sales Performance Insights AI
Analyzes conversation patterns and sales data for actionable insights
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import statistics

logger = logging.getLogger(__name__)


class SalesAnalyzer:
    """
    Analyzes sales performance from conversation and transaction data
    """
    
    def __init__(self, business_id: str):
        self.business_id = business_id
    
    def analyze_sales_performance(
        self,
        conversations: List[Dict[str, Any]],
        sales_data: List[Dict[str, Any]] = None,
        time_period: str = 'last_30_days'
    ) -> Dict[str, Any]:
        """
        Comprehensive sales performance analysis
        
        Returns:
            - key_metrics: Dict (total sales, growth, avg order value, etc.)
            - top_products: List[Dict]
            - trends: Dict
            - insights: List[str]
            - recommendations: List[str]
        """
        try:
            # Analyze conversation patterns
            conversation_insights = self._analyze_conversation_patterns(conversations)
            
            # Analyze sales data if provided
            sales_insights = {}
            if sales_data:
                sales_insights = self._analyze_sales_data(sales_data)
            
            # Calculate key metrics
            key_metrics = self._calculate_key_metrics(conversations, sales_data)
            
            # Identify trends
            trends = self._identify_trends(conversations, sales_data)
            
            # Generate insights
            insights = self._generate_insights(
                conversation_insights,
                sales_insights,
                key_metrics,
                trends
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(insights, trends)
            
            return {
                'key_metrics': key_metrics,
                'conversation_insights': conversation_insights,
                'sales_insights': sales_insights,
                'trends': trends,
                'insights': insights,
                'recommendations': recommendations,
                'analysis_period': time_period,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sales performance: {str(e)}")
            return {
                'error': str(e),
                'insights': [],
                'recommendations': []
            }
    
    def _analyze_conversation_patterns(
        self,
        conversations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze patterns in customer conversations"""
        try:
            total_conversations = len(conversations)
            
            # Extract all customer messages
            all_intents = []
            all_sentiments = []
            product_mentions = Counter()
            complaint_count = 0
            purchase_intent_count = 0
            
            for conv in conversations:
                messages = conv.get('messages', [])
                for msg in messages:
                    if msg.get('role') == 'customer':
                        # Extract intent
                        metadata = msg.get('metadata', {})
                        if 'intent' in metadata:
                            intent = metadata['intent']
                            all_intents.append(intent)
                            if intent == 'complaint':
                                complaint_count += 1
                            elif intent in ['purchase', 'product_inquiry']:
                                purchase_intent_count += 1
                        
                        # Extract sentiment
                        if 'sentiment' in metadata:
                            all_sentiments.append(metadata['sentiment'])
                        
                        # Extract product mentions (simple keyword matching)
                        content = msg.get('content', '').lower()
                        # This would be enhanced with actual product matching
                        product_mentions.update([content])
            
            # Calculate sentiment distribution
            sentiment_dist = Counter([s.get('sentiment') if isinstance(s, dict) else s for s in all_sentiments])
            
            return {
                'total_conversations': total_conversations,
                'top_intents': Counter(all_intents).most_common(5),
                'sentiment_distribution': dict(sentiment_dist),
                'complaint_rate': complaint_count / total_conversations if total_conversations > 0 else 0,
                'purchase_intent_rate': purchase_intent_count / total_conversations if total_conversations > 0 else 0,
                'avg_sentiment_score': self._calculate_avg_sentiment(all_sentiments)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation patterns: {str(e)}")
            return {}
    
    def _analyze_sales_data(self, sales_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze actual sales transactions"""
        try:
            if not sales_data:
                return {}
            
            total_sales = sum(sale.get('amount', 0) for sale in sales_data)
            total_transactions = len(sales_data)
            avg_order_value = total_sales / total_transactions if total_transactions > 0 else 0
            
            # Product performance
            product_sales = Counter()
            product_revenue = Counter()
            
            for sale in sales_data:
                items = sale.get('items', [])
                for item in items:
                    product_name = item.get('name')
                    quantity = item.get('quantity', 1)
                    price = item.get('price', 0)
                    
                    product_sales[product_name] += quantity
                    product_revenue[product_name] += quantity * price
            
            # Top performers
            top_by_volume = product_sales.most_common(5)
            top_by_revenue = product_revenue.most_common(5)
            
            # Time analysis
            sales_by_date = self._group_sales_by_date(sales_data)
            
            return {
                'total_revenue': total_sales,
                'total_transactions': total_transactions,
                'avg_order_value': avg_order_value,
                'top_products_by_volume': top_by_volume,
                'top_products_by_revenue': top_by_revenue,
                'sales_by_date': sales_by_date
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sales data: {str(e)}")
            return {}
    
    def _calculate_key_metrics(
        self,
        conversations: List[Dict[str, Any]],
        sales_data: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate key performance metrics"""
        try:
            metrics = {
                'total_conversations': len(conversations),
                'conversation_to_sale_rate': 0.0,
                'avg_conversation_length': 0.0,
                'customer_satisfaction_score': 0.0
            }
            
            # Calculate conversation length
            lengths = []
            satisfaction_ratings = []
            
            for conv in conversations:
                messages = conv.get('messages', [])
                lengths.append(len(messages))
                
                # Extract satisfaction if available
                if 'feedback' in conv:
                    rating = conv['feedback'].get('rating')
                    if rating:
                        satisfaction_ratings.append(rating)
            
            if lengths:
                metrics['avg_conversation_length'] = statistics.mean(lengths)
            
            if satisfaction_ratings:
                metrics['customer_satisfaction_score'] = statistics.mean(satisfaction_ratings)
            
            # Conversion rate
            if sales_data:
                metrics['conversion_rate'] = len(sales_data) / len(conversations) if conversations else 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating key metrics: {str(e)}")
            return {}
    
    def _identify_trends(
        self,
        conversations: List[Dict[str, Any]],
        sales_data: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Identify trends in data"""
        try:
            trends = {
                'conversation_volume_trend': 'stable',
                'sentiment_trend': 'neutral',
                'sales_trend': 'stable'
            }
            
            # Analyze conversation volume over time
            if len(conversations) >= 7:
                # Group by date
                conv_by_date = {}
                for conv in conversations:
                    date = conv.get('created_at', '')[:10]  # Extract date
                    conv_by_date[date] = conv_by_date.get(date, 0) + 1
                
                # Simple trend detection
                dates = sorted(conv_by_date.keys())
                if len(dates) >= 2:
                    recent_avg = statistics.mean([conv_by_date[d] for d in dates[-3:]])
                    earlier_avg = statistics.mean([conv_by_date[d] for d in dates[:3]])
                    
                    if recent_avg > earlier_avg * 1.2:
                        trends['conversation_volume_trend'] = 'increasing'
                    elif recent_avg < earlier_avg * 0.8:
                        trends['conversation_volume_trend'] = 'decreasing'
            
            # Analyze sentiment trend
            sentiments = []
            for conv in conversations:
                for msg in conv.get('messages', []):
                    if msg.get('role') == 'customer' and 'sentiment' in msg.get('metadata', {}):
                        sentiment_data = msg['metadata']['sentiment']
                        if isinstance(sentiment_data, dict):
                            score = sentiment_data.get('score', 0)
                            sentiments.append(score)
            
            if len(sentiments) >= 10:
                recent_sentiment = statistics.mean(sentiments[-10:])
                earlier_sentiment = statistics.mean(sentiments[:10])
                
                if recent_sentiment > earlier_sentiment + 0.1:
                    trends['sentiment_trend'] = 'improving'
                elif recent_sentiment < earlier_sentiment - 0.1:
                    trends['sentiment_trend'] = 'declining'
            
            return trends
            
        except Exception as e:
            logger.error(f"Error identifying trends: {str(e)}")
            return {}
    
    def _generate_insights(
        self,
        conversation_insights: Dict[str, Any],
        sales_insights: Dict[str, Any],
        key_metrics: Dict[str, Any],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable insights"""
        insights = []
        
        try:
            # Conversation insights
            total_convs = conversation_insights.get('total_conversations', 0)
            if total_convs > 0:
                complaint_rate = conversation_insights.get('complaint_rate', 0)
                if complaint_rate > 0.15:
                    insights.append(
                        f"⚠️ High complaint rate ({complaint_rate:.1%}). "
                        f"Consider investigating common issues."
                    )
                
                purchase_rate = conversation_insights.get('purchase_intent_rate', 0)
                if purchase_rate > 0.3:
                    insights.append(
                        f"📈 Strong purchase intent ({purchase_rate:.1%}). "
                        f"Good opportunity for conversion optimization."
                    )
            
            # Sales insights
            if sales_insights:
                avg_order = sales_insights.get('avg_order_value', 0)
                if avg_order > 0:
                    insights.append(
                        f"💰 Average order value: ₦{avg_order:,.2f}. "
                        f"Consider upselling strategies."
                    )
                
                top_products = sales_insights.get('top_products_by_revenue', [])
                if top_products:
                    top_product = top_products[0][0]
                    insights.append(
                        f"⭐ Best performer: {top_product}. "
                        f"Consider promoting similar products."
                    )
            
            # Trend insights
            if trends.get('conversation_volume_trend') == 'increasing':
                insights.append(
                    "📊 Conversation volume is increasing. "
                    "Ensure adequate support capacity."
                )
            elif trends.get('conversation_volume_trend') == 'decreasing':
                insights.append(
                    "📉 Conversation volume is decreasing. "
                    "Consider marketing initiatives to drive engagement."
                )
            
            if trends.get('sentiment_trend') == 'declining':
                insights.append(
                    "😟 Customer sentiment is declining. "
                    "Review recent changes and address common concerns."
                )
            elif trends.get('sentiment_trend') == 'improving':
                insights.append(
                    "😊 Customer sentiment is improving. "
                    "Continue current strategies."
                )
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return ["Unable to generate insights due to error"]
    
    def _generate_recommendations(
        self,
        insights: List[str],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        try:
            # Based on trends
            if trends.get('sentiment_trend') == 'declining':
                recommendations.append(
                    "1. Conduct customer feedback survey to identify pain points"
                )
                recommendations.append(
                    "2. Review and improve response quality and resolution time"
                )
            
            if trends.get('conversation_volume_trend') == 'increasing':
                recommendations.append(
                    "1. Consider expanding customer support capacity"
                )
                recommendations.append(
                    "2. Implement automated responses for common queries"
                )
            
            # General recommendations
            recommendations.append(
                "3. Monitor top-performing products and ensure adequate stock"
            )
            recommendations.append(
                "4. Analyze customer feedback to improve products/services"
            )
            recommendations.append(
                "5. Implement loyalty program for repeat customers"
            )
            
            return recommendations[:5]  # Top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []
    
    def _calculate_avg_sentiment(self, sentiments: List[Any]) -> float:
        """Calculate average sentiment score"""
        try:
            scores = []
            for s in sentiments:
                if isinstance(s, dict):
                    score = s.get('score', 0)
                    scores.append(score)
                elif isinstance(s, (int, float)):
                    scores.append(s)
            
            return statistics.mean(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating avg sentiment: {str(e)}")
            return 0.0
    
    def _group_sales_by_date(self, sales_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Group sales by date"""
        try:
            sales_by_date = {}
            for sale in sales_data:
                date = sale.get('date', '')[:10]
                amount = sale.get('amount', 0)
                sales_by_date[date] = sales_by_date.get(date, 0) + amount
            
            return sales_by_date
            
        except Exception as e:
            logger.error(f"Error grouping sales by date: {str(e)}")
            return {}
    
    def detect_performance_drop(
        self,
        current_metrics: Dict[str, Any],
        previous_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect if there's a performance drop"""
        try:
            drops = []
            
            # Check revenue drop
            current_revenue = current_metrics.get('total_revenue', 0)
            previous_revenue = previous_metrics.get('total_revenue', 0)
            
            if previous_revenue > 0:
                revenue_change = (current_revenue - previous_revenue) / previous_revenue
                if revenue_change < -0.15:  # 15% drop
                    drops.append({
                        'metric': 'revenue',
                        'change': revenue_change,
                        'severity': 'high' if revenue_change < -0.3 else 'medium',
                        'message': f"Revenue dropped by {abs(revenue_change):.1%}"
                    })
            
            # Check conversion rate drop
            current_conversion = current_metrics.get('conversion_rate', 0)
            previous_conversion = previous_metrics.get('conversion_rate', 0)
            
            if previous_conversion > 0:
                conversion_change = (current_conversion - previous_conversion) / previous_conversion
                if conversion_change < -0.2:  # 20% drop
                    drops.append({
                        'metric': 'conversion_rate',
                        'change': conversion_change,
                        'severity': 'high' if conversion_change < -0.4 else 'medium',
                        'message': f"Conversion rate dropped by {abs(conversion_change):.1%}"
                    })
            
            return {
                'has_drop': len(drops) > 0,
                'drops': drops,
                'severity': 'high' if any(d['severity'] == 'high' for d in drops) else 'medium',
                'requires_attention': len(drops) > 0
            }
            
        except Exception as e:
            logger.error(f"Error detecting performance drop: {str(e)}")
            return {'has_drop': False, 'drops': []}


def get_sales_analyzer(business_id: str) -> SalesAnalyzer:
    """Factory function to get sales analyzer instance"""
    return SalesAnalyzer(business_id)

