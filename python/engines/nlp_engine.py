"""
Production-ready NLP Engine
Supports LLM-driven logic with rule-based fallbacks
"""

import logging
import asyncio
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import config

logger = logging.getLogger(__name__)

@dataclass
class NLPResult:
    """Result from NLP processing"""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    sentiment: Dict[str, Any]
    response: str
    metadata: Dict[str, Any]

class RuleBasedNLP:
    """Rule-based NLP engine for fallback scenarios"""
    
    def __init__(self):
        self.intent_patterns = self._load_intent_patterns()
        self.entity_patterns = self._load_entity_patterns()
        self.response_templates = self._load_response_templates()
        logger.info("Rule-based NLP engine initialized")
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """Load intent recognition patterns"""
        patterns = {
            "greeting": [
                r"\b(hello|hi|hey|good morning|good afternoon|good evening)\b",
                r"\b(howdy|greetings|salutations)\b"
            ],
            "product_inquiry": [
                r"\b(what do you (offer|have|sell)|tell me about|products|services)\b",
                r"\b(catalog|portfolio|solutions|offerings)\b",
                r"\b(show me|I want to see|looking for)\b.*\b(products|solutions)\b"
            ],
            "pricing": [
                r"\b(how much|cost|price|pricing|budget|expensive|cheap)\b",
                r"\b(rates|fees|charges|payment)\b",
                r"\b(what does it cost|how much is|price of)\b"
            ],
            "demo_request": [
                r"\b(demo|demonstration|trial|preview|test)\b",
                r"\b(show me|can I see|let me try)\b",
                r"\b(free trial|test drive|hands on)\b"
            ],
            "objection": [
                r"\b(too expensive|too much|can't afford|budget|think about it)\b",
                r"\b(not interested|maybe later|not now|not sure)\b",
                r"\b(need to discuss|talk to|consult with)\b"
            ],
            "positive_interest": [
                r"\b(interested|sounds good|perfect|exactly|great)\b",
                r"\b(yes|sure|okay|alright|sounds right)\b",
                r"\b(let's proceed|want to buy|ready to purchase)\b"
            ],
            "contact_info": [
                r"\b(my name is|I'm|call me)\b",
                r"\b(my email|email me|contact me)\b",
                r"\b(my number|phone|call)\b"
            ],
            "goodbye": [
                r"\b(bye|goodbye|see you|talk later|have a good)\b",
                r"\b(thanks|thank you|appreciate)\b.*\b(bye|goodbye)\b"
            ],
            "complaint": [
                r"\b(problem|issue|complaint|broken|doesn't work)\b",
                r"\b(frustrated|angry|upset|disappointed)\b",
                r"\b(terrible|awful|horrible|worst)\b"
            ],
            "support": [
                r"\b(help|support|assistance|problem|issue)\b",
                r"\b(how do I|can you help|need help)\b",
                r"\b(technical|trouble|difficulty)\b"
            ]
        }
        
        # Compile patterns for better performance
        compiled_patterns = {}
        for intent, pattern_list in patterns.items():
            compiled_patterns[intent] = [re.compile(p, re.IGNORECASE) for p in pattern_list]
        
        return compiled_patterns
    
    def _load_entity_patterns(self) -> Dict[str, re.Pattern]:
        """Load entity extraction patterns"""
        patterns = {
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "phone": re.compile(r'\b(\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'),
            "name": re.compile(r'\b(my name is|I\'m|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', re.IGNORECASE),
            "company": re.compile(r'\b(from|at|work for|company is)\s+([A-Z][a-zA-Z\s&.,]+(?:Inc|LLC|Corp|Ltd|Co)\.?)\b', re.IGNORECASE),
            "money": re.compile(r'\$([0-9,]+(?:\.[0-9]{2})?)\b'),
            "number": re.compile(r'\b([0-9,]+)\b'),
            "website": re.compile(r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'),
            "time": re.compile(r'\b(\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?|\d{1,2}\s*[AaPp][Mm])\b'),
            "date": re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|today|tomorrow|yesterday|next week|next month)\b', re.IGNORECASE)
        }
        
        return patterns
    
    def _load_response_templates(self) -> Dict[str, List[str]]:
        """Load response templates for different intents"""
        return {
            "greeting": [
                f"Hello! I'm {config.SALES_BOT_NAME} from {config.COMPANY_NAME}. How can I help you today?",
                f"Hi there! Welcome to {config.COMPANY_NAME}. What brings you here today?",
                f"Good day! I'm {config.SALES_BOT_NAME}, your sales assistant. What can I do for you?"
            ],
            "product_inquiry": [
                "We offer several excellent solutions. Let me tell you about our key products.",
                "I'd be happy to discuss our product portfolio with you.",
                "We have some great solutions that might be perfect for your needs."
            ],
            "pricing": [
                "I'd be happy to discuss pricing with you. Let me get some details about your needs first.",
                "Our pricing is very competitive. Can you tell me more about your requirements?",
                "Pricing varies based on your specific needs. What are you looking for?"
            ],
            "demo_request": [
                "I'd love to show you a demo! When would be a good time for you?",
                "Absolutely! A demo is the best way to see our solution in action.",
                "Great idea! Let me schedule a demo for you."
            ],
            "objection": [
                "I understand your concern. Many of our clients felt the same way initially.",
                "That's a valid point. Let me explain the value you'll get.",
                "I hear you. Let's discuss how we can work within your budget."
            ],
            "positive_interest": [
                "Excellent! I'm glad this sounds like a good fit for you.",
                "That's wonderful to hear! Let's move forward.",
                "Perfect! I think you'll really benefit from our solution."
            ],
            "contact_info": [
                "Thank you for that information. I'll make sure to follow up with you.",
                "Great! I have your details and will be in touch.",
                "Perfect! I'll add that to your profile."
            ],
            "goodbye": [
                "Thank you for your time! Have a great day!",
                "It was wonderful talking with you. Take care!",
                "Thanks for your interest. We'll be in touch soon!"
            ],
            "complaint": [
                "I'm sorry to hear about that issue. Let me see how I can help resolve this.",
                "I understand your frustration. Let's work together to fix this.",
                "Thank you for bringing this to my attention. I'll make sure we address it."
            ],
            "support": [
                "I'm here to help! What specific issue are you facing?",
                "Let me assist you with that. Can you provide more details?",
                "I'd be happy to help resolve that for you."
            ],
            "fallback": [
                "I'd be happy to help you with that. Can you tell me more?",
                "That's interesting. Let me see how I can assist you.",
                "Can you elaborate on that? I want to make sure I understand correctly."
            ]
        }
    
    def classify_intent(self, text: str) -> Tuple[str, float]:
        """Classify intent using rule-based patterns"""
        text_clean = text.lower().strip()
        
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(text_clean)
                if matches:
                    score += len(matches) * 0.3  # Base score for match
                    score += min(len(' '.join(matches)) / len(text_clean), 0.5)  # Coverage bonus
            
            if score > 0:
                intent_scores[intent] = min(score, 1.0)
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
            return best_intent, confidence
        
        return "fallback", 0.1
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities using regex patterns"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.findall(text)
            if matches:
                if entity_type in ["name", "company"]:
                    # These patterns capture groups
                    entities[entity_type] = [match[1] if isinstance(match, tuple) else match for match in matches]
                else:
                    entities[entity_type] = [match if isinstance(match, str) else ''.join(match) for match in matches]
        
        return entities
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Simple rule-based sentiment analysis"""
        text_lower = text.lower()
        
        positive_words = [
            'great', 'excellent', 'perfect', 'amazing', 'wonderful', 'fantastic',
            'love', 'like', 'good', 'nice', 'awesome', 'brilliant', 'outstanding',
            'yes', 'sure', 'absolutely', 'definitely', 'interested', 'excited'
        ]
        
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'poor',
            'disappointed', 'frustrated', 'angry', 'upset', 'wrong', 'broken',
            'no', 'not', 'never', 'expensive', 'costly', 'difficult', 'hard'
        ]
        
        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        
        if positive_score > negative_score:
            sentiment = "positive"
            polarity = min(0.1 + (positive_score - negative_score) * 0.2, 1.0)
        elif negative_score > positive_score:
            sentiment = "negative"
            polarity = max(-0.1 - (negative_score - positive_score) * 0.2, -1.0)
        else:
            sentiment = "neutral"
            polarity = 0.0
        
        return {
            "label": sentiment,
            "polarity": polarity,
            "confidence": min(abs(polarity) + 0.3, 1.0)
        }
    
    def generate_response(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Generate response based on intent and entities"""
        import random
        
        templates = self.response_templates.get(intent, self.response_templates["fallback"])
        base_response = random.choice(templates)
        
        # Customize response based on entities and context
        if intent == "product_inquiry" and config.PRODUCTS:
            product_names = [p.get("name", "") for p in config.PRODUCTS]
            base_response += f" Our main solutions are: {', '.join(product_names[:3])}."
        
        elif intent == "pricing" and config.PRODUCTS:
            cheapest_product = min(config.PRODUCTS, key=lambda p: self._extract_price(p.get("price", "$999")))
            base_response += f" For example, our {cheapest_product['name']} starts at {cheapest_product['price']}."
        
        elif intent == "contact_info" and entities:
            if "name" in entities:
                base_response = f"Nice to meet you, {entities['name'][0]}! " + base_response
        
        return base_response
    
    def _extract_price(self, price_str: str) -> float:
        """Extract numeric price from price string"""
        import re
        match = re.search(r'(\d+(?:\.\d{2})?)', price_str)
        return float(match.group(1)) if match else 999.0

