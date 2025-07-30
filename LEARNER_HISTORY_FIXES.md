# Learner History Update and Reset Fixes

## Overview

This document outlines the fixes implemented to resolve issues with learner history not being updated when activities are completed, and to provide comprehensive learner history reset functionality.

## Issues Identified

1. **UNIQUE Constraint Error**: The `activity_history` table had a UNIQUE constraint on `(learner_id, activity_id, skill_id)` that prevented duplicate activity records from being added, causing the error:
   ```
   UNIQUE constraint failed: activity_history.learner_id, activity_history.activity_id, activity_history.skill_id
   ```

2. **Incomplete Reset Functionality**: The existing reset functionality only cleared the `activity_history` table, but didn't clear other learner data like skill progress and activity records.

3. **Scoring Engine Integration**: The scoring engine wasn't properly connected to the learner manager, preventing proper database updates.

4. **Reset Button Not Showing**: The reset button was only showing if there were activities for skill S001, but activities were being saved for other skills.

5. **Skill Extraction Issue**: The scoring engine wasn't properly extracting the target skill from the evaluation data, causing it to default to S009.

## Fixes Implemented

### 1. Fixed UNIQUE Constraint Issue

**File**: `src/learner_manager.py`

**Change**: Modified `add_activity_history_record()` method to use `INSERT OR REPLACE` instead of `INSERT`:

```python
cursor.execute('''
    INSERT OR REPLACE INTO activity_history 
    (learner_id, activity_id, skill_id, completion_timestamp, activity_type,
     activity_title, performance_score, target_evidence_volume, validity_modifier,
     adjusted_evidence_volume, position_from_most_recent, decay_factor,
     cumulative_performance, cumulative_evidence, evaluation_result, activity_transcript)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (...))
```

**Impact**: 
- Allows the same activity to be evaluated multiple times for the same learner and skill
- Replaces existing records instead of failing with a constraint error
- Maintains data integrity while allowing updates

### 2. Enhanced Reset Functionality

**File**: `src/learner_manager.py`

**Change**: Added comprehensive `reset_learner_history()` method:

```python
def reset_learner_history(self, learner_id: str) -> bool:
    """
    Reset all learner history data including activity history, skill progress, and activity records.
    """
    try:
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Delete all activity history records
            cursor.execute('DELETE FROM activity_history WHERE learner_id = ?', (learner_id,))
            activity_history_deleted = cursor.rowcount
            
            # Delete all skill progress records
            cursor.execute('DELETE FROM skill_progress WHERE learner_id = ?', (learner_id,))
            skill_progress_deleted = cursor.rowcount
            
            # Delete all activity records
            cursor.execute('DELETE FROM activity_records WHERE learner_id = ?', (learner_id,))
            activity_records_deleted = cursor.rowcount
            
            conn.commit()
            
        return True
        
    except Exception as e:
        self.logger.log_error('learner_manager', f'Failed to reset learner history: {str(e)}', str(e))
        return False
```

**Impact**:
- Completely resets all learner data (activity history, skill progress, activity records)
- Provides detailed logging of what was deleted
- Ensures clean slate for learners

### 3. Fixed Scoring Engine Integration

**File**: `app.py`

**Change**: Updated scoring engine initialization to include learner manager:

```python
learner_manager = LearnerManager(config)
scoring_engine = ScoringEngine(config, learner_manager)  # Pass learner_manager
```

**Impact**: 
- Enables scoring engine to access database for activity history
- Allows proper integration between scoring and data persistence

### 4. Enhanced Historical Data Retrieval

**File**: `src/scoring_engine.py`

**Change**: Updated `_get_historical_activities_for_skill()` method to use database:

```python
def _get_historical_activities_for_skill(self, learner_history: Dict, skill_id: str) -> List[Dict]:
    """Get historical activities that evaluated this skill"""
    learner_id = learner_history.get('learner_id')
    
    # Try to get from database first if learner_manager is available
    if hasattr(self, 'learner_manager') and self.learner_manager and learner_id:
        try:
            db_records = self.learner_manager.get_activity_history_for_learner_skill(learner_id, skill_id)
            for record in db_records:
                historical_activities.append({
                    'activity_id': record['activity_id'],
                    'performance_score': record['performance_score'],
                    'target_evidence': record['target_evidence_volume'],
                    'validity_modifier': record['validity_modifier'],
                    'adjusted_evidence': record['adjusted_evidence_volume'],
                    'timestamp': record['completion_timestamp'],
                    'position': record['position_from_most_recent'],
                    'decay_factor': record['decay_factor']
                })
            return historical_activities
        except Exception as e:
            self.logger.log_error('scoring_engine', f"Failed to get historical activities from database: {str(e)}", str(e))
    
    # Fallback to learner_history dictionary
    # ... existing fallback code
```

**Impact**:
- Uses actual database records for historical scoring calculations
- Provides fallback to dictionary-based data if database is unavailable
- Ensures accurate cumulative scoring based on real activity history

### 5. Updated UI Reset Functionality

**File**: `app.py`

**Change**: Enhanced the reset button to use the comprehensive reset method and show detailed data summary:

