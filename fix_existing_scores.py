#!/usr/bin/env python3
"""
Script to fix existing activity history records with correct performance scores.
"""

import sys
import os
import json
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import ConfigManager
from src.scoring_engine import ScoringEngine

def fix_existing_scores():
    """Fix existing activity history records with correct performance scores"""
    
    # Initialize components
    config_manager = ConfigManager()
    scoring_engine = ScoringEngine(config_manager)
    
    # Connect to database
    db_path = "data/evaluator_v16.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get all activity records for Sarah Martinez that need fixing
        cursor.execute('''
            SELECT ar.activity_id, ar.learner_id, ar.timestamp, ar.evaluation_result,
                   ah.performance_score, ah.cumulative_performance
            FROM activity_records ar
            LEFT JOIN activity_history ah ON ar.activity_id = ah.activity_id 
                AND ar.learner_id = ah.learner_id
            WHERE ar.learner_id = 'learner_002'
            ORDER BY ar.timestamp DESC
        ''')
        
        records = cursor.fetchall()
        print(f"Found {len(records)} activity records to check")
        
        for record in records:
            activity_id = record['activity_id']
            learner_id = record['learner_id']
            timestamp = record['timestamp']
            evaluation_result = json.loads(record['evaluation_result'])
            current_performance = record['performance_score'] if record['performance_score'] is not None else 0.0
            current_cumulative = record['cumulative_performance'] if record['cumulative_performance'] is not None else 0.0
            
            print(f"\nProcessing activity: {activity_id}")
            print(f"  Current performance score: {current_performance}")
            print(f"  Current cumulative performance: {current_cumulative}")
            
            # Add activity specification to evaluation result for skill extraction
            # Based on the activity file, this activity targets skill S002
            evaluation_result['activity_generation_output'] = {
                'target_skill': 'S002',
                'skills_targeted': ['S002']
            }
            print(f"  Added activity spec: target_skill=S002")
            
            # Extract correct performance score using the fixed scoring engine
            targeted_skills = scoring_engine._extract_targeted_skills(evaluation_result)
            
            # If no skills found in evaluation, use the skill from the activity history record
            if not targeted_skills:
                cursor.execute('''
                    SELECT skill_id FROM activity_history 
                    WHERE learner_id = ? AND activity_id = ?
                    LIMIT 1
                ''', (learner_id, activity_id))
                skill_record = cursor.fetchone()
                if skill_record:
                    targeted_skills = [skill_record['skill_id']]
                else:
                    targeted_skills = ['S002']  # Default for this activity
            
            for skill_id in targeted_skills:
                skill_data = scoring_engine._extract_skill_evaluation(evaluation_result, skill_id)
                correct_performance = skill_data['performance_score']
                correct_target_evidence = skill_data['target_evidence']
                correct_validity_modifier = skill_data['validity_modifier']
                
                # If target evidence is 0, use the value from the activity file (2.5 for this activity)
                if correct_target_evidence == 0.0:
                    correct_target_evidence = 2.5
                    print(f"    Using default target evidence: 2.5")
                
                print(f"  Skill {skill_id}:")
                print(f"    Correct performance score: {correct_performance}")
                print(f"    Target evidence: {correct_target_evidence}")
                print(f"    Validity modifier: {correct_validity_modifier}")
                
                # Update the activity history record if the performance score is wrong
                if abs(current_performance - correct_performance) > 0.001:  # Allow for floating point precision
                    print(f"    *** UPDATING: {current_performance} -> {correct_performance}")
                    
                    # Update the activity history record
                    cursor.execute('''
                        UPDATE activity_history 
                        SET performance_score = ?,
                            target_evidence_volume = ?,
                            validity_modifier = ?,
                            adjusted_evidence_volume = ?,
                            decay_adjusted_evidence_volume = ?
                        WHERE learner_id = ? AND activity_id = ? AND skill_id = ?
                    ''', (
                        correct_performance,
                        correct_target_evidence,
                        correct_validity_modifier,
                        correct_target_evidence * correct_validity_modifier,
                        correct_target_evidence * correct_validity_modifier,  # No decay for current activity
                        learner_id,
                        activity_id,
                        skill_id
                    ))
                    
                    if cursor.rowcount > 0:
                        print(f"    Updated {cursor.rowcount} record(s)")
                    else:
                        print(f"    No records updated - record may not exist")
                else:
                    print(f"    Performance score is correct")
        
        # Commit changes
        conn.commit()
        print(f"\nDatabase updates completed")
        
        # Show updated records
        print(f"\nUpdated activity history records:")
        cursor.execute('''
            SELECT activity_id, skill_id, performance_score, cumulative_performance, completion_timestamp
            FROM activity_history 
            WHERE learner_id = 'learner_002'
            ORDER BY completion_timestamp DESC
        ''')
        
        updated_records = cursor.fetchall()
        for record in updated_records:
            print(f"  {record['activity_id']} | {record['skill_id']} | {record['performance_score']} | {record['cumulative_performance']} | {record['completion_timestamp']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_existing_scores() 