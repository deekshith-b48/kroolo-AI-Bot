"""
AI Service for Kroolo Agent Bot
Handles OpenAI and Google Gemini API calls with improved error handling
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

# Try to import AI libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

class AIService:
    """Service for AI model interactions with improved reliability"""
    
    def __init__(self):
        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        
        # Model configuration - prefer Gemini (since OpenAI key is not working)
        self.primary_service = "gemini" if self.gemini_api_key and GEMINI_AVAILABLE else "openai"
        self.default_model = "gemini-1.5-flash" if self.primary_service == "gemini" else "gpt-3.5-turbo"
        
        # Configure OpenAI
        if self.openai_api_key and OPENAI_AVAILABLE:
            openai.api_key = self.openai_api_key
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = None
        
        # Configure Gemini
        if self.gemini_api_key and GEMINI_AVAILABLE:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.gemini_model = None
        
        # Rate limiting and retry configuration
        self.request_count = 0
        self.last_request_time = 0
        self.max_requests_per_minute = 15  # Reduced to prevent quota exceeded
        self.max_retries = 3
        self.retry_delay = 2.0  # Increased delay between requests
        
        # Service health tracking
        self.service_health = {
            "openai": {"status": "unknown", "last_check": 0, "error_count": 0},
            "gemini": {"status": "unknown", "last_check": 0, "error_count": 0},
            "huggingface": {"status": "unknown", "last_check": 0, "error_count": 0},
        }
    
    def _generate_query_hash(self, prompt: str) -> str:
        """Generate hash for caching queries"""
        return hashlib.md5(prompt.encode()).hexdigest()
    
    async def _check_rate_limit(self) -> bool:
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
        
        # Add a small delay between requests to be more conservative
        await asyncio.sleep(0.5)
        
        return True
    
    async def ask_openai(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7) -> str:
        """Ask OpenAI API for response"""
        if not self.openai_api_key or not self.openai_client:
            self._update_service_health("openai", "unavailable", "No API key configured")
            return "OpenAI API not configured. Please ask admin to set OPENAI_API_KEY."
        
        if not await self._check_rate_limit():
            return "Rate limit exceeded. Please wait a moment before asking another question."
        
        model_name = model or "gpt-3.5-turbo"
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                # Enhanced system prompt with persona and structure
                system_prompt = """You are Kroolo AI Bot, a helpful and knowledgeable AI assistant for Telegram communities.

CRITICAL RESPONSE GUIDELINES:
- Keep responses SHORT and to the point (max 2-3 sentences per point)
- Use bullet points (•) for lists with proper line breaks
- Use **bold** for key terms and headers
- Add line breaks between different points for better readability
- Structure your response with clear sections
- If the answer is complex, break it into 2-3 short bullet points
- Maximum response length: 200 words
- Be conversational but brief

FORMAT EXAMPLE:
**Main Point:**
• First bullet point
• Second bullet point

**Another Section:**
• Additional information

Remember: You are Kroolo AI Bot - keep it short, structured, and helpful!"""

                user_prompt = f"Please respond to this query concisely:\n\n{prompt}"

                # Make API call
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=300,
                        temperature=temperature
                    )
                )
                
                # Extract response text
                if response.choices and len(response.choices) > 0:
                    raw_answer = response.choices[0].message.content.strip()
                    
                    # Format the response for better readability
                    answer = self._format_ai_response(raw_answer)
                    
                    # Update service health
                    self._update_service_health("openai", "healthy", "")
                    
                    # Log successful API call
                    duration = time.time() - start_time
                    log_api_call("openai", model_name, "success", duration, {
                        "prompt_length": len(prompt),
                        "response_length": len(answer)
                    })
                    
                    return answer
                else:
                    raise Exception("No response from OpenAI API")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"OpenAI API error (attempt {attempt + 1}): {error_msg}")
                
                # Update service health
                self._update_service_health("openai", "error", error_msg)
                
                # Log failed API call
                duration = time.time() - start_time
                log_api_call("openai", model_name, "error", duration, {
                    "prompt_length": len(prompt),
                    "error": error_msg
                })
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    return f"Sorry, I encountered an error while processing your question: {error_msg}"
        
        return "Sorry, I couldn't process your question after multiple attempts."
    
    async def ask_gemini(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2) -> str:
        """Ask Google Gemini API for response with improved error handling"""
        if not self.gemini_api_key:
            self._update_service_health("gemini", "unavailable", "No API key configured")
            return "AI backend not configured. Please ask admin to set GEMINI_API_KEY."
        
        if not self.gemini_model:
            self._update_service_health("gemini", "unavailable", "Model not initialized")
            return "AI model not initialized. Please check configuration."
        
        if not await self._check_rate_limit():
            return "Rate limit exceeded. Please wait a moment before asking another question."
        
        model_name = model or self.default_model
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                # Configure generation parameters
                generation_config = genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=300,
                )
                
                                # Enhanced prompt with persona and structure instructions
                enhanced_prompt = f"""You are Kroolo AI Bot, a helpful and knowledgeable AI assistant for Telegram communities. 

Please respond to this query in a CONCISE, well-structured format:

{prompt}

