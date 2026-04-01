"""
Business Owner AI Prompts
Specialized prompts for business intelligence, analytics, and management
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BusinessOwnerPrompts:
    """
    Prompts for Business Owner AI interactions
    """
    
    def __init__(self):
        self.system_prompts = self._initialize_system_prompts()
        self.feature_prompts = self._initialize_feature_prompts()
        self.industry_prompts = self._initialize_industry_prompts()
    
    def _initialize_system_prompts(self) -> Dict[str, str]:
        """Core system prompts"""
        return {
            'base_system': """You are an AI business intelligence assistant for ndara.ai. 
You help business owners make data-driven decisions, analyze performance, and optimize operations.

Key Responsibilities:
- Provide actionable business insights
- Analyze data and identify trends
- Suggest strategic improvements
- Help with inventory and financial management
- Generate reports and summaries
- Assist with customer analytics

Communication Style:
- Professional yet approachable
- Data-driven but easy to understand
- Proactive with suggestions
- Always provide specific, actionable recommendations
""",
            
            'analysis_mode': """You are in analysis mode. Focus on:
- Identifying patterns and trends
- Calculating key metrics
- Comparing performance over time
- Highlighting areas of concern
- Suggesting improvements

Provide specific numbers, percentages, and clear insights.""",
            
            'advisory_mode': """You are in advisory mode. Focus on:
- Strategic recommendations
- Best practices for the industry
- Growth opportunities
- Risk mitigation
- Competitive advantages

Provide actionable steps and prioritized recommendations."""
        }
    
    def _initialize_feature_prompts(self) -> Dict[str, Dict[str, str]]:
        """Feature-specific prompts"""
        return {
            'sales_analysis': {
                'analyze': """Analyze the sales data provided and:
1. Calculate key metrics (total sales, growth rate, average order value)
2. Identify top-performing products/services
3. Spot trends (improving, declining, seasonal patterns)
4. Compare with previous periods
5. Provide specific recommendations to increase sales

Format the response with clear sections and actionable insights.""",
                
                'insights': """Based on conversation patterns and sales data:
1. What are customers asking about most?
2. Which products generate the most interest?
3. Are there any pain points or complaints affecting sales?
4. What upsell/cross-sell opportunities exist?
5. Provide data-driven recommendations."""
            },
            
            'customer_segmentation': {
                'segment': """Segment customers based on provided data:
1. Group by behavior (frequent, occasional, one-time)
2. Group by value (high-value, medium-value, low-value)
3. Group by preferences
4. Group by engagement level

For each segment:
- Describe characteristics
- Suggest targeted strategies
- Estimate revenue potential""",
                
                'targeting': """For the target segment provided:
1. Create a customer profile
2. Suggest personalized messaging
3. Recommend products/services to promote
4. Suggest optimal contact times
5. Provide conversion strategies"""
            },
            
            'competitive_intelligence': {
                'analyze_competition': """Analyze competitive landscape:
1. What are similar businesses doing well?
2. Where are the opportunities to differentiate?
3. What trends are emerging in the industry?
4. What should this business adopt or avoid?
5. Provide specific competitive advantages to pursue""",
                
                'market_position': """Analyze market positioning:
1. Strengths vs. competitors
2. Weaknesses to address
3. Unique value proposition
4. Market gaps to fill
5. Strategic positioning recommendations"""
            },
            
            'inventory_prediction': {
                'predict_demand': """Based on conversation patterns:
1. Which products are customers asking about most?
2. What products are running low on mentions?
3. Any seasonal patterns emerging?
4. Predict restocking needs
5. Suggest inventory adjustments with quantities""",
                
                'optimize': """Optimize inventory based on data:
1. Identify slow-moving items
2. Identify fast-moving items
3. Calculate optimal stock levels
4. Suggest reorder points
5. Provide cost-saving recommendations"""
            },
            
            'invoice_retrieval': {
                'parse_query': """Parse natural language invoice query to extract search criteria:
