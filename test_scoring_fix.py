#!/usr/bin/env python3
"""
Test script to verify scoring engine fix for new pipeline format.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import ConfigManager
from src.scoring_engine import ScoringEngine

def test_scoring_extraction():
    """Test that scoring engine can extract performance scores from new pipeline format"""
    
    # Initialize components
    config_manager = ConfigManager()
    scoring_engine = ScoringEngine(config_manager)
    
    # Sample evaluation result in new pipeline format (from the actual data)
    sample_evaluation = {
        "activity_id": "problem_statement_crafting_cr",
        "learner_id": "learner_002",
        "timestamp": "2025-07-28T19:27:23.806906",
        "pipeline_phases": [
            {
                "phase": "combined_evaluation",
                "success": True,
                "result": {
                    "overall_score": 0.07,
                    "validity_modifier": 1.0,
                    "target_evidence_volume": 2.5,
                    "aspect_scores": [
                        {
                            "aspect_id": "user_centered_language",
                            "aspect_name": "User-Centered Language and Perspective",
                            "score": 0.05
                        }
                    ]
                }
            },
            {
                "phase": "scoring",
                "success": True,
                "result": {
                    "activity_score": 0.07,
                    "target_evidence_volume": 2.5,
                    "validity_modifier": 1.0
                }
            }
        ],
        "activity_generation_output": {
            "target_skill": "S002",
            "skills_targeted": ["S002"]
        }
    }
    
    # Test skill extraction
    targeted_skills = scoring_engine._extract_targeted_skills(sample_evaluation)
    print(f"Targeted skills: {targeted_skills}")
    
    # Test skill evaluation extraction
    for skill_id in targeted_skills:
        skill_data = scoring_engine._extract_skill_evaluation(sample_evaluation, skill_id)
        print(f"\nSkill {skill_id} data:")
        print(f"  Performance score: {skill_data['performance_score']}")
        print(f"  Target evidence: {skill_data['target_evidence']}")
        print(f"  Validity modifier: {skill_data['validity_modifier']}")
    
    # Test full scoring
    learner_history = {"learner_id": "learner_002", "activities": []}
    try:
        scoring_result = scoring_engine.score_activity(learner_history, sample_evaluation)
        print(f"\nScoring result:")
        print(f"  Activity ID: {scoring_result.activity_id}")
        print(f"  Skills evaluated: {scoring_result.total_skills_evaluated}")
        print(f"  Skills mastered: {scoring_result.skills_mastered}")
        print(f"  Overall progress: {scoring_result.overall_progress}")
        
        for skill_id, skill_score in scoring_result.skill_scores.items():
            print(f"\n  Skill {skill_id}:")
            print(f"    Cumulative score: {skill_score.cumulative_score}")
            print(f"    Overall status: {skill_score.overall_status}")
            
    except Exception as e:
        print(f"Error in scoring: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scoring_extraction() 