class LLMBasedNLP:
    """LLM-based NLP engine using OpenAI"""
    
    def __init__(self):
        self.client = None
        try:
            import openai
            if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your-openai-api-key-here":
                self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
                logger.info("LLM-based NLP engine initialized")
            else:
                logger.warning("OpenAI API key not configured")
        except Exception as e:
            logger.error(f"Failed to initialize LLM NLP: {e}")
    
    def is_available(self) -> bool:
        """Check if LLM is available"""
        return self.client is not None
    
    async def analyze_text(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze text using LLM"""
        if not self.is_available():
            return None
        
        try:
            system_prompt = f"""
            You are an AI assistant for {config.COMPANY_NAME}. Analyze the customer's message and provide:
            
            1. Intent classification (one of: greeting, product_inquiry, pricing, demo_request, objection, positive_interest, contact_info, goodbye, complaint, support, fallback)
            2. Sentiment analysis (positive/negative/neutral with confidence 0-1)
            3. Entity extraction (names, emails, phones, companies, etc.)
            4. Confidence score (0-1) for intent classification
            
            Respond in JSON format:
            {{
                "intent": "intent_name",
                "intent_confidence": 0.8,
                "sentiment": {{"label": "positive", "confidence": 0.9}},
                "entities": {{"name": ["John"], "email": ["john@example.com"]}},
                "context_clues": ["any relevant context from the message"]
            }}
            
            Customer message: "{text}"
            """
            
            if context:
                system_prompt += f"\n\nConversation context: {json.dumps(context, indent=2)}"
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                logger.info(f"LLM analysis successful: {result['intent']} ({result['intent_confidence']})")
                return result
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from LLM: {result_text}")
                return None
                
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return None
    
    async def generate_response(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate response using LLM"""
        if not self.is_available():
            return None
        
        try:
            system_prompt = f"""
            You are {config.SALES_BOT_NAME}, a professional sales representative from {config.COMPANY_NAME}.
            
            Our products:
            {json.dumps(config.PRODUCTS, indent=2)}
            
            Guidelines:
            - Be helpful and consultative, not pushy
            - Ask qualifying questions naturally
            - Address objections with empathy
            - Provide specific product recommendations
            - Keep responses concise (2-3 sentences max)
            - Be professional but friendly
            
            Customer intent: {intent}
            Extracted entities: {json.dumps(entities)}
            Conversation context: {json.dumps(context, indent=2) if context else "None"}
            
            Generate an appropriate response for the customer.
            """
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=config.OPENAI_MODEL,
                messages=[{"role": "system", "content": system_prompt}],
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"LLM response generated: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"LLM response generation error: {e}")
            return None

class ProductionNLPEngine:
    """Production NLP Engine with LLM primary and rule-based fallback"""
    
    def __init__(self):
        self.llm_nlp = LLMBasedNLP()
        self.rule_nlp = RuleBasedNLP()
        self.prefer_llm = getattr(config, 'PREFER_LLM_NLP', True)
        logger.info(f"Production NLP Engine initialized (LLM available: {self.llm_nlp.is_available()})")
    
    async def process_text(self, text: str, context: Dict[str, Any] = None) -> NLPResult:
        """Process text with LLM primary and rule-based fallback"""
        
        # Try LLM first if available and preferred
        if self.prefer_llm and self.llm_nlp.is_available():
            try:
                llm_result = await self.llm_nlp.analyze_text(text, context)
                if llm_result:
                    # Generate response using LLM
                    response = await self.llm_nlp.generate_response(
                        llm_result["intent"],
                        llm_result.get("entities", {}),
                        context
                    )
                    
                    if response:
                        return NLPResult(
                            intent=llm_result["intent"],
                            confidence=llm_result["intent_confidence"],
                            entities=llm_result.get("entities", {}),
                            sentiment=llm_result.get("sentiment", {"label": "neutral", "confidence": 0.5}),
                            response=response,
                            metadata={"provider": "llm", "fallback": False}
                        )
            except Exception as e:
                logger.warning(f"LLM processing failed, using rule-based fallback: {e}")
        
        # Use rule-based approach
        intent, confidence = self.rule_nlp.classify_intent(text)
        entities = self.rule_nlp.extract_entities(text)
        sentiment = self.rule_nlp.analyze_sentiment(text)
        response = self.rule_nlp.generate_response(intent, entities, context)
        
        return NLPResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            sentiment=sentiment,
            response=response,
            metadata={"provider": "rules", "fallback": not self.llm_nlp.is_available()}
        )
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get status of NLP engines"""
        return {
            "llm_available": self.llm_nlp.is_available(),
            "rule_based_available": True,
            "preferred_engine": "llm" if self.prefer_llm else "rules",
            "fallback_enabled": True
        } 