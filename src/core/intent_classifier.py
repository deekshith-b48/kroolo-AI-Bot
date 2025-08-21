"""
Intent classifier for determining user intent from messages.
Uses both rule-based and ML-based approaches for accurate intent detection.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
import json

logger = logging.getLogger(__name__)


class Intent(Enum):
    """User intent classification."""
    NEWS = "news"
    QUIZ = "quiz"
    DEBATE = "debate"
    FUN = "fun"
    PERSONA_CHAT = "persona_chat"
    MODERATION = "moderation"
    ADMIN = "admin"
    HELP = "help"
    UNKNOWN = "unknown"


class IntentClassifier:
    """Classifies user intent from message content."""
    
    def __init__(self):
        # Rule-based patterns
        self.patterns = {
            Intent.NEWS: [
                r'\b(news|update|latest|breaking|announcement|release)\b',
                r'\b(ai|artificial intelligence|machine learning|deep learning)\b',
                r'\b(what\'s new|what happened|what\'s going on)\b',
                r'\b(today|yesterday|this week|recent)\b',
                r'\b(technology|tech|research|paper|study)\b'
            ],
            Intent.QUIZ: [
                r'\b(quiz|question|test|challenge|puzzle)\b',
                r'\b(how much|how many|what is|who is|when)\b',
                r'\b(trivia|knowledge|learning|education)\b',
                r'\b(play|game|fun|entertainment)\b',
                r'\b(score|points|leaderboard|ranking)\b'
            ],
            Intent.DEBATE: [
                r'\b(debate|discuss|argue|opinion|viewpoint)\b',
                r'\b(pros and cons|advantages|disadvantages)\b',
                r'\b(agree|disagree|controversial|contention)\b',
                r'\b(what do you think|your thoughts|perspective)\b',
                r'\b(compare|versus|vs|difference)\b'
            ],
            Intent.FUN: [
                r'\b(joke|funny|humor|comedy|entertainment)\b',
                r'\b(fun fact|interesting|amazing|wow|cool)\b',
                r'\b(riddle|puzzle|brain teaser|mind game)\b',
                r'\b(story|anecdote|tale|narrative)\b',
                r'\b(relax|take a break|have fun|enjoy)\b'
            ],
            Intent.PERSONA_CHAT: [
                r'\b(hello|hi|hey|greetings|good morning|good evening)\b',
                r'\b(how are you|how\'s it going|what\'s up)\b',
                r'\b(tell me about|explain|describe|what is)\b',
                r'\b(conversation|chat|talk|discuss)\b',
                r'\b(philosophy|theory|concept|idea)\b'
            ],
            Intent.HELP: [
                r'\b(help|support|assist|guide|tutorial)\b',
                r'\b(how to|what can you do|capabilities|features)\b',
                r'\b(problem|issue|error|trouble|difficulty)\b',
                r'\b(instructions|manual|documentation|guide)\b',
                r'\b(confused|lost|don\'t understand|unclear)\b'
            ],
            Intent.ADMIN: [
                r'\b(admin|administrator|moderator|owner)\b',
                r'\b(config|configuration|settings|setup)\b',
                r'\b(restart|reload|update|maintenance)\b',
                r'\b(stats|statistics|metrics|performance)\b',
                r'\b(ban|block|mute|kick|remove)\b'
            ]
        }
        
        # Intent keywords with weights
        self.keyword_weights = {
            Intent.NEWS: {
                "news": 5.0, "update": 4.0, "latest": 4.0, "breaking": 5.0,
                "ai": 3.0, "artificial intelligence": 4.0, "research": 3.0
            },
            Intent.QUIZ: {
                "quiz": 5.0, "question": 4.0, "test": 3.0, "challenge": 4.0,
                "trivia": 4.0, "puzzle": 3.0, "game": 3.0
            },
            Intent.DEBATE: {
                "debate": 5.0, "discuss": 4.0, "opinion": 4.0, "argue": 3.0,
                "pros and cons": 4.0, "controversial": 4.0, "perspective": 3.0
            },
            Intent.FUN: {
                "joke": 5.0, "funny": 4.0, "humor": 4.0, "fun fact": 5.0,
                "entertainment": 3.0, "story": 3.0, "riddle": 4.0
            },
            Intent.PERSONA_CHAT: {
                "hello": 2.0, "hi": 2.0, "explain": 3.0, "tell me": 3.0,
                "conversation": 3.0, "philosophy": 4.0, "theory": 4.0
            }
        }
        
        # Context patterns for better classification
        self.context_patterns = {
            "question_mark": 2.0,  # Boost for questions
            "exclamation": 1.5,    # Boost for exclamations
            "mention": 3.0,        # Boost for @mentions
            "command": 4.0,        # Boost for /commands
            "url": 1.0,            # Slight boost for URLs
            "emoji": 0.5           # Slight boost for emojis
        }
    
    async def classify_intent(self, text: str) -> Intent:
        """
        Classify the intent of a message.
        
        Args:
            text: Message text to classify
            
        Returns:
            Detected intent
        """
        if not text:
            return Intent.UNKNOWN
        
        text_lower = text.lower().strip()
        
        # Check for explicit commands first
        if text.startswith('/'):
            return self._classify_command_intent(text_lower)
        
        # Check for explicit mentions
        if '@' in text:
            return Intent.PERSONA_CHAT
        
        # Use rule-based classification
        intent_scores = self._calculate_rule_based_scores(text_lower)
        
        # Apply context patterns
        context_score = self._calculate_context_score(text)
        for intent in intent_scores:
            intent_scores[intent] += context_score
        
        # Get the highest scoring intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0.5:  # Threshold for confidence
                return best_intent
        
        # Fallback to persona chat for general conversation
        return Intent.PERSONA_CHAT
    
    def _classify_command_intent(self, text: str) -> Intent:
        """Classify intent for command messages."""
        command_patterns = {
            r'/news': Intent.NEWS,
            r'/quiz': Intent.QUIZ,
            r'/debate': Intent.DEBATE,
            r'/fun': Intent.FUN,
            r'/help': Intent.HELP,
            r'/config': Intent.ADMIN,
            r'/agents': Intent.HELP,
            r'/rules': Intent.HELP
        }
        
        for pattern, intent in command_patterns.items():
            if re.search(pattern, text):
                return intent
        
        return Intent.HELP
    
    def _calculate_rule_based_scores(self, text: str) -> Dict[Intent, float]:
        """Calculate intent scores using rule-based patterns."""
        scores = {intent: 0.0 for intent in Intent}
        
        for intent, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Base score from pattern matches
                    scores[intent] += len(matches) * 0.5
                    
                    # Additional score from keyword weights
                    for keyword, weight in self.keyword_weights.get(intent, {}).items():
                        if keyword in text_lower:
                            scores[intent] += weight
        
        return scores
    
    def _calculate_context_score(self, text: str) -> float:
        """Calculate context-based score adjustments."""
        context_score = 0.0
        
        # Question mark boost
        if '?' in text:
            context_score += self.context_patterns["question_mark"]
        
        # Exclamation boost
        if '!' in text:
            context_score += self.context_patterns["exclamation"]
        
        # Mention boost
        if '@' in text:
            context_score += self.context_patterns["mention"]
        
        # Command boost
        if text.startswith('/'):
            context_score += self.context_patterns["command"]
        
        # URL boost
        if 'http' in text or 'www.' in text:
            context_score += self.context_patterns["url"]
        
        # Emoji boost
        emoji_count = len(re.findall(r'[^\w\s]', text))
        if emoji_count > 0:
            context_score += emoji_count * self.context_patterns["emoji"]
        
        return context_score
    
    def get_intent_confidence(self, text: str, intent: Intent) -> float:
        """
        Get confidence score for a specific intent.
        
        Args:
            text: Message text
            intent: Intent to check confidence for
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not text:
            return 0.0
        
        text_lower = text.lower().strip()
        
        # Calculate base score
        base_score = 0.0
        
        # Pattern matching score
        if intent in self.patterns:
            for pattern in self.patterns[intent]:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                base_score += len(matches) * 0.3
        
        # Keyword weight score
        if intent in self.keyword_weights:
            for keyword, weight in self.keyword_weights[intent].items():
                if keyword in text_lower:
                    base_score += weight * 0.1
        
        # Context score
        context_score = self._calculate_context_score(text)
        base_score += context_score * 0.2
        
        # Normalize to 0.0-1.0 range
        confidence = min(1.0, base_score / 10.0)
        
        return confidence
    
    def get_alternative_intents(self, text: str, top_k: int = 3) -> List[tuple]:
        """
        Get alternative intents with confidence scores.
        
        Args:
            text: Message text
            top_k: Number of top intents to return
            
        Returns:
            List of (intent, confidence) tuples
        """
        if not text:
            return []
        
        intent_scores = []
        
        for intent in Intent:
            if intent != Intent.UNKNOWN:
                confidence = self.get_intent_confidence(text, intent)
                intent_scores.append((intent, confidence))
        
        # Sort by confidence and return top_k
        intent_scores.sort(key=lambda x: x[1], reverse=True)
        return intent_scores[:top_k]
    
    def update_patterns(self, intent: Intent, patterns: List[str]):
        """
        Update patterns for an intent (for dynamic learning).
        
        Args:
            intent: Intent to update
            patterns: New patterns to add
        """
        if intent in self.patterns:
            self.patterns[intent].extend(patterns)
            logger.info(f"Updated patterns for intent {intent.value}")
        else:
            self.patterns[intent] = patterns
            logger.info(f"Added new intent {intent.value} with patterns")
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """Get statistics about the classifier."""
        total_patterns = sum(len(patterns) for patterns in self.patterns.values())
        total_keywords = sum(len(keywords) for keywords in self.keyword_weights.values())
        
        return {
            "total_intents": len(Intent),
            "total_patterns": total_patterns,
            "total_keywords": total_keywords,
            "supported_intents": [intent.value for intent in self.patterns.keys()],
            "context_patterns": self.context_patterns
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the intent classifier."""
        try:
            stats = self.get_classification_stats()
            
            # Test classification with sample text
            test_text = "Hello, how are you?"
            test_intent = await self.classify_intent(test_text)
            test_confidence = self.get_intent_confidence(test_text, test_intent)
            
            return {
                "status": "healthy",
                "stats": stats,
                "test_classification": {
                    "text": test_text,
                    "intent": test_intent.value,
                    "confidence": test_confidence
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
