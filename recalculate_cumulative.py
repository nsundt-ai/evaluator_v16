#!/usr/bin/env python3
"""
Script to recalculate cumulative performance for all activities.
"""

import sys
import os
import json
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import ConfigManager
from src.scoring_engine import ScoringEngine

def recalculate_cumulative_performance():
    """Recalculate cumulative performance for all activities"""
    
    # Initialize components
    config_manager = ConfigManager()
    scoring_engine = ScoringEngine(config_manager)
    
    # Connect to database
    db_path = "data/evaluator_v16.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get all activity history records for Sarah Martinez
        cursor.execute('''
            SELECT learner_id, skill_id, activity_id, completion_timestamp, performance_score,
                   target_evidence_volume, validity_modifier, adjusted_evidence_volume
            FROM activity_history 
            WHERE learner_id = 'learner_002'
            ORDER BY completion_timestamp ASC
        ''')
        
        records = cursor.fetchall()
        print(f"Found {len(records)} activity history records")
        
        # Group by skill_id and recalculate cumulative performance
        skills_data = {}
        for record in records:
            skill_id = record['skill_id']
            if skill_id not in skills_data:
                skills_data[skill_id] = []
            
            skills_data[skill_id].append({
                'activity_id': record['activity_id'],
                'performance_score': record['performance_score'],
                'target_evidence': record['target_evidence_volume'],
                'validity_modifier': record['validity_modifier'],
                'adjusted_evidence': record['adjusted_evidence_volume'],
                'timestamp': record['completion_timestamp']
            })
        
        # Recalculate cumulative performance for each skill
        for skill_id, activities in skills_data.items():
            print(f"\nRecalculating cumulative performance for skill {skill_id}")
            print(f"  Activities: {len(activities)}")
            
            # Sort activities by timestamp
            activities.sort(key=lambda x: x['timestamp'])
            
            # Calculate cumulative performance using the scoring engine's algorithm
            cumulative_performance = scoring_engine._calculate_cumulative_score(activities)
            total_evidence = scoring_engine._calculate_total_evidence(activities)
            
            print(f"  Cumulative performance: {cumulative_performance:.3f}")
            print(f"  Total evidence: {total_evidence:.3f}")
            
            # Update all activities for this skill with the new cumulative performance
            for i, activity in enumerate(activities):
                # Calculate cumulative performance up to this point in time
                activities_up_to_now = activities[:i+1]
                cumulative_at_time = scoring_engine._calculate_cumulative_score(activities_up_to_now)
                cumulative_evidence_at_time = scoring_engine._calculate_total_evidence(activities_up_to_now)
                
                print(f"    {activity['activity_id']}: {activity['performance_score']:.3f} -> cumulative: {cumulative_at_time:.3f}")
                
                # Update the activity history record
                cursor.execute('''
                    UPDATE activity_history 
                    SET cumulative_performance = ?,
                        cumulative_evidence = ?
                    WHERE learner_id = ? AND activity_id = ? AND skill_id = ?
                ''', (
                    cumulative_at_time,
                    cumulative_evidence_at_time,
                    'learner_002',
                    activity['activity_id'],
                    skill_id
                ))
        
        # Commit changes
        conn.commit()
        print(f"\nCumulative performance recalculation completed")
        
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
            print(f"  {record['activity_id']} | {record['skill_id']} | {record['performance_score']:.3f} | {record['cumulative_performance']:.3f} | {record['completion_timestamp']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    recalculate_cumulative_performance() 