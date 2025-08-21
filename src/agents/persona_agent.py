"""
Persona agent implementation.
Demonstrates how to create AI agents with specific personalities and capabilities.
"""

import logging
from typing import Dict, Any, List, Optional
import openai

from .base_agent import BaseAgent
from config.settings import settings

logger = logging.getLogger(__name__)


class PersonaAgent(BaseAgent):
    """Generic persona agent with AI personality."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        
        # Set OpenAI API key
        openai.api_key = settings.openai_api_key
        
        # Persona-specific settings
        self.max_context_length = getattr(config, 'max_tokens_per_response', 2000)
        self.temperature = getattr(config, 'openai_temperature', 0.7)
        self.model = getattr(config, 'openai_model', 'gpt-4')
        
        # Safety and compliance
        self.safety_checks = getattr(config, 'guardrails', [])
        self.compliance_notes = getattr(config, 'compliance_notes', '')
        
        logger.info(f"Initialized persona agent: {self.name} ({self.handle})")
    
    async def _generate_response(self, message_info: Dict[str, Any], agent_context: Dict[str, Any]) -> str:
        """
        Generate a response based on the message and context.
        
        Args:
            message_info: Information about the incoming message
            agent_context: Context information for the agent
            
        Returns:
            Generated response text
        """
        try:
            user_message = message_info.get('text', '')
            chat_id = message_info.get('chat_id')
            
            # Prepare the prompt for the AI
            prompt = self._build_prompt(user_message, agent_context)
            
            # Generate response using OpenAI
            response = await self._call_openai(prompt)
            
            # Apply safety checks and formatting
            response = self._apply_safety_checks(response)
            response = self._format_response(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._get_fallback_response(user_message)
    
    def _build_prompt(self, user_message: str, agent_context: Dict[str, Any]) -> str:
        """Build the prompt for the AI model."""
        
        # Base persona prompt
        prompt = f"""You are {self.name}, {self.persona}

Your tone is: {self.tone}
Your domain focus: {getattr(self.config, 'domain_focus', 'general knowledge')}

IMPORTANT RULES:
1. Always stay in character as {self.name}
2. Respond in a {self.tone} tone
3. Keep responses concise but informative
4. If you don't know something, say so rather than making things up
5. Use your knowledge appropriately for your era and background

User message: {user_message}

Please respond as {self.name}:"""

        # Add RAG context if available
        if 'rag_context' in agent_context:
            rag_info = agent_context['rag_context']
            if rag_info:
                prompt += f"\n\nRelevant context: {rag_info}\n\nUse this context to inform your response:"

        # Add safety constraints
        if self.safety_checks:
            prompt += f"\n\nSAFETY CONSTRAINTS - Avoid these topics: {', '.join(self.safety_checks)}"
        
        if self.compliance_notes:
            prompt += f"\n\nCOMPLIANCE: {self.compliance_notes}"

        return prompt
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API to generate response."""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant with a specific persona."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_context_length,
                temperature=self.temperature,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}")
            raise
    
    def _apply_safety_checks(self, response: str) -> str:
        """Apply safety checks to the response."""
        # Check for blocked content
        blocked_terms = [
            "harmful", "dangerous", "illegal", "inappropriate",
            "personal advice", "medical advice", "financial advice"
        ]
        
        for term in blocked_terms:
            if term.lower() in response.lower():
                logger.warning(f"Response contains blocked term: {term}")
                response = f"I cannot provide {term} information. Please consult appropriate professionals."
                break
        
        # Check response length
        if len(response) > self.max_context_length:
            response = response[:self.max_context_length] + "..."
        
        return response
    
    def _format_response(self, response: str) -> str:
        """Format the response for better presentation."""
        # Clean up any extra whitespace
        response = response.strip()
        
        # Ensure proper sentence endings
        if response and not response.endswith(('.', '!', '?')):
            response += '.'
        
        # Add persona signature if response is long enough
        if len(response) > 100:
            response += f"\n\n— {self.name}"
        
        return response
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Get a fallback response when AI generation fails."""
        fallback_responses = [
            f"I apologize, but I'm having trouble processing your request right now. Could you rephrase that?",
            f"I'm experiencing some technical difficulties. Please try asking your question again.",
            f"I'm not able to respond properly at the moment. Please try again in a moment.",
            f"Something went wrong with my response generation. Could you try asking differently?"
        ]
        
        # Use a simple hash of the message to consistently pick the same fallback
        import hashlib
        hash_value = int(hashlib.md5(user_message.encode()).hexdigest(), 16)
        fallback_index = hash_value % len(fallback_responses)
        
        return fallback_responses[fallback_index]
    
    async def process_special_command(self, command: str, message_info: Dict[str, Any]) -> str:
        """Process special commands specific to this persona."""
        command_lower = command.lower()
        
        if command_lower in ['/whoami', '/identity', '/persona']:
            return self._get_identity_response()
        elif command_lower in ['/capabilities', '/skills', '/abilities']:
            return self._get_capabilities_response()
        elif command_lower in ['/era', '/background', '/history']:
            return self._get_background_response()
        else:
            return "I don't recognize that command. Try /whoami, /capabilities, or /era to learn more about me."
    
    def _get_identity_response(self) -> str:
        """Get response about the agent's identity."""
        return f"""I am {self.name}, {self.persona}

My tone is {self.tone}, and I focus on {getattr(self.config, 'domain_focus', 'general knowledge')}.

I'm here to engage in meaningful conversations and share knowledge within my areas of expertise."""
    
    def _get_capabilities_response(self) -> str:
        """Get response about the agent's capabilities."""
        capabilities = getattr(self.config, 'capabilities', [])
        if capabilities:
            cap_text = ", ".join(capabilities)
            return f"I can help with: {cap_text}"
        else:
            return "I'm a conversational AI with general knowledge and reasoning abilities."
    
    def _get_background_response(self) -> str:
        """Get response about the agent's background."""
        era = getattr(self.config, 'era', 'modern')
        domain = getattr(self.config, 'domain_focus', 'general knowledge')
        
        return f"I operate in the {era} context, with expertise in {domain}."
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the persona agent."""
        try:
            # Basic health check
            health_status = await super().health_check()
            
            # Add persona-specific checks
            health_status['persona_specific'] = {
                'openai_api_key_configured': bool(settings.openai_api_key),
                'model_configured': self.model,
                'temperature_setting': self.temperature,
                'max_tokens': self.max_context_length,
                'safety_checks_count': len(self.safety_checks)
            }
            
            # Test OpenAI connectivity if API key is configured
            if settings.openai_api_key:
                try:
                    # Simple test call
                    test_response = await openai.ChatCompletion.acreate(
                        model=self.model,
                        messages=[{"role": "user", "content": "Hello"}],
                        max_tokens=10
                    )
                    health_status['persona_specific']['openai_connectivity'] = 'working'
                except Exception as e:
                    health_status['persona_specific']['openai_connectivity'] = 'failed'
                    health_status['persona_specific']['openai_error'] = str(e)
            else:
                health_status['persona_specific']['openai_connectivity'] = 'not_configured'
            
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'agent': self.handle,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def get_persona_info(self) -> Dict[str, Any]:
        """Get detailed information about the persona."""
        return {
            'name': self.name,
            'handle': self.handle,
            'persona': self.persona,
            'tone': self.tone,
            'era': getattr(self.config, 'era', 'modern'),
            'domain_focus': getattr(self.config, 'domain_focus', 'general knowledge'),
            'capabilities': self.capabilities,
            'safety_checks': self.safety_checks,
            'compliance_notes': self.compliance_notes,
            'ai_model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_context_length
        }
