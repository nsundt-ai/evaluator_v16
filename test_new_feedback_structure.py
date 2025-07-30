#!/usr/bin/env python3
"""
Test the new intelligent feedback structure with backend intelligence and learner feedback sections.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from prompt_builder import PromptBuilder
from config_manager import ConfigManager

def test_new_feedback_structure():
    """Test the new feedback structure with separate backend intelligence and learner feedback"""
    
    print("🧪 Testing New Intelligent Feedback Structure")
    print("=" * 50)
    
    # Initialize components
    config_manager = ConfigManager()
    prompt_builder = PromptBuilder(config_manager)
    
    # Test 1: Check that intelligent_feedback phase is valid
    print("\n1. Testing Phase Validity")
    if 'intelligent_feedback' in prompt_builder.valid_phases:
        print("✅ intelligent_feedback phase is valid")
    else:
        print("❌ intelligent_feedback phase is not valid")
    
    # Test 2: Check prompt templates for all activity types
    print("\n2. Testing Prompt Templates")
    activity_types = ['CR', 'COD', 'RP', 'SR', 'BR']
    for activity_type in activity_types:
        template_key = f"{activity_type}_intelligent_feedback"
        if template_key in prompt_builder.prompt_templates:
            print(f"✅ {template_key} template exists")
        else:
            print(f"❌ {template_key} template missing")
    
    # Test 3: Check LLM configuration
    print("\n3. Testing LLM Configuration")
    if 'intelligent_feedback' in prompt_builder.llm_configs:
        config = prompt_builder.llm_configs['intelligent_feedback']
        print(f"✅ LLM config exists: temperature={config.get('temperature')}, max_tokens={config.get('max_tokens')}")
    else:
        print("❌ LLM configuration missing")
    
    # Test 4: Check output schema
    print("\n4. Testing Output Schema")
    if 'intelligent_feedback' in prompt_builder.output_schemas:
        schema = prompt_builder.output_schemas['intelligent_feedback']
        print("✅ Output schema exists")
        
        # Check required fields
        required = schema.get('required', [])
        if 'intelligent_feedback' in required:
            print("✅ intelligent_feedback field required")
        else:
            print("❌ intelligent_feedback field not required")
        
        # Check properties structure
        properties = schema.get('properties', {})
        if 'intelligent_feedback' in properties:
            intelligent_feedback = properties['intelligent_feedback']
            if 'properties' in intelligent_feedback:
                props = intelligent_feedback['properties']
                
                # Check backend_intelligence
                if 'backend_intelligence' in props:
                    backend_props = props['backend_intelligence']['properties']
                    backend_required = ['overview', 'strengths', 'weaknesses', 'subskill_ratings']
                    missing_backend = [field for field in backend_required if field not in backend_props]
                    if not missing_backend:
                        print("✅ Backend intelligence has all required fields")
                    else:
                        print(f"❌ Backend intelligence missing fields: {missing_backend}")
                
                # Check learner_feedback
                if 'learner_feedback' in props:
                    learner_props = props['learner_feedback']['properties']
                    learner_required = ['overall', 'strengths', 'opportunities']
                    missing_learner = [field for field in learner_required if field not in learner_props]
                    if not missing_learner:
                        print("✅ Learner feedback has all required fields")
                    else:
                        print(f"❌ Learner feedback missing fields: {missing_learner}")
            else:
                print("❌ intelligent_feedback properties missing")
        else:
            print("❌ intelligent_feedback structure missing")
    else:
        print("❌ Output schema missing")
    
    # Test 5: Check prompt components
    print("\n5. Testing Prompt Components")
    phase_specific = prompt_builder.prompt_components.get('phase_specific', {})
    if 'intelligent_feedback' in phase_specific:
        intelligent_feedback = phase_specific['intelligent_feedback']
        print("✅ intelligent_feedback in phase_specific components")
        
        # Check for backend intelligence guidelines
        if 'backend_intelligence_guidelines' in intelligent_feedback:
            print("✅ Backend intelligence guidelines included")
        else:
            print("❌ Backend intelligence guidelines missing")
        
        # Check for learner feedback guidelines
        if 'learner_feedback_guidelines' in intelligent_feedback:
            print("✅ Learner feedback guidelines included")
        else:
            print("❌ Learner feedback guidelines missing")
    else:
        print("❌ intelligent_feedback not in phase_specific components")
    
    # Test 6: Check user prompt template
    print("\n6. Testing User Prompt Template")
    template_key = "CR_intelligent_feedback"
    if template_key in prompt_builder.prompt_templates:
        template = prompt_builder.prompt_templates[template_key]
        user_prompt = template.get('user_prompt_template', '')
        
        # Check for backend intelligence section
        if 'BACKEND INTELLIGENCE' in user_prompt:
            print("✅ Backend intelligence section properly labeled")
        else:
            print("❌ Backend intelligence section not properly labeled")
        
        # Check for learner feedback section
        if 'LEARNER FEEDBACK' in user_prompt:
            print("✅ Learner feedback section properly labeled")
        else:
            print("❌ Learner feedback section not properly labeled")
        
        # Check for new JSON structure
        if 'backend_intelligence' in user_prompt and 'learner_feedback' in user_prompt:
            print("✅ New JSON structure properly defined")
        else:
            print("❌ New JSON structure not properly defined")
    else:
        print("❌ CR_intelligent_feedback template missing")
    
    print("\n" + "=" * 50)
    print("✅ New intelligent feedback structure test completed!")

if __name__ == "__main__":
    test_new_feedback_structure() 