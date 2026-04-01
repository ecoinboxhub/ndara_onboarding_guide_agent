"""
Human Behavior Simulator
Simulates natural human agent behaviors for realistic AI interactions
"""

import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class HumanBehaviorSimulator:
    """
    Simulates natural human agent behaviors to make AI indistinguishable from humans
    """
    
    def __init__(self, personality_type: str = 'professional_warm'):
        self.personality_type = personality_type
        self.personalities = self._initialize_personalities()
    
    def _initialize_personalities(self) -> Dict[str, Dict[str, Any]]:
        """Initialize personality configurations"""
        return {
            'friendly_casual': {
                'greeting_style': ['Hey!', 'Hi there!', 'Hello!', 'Good to hear from you!', 'Hi!'],
                'acknowledgments': ['Got it!', 'Sure thing!', 'Absolutely!', 'No problem!', 'Cool!'],
                'closing': ['Cheers!', 'Take care!', 'Have a great day!', 'Talk soon!', 'Catch you later!'],
                'thinking': ['Let me see...', 'Hmm...', 'Give me a sec...', 'One moment...', 'Lemme check...'],
                'typo_frequency': 0.02,      # 2% chance of casual typo
                'emoji_usage': 0.15,         # 15% chance of emoji
                'exclamation_usage': 0.25,   # 25% chance of !
                'checking_frequency': 0.20    # 20% chance to "check"
            },
            
            'nigerian_business': {
                'greeting_style': ['Good morning!', 'Hello!', 'Good afternoon!', 'Hi!', 'How can I help?'],
                'acknowledgments': ['Got it!', 'Sure!', 'No problem!', 'Okay!', 'Fine!'],
                'closing': ['Thanks!', 'No problem!', 'You\'re welcome!', 'Talk soon!', 'See you!'],
                'thinking': ['Let me check...', 'Let me see...', 'Hmm...', 'One moment...', 'Let me look...'],
                'typo_frequency': 0.01,      # 1% chance of casual typo
                'emoji_usage': 0.10,         # 10% chance of emoji (less than casual)
                'exclamation_usage': 0.20,   # 20% chance of !
                'checking_frequency': 0.30    # 30% chance to "check" (Nigerians like to confirm)
            },
            
            'professional_warm': {
                'greeting_style': ['Good morning!', 'Good afternoon!', 'Hello!', 'Hi!', 'Welcome!'],
                'acknowledgments': ['Certainly', 'Of course', 'I understand', 'Noted', 'Understood'],
                'closing': ['Best regards', 'Kind regards', 'Thank you!', 'Have a great day!', 'Take care!'],
                'thinking': ['Let me check that', 'Allow me to verify', 'One moment please', 'Let me look into that'],
                'typo_frequency': 0.0,       # Professional = fewer typos
                'emoji_usage': 0.05,         # 5% chance of emoji
                'exclamation_usage': 0.10,   # 10% chance of !
                'checking_frequency': 0.15    # 15% chance to "check"
            },
            
            'expert_consultant': {
                'greeting_style': ['Hello', 'Hi', 'Good day', 'Greetings'],
                'acknowledgments': ['Understood', 'I see', 'Right', 'Makes sense', 'Correct'],
                'closing': ['Let me know if you need anything else', 'Happy to help further', 'Feel free to reach out'],
                'thinking': ['Let me look into that', 'Based on our records', 'From what I can see', 'Let me verify'],
                'typo_frequency': 0.0,
                'emoji_usage': 0.0,          # No emojis for expert
                'exclamation_usage': 0.05,
                'checking_frequency': 0.25    # 25% chance to "check" (thorough)
            }
        }
    
    def calculate_typing_delay(self, response_text: str, message_complexity: str = 'medium') -> float:
        """
        Calculate realistic typing delay for 40 WPM max (as requested)
        
        Human typing speed: 40 words per minute maximum
        With thinking pauses: adds 1-3 seconds for complex responses
        
        Returns: Delay in seconds (min 2s, max 15s)
        """
        try:
            word_count = len(response_text.split())
            
            # Base typing time (40 wpm maximum as requested)
            base_time = (word_count / 40) * 60
            
            # Add thinking pauses for complex indicators
            complex_indicators = ['however', 'although', 'specifically', 'regarding', 'particularly']
            pause_time = sum(2 if ind in response_text.lower() else 0 for ind in complex_indicators)
            
            # Add complexity-based delay
            complexity_delays = {
                'simple': 0,
                'medium': 1,
                'complex': 2
            }
            complexity_delay = complexity_delays.get(message_complexity, 1)
            
            # Add random human variation (±30%)
            variation = random.uniform(0.8, 1.3)
            
            total_delay = (base_time + pause_time + complexity_delay) * variation
            
            # Minimum 2 seconds (human reading + thinking), maximum 15 seconds
            return max(2.0, min(total_delay, 15.0))
            
        except Exception as e:
            logger.error(f"Error calculating typing delay: {str(e)}")
            return 3.0  # Default 3 seconds
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split response into sentences
        """
        import re
        
        # Split by sentence endings, but preserve some natural flow
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        # Clean up empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # If no sentences found, return the whole text
        if not sentences:
            return [text.strip()]
        
        return sentences
    
    def calculate_sentence_delay(self, sentence: str) -> float:
        """
        Calculate delay for individual sentence (40 WPM max)
        """
        try:
            word_count = len(sentence.split())
            
            # 40 WPM maximum typing speed
            base_time = (word_count / 40) * 60
            
            # Add small thinking pause between sentences
            thinking_pause = random.uniform(0.5, 1.5)
            
            # Add random variation
            variation = random.uniform(0.8, 1.2)
            
            total_delay = (base_time + thinking_pause) * variation
            
            # Minimum 1 second, maximum 8 seconds per sentence
            return max(1.0, min(total_delay, 8.0))
            
        except Exception as e:
            logger.error(f"Error calculating sentence delay: {str(e)}")
            return 2.0  # Default 2 seconds
    
    def add_human_imperfections(self, response: str, confidence: float) -> str:
        """
        Add natural human imperfections to response
        
        - Occasional casual language
        - Self-corrections
        - Appropriate emojis
        - "Checking" behavior when uncertain
        - Shorter, more natural responses
        """
        try:
            # ONLY replace AI-like phrases with natural Nigerian alternatives
            # All other "human imperfections" removed for ultra-concise responses
            response = self.replace_ai_phrases(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error adding human imperfections: {str(e)}")
            return response
    
    def _shorten_response(self, response: str) -> str:
        """
        Make responses shorter and more natural (like a real human would type)
        """
        try:
            # If response is too long, try to make it more concise
            if len(response.split()) > 15:  # More than 15 words (ultra-concise)
                # Try to break into shorter sentences
                sentences = self.split_into_sentences(response)
                
                # Take only the first 2-3 sentences for initial response
                if len(sentences) > 2:
                    response = ". ".join(sentences[:2]) + "."
                    
                    # Add a follow-up indicator
                    if random.random() < 0.3:
                        response += " Let me know if you need more details!"
            
            return response
            
        except Exception as e:
            logger.error(f"Error shortening response: {str(e)}")
            return response
    
    def replace_ai_phrases(self, response: str) -> str:
        """
        Replace AI-like phrases with natural Nigerian alternatives.
        Uses case-insensitive matching via regex so mixed-case phrases are caught.
        """
        import re

        try:
            ai_phrase_replacements = {
                "I noticed you're interested": "You want",
                "I understand you're looking for": "You need",
                "Based on your inquiry": "You asked about",
                "I can see that you": "You want",
                "It appears you're": "You need",
                "I notice you want": "You want",
                "I can help you with that": "Sure!",
                "I would be happy to provide": "I can give you",
                "I would be happy to": "I can",
                "I'm here to assist": "I can help",
                "How may I help you today": "What can I do for you",
                "I would be delighted to": "I can",
                "I shall investigate": "I'll check",
                "I apologize for any inconvenience": "Sorry about that",
                "Please allow me to": "Let me",
                "comprehensive information": "details",
                "detailed information": "info",
                "I understand your frustration": "I know how you feel",
                "I totally understand": "I get it",
                "I can see that": "You want",
                "It seems like you": "You need",
                "Based on what you've said": "You want",
                "I understand that you": "You want",
                "I can help you with": "I can help with",
                "I would be glad to": "I can",
                "I'm happy to": "I can",
                "I'd be happy to": "I can",
            }

            for ai_phrase, nigerian_alternative in ai_phrase_replacements.items():
                response = re.sub(
                    re.escape(ai_phrase), nigerian_alternative, response, flags=re.IGNORECASE
                )

            return response

        except Exception as e:
            logger.error(f"Error replacing AI phrases: {str(e)}")
            return response
    
    def make_ultra_concise(self, response: str, customer_query: str) -> str:
        """
        Make response ultra-concise based on customer query type and communication style
        """
        try:
            query_lower = customer_query.lower()
            
            # Detect customer's communication style
            communication_style = self._detect_communication_style(customer_query)
            
            # Check if customer wants detailed explanation
            detail_keywords = ['tell me more', 'explain', 'details', 'about', 'what is', 'describe']
            wants_details = any(keyword in query_lower for keyword in detail_keywords)
            
            if wants_details:
                # Customer explicitly asked for details, keep response as is
                return response
            
            # Ultra-concise rules based on query type
            if any(word in query_lower for word in ['what services', 'what do you offer', 'services']):
                # Service list - return complete sentence with names
                return self._extract_service_names_complete(response, communication_style)
            
            elif any(word in query_lower for word in ['do you deliver', 'delivery', 'available', 'have you got']):
                # Yes/No with one detail - complete sentence
                return self._extract_yes_no_with_detail_complete(response, communication_style)
            
            elif any(word in query_lower for word in ['price', 'cost', 'how much', 'jollof', 'facial', 'massage']):
                # Product inquiry - name + price in complete sentence
                return self._extract_name_and_price_complete(response, communication_style)
            
            else:
                # Default: keep under 15 words but ensure complete sentence
                words = response.split()
                if len(words) > 15:
                    # Try to end at a natural sentence boundary
                    for i in range(15, 0, -1):
                        if i < len(words) and words[i-1].endswith(('.', '!', '?')):
                            return ' '.join(words[:i])
                    return ' '.join(words[:15])
                return response
                
        except Exception as e:
            logger.error(f"Error making ultra-concise: {str(e)}")
            return response
    
    def _detect_communication_style(self, customer_query: str) -> str:
        """
        Detect customer's communication style: formal or informal.
        We never return 'pidgin'; respond in professional English only.
        """
        try:
            query_lower = customer_query.lower()
            
            # Formal indicators (proper English greetings and polite phrases)
            formal_words = ['please', 'kindly', 'would you', 'could you', 'may i', 'good morning', 'good afternoon', 'good evening', 'sir', 'madam']
            formal_count = sum(1 for word in formal_words if word in query_lower)
            
            # Informal indicators (casual greetings)
            informal_words = ['hey', 'hi there', 'what\'s up', 'cool', 'awesome', 'yeah', 'nah', 'sup']
            informal_count = sum(1 for word in informal_words if word in query_lower)
            
            if formal_count >= 1:
                return 'formal'
            elif informal_count >= 1:
                return 'informal'
            else:
                return 'formal'
                
        except Exception as e:
            logger.error(f"Error detecting communication style: {str(e)}")
            return 'formal'
    
    def _extract_service_names(self, response: str) -> str:
        """Extract just service names from response"""
        try:
            # Look for service patterns and extract names only
            services = []
            service_keywords = ['facial', 'massage', 'consultation', 'treatment', 'therapy']
            
            for keyword in service_keywords:
                if keyword in response.lower():
                    services.append(keyword.title())
            
            if services:
                return ', '.join(services)
            else:
                # Fallback: return first 10 words
                words = response.split()[:10]
                return ' '.join(words)
                
        except Exception as e:
            logger.error(f"Error extracting service names: {str(e)}")
            return response
    
    def _extract_yes_no_with_detail(self, response: str) -> str:
        """Extract yes/no answer with one key detail"""
        try:
            # Look for yes/no indicators
            if any(word in response.lower() for word in ['yes', 'sure', 'available']):
                # Extract time/detail info
                time_patterns = ['30-45 min', '1 hour', '2 hours', 'same day', 'next day']
                for pattern in time_patterns:
                    if pattern in response.lower():
                        return f"Yes, {pattern}"
                return "Yes"
            elif any(word in response.lower() for word in ['no', 'not available', 'sorry']):
                return "No"
            else:
                # Fallback: return first 8 words
                words = response.split()[:8]
                return ' '.join(words)
                
        except Exception as e:
            logger.error(f"Error extracting yes/no with detail: {str(e)}")
            return response
    
    def _extract_name_and_price(self, response: str) -> str:
        """Extract product name and price"""
        try:
            # Look for price patterns
            import re
            price_match = re.search(r'₦[\d,]+', response)
            if price_match:
                price = price_match.group()
                # Extract product name (first few words before price)
                words = response.split()
                price_index = next((i for i, word in enumerate(words) if '₦' in word), -1)
                if price_index > 0:
                    product_name = ' '.join(words[:price_index])
                    return f"{product_name}. {price}"
            
            # Fallback: return first 10 words
            words = response.split()[:10]
            return ' '.join(words)
            
        except Exception as e:
            logger.error(f"Error extracting name and price: {str(e)}")
            return response
    
    def should_say_checking(self, query: str, confidence: float) -> bool:
        """
        Determine if agent should say "let me check"
        
        Humans don't know everything instantly
        """
        try:
            query_lower = query.lower()
            personality = self.personalities.get(self.personality_type, self.personalities['professional_warm'])
            
            # Determine query complexity
            checking_keywords = [
                'price', 'cost', 'available', 'in stock',
                'schedule', 'appointment', 'when', 'what time',
                'specific', 'exactly', 'precisely', 'how many'
            ]
            
            has_checking_keywords = any(kw in query_lower for kw in checking_keywords)
            is_complex = query_lower.count('?') > 1 or len(query.split()) > 20
            
            # Base probability from personality
            base_prob = personality['checking_frequency']
            
            # Increase probability if:
            if has_checking_keywords:
                base_prob += 0.15
            if is_complex:
                base_prob += 0.10
            if confidence < 0.7:
                base_prob += 0.20
            
            return random.random() < min(base_prob, 0.6)  # Max 60% chance
            
        except Exception as e:
            logger.error(f"Error in should_say_checking: {str(e)}")
            return False
    
    def generate_checking_response(self, query: str = None) -> str:
        """Generate natural 'checking' response"""
        try:
            personality = self.personalities.get(self.personality_type, self.personalities['professional_warm'])
            return random.choice(personality['thinking'])
        except Exception:
            return "Let me check that for you..."
    
    def generate_availability_response(self, hour: int) -> Optional[str]:
        """
        Add natural availability cues based on time
        
        If it's 2 AM, a human agent wouldn't be available unless 24/7
        """
        try:
            if 0 <= hour < 6:  # Late night/early morning
                return "Thanks for reaching out! Our team is currently offline but I'm here to help. How can I assist you?"
            elif 22 <= hour <= 23:  # Late evening
                return "Hi! I'm still here to help before we close for the day. What can I do for you?"
            
            return None  # Normal hours, no special message
            
        except Exception as e:
            logger.error(f"Error generating availability response: {str(e)}")
            return None
    
    def get_time_appropriate_greeting(self, hour: int, timezone: str = 'WAT') -> str:
        """Return time-appropriate greeting"""
        try:
            personality = self.personalities.get(self.personality_type, self.personalities['professional_warm'])
            
            if 0 <= hour < 6:
                # Late night - unusual time
                return "Hi! Up late? How can I help?"
            elif 6 <= hour < 12:
                # Morning
                greetings = ['Good morning! How can I help you today?', 'Morning! What can I do for you?']
                return random.choice(greetings)
            elif 12 <= hour < 17:
                # Afternoon
                greetings = ['Good afternoon! What can I do for you?', 'Afternoon! How can I help?']
                return random.choice(greetings)
            elif 17 <= hour < 21:
                # Evening
                greetings = ['Good evening! How may I assist you?', 'Evening! What can I help with?']
                return random.choice(greetings)
            else:
                # Late night (9 PM - midnight)
                return "Hi! Still here to help. What can I do for you?"
                
        except Exception as e:
            logger.error(f"Error getting time-appropriate greeting: {str(e)}")
            return random.choice(self.personalities['professional_warm']['greeting_style'])
    
    def add_time_context(self, response: str, hour: int, business_hours: Dict[str, str] = None) -> str:
        """Add time-relevant context to response"""
        try:
            # If business hours provided, check if open
            if business_hours:
                is_open = self._is_business_open(hour, business_hours)
                
                if not is_open:
                    response += "\n\nJust so you know, we're currently closed, but we'll be open tomorrow. You can still place orders online though!"
                elif self._is_peak_hour(hour):
                    response += "\n\nHeads up - we're pretty busy right now, but we'll take good care of you!"
            
            return response
            
        except Exception as e:
            logger.error(f"Error adding time context: {str(e)}")
            return response
    
    def get_varied_greeting(self) -> str:
        """Get varied greeting to avoid repetition"""
        try:
            personality = self.personalities.get(self.personality_type, self.personalities['professional_warm'])
            return random.choice(personality['greeting_style'])
        except Exception:
            return "Hello! How can I help you?"
    
    def get_varied_acknowledgment(self, sentiment: str = 'neutral') -> str:
        """Get varied acknowledgment based on sentiment"""
        try:
            personality = self.personalities.get(self.personality_type, self.personalities['professional_warm'])
            
            if sentiment == 'positive':
                options = ["Awesome!", "Perfect!", "Great!", "Fantastic!"] if self.personality_type == 'friendly_casual' else ["Excellent", "Very good", "Perfect"]
            else:
                options = personality['acknowledgments']
            
            return random.choice(options)
        except Exception:
            return "Understood"
    
    def get_varied_closing(self) -> str:
        """Get varied closing phrase"""
        try:
            personality = self.personalities.get(self.personality_type, self.personalities['professional_warm'])
            return random.choice(personality['closing'])
        except Exception:
            return "Thank you!"
    
    def add_nigerian_context(self, response: str, use_slang: bool = False) -> str:
        """
        Ensure currency and formatting; no Pidgin or slang.
        Response stays in professional English only.
        """
        try:
            # Ensure currency symbol is correct only
            response = response.replace('$', '₦').replace('NGN', '₦')
            return response
        except Exception as e:
            logger.error(f"Error adding Nigerian context: {str(e)}")
            return response
    
    def _is_business_open(self, hour: int, business_hours: Dict[str, str]) -> bool:
        """Check if business is currently open"""
        try:
            # Simplified check - would be more sophisticated in production
            current_day = datetime.now().strftime('%A').lower()
            hours = business_hours.get(current_day, '')
            
            if not hours or hours.lower() == 'closed':
                return False
            
            # Parse hours (e.g., "10:00-22:00")
            if '-' in hours:
                open_time, close_time = hours.split('-')
                open_hour = int(open_time.split(':')[0])
                close_hour = int(close_time.split(':')[0])
                
                return open_hour <= hour < close_hour
            
            return True
        except Exception:
            return True  # Assume open if can't determine
    
    def _is_peak_hour(self, hour: int) -> bool:
        """Check if it's peak business hour"""
        # Generally 12-2 PM (lunch) and 6-8 PM (dinner/after work)
        return (12 <= hour <= 14) or (18 <= hour <= 20)
    
    def _extract_service_names_complete(self, response: str, communication_style: str) -> str:
        """Extract service names in complete sentence based on communication style"""
        try:
            services = []
            service_keywords = ['facial', 'massage', 'consultation', 'treatment', 'therapy']
            
            for keyword in service_keywords:
                if keyword in response.lower():
                    services.append(keyword.title())
            
            if services:
                if communication_style == 'formal':
                    return f"We offer {', '.join(services)}. Which service interests you?"
                else:
                    return f"We have {', '.join(services)}. Which one?"
            else:
                # Fallback: return first 10 words
                words = response.split()[:10]
                return ' '.join(words)
                
        except Exception as e:
            logger.error(f"Error extracting service names complete: {str(e)}")
            return response
    
    def _extract_yes_no_with_detail_complete(self, response: str, communication_style: str) -> str:
        """Extract yes/no answer with one key detail in complete sentence"""
        try:
            # Look for yes/no indicators
            if any(word in response.lower() for word in ['yes', 'sure', 'available']):
                # Extract time/detail info
                time_patterns = ['30-45 min', '1 hour', '2 hours', 'same day', 'next day']
                for pattern in time_patterns:
                    if pattern in response.lower():
                        if communication_style == 'formal':
                            return f"Yes, we deliver within {pattern}"
                        else:
                            return f"Yes, we deliver in {pattern}"
                if communication_style == 'formal':
                    return "Yes, we provide delivery service"
                else:
                    return "Yes, we deliver"
            elif any(word in response.lower() for word in ['no', 'not available', 'sorry']):
                if communication_style == 'formal':
                    return "No, delivery is not available"
                else:
                    return "No, we don't deliver"
            else:
                # Fallback: return first 8 words
                words = response.split()[:8]
                return ' '.join(words)
                
        except Exception as e:
            logger.error(f"Error extracting yes/no with detail complete: {str(e)}")
            return response
    
    def _extract_name_and_price_complete(self, response: str, communication_style: str) -> str:
        """Extract product name and price in complete sentence"""
        try:
            # Look for price patterns
            import re
            price_match = re.search(r'₦[\d,]+', response)
            if price_match:
                price = price_match.group()
                # Extract product name (first few words before price)
                words = response.split()
                price_index = next((i for i, word in enumerate(words) if '₦' in word), -1)
                if price_index > 0:
                    product_name = ' '.join(words[:price_index])
                    if communication_style == 'formal':
                        return f"{product_name} costs {price}"
                    else:
                        return f"{product_name} is {price}"
            
            # Fallback: return first 10 words
            words = response.split()[:10]
            return ' '.join(words)
            
        except Exception as e:
            logger.error(f"Error extracting name and price complete: {str(e)}")
            return response


def get_human_behavior_simulator(personality_type: str = 'professional_warm') -> HumanBehaviorSimulator:
    """Factory function to get simulator instance"""
    return HumanBehaviorSimulator(personality_type)

