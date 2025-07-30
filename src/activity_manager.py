"""
Evaluator v16 - Activity Manager Module

Handles loading, validation, and management of activity files.
Supports all 5 activity types: CR, COD, RP, SR, BR with interactive state management.

Author: Generated for Evaluator v16 Project
Version: 1.0.0
"""

import json
import os
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from pathlib import Path
import logging
from datetime import datetime, timezone
import hashlib

from config_manager import ConfigManager
from logger import get_logger


@dataclass
class ActivitySpec:
    """Activity specification data structure"""
    activity_id: str
    activity_type: str  # CR, COD, RP, SR, BR
    title: str
    description: str
    target_skill: str
    target_evidence_volume: float
    cognitive_level: str  # L1, L2, L3, L4
    depth_level: str     # D1, D2, D3, D4
    rubric: Dict[str, Any]
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    activity_generation_output: Optional[Dict[str, Any]] = None
    created_date: Optional[str] = None
    version: str = "1.0"

    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now(timezone.utc).isoformat()


@dataclass
class InteractiveSession:
    """Interactive activity session state (for RP and BR)"""
    session_id: str
    activity_id: str
    learner_id: str
    session_type: str  # 'role_play' or 'branching'
    current_state: Dict[str, Any]
    interaction_history: List[Dict[str, Any]]
    start_time: str
    last_activity: str
    is_complete: bool = False
    completion_time: Optional[str] = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now(timezone.utc).isoformat()
        if self.last_activity is None:
            self.last_activity = self.start_time


