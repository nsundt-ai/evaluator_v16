#!/usr/bin/env python3
"""
Debug script to understand skill extraction issue.
"""

import sys
import os
import json
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import ConfigManager
from src.scoring_engine import ScoringEngine

def debug_skill_extraction():
    """Debug why skill extraction is returning S009 instead of S002"""
    
    # Initialize components
    config_manager = ConfigManager()
    scoring_engine = ScoringEngine(config_manager)
    
    # Get the evaluation result from database
    db_path = "data/evaluator_v16.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT evaluation_result FROM activity_records 
        WHERE learner_id = 'learner_002' AND activity_id = 'problem_statement_crafting_cr'
        LIMIT 1
    ''')
    
    record = cursor.fetchone()
    if record:
        evaluation_result = json.loads(record['evaluation_result'])
        
        print("Evaluation result structure:")
        print(f"Keys: {list(evaluation_result.keys())}")
        
        if 'activity_generation_output' in evaluation_result:
            ag_output = evaluation_result['activity_generation_output']
            print(f"Activity generation output keys: {list(ag_output.keys())}")
            print(f"Target skill: {ag_output.get('target_skill')}")
            print(f"Skills targeted: {ag_output.get('skills_targeted')}")
        
        if 'pipeline_phases' in evaluation_result:
            phases = evaluation_result['pipeline_phases']
            print(f"Pipeline phases: {[phase.get('phase') for phase in phases]}")
        
        # Test skill extraction
        targeted_skills = scoring_engine._extract_targeted_skills(evaluation_result)
        print(f"\nExtracted skills: {targeted_skills}")
        
        # Test skill evaluation extraction
        for skill_id in targeted_skills:
            skill_data = scoring_engine._extract_skill_evaluation(evaluation_result, skill_id)
            print(f"\nSkill {skill_id} data:")
            print(f"  Performance score: {skill_data['performance_score']}")
            print(f"  Target evidence: {skill_data['target_evidence']}")
            print(f"  Validity modifier: {skill_data['validity_modifier']}")
    
    conn.close()

if __name__ == "__main__":
    debug_skill_extraction() 