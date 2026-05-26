"""
Multilingual chatbot service with sentiment analysis for Jharkhand Tourism AI Platform.
"""

import asyncio
import logging
from typing import Dict, List, Optional
import json
from textblob import TextBlob
from langdetect import detect, LangDetectError
import openai
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    AI-powered multilingual chatbot for tourism assistance.
    
    Features:
    - Multi-language support (Hindi, English, local languages)
    - Sentiment analysis of user messages
    - Tourism-specific knowledge base
    - Context-aware responses
    """
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key
        self.redis_client = None
        self.conversation_history = {}
        
    async def initialize(self):
        """Initialize the chatbot service."""
        try:
            # Initialize Redis for conversation storage
            self.redis_client = await aioredis.from_url("redis://localhost:6379/3")
            
            if self.openai_api_key:
                openai.api_key = self.openai_api_key
            
            logger.info("Chatbot service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize chatbot service: {e}")
            raise
    
    async def process_message(
        self, 
        user_id: str, 
        message: str, 
        language: str = None
    ) -> Dict:
        """
        Process user message and generate response.
        
        Args:
            user_id: User identifier
            message: User message
            language: Optional language hint
            
        Returns:
            Response with message, sentiment, and metadata
        """
        try:
            # Detect language if not provided
            detected_language = language or self._detect_language(message)
            
            # Analyze sentiment
            sentiment = self._analyze_sentiment(message)
            
            # Get conversation context
            context = await self._get_conversation_context(user_id)
            
            # Generate response
            response_text = await self._generate_response(
                message, 
                context, 
                detected_language,
                sentiment
            )
            
            # Store conversation
            await self._store_conversation(user_id, message, response_text, sentiment)
            
            response = {
                'message': response_text,
                'language': detected_language,
                'sentiment': sentiment,
                'suggestions': self._get_suggestions(message, sentiment),
                'timestamp': asyncio.get_event_loop().time()
            }
            
            logger.info(f"Processed message for user {user_id}: {sentiment['label']}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return {
                'message': 'I apologize, but I encountered an error. Please try again.',
                'language': 'en',
                'sentiment': {'label': 'neutral', 'score': 0.0},
                'suggestions': [],
                'error': str(e)
            }
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the input text."""
        try:
            detected = detect(text)
            return detected
        except LangDetectError:
            return 'en'  # Default to English
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of the input text."""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                label = 'positive'
            elif polarity < -0.1:
                label = 'negative'
            else:
                label = 'neutral'
            
            return {
                'label': label,
                'score': float(polarity),
                'subjectivity': float(blob.sentiment.subjectivity)
            }
            
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return {'label': 'neutral', 'score': 0.0, 'subjectivity': 0.0}
    
    async def _generate_response(
        self, 
        message: str, 
        context: List[Dict],
        language: str,
        sentiment: Dict
    ) -> str:
        """Generate AI response to user message."""
        try:
            # Create tourism-specific system prompt
            system_prompt = self._create_system_prompt(language, sentiment)
            
            # Create conversation messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add context from previous conversation
            for msg in context[-5:]:  # Last 5 messages for context
                messages.append({"role": "user", "content": msg.get('user_message', '')})
                messages.append({"role": "assistant", "content": msg.get('bot_response', '')})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Try to use OpenAI if available
            if self.openai_api_key:
                try:
                    response = await openai.ChatCompletion.acreate(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        max_tokens=200,
                        temperature=0.7
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    logger.warning(f"OpenAI API failed: {e}")
            
            # Fallback to rule-based responses
            return self._generate_rule_based_response(message, sentiment, language)
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "I'm here to help you with your Jharkhand tourism needs. How can I assist you?"
    
    def _create_system_prompt(self, language: str, sentiment: Dict) -> str:
        """Create system prompt for the AI assistant."""
        base_prompt = """You are a helpful tourism assistant for Jharkhand state in India. 
        You provide information about destinations, accommodations, transportation, local culture, and travel tips.
        Be friendly, informative, and culturally sensitive. Recommend specific places in Jharkhand."""
        
        if language == 'hi':
            base_prompt += " Respond in Hindi when appropriate."
        
        if sentiment['label'] == 'negative':
            base_prompt += " The user seems frustrated or disappointed. Be extra helpful and empathetic."
        elif sentiment['label'] == 'positive':
            base_prompt += " The user seems excited or happy. Match their enthusiasm."
        
        return base_prompt
    
    def _generate_rule_based_response(self, message: str, sentiment: Dict, language: str) -> str:
        """Generate rule-based response when AI is not available."""
        message_lower = message.lower()
        
        # Tourism-specific responses
        if any(word in message_lower for word in ['netarhat', 'hill station']):
            return "Netarhat is a beautiful hill station in Jharkhand, perfect for sunrise and sunset views. The best time to visit is between October and March."
        
        elif any(word in message_lower for word in ['betla', 'wildlife', 'tiger']):
            return "Betla National Park is excellent for wildlife enthusiasts! You can spot tigers, elephants, and many other species. Safari bookings are recommended in advance."
        
        elif any(word in message_lower for word in ['waterfall', 'hundru']):
            return "Jharkhand has stunning waterfalls! Hundru Falls near Ranchi is spectacular during monsoons. Other popular ones include Dassam Falls and Jonha Falls."
        
        elif any(word in message_lower for word in ['ranchi', 'capital']):
            return "Ranchi, the capital of Jharkhand, offers Rock Garden, Tagore Hill, and many lakes. It's a great base for exploring the state."
        
        elif any(word in message_lower for word in ['booking', 'hotel', 'accommodation']):
            return "I can help you find accommodations! Jharkhand offers everything from luxury hotels to budget guesthouses and eco-resorts."
        
        elif any(word in message_lower for word in ['transport', 'how to reach']):
            return "Jharkhand is well connected by rail, road, and air. Ranchi has an airport with regular flights from major cities."
        
        else:
            if sentiment['label'] == 'negative':
                return "I understand your concern. Let me help you find the best solution for your Jharkhand travel needs. What specific information are you looking for?"
            else:
                return "Welcome to Jharkhand! I'm here to help you discover amazing destinations, plan your itinerary, and make your trip memorable. What would you like to know?"
    
    def _get_suggestions(self, message: str, sentiment: Dict) -> List[str]:
        """Get contextual suggestions for the user."""
        suggestions = []
        message_lower = message.lower()
        
        if 'destination' in message_lower or 'place' in message_lower:
            suggestions.extend([
                "Tell me about Netarhat hill station",
                "Wildlife safari at Betla National Park",
                "Best waterfalls in Jharkhand"
            ])
        
        elif 'plan' in message_lower or 'itinerary' in message_lower:
            suggestions.extend([
                "3-day Jharkhand itinerary",
                "Best time to visit Jharkhand",
                "Budget planning for Jharkhand trip"
            ])
        
        elif 'hotel' in message_lower or 'stay' in message_lower:
            suggestions.extend([
                "Hotels in Ranchi",
                "Eco-resorts near Netarhat",
                "Budget accommodations in Jharkhand"
            ])
        
        # Add general suggestions if none specific
        if not suggestions:
            suggestions = [
                "Popular destinations in Jharkhand",
                "Cultural experiences in Jharkhand",
                "Adventure activities available"
            ]
        
        return suggestions[:3]  # Return top 3 suggestions
    
    async def _get_conversation_context(self, user_id: str) -> List[Dict]:
        """Get conversation history for context."""
        try:
            if self.redis_client:
                conversation_data = await self.redis_client.get(f"conversation:{user_id}")
                if conversation_data:
                    return json.loads(conversation_data)
        except Exception as e:
            logger.warning(f"Failed to get conversation context: {e}")
        
        return []
    
    async def _store_conversation(
        self, 
        user_id: str, 
        user_message: str, 
        bot_response: str, 
        sentiment: Dict
    ):
        """Store conversation in Redis."""
        try:
            if self.redis_client:
                # Get existing conversation
                context = await self._get_conversation_context(user_id)
                
                # Add new exchange
                context.append({
                    'user_message': user_message,
                    'bot_response': bot_response,
                    'sentiment': sentiment,
                    'timestamp': asyncio.get_event_loop().time()
                })
                
                # Keep only last 20 exchanges
                context = context[-20:]
                
                # Store back to Redis with 1 hour TTL
                await self.redis_client.setex(
                    f"conversation:{user_id}",
                    3600,
                    json.dumps(context, default=str)
                )
        except Exception as e:
            logger.warning(f"Failed to store conversation: {e}")
    
    async def get_sentiment_analytics(self, time_period: str = '24h') -> Dict:
        """Get sentiment analytics from user interactions."""
        try:
            # Mock analytics (would query actual data in production)
            analytics = {
                'total_conversations': 156,
                'sentiment_distribution': {
                    'positive': 60,
                    'neutral': 80,
                    'negative': 16
                },
                'common_topics': [
                    {'topic': 'destinations', 'count': 45},
                    {'topic': 'accommodations', 'count': 32},
                    {'topic': 'transportation', 'count': 28}
                ],
                'satisfaction_score': 4.2
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get sentiment analytics: {e}")
            return {}
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.redis_client:
                await self.redis_client.close()
            logger.info("Chatbot service cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


if __name__ == "__main__":
    # Test the chatbot service
    async def test_chatbot():
        service = ChatbotService()
        await service.initialize()
        
        # Test messages
        test_messages = [
            "Hello, I want to visit Jharkhand",
            "Tell me about waterfalls",
            "I'm disappointed with the weather forecast"
        ]
        
        for i, message in enumerate(test_messages):
            response = await service.process_message(f"user_{i}", message)
            print(f"User: {message}")
            print(f"Bot: {response['message']}")
            print(f"Sentiment: {response['sentiment']}")
            print("---")
        
        await service.cleanup()
    
    asyncio.run(test_chatbot())