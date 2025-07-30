#!/usr/bin/env python3
"""
Test Enhanced Intelligent Feedback System
Tests the improved learner-appropriate feedback generation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_feedback_components():
    """Test the enhanced intelligent feedback components"""
    print("🧪 Testing Enhanced Intelligent Feedback Components")
    print("=" * 50)
    
    try:
        # Test 1: Check prompt builder enhancements
        print("\n📝 Test 1: Enhanced Prompt Configuration")
        
        # Import prompt builder directly
        from src.prompt_builder import PromptBuilder
        from src.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        prompt_builder = PromptBuilder(config_manager)
        
        print("✅ Prompt builder initialized successfully")
        
        # Check for enhanced components
        if 'intelligent_feedback' in prompt_builder.valid_phases:
            print("✅ intelligent_feedback phase is valid")
            
            # Check for enhanced components
            template_key = "CR_intelligent_feedback"
            if template_key in prompt_builder.prompt_templates:
                template = prompt_builder.prompt_templates[template_key]
                system_components = template.get('system_components', [])
                
                # Check for learner-appropriate guidelines
                has_learner_guidelines = any('learner_appropriate_guidelines' in comp for comp in system_components)
                if has_learner_guidelines:
                    print("✅ Learner-appropriate guidelines included")
                else:
                    print("❌ Learner-appropriate guidelines missing")
                    
                # Check for enhanced tone guidelines
                has_enhanced_tone = any('tone_guidelines' in comp for comp in system_components)
                if has_enhanced_tone:
                    print("✅ Enhanced tone guidelines included")
                else:
                    print("❌ Enhanced tone guidelines missing")
                    
                # Check for enhanced feedback objectives
                has_enhanced_objectives = any('feedback_objectives' in comp for comp in system_components)
                if has_enhanced_objectives:
                    print("✅ Enhanced feedback objectives included")
                else:
                    print("❌ Enhanced feedback objectives missing")
            else:
                print("❌ CR_intelligent_feedback template missing")
        else:
            print("❌ intelligent_feedback phase not valid")
        
        # Test 2: Check LLM configuration
        print("\n🤖 Test 2: LLM Configuration")
        if 'intelligent_feedback' in prompt_builder.llm_configs:
            config = prompt_builder.llm_configs['intelligent_feedback']
            print(f"✅ LLM config found: temperature={config.get('temperature')}, max_tokens={config.get('max_tokens')}")
        else:
            print("❌ LLM configuration missing")
        
        # Test 3: Check output schema
        print("\n📋 Test 3: Output Schema")
        if 'intelligent_feedback' in prompt_builder.output_schemas:
            schema = prompt_builder.output_schemas['intelligent_feedback']
            print("✅ Output schema exists")
            
            # Check for required fields
            required = schema.get('required', [])
            if 'intelligent_feedback' in required:
                print("✅ intelligent_feedback field required")
            else:
                print("❌ intelligent_feedback field not required")
        else:
            print("❌ Output schema missing")
        
        # Test 4: Check prompt components
        print("\n🔧 Test 4: Prompt Components")
        if hasattr(prompt_builder, 'prompt_components'):
            components = prompt_builder.prompt_components
            if 'phase_specific' in components:
                phase_specific = components['phase_specific']
                if 'intelligent_feedback' in phase_specific:
                    intelligent_feedback = phase_specific['intelligent_feedback']
                    
                    # Check for enhanced features
                    if 'learner_appropriate_guidelines' in intelligent_feedback:
                        print("✅ Learner-appropriate guidelines in components")
                        guidelines = intelligent_feedback['learner_appropriate_guidelines']
                        print(f"   - {len(guidelines)} guidelines defined")
                    else:
                        print("❌ Learner-appropriate guidelines missing from components")
                    
                    if 'feedback_objectives' in intelligent_feedback:
                        print("✅ Enhanced feedback objectives in components")
                        objectives = intelligent_feedback['feedback_objectives']
                        print(f"   - {len(objectives)} objectives defined")
                    else:
                        print("❌ Enhanced feedback objectives missing from components")
                    
                    if 'tone_guidelines' in intelligent_feedback:
                        print("✅ Enhanced tone guidelines in components")
                        tone_guidelines = intelligent_feedback['tone_guidelines']
                        print(f"   - {len(tone_guidelines)} guidelines defined")
                    else:
                        print("❌ Enhanced tone guidelines missing from components")
                else:
                    print("❌ intelligent_feedback not in phase_specific components")
            else:
                print("❌ phase_specific components missing")
        else:
            print("❌ prompt_components attribute missing")
        
        print("\n🎉 Enhanced Feedback Components Test Complete!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_feedback_components() 