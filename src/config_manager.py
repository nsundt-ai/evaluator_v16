"""
Configuration Manager for Evaluator v16
Provides centralized access to all JSON configuration files with validation and persistence.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from src.logger import get_logger

class ConfigManager:
    """Centralized configuration management for Evaluator v16"""
    
    def __init__(self, config_path: str = "config"):
        self.config_path = Path(config_path)
        self.configs = {}
        self.logger = get_logger()
        
        # Ensure config directory exists
        self.config_path.mkdir(exist_ok=True)
        
        # Load all configurations
        self.load_all_configs()
    
    def load_all_configs(self):
        """Load all JSON configuration files"""
        config_files = {
            'llm_settings': 'llm_settings.json',
            'scoring_config': 'scoring_config.json',
            'domain_model': 'domain_model.json',
            'app_state': 'app_state.json'
        }
        
        for config_key, filename in config_files.items():
            file_path = self.config_path / filename
            
            try:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.configs[config_key] = json.load(f)
                    self.logger.log_system_event('config_manager', 'config_loaded', f"Loaded config: {config_key}")
                else:
                    self.logger.log_system_event('config_manager', 'config_missing', f"Config file not found: {filename}", level="WARNING")
                    self.configs[config_key] = self._get_default_config(config_key)
                    
            except json.JSONDecodeError as e:
                self.logger.log_error('config_manager', f"Invalid JSON in {filename}: {e}", str(e))
                self.configs[config_key] = self._get_default_config(config_key)
            except Exception as e:
                self.logger.log_error('config_manager', f"Error loading {filename}: {e}", str(e))
                self.configs[config_key] = self._get_default_config(config_key)
    
    def get_config(self, config_key: str) -> Dict[str, Any]:
        """Get entire configuration by key"""
        if config_key not in self.configs:
            self.logger.log_system_event('config_manager', 'config_key_missing', f"Config key not found: {config_key}", level="WARNING")
            return {}
        return self.configs[config_key].copy()
    
    def get_llm_config(self, provider: str, phase: str = None) -> Dict[str, Any]:
        """Get LLM configuration for specific provider and phase"""
        llm_settings = self.configs.get('llm_settings', {})
        providers = llm_settings.get('providers', {})
        
        # Handle old provider names by mapping to new ones
        provider_mapping = {
            'claude_4_sonnet': 'anthropic',
            'gpt_4_1_turbo': 'openai', 
            'gemini_2_5_pro': 'google'
        }
        
        # Map old names to new names for backward compatibility
        if provider in provider_mapping:
            self.logger.log_system_event('config_manager', 'provider_mapping', f"Mapping legacy provider '{provider}' to '{provider_mapping[provider]}'")
            provider = provider_mapping[provider]
        
        if provider not in providers:
            self.logger.log_system_event('config_manager', 'provider_missing', f"LLM provider not found: {provider}", level="WARNING")
            return {}
        
        # Start with provider defaults
        config = providers[provider].copy()
        
        # Apply phase-specific overrides if specified
        if phase:
            phases = llm_settings.get('phases', {})
            if phase in phases:
                phase_config = phases[phase]
                # Apply phase overrides for this provider
                if provider in phase_config:
                    config.update(phase_config[provider])
        
        return config
    
    def get_scoring_config(self) -> Dict[str, Any]:
        """Get scoring configuration with thresholds"""
        return self.configs.get('scoring_config', {})
    
    def get_scoring_thresholds(self) -> Dict[str, Any]:
        """Get scoring thresholds specifically"""
        scoring_config = self.get_scoring_config()
        return scoring_config.get('thresholds', {})
    
    def get_domain_model(self) -> Dict[str, Any]:
        """Get domain model with competencies and skills"""
        return self.configs.get('domain_model', {})
    
    def get_competencies(self) -> Dict[str, Any]:
        """Get competencies from domain model"""
        domain_model = self.get_domain_model()
        return domain_model.get('competencies', {})
    
    def get_skills_for_competency(self, competency_id: str) -> Dict[str, Any]:
        """Get skills for a specific competency"""
        competencies = self.get_competencies()
        if competency_id in competencies:
            return competencies[competency_id].get('skills', {})
        return {}
    
    def get_app_state(self) -> Dict[str, Any]:
        """Get application state configuration"""
        return self.configs.get('app_state', {})
    
    def update_config(self, config_key: str, updates: Dict[str, Any]):
        """Update configuration and save to file"""
        if config_key not in self.configs:
            self.logger.log_error('config_manager', f"Cannot update unknown config: {config_key}", config_key)
            return False
        
        try:
            # Deep update
            self._deep_update(self.configs[config_key], updates)
            
            # Save to file
            self.save_config(config_key)
            
            self.logger.log_system_event('config_manager', 'config_updated', f"Updated config: {config_key}")
            return True
            
        except Exception as e:
            self.logger.log_error('config_manager', f"Error updating config {config_key}: {e}", str(e))
            return False
    
    def update_scoring_threshold(self, gate_type: str, level: str, value: float):
        """Update specific scoring threshold"""
        updates = {
            'thresholds': {
                gate_type: {
                    level: value
                }
            }
        }
        return self.update_config('scoring_config', updates)
    
    def save_config(self, config_key: str):
        """Save specific configuration to file"""
        config_files = {
            'llm_settings': 'llm_settings.json',
            'scoring_config': 'scoring_config.json',
            'domain_model': 'domain_model.json',
            'app_state': 'app_state.json'
        }
        
        if config_key not in config_files:
            self.logger.log_error('config_manager', f"Unknown config key: {config_key}", config_key)
            return False
        
        filename = config_files[config_key]
        file_path = self.config_path / filename
        
        try:
            # Atomic write using temporary file
            temp_path = file_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.configs[config_key], f, indent=2, ensure_ascii=False)
            
            # Atomic move
            temp_path.replace(file_path)
            
            self.logger.log_system_event('config_manager', 'config_saved', f"Saved config: {filename}")
            return True
            
        except Exception as e:
            self.logger.log_error('config_manager', f"Error saving {filename}: {e}", str(e))
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    def validate_config(self, config_key: str) -> bool:
        """Validate configuration structure"""
        config = self.configs.get(config_key, {})
        
        if config_key == 'llm_settings':
            return self._validate_llm_settings(config)
        elif config_key == 'scoring_config':
            return self._validate_scoring_config(config)
        elif config_key == 'domain_model':
            return self._validate_domain_model(config)
        elif config_key == 'app_state':
            return self._validate_app_state(config)
        
        return True  # Default to valid for unknown configs
    
    def get_llm_fallback_chain(self) -> list:
        """Get ordered list of LLM providers for fallback"""
        llm_settings = self.configs.get('llm_settings', {})
        fallback_config = llm_settings.get('fallback_configuration', {})
        return fallback_config.get('fallback_order', ['anthropic', 'openai', 'google'])
    
    def _deep_update(self, target: Dict, source: Dict):
        """Recursively update nested dictionary"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _get_default_config(self, config_key: str) -> Dict[str, Any]:
        """Get default configuration for missing files"""
        defaults = {
            'llm_settings': {
                "providers": {
                    "anthropic": {
                        "name": "Anthropic",
                        "default_model": "claude-sonnet-4-20250514",
                        "temperature": 0.1,
                        "max_tokens": 4000,
                        "timeout": 120
                    },
                    "openai": {
                        "name": "OpenAI",
                        "default_model": "gpt-4.1-turbo",
                        "temperature": 0.1,
                        "max_tokens": 4000,
                        "timeout": 120
                    },
                    "google": {
                        "name": "Google Gemini",
                        "default_model": "gemini-2.5-pro",
                        "temperature": 0.1,
                        "max_tokens": 4000,
                        "timeout": 120
                    }
                },
                "fallback_configuration": {
                    "enabled": True,
                    "fallback_order": ["anthropic", "openai", "google"]
                },
                "phases": {}
            },
            'scoring_config': {
                "algorithm": {
                    "type": "position_based_decay",
                    "decay_factor": 0.9,
                    "prior_mean": 0.0,
                    "sem_calculation": "standard"
                },
                "thresholds": {
                    "performance": {
                        "at_level": 0.75,
                        "approaching": 0.65,
                        "developing": 0.50
                    },
                    "evidence": {
                        "sufficient": 30.0,
                        "approaching": 20.0,
                        "developing": 10.0
                    }
                },
                "adjustable_ranges": {
                    "performance_gates": {"min": 0.5, "max": 0.95, "step": 0.05},
                    "evidence_gates": {"min": 10.0, "max": 100.0, "step": 5.0},
                    "decay_factor": {"min": 0.7, "max": 0.95, "step": 0.05}
                }
            },
            'domain_model': {
                "competencies": {},
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now().isoformat(),
                    "total_competencies": 0,
                    "total_skills": 0
                }
            },
            'app_state': {
                "application_settings": {
                    "app_name": "Evaluator v16",
                    "version": "1.0.0",
                    "debug_mode": True,
                    "log_level": "INFO"
                },
                "ui_state": {
                    "default_tab": "Activity Explorer",
                    "selected_learner": None,
                    "current_activity": None
                },
                "session_data": {
                    "current_session_id": None,
                    "activities_evaluated_this_session": 0
                }
            }
        }
        
        return defaults.get(config_key, {})
    
    def _validate_llm_settings(self, config: Dict) -> bool:
        """Validate LLM settings structure"""
        required_keys = ['providers', 'fallback_configuration']
        for required_key in required_keys:
            if required_key not in config:
                return False
        return True
    
    def _validate_scoring_config(self, config: Dict) -> bool:
        """Validate scoring configuration structure"""
        required_keys = ['algorithm', 'thresholds']
        for required_key in required_keys:
            if required_key not in config:
                return False
        
        # Check threshold structure
        thresholds = config.get('thresholds', {})
        required_threshold_types = ['performance', 'evidence']
        for threshold_type in required_threshold_types:
            if threshold_type not in thresholds:
                return False
        return True
    
    def _validate_domain_model(self, config: Dict) -> bool:
        """Validate domain model structure"""
        return 'competencies' in config
    
    def _validate_app_state(self, config: Dict) -> bool:
        """Validate application state structure"""
        required_keys = ['application_settings', 'ui_state']
        for required_key in required_keys:
            if required_key not in config:
                return False
        return True

# Utility functions for external use
def load_config_manager() -> ConfigManager:
    """Factory function to create ConfigManager instance"""
    return ConfigManager()

def get_config(config_key: str, config_manager: ConfigManager = None) -> Dict[str, Any]:
    """Utility function to get configuration"""
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager.get_config(config_key)