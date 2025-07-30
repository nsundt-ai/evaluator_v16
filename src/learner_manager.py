"""
Evaluator v16 - Learner Manager Module

Handles SQLite database operations for learner profiles, activity histories,
and progress tracking. Integrates with scoring engine for persistent storage.

Author: Generated for Evaluator v16 Project
Version: 1.0.0
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from contextlib import contextmanager

from src.config_manager import ConfigManager
from src.logger import get_logger


@dataclass
class LearnerProfile:
    """Learner profile data structure"""
    learner_id: str
    name: str
    email: str
    enrollment_date: str
    status: str = "active"
    background: str = ""
    experience_level: str = "beginner"
    created: Optional[str] = None
    last_updated: Optional[str] = None

    def __post_init__(self):
        if self.created is None:
            self.created = datetime.now(timezone.utc).isoformat()
        if self.last_updated is None:
            self.last_updated = self.created


@dataclass
class ActivityRecord:
    """Single activity evaluation record"""
    activity_id: str
    learner_id: str
    timestamp: str
    evaluation_result: Dict[str, Any]
    activity_transcript: Dict[str, Any]
    scored: bool = False
    record_id: Optional[int] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class SkillProgress:
    """Skill progress tracking data"""
    skill_id: str
    learner_id: str
    skill_name: str
    cumulative_score: float
    total_adjusted_evidence: float
    activity_count: int
    gate_1_status: str
    gate_2_status: str
    overall_status: str
    last_updated: str
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    standard_error: Optional[float] = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc).isoformat()


class LearnerManager:
    """
    Manages learner data persistence using SQLite database.
    Handles learner profiles, activity histories, and skill progress tracking.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize LearnerManager with database setup.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = get_logger()
        
        # Get database path from environment or config
        self.db_path = os.getenv('DATABASE_PATH', 'data/evaluator_v16.db')
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._initialize_database()
        
        # Cache for frequently accessed data
        self._profile_cache = {}
        self._cache_ttl = 300  # 5 minutes

    def _initialize_database(self) -> None:
        """Create database tables if they don't exist"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Learner profiles table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS learner_profiles (
                        learner_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        enrollment_date TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        background TEXT DEFAULT '',
                        experience_level TEXT DEFAULT 'beginner',
                        created TEXT NOT NULL,
                        last_updated TEXT NOT NULL
                    )
                ''')
                
                # Activity records table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activity_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        activity_id TEXT NOT NULL,
                        learner_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        evaluation_result TEXT NOT NULL,
                        activity_transcript TEXT NOT NULL,
                        scored INTEGER DEFAULT 0,
                        FOREIGN KEY (learner_id) REFERENCES learner_profiles (learner_id)
                    )
                ''')
                
                # Skill progress table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS skill_progress (
                        skill_id TEXT,
                        learner_id TEXT,
                        skill_name TEXT NOT NULL,
                        cumulative_score REAL NOT NULL,
                        total_adjusted_evidence REAL NOT NULL,
                        activity_count INTEGER NOT NULL,
                        gate_1_status TEXT NOT NULL,
                        gate_2_status TEXT NOT NULL,
                        overall_status TEXT NOT NULL,
                        confidence_interval_lower REAL,
                        confidence_interval_upper REAL,
                        standard_error REAL,
                        last_updated TEXT NOT NULL,
                        PRIMARY KEY (skill_id, learner_id),
                        FOREIGN KEY (learner_id) REFERENCES learner_profiles (learner_id)
                    )
                ''')
                
                # Activity history table - NEW
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activity_history (
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
                        cumulative_evidence_weight REAL NOT NULL,
                        decay_factor REAL NOT NULL,
                        decay_adjusted_evidence_volume REAL NOT NULL,
                        cumulative_performance REAL NOT NULL,
                        cumulative_evidence REAL NOT NULL,
                        evaluation_result TEXT,
                        activity_transcript TEXT,
                        FOREIGN KEY (learner_id) REFERENCES learner_profiles (learner_id),
                        UNIQUE(learner_id, activity_id, skill_id)
                    )
                ''')
                
                # Add the new column to existing tables if it doesn't exist
                try:
                    cursor.execute('''
                        ALTER TABLE activity_history 
                        ADD COLUMN decay_adjusted_evidence_volume REAL DEFAULT 0.0
                    ''')
                except sqlite3.OperationalError:
                    # Column already exists, ignore the error
                    pass
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_learner ON activity_records (learner_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_records (timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_skill_learner ON skill_progress (learner_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_history_learner_skill ON activity_history (learner_id, skill_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_history_timestamp ON activity_history (completion_timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_history_evidence_weight ON activity_history (learner_id, skill_id, cumulative_evidence_weight)')
                
                conn.commit()
                
            self.logger.log_system_event('learner_manager', 'database_initialized', 
                                        f'Database initialized at {self.db_path}')
                                        
        except Exception as e:
            self.logger.log_error('learner_manager', f'Database initialization failed: {str(e)}', 
                                str(e), {'db_path': self.db_path})
            raise

    @contextmanager
    def _get_db_connection(self):
        """Context manager for database connections with proper cleanup"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_learner(self, profile: LearnerProfile) -> bool:
        """
        Create a new learner profile.
        
        Args:
            profile: LearnerProfile instance
            
        Returns:
            bool: True if created successfully, False otherwise
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO learner_profiles 
                    (learner_id, name, email, enrollment_date, status, background, 
                     experience_level, created, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    profile.learner_id, profile.name, profile.email, 
                    profile.enrollment_date, profile.status, profile.background,
                    profile.experience_level, profile.created, profile.last_updated
                ))
                
                conn.commit()
                
            # Clear cache
            self._profile_cache.pop(profile.learner_id, None)
            
            self.logger.log_system_event('learner_manager', 'learner_created', 
                                       f'Learner {profile.learner_id} created successfully')
            return True
            
        except sqlite3.IntegrityError as e:
            self.logger.log_error('learner_manager', f'Learner creation failed - integrity error: {str(e)}',
                                str(e), {'learner_id': profile.learner_id})
            return False
        except Exception as e:
            self.logger.log_error('learner_manager', f'Learner creation failed: {str(e)}',
                                str(e), {'learner_id': profile.learner_id})
            return False

    def get_learner(self, learner_id: str) -> Optional[LearnerProfile]:
        """
        Retrieve learner profile by ID.
        
        Args:
            learner_id: Unique learner identifier
            
        Returns:
            LearnerProfile instance or None if not found
        """
        # Check cache first
        if learner_id in self._profile_cache:
            cache_time, profile = self._profile_cache[learner_id]
            if (datetime.now().timestamp() - cache_time) < self._cache_ttl:
                return profile
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM learner_profiles WHERE learner_id = ?', 
                             (learner_id,))
                row = cursor.fetchone()
                
                if row:
                    profile = LearnerProfile(**dict(row))
                    # Cache the result
                    self._profile_cache[learner_id] = (datetime.now().timestamp(), profile)
                    return profile
                    
            return None
            
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to retrieve learner: {str(e)}',
                                str(e), {'learner_id': learner_id})
            return None

    def update_learner(self, profile: LearnerProfile) -> bool:
        """
        Update existing learner profile.
        
        Args:
            profile: Updated LearnerProfile instance
            
        Returns:
            bool: True if updated successfully
        """
        try:
            profile.last_updated = datetime.now(timezone.utc).isoformat()
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE learner_profiles 
                    SET name=?, email=?, enrollment_date=?, status=?, background=?, 
                        experience_level=?, last_updated=?
                    WHERE learner_id=?
                ''', (
                    profile.name, profile.email, profile.enrollment_date,
                    profile.status, profile.background, profile.experience_level,
                    profile.last_updated, profile.learner_id
                ))
                
                conn.commit()
                
            # Clear cache
            self._profile_cache.pop(profile.learner_id, None)
            
            self.logger.log_system_event('learner_manager', 'learner_updated', 
                                       f'Learner {profile.learner_id} updated successfully')
            return cursor.rowcount > 0
            
        except Exception as e:
            self.logger.log_error('learner_manager', f'Learner update failed: {str(e)}',
                                str(e), {'learner_id': profile.learner_id})
            return False

    def list_learners(self, status: Optional[str] = None, limit: Optional[int] = None) -> List[LearnerProfile]:
        """
        List learners with optional filtering.
        
        Args:
            status: Filter by status ('active', 'inactive', etc.)
            limit: Maximum number of results
            
        Returns:
            List of LearnerProfile instances
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM learner_profiles'
                params = []
                
                if status:
                    query += ' WHERE status = ?'
                    params.append(status)
                
                query += ' ORDER BY last_updated DESC'
                
                if limit:
                    query += ' LIMIT ?'
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [LearnerProfile(**dict(row)) for row in rows]
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to list learners: {str(e)}',
                                str(e), {'status': status, 'limit': limit})
            return []

    def add_activity_record(self, record: ActivityRecord) -> bool:
        """
        Add new activity evaluation record.
        
        Args:
            record: ActivityRecord instance
            
        Returns:
            bool: True if added successfully
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO activity_records 
                    (activity_id, learner_id, timestamp, evaluation_result, 
                     activity_transcript, scored)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    record.activity_id, record.learner_id, record.timestamp,
                    json.dumps(record.evaluation_result, ensure_ascii=False),
                    json.dumps(record.activity_transcript, ensure_ascii=False),
                    1 if record.scored else 0
                ))
                
                record.record_id = cursor.lastrowid
                conn.commit()
                
            self.logger.log_system_event('learner_manager', 'activity_record_added',
                                       f'Activity record added for learner {record.learner_id}',
                                       {'activity_id': record.activity_id})
            
            # Auto-sync to JSON file
            try:
                json_path = f'data/learners/{record.learner_id}_history.json'
                self.sync_learner_history_to_json(record.learner_id, json_path)
            except Exception as e:
                self.logger.log_error('learner_manager', f'Failed to auto-sync JSON after activity record: {str(e)}',
                                    str(e), {'learner_id': record.learner_id, 'activity_id': record.activity_id})
            
            return True
            
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to add activity record: {str(e)}',
                                str(e), {'learner_id': record.learner_id, 
                                        'activity_id': record.activity_id})
            return False

    def get_learner_activities(self, learner_id: str, limit: Optional[int] = None) -> List[ActivityRecord]:
        """
        Get activity records for a learner, ordered by most recent first.
        
        Args:
            learner_id: Learner identifier
            limit: Maximum number of records to return
            
        Returns:
            List of ActivityRecord instances
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, activity_id, learner_id, timestamp, evaluation_result, 
                           activity_transcript, scored
                    FROM activity_records 
                    WHERE learner_id = ? 
                    ORDER BY timestamp DESC
                '''
                params = [learner_id]
                
                if limit:
                    query += ' LIMIT ?'
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = ActivityRecord(
                        activity_id=row['activity_id'],
                        learner_id=row['learner_id'],
                        timestamp=row['timestamp'],
                        evaluation_result=json.loads(row['evaluation_result']),
                        activity_transcript=json.loads(row['activity_transcript']),
                        scored=bool(row['scored']),
                        record_id=row['id']
                    )
                    records.append(record)
                
                return records
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get learner activities: {str(e)}',
                                str(e), {'learner_id': learner_id})
            return []

    def update_skill_progress(self, progress: SkillProgress) -> bool:
        """
        Update or insert skill progress record.
        
        Args:
            progress: SkillProgress instance
            
        Returns:
            bool: True if updated successfully
        """
        try:
            progress.last_updated = datetime.now(timezone.utc).isoformat()
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO skill_progress 
                    (skill_id, learner_id, skill_name, cumulative_score, 
                     total_adjusted_evidence, activity_count, gate_1_status, 
                     gate_2_status, overall_status, confidence_interval_lower,
                     confidence_interval_upper, standard_error, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    progress.skill_id, progress.learner_id, progress.skill_name,
                    progress.cumulative_score, progress.total_adjusted_evidence,
                    progress.activity_count, progress.gate_1_status,
                    progress.gate_2_status, progress.overall_status,
                    progress.confidence_interval_lower, progress.confidence_interval_upper,
                    progress.standard_error, progress.last_updated
                ))
                
                conn.commit()
                
            self.logger.log_system_event('learner_manager', 'skill_progress_updated',
                                       f'Skill progress updated for {progress.learner_id}',
                                       {'skill_id': progress.skill_id})
            
            # Auto-sync to JSON file
            try:
                json_path = f'data/learners/{progress.learner_id}_history.json'
                self.sync_learner_history_to_json(progress.learner_id, json_path)
            except Exception as e:
                self.logger.log_error('learner_manager', f'Failed to auto-sync JSON after skill progress update: {str(e)}',
                                    str(e), {'learner_id': progress.learner_id, 'skill_id': progress.skill_id})
            
            return True
            
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to update skill progress: {str(e)}',
                                str(e), {'learner_id': progress.learner_id, 
                                        'skill_id': progress.skill_id})
            return False

    def get_skill_progress(self, learner_id: str) -> Dict[str, SkillProgress]:
        """
        Get all skill progress records for a learner.
        
        Args:
            learner_id: Learner identifier
            
        Returns:
            Dictionary mapping skill_id to SkillProgress
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM skill_progress 
                    WHERE learner_id = ? 
                    ORDER BY last_updated DESC
                ''', (learner_id,))
                rows = cursor.fetchall()
                
                progress_dict = {}
                for row in rows:
                    progress = SkillProgress(**dict(row))
                    progress_dict[progress.skill_id] = progress
                
                return progress_dict
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get skill progress: {str(e)}',
                                str(e), {'learner_id': learner_id})
            return {}

    def get_skill_progress_summary(self, learner_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for learner's skill progress.
        
        Args:
            learner_id: Learner identifier
            
        Returns:
            Dictionary with summary statistics
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get overall statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_skills,
                        AVG(cumulative_score) as avg_score,
                        SUM(CASE WHEN overall_status = 'mastered' THEN 1 ELSE 0 END) as mastered_count,
                        SUM(activity_count) as total_activities,
                        SUM(total_adjusted_evidence) as total_evidence
                    FROM skill_progress 
                    WHERE learner_id = ?
                ''', (learner_id,))
                
                row = cursor.fetchone()
                
                if row and row['total_skills'] > 0:
                    return {
                        'total_skills_evaluated': row['total_skills'],
                        'average_skill_score': round(row['avg_score'], 3),
                        'mastered_skills_count': row['mastered_count'],
                        'total_activities_completed': row['total_activities'],
                        'total_evidence_accumulated': round(row['total_evidence'], 2),
                        'mastery_percentage': round((row['mastered_count'] / row['total_skills']) * 100, 1)
                    }
                else:
                    return {
                        'total_skills_evaluated': 0,
                        'average_skill_score': 0.0,
                        'mastered_skills_count': 0,
                        'total_activities_completed': 0,
                        'total_evidence_accumulated': 0.0,
                        'mastery_percentage': 0.0
                    }
                    
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get progress summary: {str(e)}',
                                str(e), {'learner_id': learner_id})
            return {}

    def search_learners(self, query: str, limit: int = 20) -> List[LearnerProfile]:
        """
        Search learners by name or email.
        
        Args:
            query: Search query string
            limit: Maximum results to return
            
        Returns:
            List of matching LearnerProfile instances
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                search_pattern = f'%{query.lower()}%'
                cursor.execute('''
                    SELECT * FROM learner_profiles 
                    WHERE LOWER(name) LIKE ? OR LOWER(email) LIKE ?
                    ORDER BY name
                    LIMIT ?
                ''', (search_pattern, search_pattern, limit))
                
                rows = cursor.fetchall()
                return [LearnerProfile(**dict(row)) for row in rows]
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Search failed: {str(e)}',
                                str(e), {'query': query})
            return []

    def backup_learner_data(self, learner_id: str, backup_path: str) -> bool:
        """
        Create complete backup of learner's data to JSON file.
        
        Args:
            learner_id: Learner to backup
            backup_path: Path for backup file
            
        Returns:
            bool: True if backup successful
        """
        try:
            # Get all learner data
            profile = self.get_learner(learner_id)
            activities = self.get_learner_activities(learner_id)
            skill_progress = self.get_learner_skill_progress(learner_id)
            
            if not profile:
                return False
            
            backup_data = {
                'profile': asdict(profile),
                'activities': [asdict(activity) for activity in activities],
                'skill_progress': {k: asdict(v) for k, v in skill_progress.items()},
                'backup_timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '1.0'
            }
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Write backup file
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.log_system_event('learner_manager', 'backup_created',
                                       f'Backup created for learner {learner_id}',
                                       {'backup_path': backup_path})
            return True
            
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to create backup: {str(e)}',
                                str(e), {'learner_id': learner_id, 'backup_path': backup_path})
            return False

    def sync_learner_history_to_json(self, learner_id: str, json_path: str = None) -> bool:
        """
        Sync learner data from database to JSON file format.
        
        Args:
            learner_id: Learner identifier
            json_path: Path for JSON file (defaults to data/learners/{learner_id}_history.json)
            
        Returns:
            bool: True if sync successful
        """
        try:
            # Get learner profile
            profile = self.get_learner(learner_id)
            if not profile:
                self.logger.log_error('learner_manager', f'Learner not found: {learner_id}',
                                    'not_found', {'learner_id': learner_id})
                return False
            
            # Get all activities from database
            activities = self.get_learner_activities(learner_id)
            
            # Get skill progress from database
            skill_progress = self.get_skill_progress(learner_id)
            
            # Build activity list for JSON format
            activity_list = []
            for activity in activities:
                activity_list.append(activity.activity_id)
            
            # Build skill progress for JSON format
            skill_progress_json = {}
            for skill_id, progress in skill_progress.items():
                skill_progress_json[skill_id] = {
                    'skill_name': progress.skill_name,
                    'cumulative_score': progress.cumulative_score,
                    'total_adjusted_evidence': progress.total_adjusted_evidence,
                    'activity_count': progress.activity_count,
                    'gate_1_status': progress.gate_1_status,
                    'gate_2_status': progress.gate_2_status,
                    'overall_status': progress.overall_status,
                    'last_activity_date': progress.last_updated,
                    'activities': []  # Will be populated from activity records
                }
            
            # Build complete learner history JSON
            learner_history = {
                'learner_id': learner_id,
                'created': profile.created,
                'last_updated': profile.last_updated,
                'profile': {
                    'name': profile.name,
                    'email': profile.email,
                    'enrollment_date': profile.enrollment_date,
                    'status': profile.status,
                    'background': profile.background,
                    'experience_level': profile.experience_level
                },
                'activities': activity_list,
                'skill_progress': skill_progress_json,
                'competency_progress': {},  # Will be populated if needed
                'metadata': {
                    'total_activities': len(activity_list),
                    'total_time_minutes': 0,  # Could be calculated from activity records
                    'last_activity_date': profile.last_updated
                }
            }
            
            # Determine JSON file path
            if json_path is None:
                json_path = f'data/learners/{learner_id}_history.json'
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # Write JSON file
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(learner_history, f, indent=2, ensure_ascii=False)
            
            self.logger.log_system_event('learner_manager', 'learner_history_synced',
                                       f'Learner history synced to JSON for {learner_id}',
                                       {'json_path': json_path})
            return True
            
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to sync learner history: {str(e)}',
                                str(e), {'learner_id': learner_id, 'json_path': json_path})
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics for monitoring and analytics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get counts from each table
                cursor.execute('SELECT COUNT(*) FROM learner_profiles')
                learner_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM activity_records')
                activity_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM skill_progress')
                skill_progress_count = cursor.fetchone()[0]
                
                # Get database file size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'total_learners': learner_count,
                    'total_activity_records': activity_count,
                    'total_skill_progress_records': skill_progress_count,
                    'database_size_bytes': db_size,
                    'database_path': self.db_path,
                    'cache_entries': len(self._profile_cache)
                }
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get database stats: {str(e)}', str(e))
            return {}

    def add_activity_history_record(self, learner_id: str, activity_id: str, skill_id: str,
                                   completion_timestamp: str, activity_type: str, activity_title: str,
                                   performance_score: float, target_evidence_volume: float,
                                   validity_modifier: float, adjusted_evidence_volume: float,
                                   cumulative_evidence_weight: float, decay_factor: float,
                                   decay_adjusted_evidence_volume: float,
                                   cumulative_performance: float, cumulative_evidence: float,
                                   evaluation_result: Dict, activity_transcript: Dict) -> bool:
        """
        Add new row to activity history table with decay-adjusted evidence.
        
        Args:
            All the parameters for the activity history record
            
        Returns:
            bool: True if added successfully
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO activity_history 
                    (learner_id, activity_id, skill_id, completion_timestamp, activity_type,
                     activity_title, performance_score, target_evidence_volume, validity_modifier,
                     adjusted_evidence_volume, cumulative_evidence_weight, decay_factor,
                     decay_adjusted_evidence_volume, cumulative_performance, cumulative_evidence, 
                     evaluation_result, activity_transcript)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    learner_id, activity_id, skill_id, completion_timestamp, activity_type,
                    activity_title, performance_score, target_evidence_volume, validity_modifier,
                    adjusted_evidence_volume, cumulative_evidence_weight, decay_factor,
                    decay_adjusted_evidence_volume, cumulative_performance, cumulative_evidence,
                    json.dumps(evaluation_result, ensure_ascii=False),
                    json.dumps(activity_transcript, ensure_ascii=False)
                ))
                
                conn.commit()
                
            self.logger.log_system_event('learner_manager', 'activity_history_record_added',
                                       f'Activity history record added for learner {learner_id}',
                                       {'activity_id': activity_id, 'skill_id': skill_id})
            return True
            
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to add activity history record: {str(e)}',
                                str(e), {'learner_id': learner_id, 'activity_id': activity_id, 'skill_id': skill_id})
            return False

    def reset_learner_history(self, learner_id: str) -> bool:
        """
        Reset all learner history data including activity history, skill progress, and activity records.
        
        Args:
            learner_id: Learner identifier
            
        Returns:
            bool: True if reset successfully
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Temporarily disable foreign key constraints
                cursor.execute('PRAGMA foreign_keys = OFF')
                
                # Delete all activity history records
                cursor.execute('DELETE FROM activity_history WHERE learner_id = ?', (learner_id,))
                activity_history_deleted = cursor.rowcount
                
                # Delete all skill progress records
                cursor.execute('DELETE FROM skill_progress WHERE learner_id = ?', (learner_id,))
                skill_progress_deleted = cursor.rowcount
                
                # Delete all activity records
                cursor.execute('DELETE FROM activity_records WHERE learner_id = ?', (learner_id,))
                activity_records_deleted = cursor.rowcount
                
                # Re-enable foreign key constraints
                cursor.execute('PRAGMA foreign_keys = ON')
                
                conn.commit()
                
            self.logger.log_system_event('learner_manager', 'learner_history_reset',
                                       f'Learner history reset for {learner_id}',
                                       {
                                           'activity_history_deleted': activity_history_deleted,
                                           'skill_progress_deleted': skill_progress_deleted,
                                           'activity_records_deleted': activity_records_deleted
                                       })
            return True
            
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to reset learner history: {str(e)}',
                                str(e), {'learner_id': learner_id})
            return False

    def get_activity_history_for_learner_skill(self, learner_id: str, skill_id: str) -> List[Dict]:
        """
        Get complete activity history for a learner/skill combination.
        
        Args:
            learner_id: Learner identifier
            skill_id: Skill identifier
            
        Returns:
            List of activity history records ordered by most recent first
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        activity_id,
                        activity_title,
                        completion_timestamp,
                        performance_score,
                        target_evidence_volume,
                        validity_modifier,
                        adjusted_evidence_volume,
                        cumulative_evidence_weight,
                        decay_factor,
                        decay_adjusted_evidence_volume,
                        cumulative_performance,
                        cumulative_evidence
                    FROM activity_history 
                    WHERE learner_id = ? AND skill_id = ?
                    ORDER BY completion_timestamp DESC
                ''', (learner_id, skill_id))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get activity history: {str(e)}',
                                str(e), {'learner_id': learner_id, 'skill_id': skill_id})
            return []

    def get_activity_history_chronological(self, learner_id: str, skill_id: str) -> List[Dict]:
        """
        Get complete activity history for a learner/skill combination in chronological order.
        
        Args:
            learner_id: Learner identifier
            skill_id: Skill identifier
            
        Returns:
            List of activity history records ordered by oldest first (chronological)
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        activity_id,
                        activity_title,
                        completion_timestamp,
                        performance_score,
                        target_evidence_volume,
                        validity_modifier,
                        adjusted_evidence_volume,
                        cumulative_evidence_weight,
                        decay_factor,
                        decay_adjusted_evidence_volume,
                        cumulative_performance,
                        cumulative_evidence
                    FROM activity_history 
                    WHERE learner_id = ? AND skill_id = ?
                    ORDER BY completion_timestamp ASC
                ''', (learner_id, skill_id))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get chronological activity history: {str(e)}',
                                str(e), {'learner_id': learner_id, 'skill_id': skill_id})
            return []

    def get_activity_position(self, learner_id: str, skill_id: str) -> int:
        """
        Get the position for the next activity (0-based).
        
        Args:
            learner_id: Learner identifier
            skill_id: Skill identifier
            
        Returns:
            int: Number of existing activities for this skill
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM activity_history 
                    WHERE learner_id = ? AND skill_id = ?
                ''', (learner_id, skill_id))
                result = cursor.fetchone()
                return result['count'] if result else 0
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get activity position: {str(e)}',
                                str(e), {'learner_id': learner_id, 'skill_id': skill_id})
            return 0

    def get_total_activity_count(self, learner_id: str) -> int:
        """
        Get total number of activity history records for a learner.
        
        Args:
            learner_id: Learner identifier
            
        Returns:
            int: Total number of activity history records
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM activity_history 
                    WHERE learner_id = ?
                ''', (learner_id,))
                result = cursor.fetchone()
                return result['count'] if result else 0
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get total activity count: {str(e)}',
                                str(e), {'learner_id': learner_id})
            return 0

    def get_learner_data_summary(self, learner_id: str) -> Dict[str, int]:
        """
        Get summary of all learner data counts.
        
        Args:
            learner_id: Learner identifier
            
        Returns:
            Dict with counts of different data types
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get activity history count
                cursor.execute('SELECT COUNT(*) as count FROM activity_history WHERE learner_id = ?', (learner_id,))
                activity_history_count = cursor.fetchone()['count']
                
                # Get skill progress count
                cursor.execute('SELECT COUNT(*) as count FROM skill_progress WHERE learner_id = ?', (learner_id,))
                skill_progress_count = cursor.fetchone()['count']
                
                # Get activity records count
                cursor.execute('SELECT COUNT(*) as count FROM activity_records WHERE learner_id = ?', (learner_id,))
                activity_records_count = cursor.fetchone()['count']
                
                return {
                    'activity_history': activity_history_count,
                    'skill_progress': skill_progress_count,
                    'activity_records': activity_records_count,
                    'total': activity_history_count + skill_progress_count + activity_records_count
                }
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to get learner data summary: {str(e)}',
                                str(e), {'learner_id': learner_id})
            return {'activity_history': 0, 'skill_progress': 0, 'activity_records': 0, 'total': 0}

    def update_activity_decay_adjusted_evidence(self, learner_id: str, activity_id: str, skill_id: str, 
                                              new_decay_adjusted_evidence: float, evidence_based_decay: float) -> bool:
        """
        Update the decay-adjusted evidence for a specific activity.
        
        Args:
            learner_id: Learner identifier
            activity_id: Activity identifier
            skill_id: Skill identifier
            new_decay_adjusted_evidence: New decay-adjusted evidence value
            evidence_based_decay: The evidence-based decay factor applied
            
        Returns:
            bool: True if updated successfully
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE activity_history 
                    SET decay_adjusted_evidence_volume = ?, cumulative_evidence_weight = ?
                    WHERE learner_id = ? AND activity_id = ? AND skill_id = ?
                ''', (new_decay_adjusted_evidence, new_decay_adjusted_evidence, learner_id, activity_id, skill_id))
                
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.log_error('learner_manager', f'Failed to update activity decay-adjusted evidence: {str(e)}',
                                str(e), {
                                    'learner_id': learner_id, 
                                    'activity_id': activity_id, 
                                    'skill_id': skill_id,
                                    'new_decay_adjusted_evidence': new_decay_adjusted_evidence
                                })
            return False