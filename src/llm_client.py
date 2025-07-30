"""
Multi-Provider LLM Client for Evaluator v16
Handles Claude, OpenAI, and Gemini APIs with fallback logic and error handling.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from dataclasses import dataclass
from logger import get_logger

# API clients - will need to be installed via pip
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

@dataclass
class LLMResponse:
    """Standardized LLM response container"""
    content: str
    provider: str
    model: str
    success: bool = True
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    response_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class LLMClient:
    """Multi-provider LLM client with fallback support"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.logger = get_logger()
        
        # Initialize API clients
        self.anthropic_client = None
        self.openai_client = None
        self.genai_client = None
        
        # Cost tracking (rates per 1K tokens - updated July 2025)
        self.cost_rates = {
            'anthropic': {'input': 0.003, 'output': 0.015},  # Claude Sonnet 4
            'openai': {'input': 0.00015, 'output': 0.0006},  # GPT-4.1-mini (83% cost reduction)
            'google': {'input': 0.00015, 'output': 0.0006}   # Gemini 2.5 Flash
        }
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize all available API clients"""
        # Claude/Anthropic
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key and anthropic:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                self.logger.log_system_event('llm_client', 'client_initialized', "Anthropic client initialized")
            except Exception as e:
                self.logger.log_system_event('llm_client', 'client_init_failed', f"Failed to initialize Anthropic client: {e}", level="WARNING")
        
        # OpenAI
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and openai:
            try:
                self.openai_client = openai.OpenAI(api_key=openai_key)
                self.logger.log_system_event('llm_client', 'client_initialized', "OpenAI client initialized")
            except Exception as e:
                self.logger.log_system_event('llm_client', 'client_init_failed', f"Failed to initialize OpenAI client: {e}", level="WARNING")
        
        # Google Gemini
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key and genai:
            try:
                genai.configure(api_key=gemini_key)
                self.genai_client = True  # Just a flag that it's configured
                self.logger.log_system_event('llm_client', 'client_initialized', "Gemini client initialized")
            except Exception as e:
                self.logger.log_system_event('llm_client', 'client_init_failed', f"Failed to initialize Gemini client: {e}", level="WARNING")
    
    def call_llm(self, provider: str, prompt: str, **kwargs) -> LLMResponse:
        """Call specific LLM provider with prompt"""
        start_time = time.time()
        
        # Get provider configuration
        if self.config_manager:
            config = self.config_manager.get_llm_config(provider)
        else:
            config = self._get_default_config(provider)
        
        # Merge any additional parameters
        config.update(kwargs)
        
        try:
            if provider == 'anthropic':
                response = self._call_claude(prompt, config)
            elif provider == 'openai':
                response = self._call_openai(prompt, config)
            elif provider == 'google':
                response = self._call_gemini(prompt, config)
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            # Validate response content
            if not response.content or response.content.strip() == "":
                raise Exception(f"Empty response from {provider} - possible content policy violation or API error")
            
            response.response_time = time.time() - start_time
            self.logger.log_system_event('llm_client', 'llm_call_success', f"LLM call successful: {provider} ({response.response_time:.2f}s)")
            
            return response
            
        except Exception as e:
            self.logger.log_error('llm_client', f"LLM call failed: {provider} - {e}", str(e))
            raise
    
    def call_llm_with_fallback(self, system_prompt: str = None, user_prompt: str = None, prompt: str = None, phase: str = None, **kwargs) -> LLMResponse:
        """Call LLM with automatic fallback to alternative providers"""
        # Handle different prompt formats more efficiently
        if prompt is None:
            if system_prompt and user_prompt:
                # Use separate system and user prompts for better efficiency
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                if user_prompt:
                    messages.append({"role": "user", "content": user_prompt})
            elif user_prompt:
                messages = [{"role": "user", "content": user_prompt}]
            else:
                raise ValueError("Must provide either 'prompt' or 'user_prompt'")
        else:
            # Legacy single prompt format
            messages = [{"role": "user", "content": prompt}]

        if self.config_manager:
            fallback_chain = self.config_manager.get_llm_fallback_chain()
        else:
            fallback_chain = ['openai', 'anthropic', 'google']  # Prioritize faster/cheaper providers
        
        last_error = None
        
        for provider in fallback_chain:
            if not self._is_provider_available(provider):
                self.logger.log_system_event('llm_client', 'provider_unavailable', f"Provider not available: {provider}", level="WARNING")
                continue
            
            try:
                # Get phase-specific configuration if provided
                if self.config_manager and phase:
                    config = self.config_manager.get_llm_config(provider, phase)
                else:
                    config = self._get_default_config(provider)
                
                config.update(kwargs)
                
                # Use optimized call method that handles messages directly
                response = self._call_llm_with_messages(provider, messages, **config)
                
                # Only log as fallback if this isn't the first provider in the chain
                if provider != fallback_chain[0]:
                    self.logger.log_system_event('llm_client', 'fallback_success', f"Fallback successful with provider: {provider}")
                else:
                    self.logger.log_system_event('llm_client', 'primary_success', f"Primary provider successful: {provider}")
                
                return response
                
            except Exception as e:
                last_error = e
                self.logger.log_system_event('llm_client', 'provider_failed', f"Provider {provider} failed, trying next: {e}", level="WARNING")
                continue
        
        # All providers failed
        self.logger.log_error('llm_client', "All LLM providers failed", "All providers failed")
        return LLMResponse(
            content="Failed to generate response",
            provider="none",
            model="none",
            success=False,
            error=f"All LLM providers failed. Last error: {last_error}"
        )

    def _call_llm_with_messages(self, provider: str, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Call specific LLM provider with structured messages"""
        start_time = time.time()
        
        try:
            if provider == 'anthropic':
                response = self._call_claude_with_messages(messages, kwargs)
            elif provider == 'openai':
                response = self._call_openai_with_messages(messages, kwargs)
            elif provider == 'google':
                response = self._call_gemini_with_messages(messages, kwargs)
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            # Validate response content
            if not response.content or response.content.strip() == "":
                raise Exception(f"Empty response from {provider} - possible content policy violation or API error")
            
            response.response_time = time.time() - start_time
            self.logger.log_system_event('llm_client', 'llm_call_success', f"LLM call successful: {provider} ({response.response_time:.2f}s)")
            
            return response
            
        except Exception as e:
            self.logger.log_error('llm_client', f"LLM call failed: {provider} - {e}", str(e))
            raise

    def _call_claude_with_messages(self, messages: List[Dict[str, str]], config: Dict) -> LLMResponse:
        """Call Anthropic Claude API with structured messages"""
        if not self.anthropic_client:
            raise Exception("Anthropic client not initialized")
        
        try:
            response = self.anthropic_client.messages.create(
                model=config.get('default_model', 'claude-3-5-sonnet-20241022'),
                max_tokens=config.get('max_tokens', 4000),
                temperature=config.get('temperature', 0.1),
                messages=messages
            )
            
            content = response.content[0].text
            
            # Clean up markdown-wrapped JSON responses
            content = self._clean_json_response(content)
            
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            cost = self._calculate_cost('anthropic', 
                                       response.usage.input_tokens, 
                                       response.usage.output_tokens)
            
            return LLMResponse(
                content=content,
                provider='anthropic',
                model=config.get('default_model', 'claude-3-5-sonnet-20241022'),
                tokens_used=tokens_used,
                cost_estimate=cost,
                metadata={
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            )
            
        except Exception as e:
            raise Exception(f"Claude API error: {e}")

    def _call_openai_with_messages(self, messages: List[Dict[str, str]], config: Dict) -> LLMResponse:
        """Call OpenAI GPT API with structured messages"""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        try:
            response = self.openai_client.chat.completions.create(
                model=config.get('default_model', 'gpt-4.1-mini'),
                messages=messages,
                max_tokens=config.get('max_tokens', 4000),
                temperature=config.get('temperature', 0.1)
            )
            
            content = response.choices[0].message.content
            
            # Clean up markdown-wrapped JSON responses
            content = self._clean_json_response(content)
            
            tokens_used = response.usage.total_tokens
            
            cost = self._calculate_cost('openai',
                                       response.usage.prompt_tokens,
                                       response.usage.completion_tokens)
            
            return LLMResponse(
                content=content,
                provider='openai',
                model=config.get('default_model', 'gpt-4.1-mini'),
                tokens_used=tokens_used,
                cost_estimate=cost,
                metadata={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                }
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")

    def _call_gemini_with_messages(self, messages: List[Dict[str, str]], config: Dict) -> LLMResponse:
        """Call Google Gemini API with structured messages"""
        if not self.genai_client:
            raise Exception("Gemini client not initialized")
        
        try:
            model = genai.GenerativeModel(config.get('default_model', 'gemini-2.5-flash'))
            
            generation_config = genai.types.GenerationConfig(
                temperature=config.get('temperature', 0.1),
                max_output_tokens=config.get('max_tokens', 4000)
            )
            
            # Combine messages for Gemini (it doesn't support separate system/user messages)
            combined_prompt = self._combine_messages_for_gemini(messages)
            
            response = model.generate_content(
                combined_prompt,
                generation_config=generation_config
            )
            
            # Check for safety filters or empty responses
            if response.prompt_feedback:
                for feedback in response.prompt_feedback:
                    if feedback.block_reason:
                        raise Exception(f"Content blocked by safety filter: {feedback.block_reason}")
            
            content = response.text
            
            # Check if content is empty or None
            if not content or content.strip() == "":
                raise Exception("Empty response from Gemini API - possible content policy violation")
            
            # Clean up markdown-wrapped JSON responses from Gemini
            content = self._clean_json_response(content)
            
            # Note: Gemini API doesn't always provide token counts
            tokens_used = getattr(response.usage_metadata, 'total_token_count', None) if hasattr(response, 'usage_metadata') else None
            
            cost = self._calculate_cost('google', 
                                       tokens_used or 1000,  # Rough estimate if not provided
                                       tokens_used or 500)
            
            return LLMResponse(
                content=content,
                provider='google',
                model=config.get('default_model', 'gemini-2.5-flash'),
                tokens_used=tokens_used,
                cost_estimate=cost,
                metadata={}
            )
            
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")

    def _combine_messages_for_gemini(self, messages: List[Dict[str, str]]) -> str:
        """Combine system and user messages for Gemini API"""
        combined = []
        for message in messages:
            if message['role'] == 'system':
                combined.append(f"System: {message['content']}")
            elif message['role'] == 'user':
                combined.append(f"User: {message['content']}")
        return "\n\n".join(combined)

    def _clean_json_response(self, content: str) -> str:
        """Clean up JSON responses from various LLM providers"""
        content = content.strip()
        if content.startswith('```json') and content.endswith('```'):
            content = content[7:-3].strip()  # Remove ```json and ``` wrapper
        elif content.startswith('```') and content.endswith('```'):
            content = content[3:-3].strip()  # Remove ``` wrapper
        return content.strip()
    
    def _call_claude(self, prompt: str, config: Dict) -> LLMResponse:
        """Call Anthropic Claude API"""
        if not self.anthropic_client:
            raise Exception("Anthropic client not initialized")
        
        try:
            response = self.anthropic_client.messages.create(
                model=config.get('default_model', 'claude-3-5-sonnet-20241022'),
                max_tokens=config.get('max_tokens', 4000),
                temperature=config.get('temperature', 0.1),
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Clean up markdown-wrapped JSON responses
            content = content.strip()
            if content.startswith('```json') and content.endswith('```'):
                content = content[7:-3].strip()  # Remove ```json and ``` wrapper
            elif content.startswith('```') and content.endswith('```'):
                content = content[3:-3].strip()  # Remove ``` wrapper
            content = content.strip()
            
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            cost = self._calculate_cost('anthropic', 
                                       response.usage.input_tokens, 
                                       response.usage.output_tokens)
            
            return LLMResponse(
                content=content,
                provider='anthropic',
                model=config.get('default_model', 'claude-3-5-sonnet-20241022'),
                tokens_used=tokens_used,
                cost_estimate=cost,
                metadata={
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens
                }
            )
            
        except Exception as e:
            raise Exception(f"Claude API error: {e}")
    
    def _call_openai(self, prompt: str, config: Dict) -> LLMResponse:
        """Call OpenAI GPT API"""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        try:
            response = self.openai_client.chat.completions.create(
                model=config.get('default_model', 'gpt-4-turbo'),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.get('max_tokens', 4000),
                temperature=config.get('temperature', 0.1)
            )
            
            content = response.choices[0].message.content
            
            # Clean up markdown-wrapped JSON responses
            content = content.strip()
            if content.startswith('```json') and content.endswith('```'):
                content = content[7:-3].strip()  # Remove ```json and ``` wrapper
            elif content.startswith('```') and content.endswith('```'):
                content = content[3:-3].strip()  # Remove ``` wrapper
            content = content.strip()
            
            tokens_used = response.usage.total_tokens
            
            cost = self._calculate_cost('openai',
                                       response.usage.prompt_tokens,
                                       response.usage.completion_tokens)
            
            return LLMResponse(
                content=content,
                provider='openai',
                model=config.get('default_model', 'gpt-4-turbo'),
                tokens_used=tokens_used,
                cost_estimate=cost,
                metadata={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens
                }
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    def _call_gemini(self, prompt: str, config: Dict) -> LLMResponse:
        """Call Google Gemini API"""
        if not self.genai_client:
            raise Exception("Gemini client not initialized")
        
        try:
            model = genai.GenerativeModel(config.get('default_model', 'gemini-2.5-flash'))
            
            generation_config = genai.types.GenerationConfig(
                temperature=config.get('temperature', 0.1),
                max_output_tokens=config.get('max_tokens', 4000)
            )
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Check for safety filters or empty responses
            if response.prompt_feedback:
                for feedback in response.prompt_feedback:
                    if feedback.block_reason:
                        raise Exception(f"Content blocked by safety filter: {feedback.block_reason}")
            
            content = response.text
            
            # Check if content is empty or None
            if not content or content.strip() == "":
                raise Exception("Empty response from Gemini API - possible content policy violation")
            
            # Clean up markdown-wrapped JSON responses from Gemini
            content = content.strip()
            if content.startswith('```json') and content.endswith('```'):
                content = content[7:-3].strip()  # Remove ```json and ``` wrapper
            elif content.startswith('```') and content.endswith('```'):
                content = content[3:-3].strip()  # Remove ``` wrapper
            # Also handle cases where there might be extra whitespace or newlines
            content = content.strip()
            
            # Note: Gemini API doesn't always provide token counts
            tokens_used = getattr(response.usage_metadata, 'total_token_count', None) if hasattr(response, 'usage_metadata') else None
            
            cost = self._calculate_cost('google', 
                                       tokens_used or 1000,  # Rough estimate if not provided
                                       tokens_used or 500)
            
            return LLMResponse(
                content=content,
                provider='google',
                model=config.get('default_model', 'gemini-2.5-flash'),
                tokens_used=tokens_used,
                cost_estimate=cost,
                metadata={}
            )
            
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
    
    def _is_provider_available(self, provider: str) -> bool:
        """Check if provider is available and configured"""
        if provider == 'anthropic':
            return self.anthropic_client is not None
        elif provider == 'openai':
            return self.openai_client is not None
        elif provider == 'google':
            return self.genai_client is not None
        return False
    
    def _calculate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for API call"""
        if provider not in self.cost_rates:
            return 0.0
        
        rates = self.cost_rates[provider]
        input_cost = (input_tokens / 1000) * rates['input']
        output_cost = (output_tokens / 1000) * rates['output']
        
        return input_cost + output_cost
    
    def _get_default_config(self, provider: str) -> Dict[str, Any]:
        """Get default configuration for provider"""
        defaults = {
            'anthropic': {
                'default_model': 'claude-sonnet-4-20250514',
                'temperature': 0.1,
                'max_tokens': 2000,
                'timeout': 60
            },
                    'openai': {
            'default_model': 'gpt-4.1-mini',
            'temperature': 0.1,
            'max_tokens': 2000,
            'timeout': 60
        },
            'google': {
                'default_model': 'gemini-2.5-flash',
                'temperature': 0.05,
                'max_tokens': 2000,
                'timeout': 60
            }
        }
        
        return defaults.get(provider, {})
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        providers = []
        
        if self._is_provider_available('anthropic'):
            providers.append('anthropic')
        if self._is_provider_available('openai'):
            providers.append('openai')
        if self._is_provider_available('google'):
            providers.append('google')
        
        return providers
    
    def test_connection(self, provider: str) -> bool:
        """Test connection to specific provider"""
        try:
            response = self.call_llm(provider, "Test connection. Reply with 'OK'.", max_tokens=10)
            return response.content.strip().upper() == 'OK'
        except Exception as e:
            self.logger.log_error('llm_client', f"Connection test failed for {provider}: {e}", str(e))
            return False
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers"""
        status = {}
        
        for provider in ['anthropic', 'openai', 'google']:
            status[provider] = {
                'available': self._is_provider_available(provider),
                'configured': self._is_provider_available(provider),  # Same for now
                'api_key_set': self._check_api_key(provider),
                'last_test': None  # Could add connection test results
            }
        
        return status
    
    def _check_api_key(self, provider: str) -> bool:
        """Check if API key is set for provider"""
        key_map = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'google': 'GEMINI_API_KEY'
        }
        
        env_key = key_map.get(provider)
        return bool(os.getenv(env_key))

# Utility functions
def create_llm_client(config_manager=None) -> LLMClient:
    """Factory function to create LLM client"""
    return LLMClient(config_manager)

def quick_llm_call(prompt: str, provider: str = None) -> str:
    """Utility function for quick LLM calls"""
    client = LLMClient()
    
    if provider:
        response = client.call_llm(provider, prompt)
    else:
        response = client.call_llm_with_fallback(prompt)
    
    return response.content