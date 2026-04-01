"""
OpenAI Service for Business Owner AI
Handles all OpenAI API calls for generating business intelligence responses
"""

import os
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI integration"""
    
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - NLP responses will not be generated")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', 0.7))
    
    def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Generate a response from OpenAI
        
        Args:
            prompt: The user query/prompt
            system_message: Optional system message to set context
            max_tokens: Maximum tokens in response
        
        Returns:
            Dict with success status, response text, and token usage
        """
        try:
            messages = []
            
            if system_message:
                messages.append({
                    "role": "system",
                    "content": system_message
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            logger.debug(f"Calling OpenAI API with model={self.model}, max_tokens={max_tokens}")
            logger.debug(f"Prompt preview: {prompt[:100]}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            
            logger.info(f"OpenAI response received - Tokens used: {response.usage.total_tokens}")
            logger.debug(f"Response preview: {response.choices[0].message.content[:100]}...")
            
            return {
                'success': True,
                'response': response.choices[0].message.content,
                'tokens_used': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        except Exception as e:
            logger.error(f"Error generating response from OpenAI: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'response': None
            }
    
    def classify_intent(
        self,
        query: str,
        system_message: str,
        function_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify intent using OpenAI function calling
        
        Args:
            query: The user query to classify
            system_message: System message with intent descriptions
            function_definition: Function definition for classification
        
        Returns:
            Dict with primary_intent, confidence, extracted_parameters, secondary_intents
        """
        try:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ]
            
            logger.debug(f"Classifying intent for query: {query[:100]}...")
            
            # Use GPT-3.5-turbo for faster, cheaper classification
            classification_model = os.getenv('CLASSIFICATION_MODEL', 'gpt-3.5-turbo')
            
            response = self.client.chat.completions.create(
                model=classification_model,
                messages=messages,
                functions=[function_definition],
                function_call={"name": function_definition["name"]},
                temperature=0.3  # Lower temperature for more consistent classification
            )
            
            # Extract function call arguments
            function_call = response.choices[0].message.function_call
            if function_call:
                import json
                result = json.loads(function_call.arguments)
                logger.info(f"Intent classified: {result.get('primary_intent')} (confidence: {result.get('confidence', 0):.2f})")
                return result
            else:
                logger.warning("No function call in response, returning default")
                return {
                    'primary_intent': 'general',
                    'confidence': 0.3,
                    'extracted_parameters': {},
                    'secondary_intents': []
                }
                
        except Exception as e:
            logger.error(f"Error in intent classification: {str(e)}", exc_info=True)
            raise  # Re-raise to trigger fallback in caller
    
    def generate_sales_analysis_response(
        self,
        query: str,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate conversational NLP response for sales analysis"""
        system_message = """You are a friendly and professional business intelligence AI assistant specialized in sales analysis.

Your role:
- Engage with the business owner in a warm, conversational manner
- Provide clear, actionable insights based on the data
- Be encouraging and supportive about their performance
- Point out both wins and areas for improvement tactfully
- Keep responses natural and easy to understand
- Use emojis sparingly to add warmth (📊 💰 📈 ✨)
- End with a helpful suggestion or question to keep the conversation going

Tone: Professional but friendly, like a knowledgeable colleague who cares about their success."""
        
        prompt = f"""The business owner asked: "{query}"

Here's their sales analysis data:
{self._format_data(analysis_data)}

Provide a warm, conversational response that:
1. Addresses their specific question
2. Highlights key insights from the data
3. Offers 1-2 actionable recommendations
4. Keeps it concise (3-5 sentences)
5. Ends with engagement (e.g., "Would you like me to dig deeper into any specific area?")"""
        
        return self.generate_response(prompt, system_message, max_tokens=400)
    
    def generate_inventory_response(
        self,
        query: str,
        parsed_query: Dict[str, Any],
        search_filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate conversational NLP response for inventory queries"""
        system_message = """You are a friendly business intelligence AI assistant specialized in inventory management.

Your role:
- Help business owners understand their inventory in plain language
- Be proactive about alerting to stock issues
- Suggest practical next steps
- Keep responses clear and conversational
- Show empathy for their operational challenges

Tone: Helpful and supportive, like a trusted operations manager."""
        
        prompt = f"""The business owner asked: "{query}"

Parsed intent:
- Action: {parsed_query.get('action')}
- Filters: {self._format_data(search_filters)}

Provide a friendly, conversational response that:
1. Confirms what they're looking for
2. Explains what the search will find
3. Suggests helpful next steps or related actions
4. Keeps it brief (2-3 sentences)

Example tone: "I'll search for products with low stock levels. This will help you identify items that might need reordering soon. Would you like me to also check for any items that are completely out of stock?"
"""
        
        return self.generate_response(prompt, system_message, max_tokens=300)
    
    def generate_invoice_response(
        self,
        query: str,
        parsed_query: Dict[str, Any],
        search_filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate conversational NLP response for invoice queries"""
        system_message = """You are a friendly business intelligence AI assistant specialized in invoice management.

Your role:
- Help business owners track payments and billing in simple terms
- Be professional but approachable about financial matters
- Offer practical suggestions for payment follow-up
- Keep responses clear and actionable

Tone: Professional and reassuring, like a trusted bookkeeper."""
        
        prompt = f"""The business owner asked: "{query}"

Search intent:
- Action: {parsed_query.get('action')}
- Filters: {self._format_data(search_filters)}

Provide a conversational response that:
1. Confirms what invoices they're looking for
2. Explains the search clearly
3. Offers a helpful next step (e.g., "Once I find them, would you like help following up on overdue payments?")
4. Keep it brief (2-3 sentences)"""
        
        return self.generate_response(prompt, system_message, max_tokens=300)
    
    def generate_appointment_response(
        self,
        query: str,
        parsed_query: Dict[str, Any],
        appointments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate conversational NLP response for appointment queries"""
        system_message = """You are a friendly business intelligence AI assistant specialized in appointment management.

Your role:
- Help business owners manage their schedule naturally
- Be warm and helpful about their appointments
- Suggest practical scheduling actions
- Keep responses conversational and brief

Tone: Supportive and organized, like a personal assistant."""
        
        appointments_summary = ""
        if appointments:
            appointments_summary = f"\n\nFound {len(appointments)} appointment(s):\n{self._format_data(appointments[:3])}"
        
        prompt = f"""The business owner asked: "{query}"

Intent:
- Action: {parsed_query.get('action')}
- Filters: {self._format_data(parsed_query.get('filters', {}))}
{appointments_summary}

Provide a warm, conversational response that:
1. Addresses their question naturally
2. Summarizes what was found (if any)
3. Offers a helpful suggestion
4. Keep it friendly and brief (2-4 sentences)

Example: "You have 3 appointments scheduled for today! The first one is at 9am with Sarah. Would you like me to show you the full details or help you reschedule any of them?"
"""
        
        return self.generate_response(prompt, system_message, max_tokens=300)
    
    def generate_general_response(self, query: str) -> Dict[str, Any]:
        """Generate NLP response for general queries"""
        system_message = """You are a friendly and professional business intelligence AI assistant for business owners.

Your role:
- Engage naturally in conversation, including greetings and casual chat
- Be warm, approachable, and helpful
- When asked about capabilities, mention you can help with: sales analysis, customer segmentation, inventory management, invoice tracking, appointment scheduling, and broadcast messaging
- For greetings like "Hi" or "How are you?", respond warmly and naturally, then offer to help
- Keep responses conversational and friendly, like a helpful colleague
- If the query is unclear, ask clarifying questions about what they need help with

Tone: Professional but friendly, warm and approachable."""
        
        prompt = f"""The business owner said: "{query}"

Provide a natural, conversational response. If it's a greeting, respond warmly. If they're asking about what you can do, explain your capabilities. If unclear, ask what they'd like help with."""
        
        return self.generate_response(prompt, system_message, max_tokens=400)
    
    def _format_data(self, data: Any) -> str:
        """Format data for inclusion in prompts"""
        if isinstance(data, dict):
            return "\n".join([f"  {k}: {v}" for k, v in data.items()])
        elif isinstance(data, list):
            if not data:
                return "  (empty)"
            return "\n".join([f"  - {item}" for item in data[:5]])
        else:
            return str(data)


def get_openai_service() -> OpenAIService:
    """Factory function to get OpenAI service instance"""
    return OpenAIService()
