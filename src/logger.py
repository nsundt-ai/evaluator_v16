"""
Logging System for Evaluator v16
Provides structured logging for evaluation pipeline, errors, and system events.
"""

import os
import json
import logging
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import time

@dataclass
class EvaluationLogEntry:
    """Structured log entry for evaluation events"""
    timestamp: str
    event_type: str  # evaluation_start, evaluation_complete, phase_start, phase_complete, error
    learner_id: str
    activity_id: str
    phase_name: Optional[str] = None
    provider: Optional[str] = None
    success: bool = True
    duration_seconds: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SystemLogEntry:
    """Structured log entry for system events"""
    timestamp: str
    level: str  # INFO, WARNING, ERROR, DEBUG
    component: str  # config_manager, llm_client, scoring_engine, etc.
    event_type: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class EvaluatorLogger:
    """Structured logging system for Evaluator v16"""
    
    def __init__(self, log_dir: str = "data/logs", debug_mode: bool = False):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.debug_mode = debug_mode

        self.evaluation_log_file = self.log_dir / "evaluations.jsonl"
        self.system_log_file = self.log_dir / "system.log"
        self.error_log_file = self.log_dir / "errors.jsonl"

        self._setup_python_logging()

        self.logger = logging.getLogger(__name__)

        self._initialize_log_files()
    
    def _setup_python_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)

        root_logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # Ensure this is INFO
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            self.system_log_file,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    def _initialize_log_files(self):
        if not self.evaluation_log_file.exists():
            self.evaluation_log_file.touch()
        if not self.error_log_file.exists():
            self.error_log_file.touch()
    
    def log_evaluation_start(self, learner_id: str, activity_id: str, **metadata):
        entry = EvaluationLogEntry(
            timestamp=self._get_timestamp(),
            event_type="evaluation_start",
            learner_id=learner_id,
            activity_id=activity_id,
            metadata=metadata
        )
        self._write_evaluation_log(entry)
        self.logger.info(f"Evaluation started: {activity_id} for learner {learner_id}")

    def log_evaluation_complete(self, learner_id: str, activity_id: str,
                               duration_seconds: float, success: bool = True,
                               **metadata):
        entry = EvaluationLogEntry(
            timestamp=self._get_timestamp(),
            event_type="evaluation_complete",
            learner_id=learner_id,
            activity_id=activity_id,
            success=success,
            duration_seconds=duration_seconds,
            metadata=metadata
        )
        self._write_evaluation_log(entry)
        
        status = "completed successfully" if success else "failed"
        self.logger.info(f"Evaluation {status}: {activity_id} ({duration_seconds:.2f}s)")

    def log_phase_start(self, learner_id: str, activity_id: str, phase_name: str,
                       provider: str = None, **metadata):
        entry = EvaluationLogEntry(
            timestamp=self._get_timestamp(),
            event_type="phase_start",
            learner_id=learner_id,
            activity_id=activity_id,
            phase_name=phase_name,
            provider=provider,
            metadata=metadata
        )
        self._write_evaluation_log(entry)
        provider_info = f" with {provider}" if provider else ""
        self.logger.debug(f"Phase started: {phase_name}{provider_info}")
    
    def log_phase_complete(self, learner_id: str, activity_id: str, phase_name: str,
                          provider: str = None, duration_seconds: float = None,
                          tokens_used: int = None, cost_estimate: float = None,
                          success: bool = True, **metadata):
        entry = EvaluationLogEntry(
            timestamp=self._get_timestamp(),
            event_type="phase_complete",
            learner_id=learner_id,
            activity_id=activity_id,
            phase_name=phase_name,
            provider=provider,
            success=success,
            duration_seconds=duration_seconds,
            tokens_used=tokens_used,
            cost_estimate=cost_estimate,
            metadata=metadata
        )
        self._write_evaluation_log(entry)
        
        status = "completed" if success else "failed"
        duration_info = f" ({duration_seconds:.2f}s)" if duration_seconds else ""
        token_info = f", {tokens_used} tokens" if tokens_used else ""
        cost_info = f", ${cost_estimate:.4f}" if cost_estimate else ""
        self.logger.debug(f"Phase {status}: {phase_name}{duration_info}{token_info}{cost_info}")
    
    def log_llm_call(self, provider: str, phase_name: str, success: bool,
                    duration_seconds: float = None, tokens_used: int = None,
                    cost_estimate: float = None, error_message: str = None,
                    **metadata):
        entry = EvaluationLogEntry(
            timestamp=self._get_timestamp(),
            event_type="llm_call",
            learner_id=metadata.get('learner_id', 'unknown'),
            activity_id=metadata.get('activity_id', 'unknown'),
            phase_name=phase_name,
            provider=provider,
            success=success,
            duration_seconds=duration_seconds,
            tokens_used=tokens_used,
            cost_estimate=cost_estimate,
            error_message=error_message,
            metadata=metadata
        )
        self._write_evaluation_log(entry)
        
        if success:
            self.logger.debug(f"LLM call successful: {provider} for {phase_name}")
        else:
            self.logger.warning(f"LLM call failed: {provider} for {phase_name} - {error_message}")

    def log_error(self, error_type: str, error_message: str, component: str = None,
                 learner_id: str = None, activity_id: str = None, **metadata):
        if learner_id and activity_id:
            eval_entry = EvaluationLogEntry(
                timestamp=self._get_timestamp(),
                event_type="error",
                learner_id=learner_id,
                activity_id=activity_id,
                success=False,
                error_message=error_message,
                metadata={
                    'error_type': error_type,
                    'component': component,
                    **metadata
                }
            )
            self._write_evaluation_log(eval_entry)

        error_entry = {
            'timestamp': self._get_timestamp(),
            'error_type': error_type,
            'component': component,
            'learner_id': learner_id,
            'activity_id': activity_id,
            'error_message': error_message,
            'metadata': metadata
        }
        self._write_error_log(error_entry)
        self.logger.error(f"{error_type}: {error_message}")
    
    def log_debug(self, component: str, message: str, **metadata):
        """Log debug message with optional metadata"""
        entry = SystemLogEntry(
            timestamp=self._get_timestamp(),
            level="DEBUG",
            component=component,
            event_type="debug",
            message=message,
            metadata=metadata
        )
        logger = logging.getLogger(component)
        logger.debug(message)

    def log_system_event(self, component: str, event_type: str, message: str,
                        level: str = "INFO", **metadata):
        entry = SystemLogEntry(
            timestamp=self._get_timestamp(),
            level=level,
            component=component,
            event_type=event_type,
            message=message,
            metadata=metadata
        )
        logger = logging.getLogger(component)
        if level == "DEBUG":
            logger.debug(message)
        elif level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
    
    def get_evaluation_stats(self, hours: int = 24) -> Dict[str, Any]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        stats = {
            'total_evaluations': 0,
            'successful_evaluations': 0,
            'failed_evaluations': 0,
            'average_duration': 0.0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'provider_usage': {},
            'phase_performance': {},
            'error_summary': {}
        }
        try:
            if self.evaluation_log_file.exists():
                with open(self.evaluation_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        entry_data = json.loads(line)
                        entry_time = datetime.fromisoformat(entry_data['timestamp'].replace('Z', '+00:00'))
                        if entry_time < cutoff_time:
                            continue
                        if entry_data['event_type'] == 'evaluation_complete':
                            stats['total_evaluations'] += 1
                            if entry_data['success']:
                                stats['successful_evaluations'] += 1
                            else:
                                stats['failed_evaluations'] += 1
                        if entry_data.get('tokens_used'):
                            stats['total_tokens'] += entry_data['tokens_used']
                        if entry_data.get('cost_estimate'):
                            stats['total_cost'] += entry_data['cost_estimate']
                        if entry_data.get('provider'):
                            provider = entry_data['provider']
                            stats['provider_usage'][provider] = stats['provider_usage'].get(provider, 0) + 1
        except Exception as e:
            self.logger.error(f"Error calculating stats: {e}")
        if stats['total_evaluations'] > 0:
            stats['success_rate'] = stats['successful_evaluations'] / stats['total_evaluations']
        else:
            stats['success_rate'] = 0.0
        return stats
    
    def get_recent_errors(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        errors = []
        try:
            if self.error_log_file.exists():
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        error_data = json.loads(line)
                        error_time = datetime.fromisoformat(error_data['timestamp'].replace('Z', '+00:00'))
                        if error_time >= cutoff_time:
                            errors.append(error_data)
                        if len(errors) >= limit:
                            break
        except Exception as e:
            self.logger.error(f"Error reading error log: {e}")
        errors.sort(key=lambda x: x['timestamp'], reverse=True)
        return errors[:limit]
    
    def export_logs(self, output_dir: str = None, hours: int = 24) -> Dict[str, str]:
        if output_dir is None:
            output_dir = self.log_dir / "exports"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        exported_files = {}
        try:
            eval_export_file = output_dir / f"evaluations_{timestamp_str}.jsonl"
            with open(eval_export_file, 'w', encoding='utf-8') as out_file:
                if self.evaluation_log_file.exists():
                    with open(self.evaluation_log_file, 'r', encoding='utf-8') as in_file:
                        for line in in_file:
                            if not line.strip():
                                continue
                            entry_data = json.loads(line)
                            entry_time = datetime.fromisoformat(entry_data['timestamp'].replace('Z', '+00:00'))
                            if entry_time >= cutoff_time:
                                out_file.write(line)
            exported_files['evaluations'] = str(eval_export_file)
            error_export_file = output_dir / f"errors_{timestamp_str}.jsonl"
            with open(error_export_file, 'w', encoding='utf-8') as out_file:
                if self.error_log_file.exists():
                    with open(self.error_log_file, 'r', encoding='utf-8') as in_file:
                        for line in in_file:
                            if not line.strip():
                                continue
                            error_data = json.loads(line)
                            error_time = datetime.fromisoformat(error_data['timestamp'].replace('Z', '+00:00'))
                            if error_time >= cutoff_time:
                                out_file.write(line)
            exported_files['errors'] = str(error_export_file)
            if self.system_log_file.exists():
                system_export_file = output_dir / f"system_{timestamp_str}.log"
                with open(system_export_file, 'w', encoding='utf-8') as out_file:
                    with open(self.system_log_file, 'r', encoding='utf-8') as in_file:
                        out_file.write(in_file.read())
                exported_files['system'] = str(system_export_file)
            self.logger.info(f"Logs exported to {output_dir}")
        except Exception as e:
            self.logger.error(f"Error exporting logs: {e}")
            raise
        return exported_files
    
    def cleanup_old_logs(self, days: int = 30):
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        self._cleanup_jsonl_file(self.evaluation_log_file, cutoff_time)
        self._cleanup_jsonl_file(self.error_log_file, cutoff_time)
        self.logger.info(f"Cleaned up logs older than {days} days")
    
    def _cleanup_jsonl_file(self, file_path: Path, cutoff_time: datetime):
        if not file_path.exists():
            return
        temp_file = file_path.with_suffix('.tmp')
        kept_entries = 0
        removed_entries = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as in_file:
                with open(temp_file, 'w', encoding='utf-8') as out_file:
                    for line in in_file:
                        if not line.strip():
                            continue
                        try:
                            entry_data = json.loads(line)
                            entry_time = datetime.fromisoformat(entry_data['timestamp'].replace('Z', '+00:00'))
                            if entry_time >= cutoff_time:
                                out_file.write(line)
                                kept_entries += 1
                            else:
                                removed_entries += 1
                        except (json.JSONDecodeError, ValueError, KeyError):
                            out_file.write(line)
                            kept_entries += 1
            temp_file.replace(file_path)
            self.logger.debug(f"Cleanup {file_path.name}: kept {kept_entries}, removed {removed_entries}")
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise e
    
    @contextmanager
    def evaluation_context(self, learner_id: str, activity_id: str, **metadata):
        start_time = time.time()
        try:
            self.log_evaluation_start(learner_id, activity_id, **metadata)
            yield self
            duration = time.time() - start_time
            self.log_evaluation_complete(learner_id, activity_id, duration, success=True)
        except Exception as e:
            duration = time.time() - start_time
            self.log_evaluation_complete(learner_id, activity_id, duration, success=False)
            self.log_error(
                error_type="evaluation_error",
                error_message=str(e),
                component="evaluation_pipeline",
                learner_id=learner_id,
                activity_id=activity_id
            )
            raise

    @contextmanager
    def phase_context(self, phase_name: str, learner_id: str, activity_id: str,
                     provider: str = None, **metadata):
        start_time = time.time()
        try:
            self.log_phase_start(learner_id, activity_id, phase_name, provider, **metadata)
            yield self
            duration = time.time() - start_time
            self.log_phase_complete(
                learner_id, activity_id, phase_name, provider, 
                duration_seconds=duration, success=True, **metadata
            )
        except Exception as e:
            duration = time.time() - start_time
            self.log_phase_complete(
                learner_id, activity_id, phase_name, provider,
                duration_seconds=duration, success=False, **metadata
            )
            self.log_error(
                error_type="phase_error", 
                error_message=str(e),
                component="evaluation_pipeline",
                learner_id=learner_id,
                activity_id=activity_id,
                phase_name=phase_name
            )
            raise
    
    def _write_evaluation_log(self, entry: EvaluationLogEntry):
        try:
            with open(self.evaluation_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write evaluation log: {e}")
    
    def _write_error_log(self, entry: Dict[str, Any]):
        try:
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write error log: {e}")
    
    def _get_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

_global_logger = None

def get_logger() -> EvaluatorLogger:
    global _global_logger
    if _global_logger is None:
        _global_logger = EvaluatorLogger()
    return _global_logger

def setup_logging(log_dir: str = "data/logs", debug_mode: bool = False) -> EvaluatorLogger:
    global _global_logger
    _global_logger = EvaluatorLogger(log_dir, debug_mode)
    return _global_logger

def log_evaluation_start(learner_id: str, activity_id: str, **metadata):
    get_logger().log_evaluation_start(learner_id, activity_id, **metadata)

def log_evaluation_complete(learner_id: str, activity_id: str, duration_seconds: float, 
                          success: bool = True, **metadata):
    get_logger().log_evaluation_complete(learner_id, activity_id, duration_seconds, success, **metadata)

def log_error(error_type: str, error_message: str, component: str = None, **metadata):
    get_logger().log_error(error_type, error_message, component, **metadata)

def log_llm_call(provider: str, phase_name: str, success: bool, **metadata):
    get_logger().log_llm_call(provider, phase_name, success, **metadata)