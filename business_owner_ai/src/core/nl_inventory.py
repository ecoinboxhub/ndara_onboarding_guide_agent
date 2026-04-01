"""
Natural Language Inventory Interface AI
Converts natural language queries to structured inventory queries
"""

import logging
from typing import Dict, Any
import re

logger = logging.getLogger(__name__)


class NLInventory:
    """Converts natural language to structured inventory queries"""
    
    def __init__(self, business_id: str):
        self.business_id = business_id
    
    def parse_query(self, nl_query: str) -> Dict[str, Any]:
        """Parse natural language query into structured format"""
        try:
            nl_lower = nl_query.lower()
            
            # Determine query type
            query_type = self._determine_query_type(nl_lower)
            
            # Extract filters
            filters = self._extract_filters(nl_lower)
            
            # Determine sorting
            sort_by, sort_order = self._extract_sorting(nl_lower)
            
            # Extract limit
            limit = self._extract_limit(nl_lower)
            
            structured_query = {
                'query_type': query_type,
                'filters': filters,
                'sort_by': sort_by,
                'sort_order': sort_order,
                'limit': limit,
                'original_query': nl_query
            }
            
            # Generate SQL/NoSQL equivalent
            sql_query = self._generate_sql(structured_query)
            
            return {
                'success': True,
                'structured_query': structured_query,
                'sql_equivalent': sql_query,
                'explanation': self._generate_explanation(structured_query)
            }
        except Exception as e:
            logger.error(f"Error parsing query: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _determine_query_type(self, query) -> str:
        """Determine the type of query"""
        if any(word in query for word in ['show', 'list', 'display', 'get']):
            return 'list'
        elif any(word in query for word in ['count', 'how many']):
            return 'count'
        elif any(word in query for word in ['find', 'search']):
            return 'search'
        elif any(word in query for word in ['analyze', 'summary']):
            return 'analyze'
        else:
            return 'list'
    
    def _extract_filters(self, query) -> Dict[str, Any]:
        """Extract filter conditions"""
        filters = {}
        
        # Stock level
        if 'low stock' in query or 'running low' in query:
            filters['stock_level'] = 'low'
        elif 'out of stock' in query:
            filters['stock_level'] = 'zero'
        elif 'high stock' in query or 'overstocked' in query:
            filters['stock_level'] = 'high'
        
        # Price range
        price_match = re.search(r'under (\d+)|below (\d+)|less than (\d+)', query)
        if price_match:
            price = int(price_match.group(1) or price_match.group(2) or price_match.group(3))
            filters['price_max'] = price
        
        price_match = re.search(r'over (\d+)|above (\d+)|more than (\d+)', query)
        if price_match:
            price = int(price_match.group(1) or price_match.group(2) or price_match.group(3))
            filters['price_min'] = price
        
        # Category
        categories = ['electronics', 'clothing', 'food', 'furniture', 'accessories']
        for cat in categories:
            if cat in query:
                filters['category'] = cat
                break
        
        return filters
    
    def _extract_sorting(self, query) -> tuple:
        """Extract sorting preferences"""
        if 'most expensive' in query or 'highest price' in query:
            return ('price', 'desc')
        elif 'cheapest' in query or 'lowest price' in query:
            return ('price', 'asc')
        elif 'most popular' in query or 'best selling' in query:
            return ('sales_count', 'desc')
        elif 'newest' in query or 'latest' in query:
            return ('created_at', 'desc')
        else:
            return ('name', 'asc')
    
    def _extract_limit(self, query) -> int:
        """Extract result limit"""
        # Check for explicit numbers
        match = re.search(r'top (\d+)|first (\d+)', query)
        if match:
            return int(match.group(1) or match.group(2))
        return 100  # Default limit
    
    def _generate_sql(self, structured_query) -> str:
        """Generate SQL query equivalent"""
        sql = "SELECT * FROM inventory WHERE 1=1"
        
        filters = structured_query['filters']
        if 'stock_level' in filters:
            if filters['stock_level'] == 'low':
                sql += " AND stock_quantity < reorder_point"
            elif filters['stock_level'] == 'zero':
                sql += " AND stock_quantity = 0"
            elif filters['stock_level'] == 'high':
                sql += " AND stock_quantity > reorder_point * 2"
        
        if 'price_min' in filters:
            sql += f" AND price >= {filters['price_min']}"
        if 'price_max' in filters:
            sql += f" AND price <= {filters['price_max']}"
        if 'category' in filters:
            sql += f" AND category = '{filters['category']}'"
        
        sort_by = structured_query['sort_by']
        sort_order = structured_query['sort_order']
        sql += f" ORDER BY {sort_by} {sort_order.upper()}"
        sql += f" LIMIT {structured_query['limit']}"
        
        return sql
    
    def _generate_explanation(self, structured_query) -> str:
        """Generate human-readable explanation"""
        explanation = f"Query type: {structured_query['query_type']}\n"
        if structured_query['filters']:
            explanation += "Filters:\n"
            for key, value in structured_query['filters'].items():
                explanation += f"  - {key}: {value}\n"
        explanation += f"Sort by: {structured_query['sort_by']} ({structured_query['sort_order']})\n"
        explanation += f"Limit: {structured_query['limit']} results"
        return explanation


def get_nl_inventory(business_id: str) -> NLInventory:
    """Factory function"""
    return NLInventory(business_id)

