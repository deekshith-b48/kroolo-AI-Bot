"""
AI Service for Kroolo Agent Bot
Handles Google Gemini API calls with improved error handling
"""

import os
import hashlib
import logging
import time
import json
from typing import Optional, Dict, Any, List
import httpx
from utils.logger import log_api_call, log_error
import asyncio
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AIService:
    """Service for AI model interactions with improved reliability"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.exa_api_key = os.getenv("EXA_API_KEY")
        self.default_model = "gemini-1.5-flash"
        self.fallback_model = "gemini-1.5-flash"
        
        # Configure Gemini
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel(self.default_model)
        else:
            self.model = None
        
        # Rate limiting and retry configuration
        self.request_count = 0
        self.last_request_time = 0
        self.max_requests_per_minute = 60
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
        # Service health tracking
        self.service_health = {
            "gemini": {"status": "unknown", "last_check": 0, "error_count": 0},
            "huggingface": {"status": "unknown", "last_check": 0, "error_count": 0},
            "exa": {"status": "unknown", "last_check": 0, "error_count": 0},
        }
    
    def _generate_query_hash(self, prompt: str) -> str:
        """Generate hash for caching queries"""
        return hashlib.md5(prompt.encode()).hexdigest()
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        current_time = time.time()
        
        # Reset counter if a minute has passed
        if current_time - self.last_request_time >= 60:
            self.request_count = 0
            self.last_request_time = current_time
        
        # Check if we've exceeded the limit
        if self.request_count >= self.max_requests_per_minute:
            return False
        
        self.request_count += 1
        return True
    
    async def ask_gemini(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2) -> str:
        """Ask Google Gemini API for response with improved error handling"""
        if not self.gemini_api_key:
            self._update_service_health("gemini", "unavailable", "No API key configured")
            return "AI backend not configured. Please ask admin to set GEMINI_API_KEY."
        
        if not self.model:
            self._update_service_health("gemini", "unavailable", "Model not initialized")
            return "AI model not initialized. Please check configuration."
        
        if not self._check_rate_limit():
            return "Rate limit exceeded. Please wait a moment before asking another question."
        
        model_name = model or self.default_model
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                # Configure generation parameters
                generation_config = genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=1000,
                )
                
                # Generate response
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self.model.generate_content(
                        prompt, 
                        generation_config=generation_config
                    )
                )
                
                response_time = time.time() - start_time
                
                if response and response.text:
                    answer = response.text.strip()
                    
                    # Update service health
                    self._update_service_health("gemini", "healthy")
                    
                    log_api_call(
                        "Gemini",
                        "generate_content",
                        "success",
                        response_time,
                        {"model": model_name, "tokens_used": len(prompt) + len(answer)}
                    )
                    
                    return answer
                
                else:
                    # Handle Gemini-specific errors
                    if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                        if response.prompt_feedback.block_reason:
                            self._update_service_health("gemini", "error", f"Content blocked: {response.prompt_feedback.block_reason}")
                            return "Your message was blocked by content filters. Please rephrase your question."
                    
                    self._update_service_health("gemini", "error", "No response generated")
                    return "AI service could not generate a response. Please try again."
                        
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    self._update_service_health("gemini", "error", str(e))
                    log_error(e, "Gemini API call")
                    return f"AI service error: {str(e)}. Please try again later."
        
        return "AI service is temporarily unavailable. Please try again later."
    
    async def ask_huggingface(self, prompt: str, model: str = "gpt2") -> str:
        """Ask HuggingFace API for response (fallback)"""
        if not self.hf_api_key:
            self._update_service_health("huggingface", "unavailable", "No API key configured")
            return "HuggingFace API not configured."
        
        if not self._check_rate_limit():
            return "Rate limit exceeded. Please wait a moment before asking another question."
        
        start_time = time.time()
        
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_length": 200,
                "temperature": 0.7,
                "do_sample": True
            }
        }
        
        for attempt in range(self.max_retries):
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
                        if isinstance(data, list) and len(data) > 0:
                            answer = data[0].get("generated_text", "").replace(prompt, "").strip()
                            
                            self._update_service_health("huggingface", "healthy")
                            
                            log_api_call(
                                "HuggingFace",
                                "inference",
                                "success",
                                response_time,
                                {"model": model}
                            )
                            
                            return answer
                        else:
                            return "No response generated from HuggingFace API."
                    
                    elif response.status_code == 503:
                        # Model is loading
                        wait_time = 20
                        logger.warning(f"HuggingFace model {model} is loading, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        self._update_service_health("huggingface", "error", f"HTTP {response.status_code}")
                        return f"HuggingFace API error: {response.status_code}"
                        
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    self._update_service_health("huggingface", "error", str(e))
                    log_error(e, "HuggingFace API call")
                    return f"HuggingFace API error: {str(e)}"
        
        return "HuggingFace API is temporarily unavailable."
    
    async def ask_ai(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2) -> str:
        """Main AI query method with fallback logic"""
        # Try Gemini first
        try:
            result = await self.ask_gemini(prompt, model, temperature)
            if result and not result.startswith("AI backend not configured"):
                return result
        except Exception as e:
            logger.warning(f"Gemini API failed: {e}")
        
        # Fallback to HuggingFace
        try:
            result = await self.ask_huggingface(prompt)
            if result and not result.startswith("HuggingFace API not configured"):
                return result
        except Exception as e:
            logger.warning(f"HuggingFace API failed: {e}")
        
        # Final fallback
        return "AI services are currently unavailable. Please try again later."
    
    def _update_service_health(self, service: str, status: str, error: str = ""):
        """Update service health status"""
        self.service_health[service] = {
            "status": status,
            "last_check": time.time(),
            "error_count": self.service_health[service].get("error_count", 0) + (1 if status == "error" else 0),
            "error": error
        }
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get current service health status"""
        return self.service_health.copy()
    
    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Summarize text using AI"""
        prompt = f"Please summarize the following text in {max_length} characters or less:\n\n{text}"
        return await self.ask_ai(prompt)
    
    async def detect_spam(self, text: str) -> bool:
        """Detect if text is spam using AI"""
        prompt = f"Is the following text spam or inappropriate? Answer only 'yes' or 'no':\n\n{text}"
        response = await self.ask_ai(prompt)
        return response.lower().strip() in ['yes', 'true', '1']
    
    async def generate_topic_suggestions(self, text: str) -> List[str]:
        """Generate topic suggestions from text"""
        prompt = f"Generate 3-5 relevant topic suggestions for this text. Return as a JSON array:\n\n{text}"
        response = await self.ask_ai(prompt)
        
        try:
            # Try to parse as JSON
            topics = json.loads(response)
            if isinstance(topics, list):
                return topics[:5]  # Limit to 5 topics
        except json.JSONDecodeError:
            pass
        
        # Fallback: split by lines or commas
        topics = [t.strip() for t in response.replace('\n', ',').split(',') if t.strip()]
        return topics[:5]
    
    async def generate_quiz_question(self, topic: str = "general knowledge") -> Dict[str, Any]:
        """Generate a quiz question"""
        prompt = f"""Generate a multiple choice quiz question about {topic}. 
        Return as JSON with this format:
        {{
            "question": "Your question here?",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "correct_answer": "A",
            "explanation": "Why this answer is correct"
        }}"""
        
        response = await self.ask_ai(prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback question
            return {
                "question": f"What is a key concept in {topic}?",
                "options": ["A) Option A", "B) Option B", "C) Option C", "D) Option D"],
                "correct_answer": "A",
                "explanation": "This is the correct answer."
            }
    
    async def generate_fun_fact(self, topic: str = "technology") -> str:
        """Generate a fun fact"""
        prompt = f"Generate an interesting and educational fun fact about {topic}. Keep it under 200 characters."
        return await self.ask_ai(prompt)
    
    async def generate_joke(self, topic: str = "programming") -> str:
        """Generate a joke"""
        prompt = f"Generate a clean, family-friendly joke about {topic}. Keep it under 150 characters."
        return await self.ask_ai(prompt)