CRITICAL RESPONSE GUIDELINES:
- Keep responses SHORT and to the point (max 2-3 sentences per point)
- Use bullet points (•) for lists with proper line breaks
- Use **bold** for key terms and headers
- Add line breaks between different points for better readability
- Structure your response with clear sections
- If the answer is complex, break it into 2-3 short bullet points
- Maximum response length: 200 words
- Be conversational but brief

FORMAT EXAMPLE:
**Main Point:**
• First bullet point
• Second bullet point

**Another Section:**
• Additional information

Remember: You are Kroolo AI Bot - keep it short, structured, and helpful!"""

                # Generate response
                response = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: self.gemini_model.generate_content(
                        enhanced_prompt,
                        generation_config=generation_config
                    )
                )
                
                response_time = time.time() - start_time
                
                if response and response.text:
                    raw_answer = response.text.strip()
                    
                    # Format the response for better readability
                    answer = self._format_ai_response(raw_answer)
                    
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
                error_str = str(e)
                
                # Handle quota exceeded errors specifically
                if "429" in error_str or "quota" in error_str.lower() or "ratelimitexceeded" in error_str.lower():
                    self._update_service_health("gemini", "error", "Quota exceeded")
                    return "AI service quota exceeded. Please wait a few minutes before trying again."
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    self._update_service_health("gemini", "error", error_str)
                    log_error(e, "Gemini API call")
                    return f"AI service error: {error_str}. Please try again later."
        
        return "AI service is temporarily unavailable. Please try again later."
    
    async def ask_huggingface(self, prompt: str, model: str = "gpt2") -> str:
        """Ask HuggingFace API for response (fallback)"""
        if not self.hf_api_key:
            self._update_service_health("huggingface", "unavailable", "No API key configured")
            return "HuggingFace API not configured."
        
        if not await self._check_rate_limit():
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
    
    async def ask_ai(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7) -> str:
        """Main AI query method with fallback logic - Gemini first, then OpenAI"""
        
        # Try Gemini first (since OpenAI key is not working)
        if self.gemini_model and self.gemini_api_key:
            try:
                result = await self.ask_gemini(prompt, model, temperature)
                if result and not result.startswith("AI backend not configured"):
                    return result
            except Exception as e:
                logger.warning(f"Gemini API failed: {e}")
        
        # Fallback to OpenAI (if available)
        if self.openai_client and self.openai_api_key:
            try:
                result = await self.ask_openai(prompt, model, temperature)
                if result and not result.startswith("OpenAI API not configured"):
                    return result
            except Exception as e:
                logger.warning(f"OpenAI API failed: {e}")
        
        # Fallback to HuggingFace
        if self.hf_api_key:
            try:
                result = await self.ask_huggingface(prompt)
                if result and not result.startswith("HuggingFace API not configured"):
                    return result
            except Exception as e:
                logger.warning(f"HuggingFace API failed: {e}")
        
        # Final fallback
        return ("❌ Sorry, I encountered an error while processing your question.\n\n"
                "Possible reasons:\n"
                "• AI service is temporarily unavailable\n"
                "• Your question is too complex\n"
                "• Network connectivity issues\n\n"
                "Please try:\n"
                "• Rephrasing your question\n"
                "• Waiting a few minutes\n"
                "• Contacting support if the issue persists")
    
    def _format_ai_response(self, text: str) -> str:
        """Format AI response for better readability in Telegram with proper structure"""
        import re
        
        # Clean up the text first
        text = text.strip()
        
        # Remove any existing Kroolo Bot greetings to avoid duplication
        if text.lower().startswith(('hello! i\'m kroolo', 'hello! i am kroolo', 'hi there! i\'m kroolo')):
            text = text.split('\n', 2)[-1].strip()
        
        # Split into lines and process
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue  # Skip empty lines
            
            # Format bullet points with proper spacing
            if line.startswith('•') or line.startswith('-'):
                formatted_lines.append(f"• {line[1:].strip()}")
            elif line.startswith('*') and not line.startswith('**'):
                formatted_lines.append(f"• {line[1:].strip()}")
            
            # Format headers with proper spacing
            elif line.endswith(':') and len(line) < 80:
                formatted_lines.append(f"\n**{line}**")
            elif line.startswith('##'):
                formatted_lines.append(f"\n**{line.replace('##', '').strip()}:**")
            elif line.startswith('#'):
                formatted_lines.append(f"\n**{line.replace('#', '').strip()}:**")
            
            # Format numbered lists
            elif re.match(r'^\d+\.', line):
                formatted_lines.append(f"\n**{line}**")
            
            # Regular text - add proper spacing
            else:
                formatted_lines.append(line)
        
        # Join lines with proper spacing
        formatted_text = '\n'.join(formatted_lines)
        
        # Add proper spacing between sections
        formatted_text = re.sub(r'\n(•)', r'\n\n\1', formatted_text)  # Space before bullet points
        formatted_text = re.sub(r'\n(\*\*)', r'\n\n\1', formatted_text)  # Space before headers
        
        # Clean up excessive newlines but keep structure
        formatted_text = re.sub(r'\n{4,}', '\n\n\n', formatted_text)
        formatted_text = re.sub(r'\n{3}', '\n\n', formatted_text)
        
        # Ensure it's not too long for Telegram (max 4096 characters)
        if len(formatted_text) > 3800:
            formatted_text = formatted_text[:3700] + "\n\n*... Response truncated for readability.*"
        
        return formatted_text
    
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
