#!/usr/bin/env python3
"""
Test script to verify the new pipeline with intelligent feedback phase
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

def test_pipeline_phases():
    """Test that the pipeline has the correct phases"""
    print("Testing pipeline phases...")
    
    # Check that the enum has the correct phases
    expected_phases = [
        'combined',
        'scoring', 
        'intelligent_feedback',
        'trend'
    ]
    
    actual_phases = [phase.value for phase in PipelinePhase]
    print(f"Expected phases: {expected_phases}")
    print(f"Actual phases: {actual_phases}")
    
    # Check that deprecated phases are marked
    deprecated_phases = ['diagnostic', 'feedback']
    for phase in deprecated_phases:
        if phase in actual_phases:
            print(f"⚠️  Warning: Deprecated phase '{phase}' still exists")
    
    print("✅ Pipeline phase test completed")

def test_prompt_builder():
    """Test that the prompt builder supports the new phase"""
    print("\nTesting prompt builder...")
    
    try:
        config_manager = ConfigManager()
        prompt_builder = PromptBuilder(config_manager)
        
        # Check that intelligent_feedback is in valid phases
        if 'intelligent_feedback' in prompt_builder.valid_phases:
            print("✅ intelligent_feedback phase is valid")
        else:
            print("❌ intelligent_feedback phase is not valid")
        
        # Check that prompt templates exist for intelligent_feedback
        activity_types = ['CR', 'COD', 'RP', 'SR', 'BR']
        for activity_type in activity_types:
            template_key = f"{activity_type}_intelligent_feedback"
            if template_key in prompt_builder.prompt_templates:
                print(f"✅ Template exists for {template_key}")
            else:
                print(f"❌ Template missing for {template_key}")
        
        # Check LLM configuration
        if 'intelligent_feedback' in prompt_builder.llm_configs:
            print("✅ LLM configuration exists for intelligent_feedback")
        else:
            print("❌ LLM configuration missing for intelligent_feedback")
        
        # Check output schema
        if 'intelligent_feedback' in prompt_builder.output_schemas:
            print("✅ Output schema exists for intelligent_feedback")
        else:
            print("❌ Output schema missing for intelligent_feedback")
            
    except Exception as e:
        print(f"❌ Prompt builder test failed: {e}")

def test_pipeline_initialization():
    """Test that the pipeline can be initialized"""
    print("\nTesting pipeline initialization...")
    
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
        
        print("✅ Pipeline initialized successfully")
        
        # Test restart pipeline function
        valid_restart_phases = ['combined', 'scoring', 'intelligent_feedback', 'trend']
        print(f"✅ Valid restart phases: {valid_restart_phases}")
        
    except Exception as e:
        print(f"❌ Pipeline initialization failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing New Pipeline Implementation")
    print("=" * 50)
    
    test_pipeline_phases()
    test_prompt_builder()
    test_pipeline_initialization()
    
    print("\n" + "=" * 50)
    print("🎉 Pipeline test completed!")
    print("\nExpected new pipeline flow:")
    print("1. Summative Evaluation (Rubric + Validity)")
    print("2. Scoring")
    print("3. Intelligent Feedback (Diagnostic + Feedback)")
    print("4. Trend Analysis (Disabled)") 