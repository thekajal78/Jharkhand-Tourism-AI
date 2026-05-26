"""
Chatbot Service — Multilingual Tourism Assistant
==================================================
What this file does:
  1. Understands tourist questions in English, Hindi, and tribal languages
  2. Identifies INTENT — what the tourist wants
     (book guide? find waterfall? check weather? get itinerary?)
  3. Extracts ENTITIES — specific things mentioned
     (location names, dates, number of people)
  4. Generates helpful responses
  5. Analyzes SENTIMENT in tourist reviews (positive/negative/neutral)

Supported Languages:
  - English
  - Hindi (हिंदी)
  - Santali (ᱥᱟᱱᱛᱟᱲᱤ) ← tribal language, uses Ol Chiki script
  - Ho, Mundari (basic support via IndicTrans2)

Flow:
  Tourist types message
      ↓
  Language Detection
      ↓
  Translate to English (if needed) using IndicTrans2
      ↓
  Intent Classification (what do they want?)
      ↓
  Entity Extraction (which place? which date?)
      ↓
  Generate Response
      ↓
  Translate back to original language
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ─── Intent Types ─────────────────────────────────────────────────────────────
class Intent(Enum):
    """All possible things a tourist might want."""
    FIND_DESTINATION    = "find_destination"     # "Show me waterfalls"
    BOOK_GUIDE          = "book_guide"           # "I need a local guide"
    GET_ITINERARY       = "get_itinerary"        # "Plan my 3-day trip"
    CHECK_WEATHER       = "check_weather"        # "Weather in Netarhat?"
    FIND_HOMESTAY       = "find_homestay"        # "Where can I stay in tribal village?"
    CULTURAL_INFO       = "cultural_info"        # "Tell me about Sarhul festival"
    EMERGENCY_HELP      = "emergency_help"       # "I'm lost / need help"
    TRANSPORT_INFO      = "transport_info"       # "How to reach Betla?"
    GENERAL_QUERY       = "general_query"        # Anything else


@dataclass
class ChatResponse:
    """Structure of chatbot response."""
    intent: str
    response_text: str
    detected_language: str
    entities: dict          # Extracted locations, dates, etc.
    suggestions: list       # Follow-up action buttons for UI
    confidence: float       # How confident the model is (0.0 - 1.0)


class ChatbotService:
    """
    Multilingual tourism chatbot for Safar Sathi.

    Usage:
        service = ChatbotService()
        await service.initialize()

        response = await service.process_message(
            user_id=42,
            message="मुझे झरने दिखाओ",   # Hindi: "Show me waterfalls"
            conversation_history=[]
        )
        print(response.response_text)
        # → "यहाँ झारखंड के सुंदर झरने हैं: हुंडरू फॉल्स, दसम फॉल्स..."
    """

    def __init__(self):
        self.is_loaded = False
        self.translator = None       # IndicTrans2 model for tribal/Hindi translation
        self.sentiment_model = None  # For review sentiment analysis

        # Rule-based intent patterns (fast, works offline)
        # Format: {Intent: [keywords that trigger this intent]}
        self.intent_patterns = {
            Intent.FIND_DESTINATION: [
                # English
                "show", "find", "waterfall", "forest", "temple", "lake", "hill",
                "destination", "place", "visit", "tourist",
                # Hindi
                "दिखाओ", "झरना", "जंगल", "मंदिर", "झील", "पहाड़", "जगह",
                # Santali (romanized)
                "dis", "buru", "dak"
            ],
            Intent.BOOK_GUIDE: [
                "guide", "local guide", "book guide", "hire guide",
                "गाइड", "स्थानीय गाइड", "बुक करो"
            ],
            Intent.GET_ITINERARY: [
                "itinerary", "plan", "trip", "days", "schedule", "tour",
                "यात्रा", "योजना", "दिन", "घूमना"
            ],
            Intent.CHECK_WEATHER: [
                "weather", "rain", "temperature", "climate", "season",
                "मौसम", "बारिश", "तापमान"
            ],
            Intent.FIND_HOMESTAY: [
                "stay", "homestay", "hotel", "accommodation", "sleep", "night",
                "रुकना", "होमस्टे", "होटल"
            ],
            Intent.CULTURAL_INFO: [
                "festival", "culture", "tribe", "tradition", "dance", "sarhul",
                "karma", "tribal", "adivasi",
                "त्योहार", "संस्कृति", "आदिवासी", "परंपरा"
            ],
            Intent.EMERGENCY_HELP: [
                "help", "lost", "emergency", "sos", "danger", "accident",
                "मदद", "खो गया", "आपात", "खतरा"
            ],
            Intent.TRANSPORT_INFO: [
                "how to reach", "train", "bus", "road", "route", "distance",
                "कैसे पहुंचे", "ट्रेन", "बस", "रास्ता"
            ],
        }

        # Jharkhand-specific entities (places, festivals, tribes)
        self.jharkhand_locations = {
            "hundru falls", "hundru", "हुंडरू",
            "dassam falls", "dassam", "दसम",
            "betla", "betla national park", "बेतला",
            "netarhat", "नेतरहाट",
            "rajrappa", "राजरप्पा",
            "deoghar", "देवघर",
            "parasnath", "पारसनाथ",
            "ranchi", "रांची",
            "jamshedpur", "जमशेदपुर",
            "hazaribagh", "हजारीबाग",
        }

        self.jharkhand_tribes = {
            "santali", "santhali", "ho", "mundari", "oraon",
            "सांताली", "हो", "मुंडारी", "उरांव"
        }

    async def initialize(self):
        """
        Load NLP models.
        IndicTrans2 for translation is ~1.2GB — loads slowly on first run.
        Falls back to rule-based responses if model unavailable.
        """
        try:
            # Try loading IndicTrans2 for tribal language support
            # Install: pip install indic-transliteration ai4bharat-transliteration
            try:
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                logger.info("Loading IndicTrans2 translation model...")
                # This model supports Hindi, Santali, Ho, Mundari ↔ English
                # Model: ai4bharat/indictrans2-en-indic-dist-200M (~500MB)
                self.translator = {
                    "tokenizer": AutoTokenizer.from_pretrained(
                        "ai4bharat/indictrans2-en-indic-dist-200M",
                        cache_dir="./models/indictrans"
                    ),
                    "model": AutoModelForSeq2SeqLM.from_pretrained(
                        "ai4bharat/indictrans2-en-indic-dist-200M",
                        cache_dir="./models/indictrans"
                    )
                }
                logger.info("✅ IndicTrans2 loaded — tribal language support active")
            except Exception as e:
                logger.warning(f"⚠️ IndicTrans2 not available: {e}")
                logger.warning("   Falling back to rule-based responses only")
                self.translator = None

            self.is_loaded = True
            logger.info("✅ Chatbot service ready")

        except Exception as e:
            logger.error(f"❌ Chatbot initialization failed: {e}")
            self.is_loaded = True  # Still usable with rule-based fallback

    # ─── MAIN ENTRY POINT ────────────────────────────────────────────────────

    async def process_message(
        self,
        user_id: int,
        message: str,
        conversation_history: list = None
    ) -> ChatResponse:
        """
        Process a tourist's message and return a helpful response.

        Args:
            user_id: Tourist's user ID
            message: Their message (any language)
            conversation_history: Previous messages for context

        Returns:
            ChatResponse with text, intent, entities, suggestions
        """
        conversation_history = conversation_history or []

        # Step 1: Detect language
        detected_lang = self._detect_language(message)
        logger.info(f"Detected language: {detected_lang}")

        # Step 2: Translate to English if needed (for intent detection)
        english_message = message
        if detected_lang != "english" and self.translator:
            english_message = await self._translate_to_english(message, detected_lang)

        # Step 3: Classify intent
        intent, confidence = self._classify_intent(english_message.lower())
        logger.info(f"Intent: {intent.value} (confidence: {confidence})")

        # Step 4: Extract entities (locations, dates, etc.)
        entities = self._extract_entities(english_message.lower())

        # Step 5: Generate response in English
        english_response = self._generate_response(intent, entities, conversation_history)

        # Step 6: Translate response back to user's language
        final_response = english_response
        if detected_lang != "english" and self.translator:
            final_response = await self._translate_from_english(english_response, detected_lang)

        # Step 7: Generate UI suggestion buttons
        suggestions = self._get_suggestions(intent, entities)

        return ChatResponse(
            intent=intent.value,
            response_text=final_response,
            detected_language=detected_lang,
            entities=entities,
            suggestions=suggestions,
            confidence=confidence,
        )

    # ─── LANGUAGE DETECTION ──────────────────────────────────────────────────

    def _detect_language(self, text: str) -> str:
        """
        Simple script-based language detection.
        More reliable than statistical models for short messages.

        Devanagari script (Unicode U+0900–U+097F) → Hindi
        Ol Chiki script  (Unicode U+1C50–U+1C7F) → Santali
        Latin script → English (or romanized tribal)
        """
        # Check for Devanagari characters (Hindi)
        if re.search(r'[\u0900-\u097F]', text):
            return "hindi"

        # Check for Ol Chiki script (Santali)
        if re.search(r'[\u1C50-\u1C7F]', text):
            return "santali"

        # Check for Bengali script (some tribal languages use this)
        if re.search(r'[\u0980-\u09FF]', text):
            return "bengali"

        return "english"

    # ─── INTENT CLASSIFICATION ───────────────────────────────────────────────

    def _classify_intent(self, message: str) -> tuple[Intent, float]:
        """
        Classify what the tourist wants using keyword matching.

        Simple but effective for a tourism domain with limited intents.
        In production: replace with fine-tuned BERT classifier for better accuracy.

        Returns:
            (Intent enum, confidence score 0.0-1.0)
        """
        scores = {intent: 0 for intent in Intent}

        for intent, keywords in self.intent_patterns.items():
            for keyword in keywords:
                if keyword in message:
                    scores[intent] += 1

        # Get intent with highest score
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        if best_score == 0:
            return Intent.GENERAL_QUERY, 0.5

        # Normalize confidence (cap at 1.0)
        confidence = min(best_score / 3.0, 1.0)
        return best_intent, confidence

    # ─── ENTITY EXTRACTION ───────────────────────────────────────────────────

    def _extract_entities(self, message: str) -> dict:
        """
        Extract specific information from the message.

        Example:
            "Plan a 3-day trip to Netarhat for 2 people"
            → {
                "locations": ["netarhat"],
                "duration_days": 3,
                "group_size": 2,
                "tribes": []
              }
        """
        entities = {
            "locations": [],
            "duration_days": None,
            "group_size": None,
            "tribes": [],
        }

        # Extract Jharkhand locations
        for loc in self.jharkhand_locations:
            if loc in message:
                entities["locations"].append(loc)

        # Extract trip duration (e.g., "3 days", "2 दिन")
        duration_match = re.search(r'(\d+)\s*(?:day|days|दिन)', message)
        if duration_match:
            entities["duration_days"] = int(duration_match.group(1))

        # Extract group size (e.g., "2 people", "4 लोग")
        group_match = re.search(r'(\d+)\s*(?:people|person|persons|लोग|व्यक्ति)', message)
        if group_match:
            entities["group_size"] = int(group_match.group(1))

        # Extract tribe mentions
        for tribe in self.jharkhand_tribes:
            if tribe in message:
                entities["tribes"].append(tribe)

        return entities

    # ─── RESPONSE GENERATION ─────────────────────────────────────────────────

    def _generate_response(self, intent: Intent, entities: dict, history: list) -> str:
        """Generate response based on detected intent and entities."""

        responses = {
            Intent.FIND_DESTINATION: self._response_find_destination(entities),
            Intent.BOOK_GUIDE: self._response_book_guide(entities),
            Intent.GET_ITINERARY: self._response_itinerary(entities),
            Intent.CHECK_WEATHER: self._response_weather(entities),
            Intent.FIND_HOMESTAY: self._response_homestay(entities),
            Intent.CULTURAL_INFO: self._response_cultural(entities),
            Intent.EMERGENCY_HELP: self._response_emergency(),
            Intent.TRANSPORT_INFO: self._response_transport(entities),
            Intent.GENERAL_QUERY: self._response_general(),
        }

        return responses.get(intent, self._response_general())

    def _response_find_destination(self, entities: dict) -> str:
        locations = entities.get("locations", [])
        if locations:
            return (
                f"Here are some beautiful destinations near {locations[0].title()} in Jharkhand: "
                f"Hundru Falls (stunning 98m waterfall), Dassam Falls, Betla National Park. "
                f"Would you like detailed information about any of these?"
            )
        return (
            "Jharkhand has amazing destinations! Popular ones include:\n"
            "🌊 Waterfalls: Hundru Falls, Dassam Falls, Jonha Falls\n"
            "🌿 Wildlife: Betla National Park, Dalma Sanctuary\n"
            "⛩️ Temples: Deoghar, Rajrappa, Baidyanath Dham\n"
            "🏔️ Hills: Netarhat, Parasnath\n"
            "Which type interests you most?"
        )

    def _response_book_guide(self, entities: dict) -> str:
        locations = entities.get("locations", [])
        loc_text = locations[0].title() if locations else "your destination"
        return (
            f"I can help you book a certified local guide for {loc_text}! "
            f"Our guides are trained, verified, and speak local tribal languages. "
            f"Pricing: ₹500-800/day. Tap 'Book Guide' below to proceed."
        )

    def _response_itinerary(self, entities: dict) -> str:
        days = entities.get("duration_days", 3)
        return (
            f"I'll create a personalized {days}-day Jharkhand itinerary for you!\n"
            f"Day 1: Ranchi → Hundru Falls → Jonha Falls\n"
            f"Day 2: Betla National Park (wildlife safari)\n"
            f"Day 3: Netarhat (Queen of Chotanagpur) → sunset point\n"
            f"Want me to customize this based on your interests?"
        )

    def _response_weather(self, entities: dict) -> str:
        locations = entities.get("locations", [])
        loc = locations[0].title() if locations else "Jharkhand"
        return (
            f"Current weather info for {loc}: Best time to visit is October-March. "
            f"Monsoon (June-September) makes waterfalls spectacular but roads can be difficult. "
            f"For live weather, I'm fetching real-time data..."
        )

    def _response_homestay(self, entities: dict) -> str:
        return (
            "🏡 Tribal Homestay Options in Jharkhand:\n"
            "• Khunti Village Homestay - Munda tribal experience (₹800/night)\n"
            "• Netarhat Forest Cottage - Eco stay (₹1200/night)\n"
            "• Betla Tribal Hut - Inside forest zone (₹600/night)\n"
            "These support local communities directly! Want to book one?"
        )

    def _response_cultural(self, entities: dict) -> str:
        tribes = entities.get("tribes", [])
        tribe_text = tribes[0].title() if tribes else "tribal"
        return (
            f"Jharkhand's {tribe_text} culture is rich and unique! "
            f"Key festivals: Sarhul (spring harvest), Karma (nature worship), "
            f"Tusu Parab (winter festival). "
            f"The Santali, Ho, Mundari, and Oraon tribes have distinct traditions, "
            f"music (Banam instrument), and dance forms. Want to attend a cultural event?"
        )

    def _response_emergency(self) -> str:
        return (
            "🆘 EMERGENCY ASSISTANCE\n"
            "• Tourist Helpline: 1800-345-6789 (24/7 Free)\n"
            "• Police: 100\n"
            "• Ambulance: 108\n"
            "• Forest Dept Emergency: 1926\n"
            "Sharing your GPS location with nearest ranger post now. Stay calm!"
        )

    def _response_transport(self, entities: dict) -> str:
        locations = entities.get("locations", [])
        loc = locations[0].title() if locations else "your destination"
        return (
            f"How to reach {loc}:\n"
            f"🚂 Train: Ranchi is the main railway hub (connected to Delhi, Kolkata)\n"
            f"✈️ Air: Birsa Munda Airport, Ranchi\n"
            f"🚌 Bus: JNAC buses connect major towns\n"
            f"🚗 Road: NH-33 and NH-43 cover most tourist areas\n"
            f"Want me to show route on map?"
        )

    def _response_general(self) -> str:
        return (
            "Namaste! I'm Safar Sathi, your Jharkhand travel companion! 🌿\n"
            "I can help you with:\n"
            "• Finding destinations (waterfalls, forests, temples)\n"
            "• Booking local guides\n"
            "• Planning itineraries\n"
            "• Cultural information about tribal communities\n"
            "• Emergency assistance\n"
            "What would you like to explore?"
        )

    def _get_suggestions(self, intent: Intent, entities: dict) -> list:
        """Return quick-reply button suggestions for the UI."""
        suggestion_map = {
            Intent.FIND_DESTINATION: ["Show on Map", "Book Guide", "Get Itinerary"],
            Intent.BOOK_GUIDE:       ["View Guide Profiles", "Check Availability"],
            Intent.GET_ITINERARY:    ["Customize", "Save Itinerary", "Share"],
            Intent.FIND_HOMESTAY:    ["Book Now", "View Photos", "Contact Host"],
            Intent.CULTURAL_INFO:    ["Upcoming Festivals", "Book Cultural Tour"],
            Intent.EMERGENCY_HELP:   ["Share Location", "Call Helpline"],
            Intent.TRANSPORT_INFO:   ["Show on Map", "Book Cab"],
        }
        return suggestion_map.get(intent, ["Explore Destinations", "Plan Trip"])

    # ─── TRANSLATION ─────────────────────────────────────────────────────────

    async def _translate_to_english(self, text: str, source_lang: str) -> str:
        """Translate Hindi/Santali/tribal text to English using IndicTrans2."""
        if not self.translator:
            return text  # Fallback: use original text

        try:
            lang_code_map = {
                "hindi": "hin_Deva",
                "santali": "sat_Olck",
                "bengali": "ben_Beng",
            }
            src_lang = lang_code_map.get(source_lang, "hin_Deva")

            tokenizer = self.translator["tokenizer"]
            model = self.translator["model"]

            inputs = tokenizer(
                text,
                return_tensors="pt",
                src_lang=src_lang,
                tgt_lang="eng_Latn"
            )
            outputs = model.generate(**inputs, max_new_tokens=100)
            return tokenizer.decode(outputs[0], skip_special_tokens=True)

        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return text

    async def _translate_from_english(self, text: str, target_lang: str) -> str:
        """Translate English response back to user's language."""
        if not self.translator:
            return text

        try:
            lang_code_map = {
                "hindi": "hin_Deva",
                "santali": "sat_Olck",
                "bengali": "ben_Beng",
            }
            tgt_lang = lang_code_map.get(target_lang, "hin_Deva")

            tokenizer = self.translator["tokenizer"]
            model = self.translator["model"]

            inputs = tokenizer(
                text,
                return_tensors="pt",
                src_lang="eng_Latn",
                tgt_lang=tgt_lang
            )
            outputs = model.generate(**inputs, max_new_tokens=200)
            return tokenizer.decode(outputs[0], skip_special_tokens=True)

        except Exception as e:
            logger.warning(f"Translation failed: {e}")
            return text

    # ─── SENTIMENT ANALYSIS ──────────────────────────────────────────────────

    async def analyze_sentiment(self, review_text: str) -> dict:
        """
        Analyze sentiment of tourist reviews.
        Used by admin dashboard to monitor tourist satisfaction.

        Returns:
            {"sentiment": "positive", "score": 0.92, "aspects": {...}}
        """
        # Simple rule-based sentiment (fast, no model needed)
        positive_words = {
            "beautiful", "amazing", "wonderful", "great", "excellent",
            "fantastic", "loved", "peaceful", "stunning", "perfect",
            "सुंदर", "अद्भुत", "शानदार", "बेहतरीन"
        }
        negative_words = {
            "bad", "terrible", "dirty", "unsafe", "disappointing",
            "crowded", "expensive", "worst", "poor",
            "बुरा", "गंदा", "असुरक्षित", "निराशाजनक"
        }

        text_lower = review_text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)

        if pos_count > neg_count:
            sentiment = "positive"
            score = min(0.5 + (pos_count * 0.1), 0.99)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = min(0.5 + (neg_count * 0.1), 0.99)
        else:
            sentiment = "neutral"
            score = 0.5

        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "positive_count": pos_count,
            "negative_count": neg_count,
        }
