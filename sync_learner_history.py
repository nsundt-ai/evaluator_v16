#!/usr/bin/env python3
"""
Script to sync learner history from database to JSON files.
This ensures the JSON files are updated with the latest activities and progress.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import ConfigManager
from src.learner_manager import LearnerManager

def main():
    """Sync learner history for Sarah Martinez"""
    
    # Initialize components
    config_manager = ConfigManager()
    learner_manager = LearnerManager(config_manager)
    
    # Sync Sarah Martinez's learner history
    learner_id = "learner_002"  # Sarah Martinez
    json_path = "data/learners/learner_002_history.json"
    
    print(f"Syncing learner history for {learner_id}...")
    
    success = learner_manager.sync_learner_history_to_json(learner_id, json_path)
    
    if success:
        print(f"✅ Successfully synced learner history for {learner_id}")
        print(f"📁 Updated file: {json_path}")
        
        # Show what was synced
        activities = learner_manager.get_learner_activities(learner_id)
        print(f"📊 Total activities in database: {len(activities)}")
        
        for i, activity in enumerate(activities[:5], 1):  # Show first 5
            print(f"  {i}. {activity.activity_id} ({activity.timestamp})")
        
        if len(activities) > 5:
            print(f"  ... and {len(activities) - 5} more activities")
            
    else:
        print(f"❌ Failed to sync learner history for {learner_id}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 