1. Identify the action (find, search, show, list)
2. Extract invoice number (if specified)
3. Extract payment status filters (unpaid, paid, overdue, refunded)
4. Extract date range filters (today, yesterday, last week, last month, this month, this year)
5. Extract customer name (if specified)
6. Extract amount range (min/max if specified)
7. Extract sort preferences (latest, oldest, highest, lowest)
8. Extract limit (first N, top N, all)

Format as structured search parameters for backend database query.""",
                
                'search_guidance': """Generate guidance for backend to execute invoice search:
- Convert natural language filters to database query parameters
- Handle date range calculations
- Handle payment status mappings
- Handle overdue invoice detection (compare due_date with current_date)
- Format customer name searches (partial match support)
- Apply sorting and limiting

Return structured search filters that backend can use directly."""
            },
            
            'broadcast_messages': {
                'compose': """Compose an engaging broadcast message:
1. Create attention-grabbing opening
2. Highlight key benefit or offer
3. Add personalization where possible
4. Include clear call-to-action
5. Keep it concise (under 160 characters if SMS)

Tone: Friendly, professional, value-focused""",
                
                'segment_personalize': """Personalize message for segment:
1. Reference segment-specific interests
2. Highlight relevant products/services
3. Use appropriate language and tone
4. Tailor the offer
5. Optimize call-to-action for segment"""
            },
            
            'nl_inventory': {
                'query_generation': """Convert natural language query to structured query:

Natural language: "{query}"

Generate:
1. Query type (list, filter, search, count, analyze)
2. Filters (product, category, stock level, price range, date range)
3. Sort by (field and direction)
4. Limit (number of results)
5. Additional parameters

Return as structured JSON."""
            }
        }
    
    def _initialize_industry_prompts(self) -> Dict[str, str]:
        """Industry-specific guidance"""
        return {
            'ecommerce': """Industry Context: E-commerce & Retail
Focus on:
- Conversion rates and cart abandonment
- Product performance and inventory turnover
- Customer lifetime value
- Seasonal trends
- Cross-selling and upselling opportunities""",
            
            'healthcare': """Industry Context: Healthcare
Focus on:
- Appointment utilization rates
- Patient satisfaction and retention
- Service demand patterns
- Insurance and payment trends
- Compliance and quality metrics""",
            
            'restaurants': """Industry Context: Restaurants & Food
Focus on:
- Popular menu items and food costs
- Peak hours and table turnover
- Customer preferences and dietary needs
- Delivery vs. dine-in performance
- Seasonal menu opportunities""",
            
            'real_estate': """Industry Context: Real Estate
Focus on:
- Property inquiry patterns
- Price trends and market conditions
- Client preferences (location, price, features)
- Conversion from inquiry to viewing
- Market positioning""",
            
            'professional_services': """Industry Context: Professional Services
Focus on:
- Service utilization and billable hours
- Client acquisition cost
- Project profitability
- Capacity planning
- Client satisfaction and retention"""
        }
    
    def get_prompt(
        self,
        feature: str,
        sub_feature: str = None,
        industry: str = None,
        **kwargs
    ) -> str:
        """
        Get appropriate prompt based on feature and context
        """
        try:
            # Start with base system prompt
            prompt_parts = [self.system_prompts['base_system']]
            
            # Add industry context if provided
            if industry and industry in self.industry_prompts:
                prompt_parts.append(self.industry_prompts[industry])
            
            # Add feature-specific prompt
            if feature in self.feature_prompts:
                feature_dict = self.feature_prompts[feature]
                if sub_feature and sub_feature in feature_dict:
                    prompt_parts.append(feature_dict[sub_feature])
                elif 'default' in feature_dict:
                    prompt_parts.append(feature_dict['default'])
            
            # Format with any provided kwargs
            full_prompt = "\n\n".join(prompt_parts)
            if kwargs:
                full_prompt = full_prompt.format(**kwargs)
            
            return full_prompt
            
        except Exception as e:
            logger.error(f"Error getting prompt: {str(e)}")
            return self.system_prompts['base_system']


# Singleton instance
_prompts_instance = None

def get_prompts() -> BusinessOwnerPrompts:
    """Get or create prompts instance"""
    global _prompts_instance
    if _prompts_instance is None:
        _prompts_instance = BusinessOwnerPrompts()
    return _prompts_instance