class ActivityManager:
    """
    Manages activity loading, validation, and interactive session handling.
    Supports all 5 activity types with proper schema validation.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize ActivityManager with configuration.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = get_logger()
        
        # Get activities path from environment or config
        self.activities_path = os.getenv('ACTIVITIES_PATH', 'data/activities')
        
        # Ensure activities directory exists
        os.makedirs(self.activities_path, exist_ok=True)
        
        # Activity cache
        self._activity_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Interactive session tracking
        self._active_sessions = {}
        
        # Valid activity types
        self.valid_activity_types = {'CR', 'COD', 'RP', 'SR', 'BR'}
        
        # Schema validation rules
        self._init_validation_schemas()
        
        self.logger.log_system_event('activity_manager', 'initialized', 
                                    f'Activity manager initialized with path: {self.activities_path}')

    def _init_validation_schemas(self) -> None:
        """Initialize activity schema validation rules"""
        self.required_fields = {
            'base': {
                'activity_id', 'activity_type', 'title', 'description', 
                'target_skill', 'target_evidence_volume', 'cognitive_level', 
                'depth_level', 'content', 'metadata'
            },
            'rubric_required': {'CR', 'COD', 'RP'},  # These types need rubrics
            'autoscored': {'SR', 'BR'}  # These types are autoscored
        }
        
        self.valid_cognitive_levels = {'L1', 'L2', 'L3', 'L4'}
        self.valid_depth_levels = {'D1', 'D2', 'D3', 'D4'}

    def load_activities(self, force_reload: bool = False) -> Dict[str, ActivitySpec]:
        """
        Load all activities from the activities directory.
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            Dictionary mapping activity_id to ActivitySpec
        """
        activities = {}
        
        try:
            if not os.path.exists(self.activities_path):
                self.logger.log_error('activity_manager', 'Activities directory not found', 
                                    '', {'path': self.activities_path})
                return {}
            
            # Scan for JSON files
            json_files = list(Path(self.activities_path).glob('*.json'))
            
            for json_file in json_files:
                activity_id = json_file.stem
                
                # Check if we need to reload this file
                if not force_reload and self._is_cached_valid(activity_id, json_file):
                    activities[activity_id] = self._activity_cache[activity_id]
                    continue
                
                # Load and validate activity
                activity = self._load_single_activity(json_file)
                if activity:
                    activities[activity.activity_id] = activity
                    # Cache the activity
                    self._activity_cache[activity.activity_id] = activity
                    self._cache_timestamps[activity.activity_id] = datetime.now().timestamp()
            
            self.logger.log_system_event('activity_manager', 'activities_loaded', 
                                       f'Loaded {len(activities)} activities')
            return activities
            
        except Exception as e:
            self.logger.log_error('activity_manager', f'Failed to load activities: {str(e)}', 
                                str(e), {'path': self.activities_path})
            return {}

    def _is_cached_valid(self, activity_id: str, file_path: Path) -> bool:
        """Check if cached activity is still valid"""
        if activity_id not in self._activity_cache:
            return False
        
        if activity_id not in self._cache_timestamps:
            return False
        
        # Check cache TTL
        cache_age = datetime.now().timestamp() - self._cache_timestamps[activity_id]
        if cache_age > self._cache_ttl:
            return False
        
        # Check file modification time
        try:
            file_mtime = file_path.stat().st_mtime
            cache_time = self._cache_timestamps[activity_id]
            if file_mtime > cache_time:
                return False
        except OSError:
            return False
        
        return True

    def _load_single_activity(self, file_path: Path) -> Optional[ActivitySpec]:
        """
        Load and validate a single activity file.
        
        Args:
            file_path: Path to activity JSON file
            
        Returns:
            ActivitySpec instance or None if invalid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                activity_data = json.load(f)
            
            # Validate the activity
            if not self._validate_activity_schema(activity_data, str(file_path)):
                return None
            
            # Create ActivitySpec instance
            activity = ActivitySpec(
                activity_id=activity_data['activity_id'],
                activity_type=activity_data['activity_type'],
                title=activity_data['title'],
                description=activity_data['description'],
                target_skill=activity_data['target_skill'],
                target_evidence_volume=float(activity_data['target_evidence_volume']),
                cognitive_level=activity_data['cognitive_level'],
                depth_level=activity_data['depth_level'],
                rubric=activity_data.get('rubric', {}),
                content=activity_data['content'],
                metadata=activity_data['metadata'],
                activity_generation_output=activity_data.get('activity_generation_output'),
                created_date=activity_data.get('created_date'),
                version=activity_data.get('version', '1.0')
            )
            
            self.logger.log_system_event('activity_manager', 'activity_loaded', 
                                       f'Activity {activity.activity_id} loaded successfully',
                                       {'file_path': str(file_path), 'type': activity.activity_type})
            
            return activity
            
        except json.JSONDecodeError as e:
            self.logger.log_error('activity_manager', f'JSON parsing error in {file_path}: {str(e)}', 
                                str(e), {'file_path': str(file_path)})
            return None
        except Exception as e:
            self.logger.log_error('activity_manager', f'Failed to load activity {file_path}: {str(e)}', 
                                str(e), {'file_path': str(file_path)})
            return None

    def _validate_activity_schema(self, activity_data: Dict[str, Any], file_path: str) -> bool:
        """
        Validate activity data against schema requirements.
        
        Args:
            activity_data: Activity data dictionary
            file_path: File path for error reporting
            
        Returns:
            bool: True if valid
        """
        try:
            # Check required base fields
            missing_fields = self.required_fields['base'] - set(activity_data.keys())
            if missing_fields:
                self.logger.log_error('activity_manager', 
                                    f'Missing required fields in {file_path}: {missing_fields}',
                                    'schema_validation_error', 
                                    {'file_path': file_path, 'missing_fields': list(missing_fields)})
                return False
            
            # Validate activity type
            activity_type = activity_data['activity_type']
            if activity_type not in self.valid_activity_types:
                self.logger.log_error('activity_manager', 
                                    f'Invalid activity type in {file_path}: {activity_type}',
                                    'schema_validation_error',
                                    {'file_path': file_path, 'invalid_type': activity_type})
                return False
            
            # Validate cognitive and depth levels
            if activity_data['cognitive_level'] not in self.valid_cognitive_levels:
                self.logger.log_error('activity_manager', 
                                    f'Invalid cognitive level in {file_path}: {activity_data["cognitive_level"]}',
                                    'schema_validation_error', {'file_path': file_path})
                return False
            
            if activity_data['depth_level'] not in self.valid_depth_levels:
                self.logger.log_error('activity_manager', 
                                    f'Invalid depth level in {file_path}: {activity_data["depth_level"]}',
                                    'schema_validation_error', {'file_path': file_path})
                return False
            
            # Validate target evidence volume
            try:
                evidence_vol = float(activity_data['target_evidence_volume'])
                if evidence_vol <= 0:
                    self.logger.log_error('activity_manager', 
                                        f'Invalid target evidence volume in {file_path}: {evidence_vol}',
                                        'schema_validation_error', {'file_path': file_path})
                    return False
            except (ValueError, TypeError):
                self.logger.log_error('activity_manager', 
                                    f'Invalid target evidence volume format in {file_path}',
                                    'schema_validation_error', {'file_path': file_path})
                return False
            
            # Validate rubric requirements
            if activity_type in self.required_fields['rubric_required']:
                if not activity_data.get('rubric') or not isinstance(activity_data['rubric'], dict):
                    self.logger.log_error('activity_manager', 
                                        f'Missing or invalid rubric for {activity_type} in {file_path}',
                                        'schema_validation_error', {'file_path': file_path})
                    return False
                
                # Check rubric has required structure
                rubric = activity_data['rubric']
                if not rubric.get('aspects') or not isinstance(rubric['aspects'], list):
                    self.logger.log_error('activity_manager', 
                                        f'Rubric missing aspects array in {file_path}',
                                        'schema_validation_error', {'file_path': file_path})
                    return False
            
            # Validate content structure
            content = activity_data['content']
            if not isinstance(content, dict):
                self.logger.log_error('activity_manager', 
                                    f'Invalid content structure in {file_path}',
                                    'schema_validation_error', {'file_path': file_path})
                return False
            
            # Type-specific validation
            if not self._validate_type_specific_content(activity_type, content, file_path):
                return False
            
            return True
            
        except Exception as e:
            self.logger.log_error('activity_manager', f'Schema validation error in {file_path}: {str(e)}', 
                                str(e), {'file_path': file_path})
            return False

    def _validate_type_specific_content(self, activity_type: str, content: Dict[str, Any], 
                                      file_path: str) -> bool:
        """Validate activity type-specific content requirements"""
        
        if activity_type == 'CR':  # Constructed Response
            required = {'prompt', 'response_guidelines'}
            
        elif activity_type == 'COD':  # Coding Exercise
            required = {'problem_statement', 'starter_code', 'test_cases'}
            
        elif activity_type == 'RP':  # Role Play
            required = {'scenario_context', 'character_profile', 'objectives'}
            
        elif activity_type == 'SR':  # Single Response
            required = {'question', 'options', 'correct_answer'}
            
        elif activity_type == 'BR':  # Branching Response
            required = {'initial_scenario', 'decision_points', 'paths'}
            
        else:
            return True  # Unknown type, skip specific validation
        
        missing = required - set(content.keys())
        if missing:
            self.logger.log_error('activity_manager', 
                                f'Missing {activity_type}-specific content in {file_path}: {missing}',
                                'type_validation_error', 
                                {'file_path': file_path, 'missing': list(missing)})
            return False
        
        return True

    def get_activity(self, activity_id: str) -> Optional[ActivitySpec]:
        """
        Get a specific activity by ID.
        
        Args:
            activity_id: Activity identifier
            
        Returns:
            ActivitySpec instance or None if not found
        """
        # Check cache first
        if activity_id in self._activity_cache:
            cache_time = self._cache_timestamps.get(activity_id, 0)
            if (datetime.now().timestamp() - cache_time) < self._cache_ttl:
                return self._activity_cache[activity_id]
        
        # Load all activities if not already loaded
        all_activities = self.load_activities()
        if activity_id in all_activities:
            return all_activities[activity_id]
        
        self.logger.log_error('activity_manager', f'Activity not found: {activity_id}', 
                            'not_found', {'activity_id': activity_id})
        return None

    def get_activities_by_type(self, activity_type: str) -> List[ActivitySpec]:
        """
        Get all activities of a specific type.
        
        Args:
            activity_type: Activity type (CR, COD, RP, SR, BR)
            
        Returns:
            List of matching ActivitySpec instances
        """
        if activity_type not in self.valid_activity_types:
            return []
        
        all_activities = self.load_activities()
        return [activity for activity in all_activities.values() 
                if activity.activity_type == activity_type]

    def get_activities_by_skill(self, skill_id: str) -> List[ActivitySpec]:
        """
        Get all activities targeting a specific skill.
        
        Args:
            skill_id: Target skill identifier
            
        Returns:
            List of matching ActivitySpec instances
        """
        all_activities = self.load_activities()
        return [activity for activity in all_activities.values() 
                if activity.target_skill == skill_id]

    def create_interactive_session(self, activity_id: str, learner_id: str) -> Optional[str]:
        """
        Create new interactive session for RP or BR activities.
        
        Args:
            activity_id: Activity identifier
            learner_id: Learner identifier
            
        Returns:
            Session ID if created successfully, None otherwise
        """
        activity = self.get_activity(activity_id)
        if not activity:
            return None
        
        if activity.activity_type not in {'RP', 'BR'}:
            self.logger.log_error('activity_manager', 
                                f'Cannot create interactive session for non-interactive activity type: {activity.activity_type}',
                                'invalid_type', {'activity_id': activity_id, 'type': activity.activity_type})
            return None
        
        # Generate session ID
        timestamp = datetime.now(timezone.utc).isoformat()
        session_data = f"{activity_id}_{learner_id}_{timestamp}"
        session_id = hashlib.md5(session_data.encode()).hexdigest()[:12]
        
        # Initialize session state based on activity type
        if activity.activity_type == 'RP':
            initial_state = {
                'current_turn': 0,
                'character_context': activity.content.get('character_profile', {}),
                'objectives_status': {obj: 'not_started' for obj in activity.content.get('objectives', [])},
                'conversation_phase': 'introduction'
            }
        else:  # BR
            initial_state = {
                'current_node': 'start',
                'path_taken': [],
                'decisions_made': [],
                'scenario_state': activity.content.get('initial_scenario', {})
            }
        
        session = InteractiveSession(
            session_id=session_id,
            activity_id=activity_id,
            learner_id=learner_id,
            session_type='role_play' if activity.activity_type == 'RP' else 'branching',
            current_state=initial_state,
            interaction_history=[],
            start_time=timestamp,
            last_activity=timestamp
        )
        
        self._active_sessions[session_id] = session
        
        self.logger.log_system_event('activity_manager', 'interactive_session_created', 
                                   f'Session {session_id} created for activity {activity_id}',
                                   {'session_id': session_id, 'activity_id': activity_id, 'learner_id': learner_id})
        
        return session_id

    def get_interactive_session(self, session_id: str) -> Optional[InteractiveSession]:
        """
        Get interactive session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            InteractiveSession instance or None if not found
        """
        return self._active_sessions.get(session_id)

    def update_interactive_session(self, session_id: str, new_interaction: Dict[str, Any], 
                                 new_state: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update interactive session with new interaction.
        
        Args:
            session_id: Session identifier
            new_interaction: New interaction data
            new_state: Updated session state (optional)
            
        Returns:
            bool: True if updated successfully
        """
        if session_id not in self._active_sessions:
            return False
        
        try:
            session = self._active_sessions[session_id]
            
            # Add timestamp to interaction
            new_interaction['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Update session
            session.interaction_history.append(new_interaction)
            session.last_activity = new_interaction['timestamp']
            
            if new_state:
                session.current_state.update(new_state)
            
            self.logger.log_system_event('activity_manager', 'interactive_session_updated', 
                                       f'Session {session_id} updated',
                                       {'session_id': session_id, 'interaction_count': len(session.interaction_history)})
            
            return True
            
        except Exception as e:
            self.logger.log_error('activity_manager', f'Failed to update session {session_id}: {str(e)}', 
                                str(e), {'session_id': session_id})
            return False

    def complete_interactive_session(self, session_id: str) -> bool:
        """
        Mark interactive session as complete.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if completed successfully
        """
        if session_id not in self._active_sessions:
            return False
        
        session = self._active_sessions[session_id]
        session.is_complete = True
        session.completion_time = datetime.now(timezone.utc).isoformat()
        
        self.logger.log_system_event('activity_manager', 'interactive_session_completed', 
                                   f'Session {session_id} completed',
                                   {'session_id': session_id, 'duration_interactions': len(session.interaction_history)})
        
        return True

    def get_activity_stats(self) -> Dict[str, Any]:
        """
        Get activity manager statistics.
        
        Returns:
            Dictionary with activity statistics
        """
        try:
            all_activities = self.load_activities()
            
            type_counts = {}
            for activity_type in self.valid_activity_types:
                type_counts[activity_type] = sum(1 for a in all_activities.values() 
                                               if a.activity_type == activity_type)
            
            return {
                'total_activities': len(all_activities),
                'activities_by_type': type_counts,
                'cached_activities': len(self._activity_cache),
                'active_sessions': len(self._active_sessions),
                'activities_path': self.activities_path,
                'valid_types': list(self.valid_activity_types)
            }
            
        except Exception as e:
            self.logger.log_error('activity_manager', f'Failed to get activity stats: {str(e)}', str(e))
            return {}

    def validate_all_activities(self) -> Dict[str, Any]:
        """
        Validate all activity files and return detailed results.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'valid_activities': [],
            'invalid_activities': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            if not os.path.exists(self.activities_path):
                validation_results['errors'].append(f"Activities directory not found: {self.activities_path}")
                return validation_results
            
            json_files = list(Path(self.activities_path).glob('*.json'))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        activity_data = json.load(f)
                    
                    if self._validate_activity_schema(activity_data, str(json_file)):
                        validation_results['valid_activities'].append({
                            'file': json_file.name,
                            'activity_id': activity_data.get('activity_id'),
                            'type': activity_data.get('activity_type')
                        })
                    else:
                        validation_results['invalid_activities'].append({
                            'file': json_file.name,
                            'reason': 'Schema validation failed'
                        })
                
                except json.JSONDecodeError as e:
                    validation_results['invalid_activities'].append({
                        'file': json_file.name,
                        'reason': f'JSON parsing error: {str(e)}'
                    })
                except Exception as e:
                    validation_results['errors'].append(f"Error processing {json_file.name}: {str(e)}")
            
            # Add summary
            validation_results['summary'] = {
                'total_files': len(json_files),
                'valid_count': len(validation_results['valid_activities']),
                'invalid_count': len(validation_results['invalid_activities']),
                'error_count': len(validation_results['errors'])
            }
            
        except Exception as e:
            validation_results['errors'].append(f"Validation process failed: {str(e)}")
        
        return validation_results

    def validate_activity(self, activity: dict) -> bool:
        """
        Validate a single in-memory activity dictionary (for UI row validation).
        """
        return self._validate_activity_schema(activity, "in-memory")
