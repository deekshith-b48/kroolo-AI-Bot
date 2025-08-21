"""
Message formatter utility for Telegram.
Handles safe formatting, emoji, and message presentation.
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Formats messages for Telegram with safety and style."""
    
    def __init__(self):
        # Emoji mappings for different tones
        self.tone_emojis = {
            'precise': ['🔬', '📊', '📈', '🎯', '⚡'],
            'skeptical': ['🤔', '🧐', '🤨', '💭', '❓'],
            'enthusiastic': ['🚀', '💡', '🎉', '🔥', '✨'],
            'formal': ['📋', '📝', '📚', '🎓', '🏛️'],
            'witty': ['😏', '🎭', '🎪', '🎨', '🎭'],
            'neutral': ['💬', '📱', '💻', '🌐', '📡']
        }
        
        # Safe formatting patterns
        self.safe_patterns = {
            'bold': r'\*\*(.*?)\*\*',
            'italic': r'\*([^*]+)\*',
            'code': r'`([^`]+)`',
            'pre': r'```([^`]+)```',
            'link': r'\[([^\]]+)\]\(([^)]+)\)'
        }
    
    async def format_message(self, text: str, agent_tone: str = 'neutral', 
                           chat_type: str = 'group', include_emoji: bool = True) -> str:
        """
        Format a message for Telegram with appropriate styling.
        
        Args:
            text: Raw message text
            agent_tone: Tone of the agent (affects emoji choice)
            chat_type: Type of chat (group, private, channel)
            include_emoji: Whether to include emojis
            
        Returns:
            Formatted message text
        """
        try:
            # Clean and sanitize text
            formatted_text = self._sanitize_text(text)
            
            # Apply tone-based formatting
            formatted_text = self._apply_tone_formatting(formatted_text, agent_tone)
            
            # Add emojis if enabled
            if include_emoji:
                formatted_text = self._add_tone_emojis(formatted_text, agent_tone)
            
            # Apply chat-type specific formatting
            formatted_text = self._apply_chat_formatting(formatted_text, chat_type)
            
            # Final safety check
            formatted_text = self._final_safety_check(formatted_text)
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            # Return safe fallback
            return self._create_safe_fallback(text)
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for safe Telegram formatting."""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        text = text.replace('\x00', '')  # Null bytes
        text = text.replace('\r', '\n')  # Normalize line endings
        
        # Escape backslashes
        text = text.replace('\\', '\\\\')
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _apply_tone_formatting(self, text: str, tone: str) -> str:
        """Apply formatting based on agent tone."""
        if tone == 'precise':
            # Add structure for precise responses
            if '\n' in text and len(text) > 200:
                text = self._add_precise_structure(text)
        elif tone == 'enthusiastic':
            # Add emphasis for enthusiastic responses
            text = self._add_enthusiasm(text)
        elif tone == 'formal':
            # Add formal structure
            text = self._add_formal_structure(text)
        
        return text
    
    def _add_precise_structure(self, text: str) -> str:
        """Add structure for precise responses."""
        lines = text.split('\n')
        structured_lines = []
        
        for i, line in enumerate(lines):
            if line.strip():
                if i == 0:  # First line
                    structured_lines.append(f"**{line.strip()}**")
                elif line.startswith('-') or line.startswith('•'):
                    structured_lines.append(line)
                elif len(line) > 50:  # Long lines get bullet points
                    structured_lines.append(f"• {line.strip()}")
                else:
                    structured_lines.append(line)
        
        return '\n'.join(structured_lines)
    
    def _add_enthusiasm(self, text: str) -> str:
        """Add emphasis for enthusiastic responses."""
        # Add emphasis to key phrases
        emphasis_patterns = [
            (r'\b(exciting|amazing|incredible|fantastic)\b', r'**\1**'),
            (r'\b(breakthrough|innovation|revolutionary|game-changing)\b', r'**\1**'),
            (r'\b(future|potential|possibilities|opportunities)\b', r'**\1**')
        ]
        
        for pattern, replacement in emphasis_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _add_formal_structure(self, text: str) -> str:
        """Add formal structure to responses."""
        if len(text) > 300:
            # Add section headers for long formal responses
            sections = text.split('\n\n')
            if len(sections) > 1:
                formatted_sections = []
                for i, section in enumerate(sections):
                    if i == 0:
                        formatted_sections.append(f"**{section.strip()}**")
                    else:
                        formatted_sections.append(section.strip())
                text = '\n\n'.join(formatted_sections)
        
        return text
    
    def _add_tone_emojis(self, text: str, tone: str) -> str:
        """Add appropriate emojis based on tone."""
        emojis = self.tone_emojis.get(tone, self.tone_emojis['neutral'])
        
        # Add emoji at the beginning if text is short
        if len(text) < 100:
            import random
            emoji = random.choice(emojis)
            text = f"{emoji} {text}"
        
        # Add emoji at the end for longer texts
        elif len(text) > 200:
            import random
            emoji = random.choice(emojis)
            text = f"{text}\n\n{emoji}"
        
        return text
    
    def _apply_chat_formatting(self, text: str, chat_type: str) -> str:
        """Apply formatting specific to chat type."""
        if chat_type == 'group':
            # In groups, be more concise
            if len(text) > 500:
                text = self._truncate_for_group(text)
        elif chat_type == 'private':
            # In private chats, can be more detailed
            pass
        elif chat_type == 'channel':
            # In channels, add more structure
            text = self._add_channel_structure(text)
        
        return text
    
    def _truncate_for_group(self, text: str) -> str:
        """Truncate text for group chats."""
        if len(text) <= 500:
            return text
        
        # Find a good breaking point
        truncated = text[:500]
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        
        if last_period > last_newline and last_period > 400:
            truncated = truncated[:last_period + 1]
        elif last_newline > 400:
            truncated = truncated[:last_newline]
        
        truncated += "\n\n*[Message truncated for group chat. Send me a private message for the full response.]*"
        return truncated
    
    def _add_channel_structure(self, text: str) -> str:
        """Add structure for channel posts."""
        if len(text) > 300:
            # Add a summary line at the top
            lines = text.split('\n')
            if lines:
                first_line = lines[0]
                if len(first_line) > 100:
                    summary = first_line[:100] + "..."
                    lines.insert(0, f"**📋 Summary:** {summary}")
                    text = '\n'.join(lines)
        
        return text
    
    def _final_safety_check(self, text: str) -> str:
        """Final safety check for formatted text."""
        # Ensure text doesn't exceed Telegram limits
        if len(text) > 4096:
            text = text[:4090] + "..."
        
        # Check for balanced markdown
        text = self._balance_markdown(text)
        
        return text
    
    def _balance_markdown(self, text: str) -> str:
        """Balance markdown formatting."""
        # Count bold markers
        bold_open = text.count('**')
        if bold_open % 2 != 0:
            # Remove unpaired bold markers
            text = text.replace('**', '', 1)
        
        # Count italic markers
        italic_open = text.count('*')
        if italic_open % 2 != 0:
            # Remove unpaired italic markers
            text = text.replace('*', '', 1)
        
        return text
    
    def _create_safe_fallback(self, original_text: str) -> str:
        """Create a safe fallback message."""
        if not original_text:
            return "I'm having trouble formatting my response right now."
        
        # Simple fallback: just return the text with basic cleaning
        safe_text = original_text.replace('*', '').replace('_', '').replace('`', '')
        safe_text = safe_text[:4000]  # Stay well under limit
        
        return safe_text
    
    def format_news_message(self, title: str, summary: str, source: str, 
                           include_emoji: bool = True) -> str:
        """Format a news message specifically."""
        emoji = "📰" if include_emoji else ""
        
        formatted = f"{emoji} **{title}**\n\n"
        formatted += f"{summary}\n\n"
        formatted += f"🔗 *Source:* {source}"
        
        return formatted
    
    def format_quiz_message(self, question: str, options: list, 
                           include_emoji: bool = True) -> str:
        """Format a quiz message."""
        emoji = "🧠" if include_emoji else ""
        
        formatted = f"{emoji} **{question}**\n\n"
        for i, option in enumerate(options):
            formatted += f"{i+1}. {option}\n"
        
        return formatted
    
    def format_debate_message(self, topic: str, speaker: str, 
                             message: str, include_emoji: bool = True) -> str:
        """Format a debate message."""
        emoji = "🎭" if include_emoji else ""
        
        formatted = f"{emoji} **{topic}**\n\n"
        formatted += f"*{speaker}:* {message}"
        
        return formatted
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the message formatter."""
        try:
            # Test formatting with sample text
            test_text = "This is a **test** message with *formatting*."
            formatted = await self.format_message(test_text, 'neutral', 'private', True)
            
            return {
                "status": "healthy",
                "test_formatting": {
                    "original": test_text,
                    "formatted": formatted,
                    "length_change": len(formatted) - len(test_text)
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
