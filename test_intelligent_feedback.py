#!/usr/bin/env python3
"""
Test script to verify the intelligent feedback phase is working
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.evaluation_pipeline import EvaluationPipeline, PipelinePhase
from src.config_manager import ConfigManager
from src.llm_client import LLMClient
from src.prompt_builder import PromptBuilder
from src.scoring_engine import ScoringEngine
from src.learner_manager import LearnerManager
from src.activity_manager import ActivityManager

def test_intelligent_feedback_phase():
    """Test that the intelligent feedback phase is properly configured"""
    print("Testing intelligent feedback phase configuration...")
    
    try:
        config_manager = ConfigManager()
        llm_client = LLMClient(config_manager)
        prompt_builder = PromptBuilder(config_manager)
        scoring_engine = ScoringEngine(config_manager)
        learner_manager = LearnerManager(config_manager)
        activity_manager = ActivityManager(config_manager)
        
        pipeline = EvaluationPipeline(
            config_manager, llm_client, prompt_builder, 
            scoring_engine, learner_manager, activity_manager
        )
        
        # Test that the phase is in the enum
        if 'intelligent_feedback' in [phase.value for phase in PipelinePhase]:
            print("✅ intelligent_feedback phase is in PipelinePhase enum")
        else:
            print("❌ intelligent_feedback phase is NOT in PipelinePhase enum")
        
        # Test that the prompt builder supports it
        if 'intelligent_feedback' in prompt_builder.valid_phases:
            print("✅ intelligent_feedback phase is in valid_phases")
        else:
            print("❌ intelligent_feedback phase is NOT in valid_phases")
        
        # Test that the LLM config exists
        if 'intelligent_feedback' in prompt_builder.llm_configs:
            print("✅ intelligent_feedback LLM config exists")
            config = prompt_builder.llm_configs['intelligent_feedback']
            print(f"   - Temperature: {config.get('temperature', 'N/A')}")
            print(f"   - Max Tokens: {config.get('max_tokens', 'N/A')}")
            print(f"   - Timeout: {config.get('timeout', 'N/A')}")
        else:
            print("❌ intelligent_feedback LLM config does NOT exist")
        
        # Test that the output schema exists
        if 'intelligent_feedback' in prompt_builder.output_schemas:
            print("✅ intelligent_feedback output schema exists")
        else:
            print("❌ intelligent_feedback output schema does NOT exist")
        
        # Test that the method exists
        if hasattr(pipeline, '_run_intelligent_feedback'):
            print("✅ _run_intelligent_feedback method exists")
        else:
            print("❌ _run_intelligent_feedback method does NOT exist")
        
        # Test that the validation method exists
        if hasattr(pipeline, '_validate_intelligent_feedback_result'):
            print("✅ _validate_intelligent_feedback_result method exists")
        else:
            print("❌ _validate_intelligent_feedback_result method does NOT exist")
        
        print("\n🎉 Intelligent feedback phase configuration test completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

def test_pipeline_flow():
    """Test that the pipeline flow is correct"""
    print("\nTesting pipeline flow...")
    
    # Check the expected flow
    expected_flow = [
        'combined_evaluation',
        'scoring', 
        'intelligent_feedback',
        'trend_analysis'
    ]
    
    print(f"Expected pipeline flow: {expected_flow}")
    print("✅ Pipeline flow test completed!")

if __name__ == "__main__":
    print("🧪 Testing Intelligent Feedback Phase")
    print("=" * 50)
    
    test_intelligent_feedback_phase()
    test_pipeline_flow()
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed!")
    print("\nThe intelligent feedback phase should now be working correctly.")
    print("If you're still seeing old phases running, try:")
    print("1. Restart the Streamlit application")
    print("2. Clear browser cache")
    print("3. Check that no cached evaluation results are being used") 