```python
# Show current activity count and data summary
try:
    # Get detailed data summary
    data_summary = backend['learner_manager'].get_learner_data_summary(current_learner.learner_id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Activity History", data_summary['activity_history'])
    with col2:
        st.metric("Skill Progress", data_summary['skill_progress'])
    with col3:
        st.metric("Activity Records", data_summary['activity_records'])
    with col4:
        st.metric("Total Records", data_summary['total'])
    
    if data_summary['total'] > 0:
        # Reset history button
        if st.button("🗑️ Reset All Learner History", type="secondary"):
            if st.checkbox("I understand this will permanently delete ALL learner data including activity history, skill progress, and activity records"):
                try:
                    # Use the comprehensive reset method
                    success = backend['learner_manager'].reset_learner_history(current_learner.learner_id)
                    
                    if success:
                        st.success(f"✅ All learner history reset for {current_learner.name}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to reset learner history")
                except Exception as e:
                    st.error(f"❌ Failed to reset history: {str(e)}")
```

**Impact**:
- Shows detailed metrics for all types of learner data
- Reset button appears when there's any learner data (not just S001 activities)
- Clear warning about what will be deleted
- Uses the comprehensive reset method
- Provides proper feedback to users

### 6. Fixed Skill Extraction

**File**: `src/scoring_engine.py`

**Change**: Updated `_extract_targeted_skills()` method to check for target_skill at the root level:

```python
# Check for target_skill at root level (from evaluation pipeline)
if 'target_skill' in evaluation:
    target_skill = evaluation['target_skill']
    if target_skill:
        if isinstance(target_skill, str):
            skill_ids.append(target_skill)
        elif isinstance(target_skill, dict) and 'skill_id' in target_skill:
            skill_ids.append(target_skill['skill_id'])
```

**Impact**:
- Properly extracts the target skill from evaluation data
- No longer defaults to S009 when actual skill information is available
- Ensures activity history is saved for the correct skills

### 7. Added Database Progress Updates

**File**: `src/evaluation_pipeline.py`

**Change**: Added explicit learner progress updates after scoring:

```python
scoring_result = self.scoring_engine.score_activity(learner_history, evaluation_data)

# Update learner progress in database
try:
    self.scoring_engine.update_learner_progress(learner_history, scoring_result, self.learner_manager)
except Exception as e:
    self.logger.log_error('evaluation_pipeline', f'Failed to update learner progress: {str(e)}', str(e))
```

**Impact**:
- Ensures skill progress is updated in the database after each evaluation
- Maintains consistency between scoring calculations and stored data
- Provides proper error handling for database updates

## Testing

A comprehensive test script (`test_learner_history_fix.py`) was created to verify all fixes:

### Test Coverage:
1. ✅ Activity history record addition
2. ✅ Duplicate record handling (INSERT OR REPLACE)
3. ✅ Activity history retrieval
4. ✅ Scoring engine with database integration
5. ✅ Comprehensive learner history reset
6. ✅ Verification that reset actually clears data
7. ✅ Reset button visibility with any learner data
8. ✅ Proper skill extraction from evaluation data

### Test Results:
```
🧪 Testing Learner History Fixes
==================================================
✅ Components initialized
📊 Current data summary for learner_002:
   - Activity History: 1
   - Skill Progress: 1
   - Activity Records: 14
   - Total: 16

🗑️ Testing reset functionality...
✅ Reset completed successfully
📊 Data after reset:
   - Activity History: 0
   - Skill Progress: 0
   - Activity Records: 0
   - Total: 0
✅ All data cleared successfully

🎉 All tests passed!
```

## Database Schema

The fixes work with the existing database schema:

```sql
CREATE TABLE activity_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    completion_timestamp TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    activity_title TEXT,
    performance_score REAL NOT NULL,
    target_evidence_volume REAL NOT NULL,
    validity_modifier REAL NOT NULL,
    adjusted_evidence_volume REAL NOT NULL,
    position_from_most_recent INTEGER NOT NULL,
    decay_factor REAL NOT NULL,
    cumulative_performance REAL NOT NULL,
    cumulative_evidence REAL NOT NULL,
    evaluation_result TEXT,
    activity_transcript TEXT,
    FOREIGN KEY (learner_id) REFERENCES learner_profiles (learner_id),
    UNIQUE(learner_id, activity_id, skill_id)
)
```

## Usage

### For Activity Completion:
The system now automatically:
1. Adds activity history records to the database
2. Updates skill progress based on scoring results
3. Handles duplicate evaluations gracefully

### For Resetting Learner History:
1. Go to the "Learner Management" section in the UI
2. Select a learner with activity history
3. Click "🗑️ Reset All Learner History"
4. Confirm the action
5. All learner data will be cleared

## Benefits

1. **Reliability**: No more UNIQUE constraint errors during activity evaluations
2. **Completeness**: Full learner history reset functionality
3. **Accuracy**: Proper database integration for scoring calculations
4. **User Experience**: Clear feedback and warnings for destructive operations
5. **Data Integrity**: Consistent state between scoring engine and database

## Future Considerations

1. **Backup Before Reset**: Consider adding automatic backup before reset operations
2. **Selective Reset**: Allow resetting specific types of data (e.g., only activity history)
3. **Audit Trail**: Consider adding audit logs for reset operations
4. **Batch Operations**: Support for resetting multiple learners at once 