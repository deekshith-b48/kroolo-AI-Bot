"""
AI Service for Kroolo Agent Bot
Handles OpenAI and HuggingFace API calls
"""

import os
import hashlib
import logging
import time
from typing import Optional, Dict, Any, List
import httpx
from utils.logger import log_api_call, log_error

logger = logging.getLogger(__name__)

class AIService:
    """Service for AI model interactions"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.default_model = "gpt-4o-mini"
        self.fallback_model = "gpt-3.5-turbo"
        
        # Rate limiting
        self.request_count = 0
        self.last_request_time = 0
        self.max_requests_per_minute = 60
    
    def _generate_query_hash(self, prompt: str) -> str:
        """Generate hash for caching queries"""
        return hashlib.md5(prompt.encode()).hexdigest()
    
    async def ask_openai(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2) -> str:
        """Ask OpenAI API for response"""
        if not self.openai_api_key:
            return "AI backend not configured. Please ask admin to set OPENAI_API_KEY."
        
        start_time = time.time()
        model = model or self.default_model
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["choices"][0]["message"]["content"]
                    
                    log_api_call(
                        "OpenAI",
                        "chat/completions",
                        "success",
                        response_time,
                        {"model": model, "tokens_used": data.get("usage", {}).get("total_tokens", 0)}
                    )
                    
                    return answer
                else:
                    log_api_call(
                        "OpenAI",
                        "chat/completions",
                        f"error_{response.status_code}",
                        response_time,
                        {"error": response.text}
                    )
                    
                    # Try fallback model if main model fails
                    if model != self.fallback_model:
                        logger.warning(f"OpenAI API failed with model {model}, trying fallback {self.fallback_model}")
                        return await self.ask_openai(prompt, self.fallback_model, temperature)
                    
                    return f"Sorry, AI service is currently unavailable. Error: {response.status_code}"
                    
        except httpx.TimeoutException:
            log_error(Exception("Request timeout"), "OpenAI API call")
            return "Sorry, AI service is taking too long to respond. Please try again."
        except Exception as e:
            log_error(e, "OpenAI API call")
            return "Sorry, AI service encountered an error. Please try again later."
    
    async def ask_huggingface(self, prompt: str, model: str = "gpt2") -> str:
        """Ask HuggingFace API for response (fallback)"""
        if not self.hf_api_key:
            return "HuggingFace API not configured."
        
        start_time = time.time()
        
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_length": 100,
                "temperature": 0.7
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=headers,
                    json=payload
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data[0]["generated_text"] if isinstance(data, list) else str(data)
                    
                    log_api_call(
                        "HuggingFace",
                        f"models/{model}",
                        "success",
                        response_time
                    )
                    
                    return answer
                else:
                    log_api_call(
                        "HuggingFace",
                        f"models/{model}",
                        f"error_{response.status_code}",
                        response_time,
                        {"error": response.text}
                    )
                    
                    return f"Sorry, HuggingFace service is currently unavailable. Error: {response.status_code}"
                    
        except Exception as e:
            log_error(e, "HuggingFace API call")
            return "Sorry, HuggingFace service encountered an error. Please try again later."
    
    async def ask_ai(self, prompt: str, use_cache: bool = True) -> str:
        """Main method to ask AI - tries OpenAI first, falls back to HuggingFace"""
        try:
            # Try OpenAI first
            response = await self.ask_openai(prompt)
            if response and not response.startswith("Sorry"):
                return response
            
            # Fallback to HuggingFace
            logger.info("Falling back to HuggingFace API")
            return await self.ask_huggingface(prompt)
            
        except Exception as e:
            log_error(e, "AI service fallback")
            return "Sorry, all AI services are currently unavailable. Please try again later."
    
    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Summarize long text using AI"""
        prompt = f"Please provide a concise summary of the following text in {max_length} characters or less:\n\n{text}"
        return await self.ask_ai(prompt)
    
    async def detect_spam(self, text: str) -> Dict[str, Any]:
        """Detect potential spam content"""
        prompt = f"Analyze this text for spam indicators. Respond with JSON: {{\"is_spam\": true/false, \"confidence\": 0.0-1.0, \"reasons\": [\"reason1\", \"reason2\"]}}\n\nText: {text}"
        
        try:
            response = await self.ask_ai(prompt)
            # Try to parse JSON response
            import json
            return json.loads(response)
        except:
            # Fallback response if JSON parsing fails
            return {
                "is_spam": False,
                "confidence": 0.5,
                "reasons": ["AI analysis unavailable"]
            }
    
    async def generate_topic_suggestions(self, chat_context: str) -> List[str]:
        """Generate topic suggestions based on chat context"""
        prompt = f"Based on this chat context, suggest 3-5 relevant discussion topics. Respond with a simple list:\n\nContext: {chat_context}"
        
        try:
            response = await self.ask_ai(prompt)
            # Parse response into list
            lines = response.strip().split('\n')
            topics = [line.strip().lstrip('- ').lstrip('* ').lstrip('0123456789. ') for line in lines if line.strip()]
            return topics[:5]  # Limit to 5 topics
        except:
            return ["General Discussion", "Questions & Answers", "Community Updates"]
    
    def get_available_models(self) -> List[str]:
        """Get list of available AI models"""
        models = []
        
        if self.openai_api_key:
            models.extend([
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-3.5-turbo",
                "gpt-4-turbo"
            ])
        
        if self.hf_api_key:
            models.extend([
                "gpt2",
                "distilgpt2",
                "microsoft/DialoGPT-medium"
            ])
        
        return models
    
    def is_service_available(self) -> Dict[str, bool]:
        """Check availability of AI services"""
        return {
            "openai": bool(self.openai_api_key),
            "huggingface": bool(self.hf_api_key),
            "overall": bool(self.openai_api_key or self.hf_api_key)
        }
