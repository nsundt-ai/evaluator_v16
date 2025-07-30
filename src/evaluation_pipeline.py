"""
Evaluation Pipeline for Evaluator v16
Orchestrates multi-phase evaluation process with LLM integration.
"""

import os
import json
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
import asyncio
from enum import Enum
import traceback

from config_manager import ConfigManager
from llm_client import LLMClient
from prompt_builder import PromptBuilder, PromptConfiguration
from scoring_engine import ScoringEngine, SkillScore
from learner_manager import LearnerManager, ActivityRecord
from activity_manager import ActivityManager, ActivitySpec
from logger import get_logger


class PipelinePhase(Enum):
    """Evaluation pipeline phases"""
    COMBINED_EVALUATION = "combined"
    RUBRIC_EVALUATION = "rubric"  # DEPRECATED
    VALIDITY_ANALYSIS = "validity"  # DEPRECATED
    SCORING = "scoring"
    DIAGNOSTIC_INTELLIGENCE = "diagnostic"  # DEPRECATED - Combined into intelligent_feedback
    TREND_ANALYSIS = "trend"
    FEEDBACK_GENERATION = "feedback"  # DEPRECATED - Combined into intelligent_feedback
    INTELLIGENT_FEEDBACK = "intelligent_feedback"  # NEW: Combined diagnostic + feedback


@dataclass
class PhaseResult:
    """Result from a single pipeline phase"""
    phase: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None


@dataclass
class EvaluationResult:
    """Complete evaluation result"""
    activity_id: str
    learner_id: str
    evaluation_timestamp: str
    pipeline_phases: List[PhaseResult]
    final_skill_scores: Dict[str, SkillScore]
    overall_success: bool
    total_execution_time_ms: int
    total_cost_estimate: float
    error_summary: Optional[str] = None


class EvaluationPipeline:
    """
    Orchestrates the complete evaluation pipeline with all 5 phases.
    Integrates all backend modules and handles error recovery.
    """

    def __init__(self, config_manager: ConfigManager, llm_client: LLMClient,
                 prompt_builder: PromptBuilder, scoring_engine: ScoringEngine,
                 learner_manager: LearnerManager, activity_manager: ActivityManager):
        self.config = config_manager
        self.config_manager = config_manager  # Add this line for backward compatibility
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.scoring_engine = scoring_engine
        self.learner_manager = learner_manager
        self.activity_manager = activity_manager
        self.logger = get_logger()
        self.rubric_required_types = {'CR', 'COD', 'RP'}
        self.autoscored_types = {'SR', 'BR'}
        self.max_retries = 3
        self.phase_timeout_seconds = 300  # 5 minutes per phase
        
        # Add caching for expensive operations
        self._domain_model_cache = None
        self._leveling_framework_cache = None
        self._skill_context_cache = {}
        self._prerequisite_cache = {}
        self._historical_data_cache = {}  # Cache historical data by learner_id
        self._temporal_context_cache = {}  # Cache temporal context by learner_id
        
        # Pass learner_manager to scoring engine for activity history
        if hasattr(self.scoring_engine, 'learner_manager'):
            self.scoring_engine.learner_manager = self.learner_manager
        
        self.logger.log_system_event('evaluation_pipeline', 'initialized', 
                                    'Evaluation pipeline initialized with all modules')

    def evaluate_activity(self, activity_id: str, learner_id: str, 
                         activity_transcript: Dict[str, Any],
                         evaluation_mode: str = 'full') -> EvaluationResult:
        """Evaluate an activity using the AI-powered pipeline"""
        start_time = datetime.now()
        
        # Validate inputs
        if not activity_id or not learner_id:
            return self._create_failed_result(activity_id, learner_id, 
                                           datetime.now().isoformat(), 
                                           "Missing activity_id or learner_id")
        
        # Get activity and learner data
        try:
            activity = self.activity_manager.get_activity(activity_id)
            if not activity:
                return self._create_failed_result(activity_id, learner_id,
                                               datetime.now().isoformat(),
                                               f"Activity not found: {activity_id}")
            
            learner = self.learner_manager.get_learner(learner_id)
            if not learner:
                return self._create_failed_result(activity_id, learner_id,
                                               datetime.now().isoformat(),
                                               f"Learner not found: {learner_id}")
            
            learner_activities = self.learner_manager.get_learner_activities(learner_id) or []
        except Exception as e:
            return self._create_failed_result(activity_id, learner_id,
                                           datetime.now().isoformat(),
                                           f"Failed to load activity/learner data: {str(e)}")
        
        # Initialize pipeline state
        pipeline_phases = []
        total_cost = 0.0
        overall_success = True
        error_summary = None
        
        # Initialize pipeline state
        pipeline_phases = []
        total_cost = 0.0
        overall_success = True
        error_summary = None
        previous_results = {}
        
        try:
            # Phase 1: Summative Evaluation (Rubric + Validity Analysis)
            combined_results = None
            
            with self.logger.phase_context('combined_evaluation', activity_id, learner_id):
                combined_context = self._prepare_phase_specific_context(activity, learner, activity_transcript, learner_activities, 'combined', learner_id)
                phase_result = self._run_combined_evaluation(activity, combined_context)
                pipeline_phases.append(phase_result)
                total_cost += phase_result.cost_estimate or 0.0
                if phase_result.success:
                    combined_results = phase_result.result
                    # With simplified structure, the combined results contain all the data directly
                    rubric_results = {
                        'aspect_scores': combined_results.get('aspect_scores', []),
                        'overall_score': combined_results.get('overall_score', 0.0),
                        'rationale': combined_results.get('rationale', '')
                    }
                    validity_results = {
                        'validity_modifier': combined_results.get('validity_modifier', 1.0),
                        'validity_analysis': combined_results.get('validity_analysis', ''),
                        'validity_reason': combined_results.get('validity_reason', '')
                    }
                    previous_results['phase_1_combined_evaluation'] = combined_results
                    previous_results['phase_1a_rubric_evaluation'] = rubric_results
                    previous_results['phase_1b_validity_analysis'] = validity_results
                else:
                    overall_success = False
                    error_summary = f"Combined evaluation failed: {phase_result.error}"
                    # Use default results
                    rubric_results = {'aspect_scores': [], 'overall_score': 0.5, 'rationale': 'Defaulted due to error'}
                    validity_results = {'validity_modifier': 1.0, 'validity_analysis': 'Defaulted due to error'}
                    previous_results['rubric'] = rubric_results
                    previous_results['validity'] = validity_results

            # Phase 2: Scoring
            scoring_results = None
            with self.logger.phase_context('scoring', activity_id, learner_id):
                try:
                    phase_result = self._run_scoring_phase(activity, rubric_results, validity_results, learner_activities, learner_id)
                    pipeline_phases.append(phase_result)
                    total_cost += phase_result.cost_estimate or 0.0
                    if phase_result.success:
                        scoring_results = phase_result.result
                        self.logger.log_system_event('evaluation_pipeline', 'scoring_complete', 'Scoring phase completed successfully.')
                    else:
                        overall_success = False
                        error_summary = f"Scoring failed: {phase_result.error}"
                except Exception as e:
                    self.logger.log_error('scoring_phase_exception', f'Scoring phase exception: {str(e)}', 'evaluation_pipeline')
                    overall_success = False
                    error_summary = f"Scoring exception: {str(e)}"

            # Phase 3: Intelligent Feedback (Combined Diagnostic + Feedback)
            intelligent_feedback_results = None
            with self.logger.phase_context('intelligent_feedback', activity_id, learner_id):
                try:
                    # Prepare context that combines diagnostic and feedback requirements
                    intelligent_context = self._prepare_phase_specific_context(activity, learner, activity_transcript, learner_activities, 'intelligent_feedback', learner_id)
                    intelligent_context = self._prepare_phase_specific_context_with_results(intelligent_context, 'intelligent_feedback', previous_results)
                    intelligent_context['performance_context'] = self._determine_performance_context(scoring_results) if scoring_results else {}
                    phase_result = self._run_intelligent_feedback(activity, intelligent_context)
                    pipeline_phases.append(phase_result)
                    total_cost += phase_result.cost_estimate or 0.0
                    if phase_result.success:
                        intelligent_feedback_results = phase_result.result
                        previous_results['intelligent_feedback'] = intelligent_feedback_results
                    else:
                        overall_success = False
                        error_summary = f"Intelligent feedback failed: {phase_result.error}"
                except Exception as e:
                    self.logger.log_error('intelligent_feedback_phase_exception', f'Intelligent feedback phase exception: {str(e)}', 'evaluation_pipeline')
                    intelligent_feedback_results = None
                    phase_result = PhaseResult(
                        phase='intelligent_feedback',
                        success=False,
                        error=str(e),
                        result=None,
                        execution_time_ms=0,
                        tokens_used=0,
                        cost_estimate=0.0
                    )
                    pipeline_phases.append(phase_result)

            # Phase 4: Trend Analysis - DISABLED
            trend_results = None
            with self.logger.phase_context('trend_analysis', activity_id, learner_id):
                # TREND ANALYSIS DISABLED - Hardcoded disabled result
                # This eliminates LLM costs and processing time while maintaining pipeline structure
                trend_start_time = datetime.now()
                
                disabled_result = {
                    'trend_analysis': {
                        'performance_trajectory': 'stable',
                        'trend_analysis': 'Trend Analysis Disabled - This feature has been disabled to reduce costs and processing time.',
                        'growth_patterns': [],
                        'learning_velocity': {
                            'current_velocity': 'stable',
                            'velocity_trend': 'no_change',
                            'velocity_factors': ['feature_disabled']
                        },
                        'improvement_areas': ['feature_disabled'],
                        'strength_areas': ['feature_disabled'],
                        'recommendations': ['Trend analysis has been disabled to reduce costs and processing time.']
                    }
                }
                execution_time_ms = int((datetime.now() - trend_start_time).total_seconds() * 1000)
                self.logger.log_system_event('evaluation_pipeline', 'trend_analysis_disabled', 
                                           f'Trend analysis disabled - returning disabled message in {execution_time_ms/1000:.2f}s')
                phase_result = PhaseResult(
                    phase='trend_analysis',
                    success=True,
                    result=disabled_result,
                    execution_time_ms=execution_time_ms,
                    tokens_used=0,
                    cost_estimate=0.0,
                    error=None
                )
                pipeline_phases.append(phase_result)
                trend_results = phase_result.result
                previous_results['trend'] = trend_results

            # Save evaluation record
            evaluation_results = {
                'overall_success': overall_success,
                'error_summary': error_summary,
                'total_cost': total_cost,
                'pipeline_phases': [phase.__dict__ for phase in pipeline_phases]
            }
            self._save_evaluation_record(activity_id, learner_id, activity_transcript, evaluation_results)
            
            # Clear historical cache for this learner since new data was added
            self._clear_historical_cache(learner_id)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if overall_success:
                self.logger.log_system_event('evaluation_pipeline', 'evaluation_complete', f'Evaluation completed successfully: {activity_id} ({execution_time:.2f}s)')
            else:
                self.logger.log_system_event('evaluation_pipeline', 'evaluation_failed', f'Evaluation failed: {activity_id} ({execution_time:.2f}s)')
            
            return EvaluationResult(
                activity_id=activity_id,
                learner_id=learner_id,
                evaluation_timestamp=datetime.now().isoformat(),
                pipeline_phases=pipeline_phases,
                final_skill_scores={},  # Will be populated by scoring engine
                overall_success=overall_success,
                total_execution_time_ms=int(execution_time * 1000),
                total_cost_estimate=total_cost,
                error_summary=error_summary
            )
            
        except Exception as e:
            self.logger.log_error('evaluation_pipeline', f'Pipeline execution failed: {str(e)}', str(e))
            return EvaluationResult(
                activity_id=activity_id,
                learner_id=learner_id,
                evaluation_timestamp=datetime.now().isoformat(),
                pipeline_phases=[],
                final_skill_scores={},
                overall_success=False,
                total_execution_time_ms=0,
                total_cost_estimate=0.0,
                error_summary=f"Pipeline execution failed: {str(e)}"
            )

    def _run_combined_evaluation(self, activity: ActivitySpec, context: Dict[str, Any]) -> PhaseResult:
        """
        Combined evaluation phase that integrates rubric assessment with validity analysis.
        This replaces the separate rubric_evaluation and validity_analysis phases.
        """
        start_time = datetime.now()
        try:
            # Prepare context for combined evaluation
            enhanced_context = self.prompt_builder.prepare_context_data(context, 'combined')
            prompt_config = self.prompt_builder.build_prompt('combined', activity.activity_type, enhanced_context)
            response = self.llm_client.call_llm_with_fallback(
                system_prompt=prompt_config.system_prompt,
                user_prompt=prompt_config.user_prompt,
                phase='combined_evaluation',
                expected_schema=prompt_config.output_schema
            )
            if response.success:
                # Parse JSON response using optimized parser
                try:
                    parsed_content = self._parse_llm_response(response.content)
                except Exception as e:
                    parsed_content = {
                        'aspect_scores': [],
                        'overall_score': 0.5,
                        'rationale': 'Combined evaluation failed due to parsing error',
                        'validity_modifier': 1.0,
                        'validity_analysis': 'Evaluation failed due to parsing error',
                        'validity_reason': 'Parsing error occurred',
                        'evidence_quality': 'Unable to assess due to parsing error',
                        'assistance_impact': 'Unable to assess due to parsing error',
                        'evidence_volume_assessment': 'Unable to assess due to parsing error',
                        'assessment_confidence': 'Unable to assess due to parsing error',
                        'key_observations': ['Combined evaluation parsing failed']
                    }
                
                result = self._validate_combined_result(parsed_content)
                # Add metadata with token information to the result
                if hasattr(response, 'metadata') and response.metadata:
                    result['metadata'] = response.metadata
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return PhaseResult(
                    phase='combined_evaluation',
                    success=True,
                    result=result,
                    execution_time_ms=execution_time,
                    tokens_used=response.tokens_used,
                    cost_estimate=response.cost_estimate
                )
            else:
                # Return a default result even on failure to prevent iteration errors
                default_result = {
                    'aspect_scores': [],
                    'overall_score': 0.5,
                    'rationale': 'Combined evaluation failed',
                    'validity_modifier': 1.0,
                    'validity_analysis': 'Evaluation failed due to LLM error',
                    'validity_reason': 'LLM call failed',
                    'evidence_quality': 'Unable to assess due to LLM error',
                    'assistance_impact': 'Unable to assess due to LLM error',
                    'evidence_volume_assessment': 'Unable to assess due to LLM error',
                    'assessment_confidence': 'Unable to assess due to LLM error',
                    'key_observations': ['Combined evaluation LLM call failed']
                }
                return PhaseResult(
                    phase='combined_evaluation',
                    success=False,
                    result=default_result,
                    error=f"LLM call failed: {response.error}",
                    execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                )
        except Exception as e:
            # Return a default result even on exception to prevent iteration errors
            default_result = {
                'aspect_scores': [],
                'overall_score': 0.5,
                'rationale': 'Combined evaluation failed due to error',
                'validity_modifier': 1.0,
                'validity_analysis': 'Evaluation failed due to exception',
                'validity_reason': 'Exception occurred during evaluation',
                'evidence_quality': 'Unable to assess due to exception',
                'assistance_impact': 'Unable to assess due to exception',
                'evidence_volume_assessment': 'Unable to assess due to exception',
                'assessment_confidence': 'Unable to assess due to exception',
                'key_observations': ['Combined evaluation exception occurred']
            }
            return PhaseResult(
                phase='combined_evaluation',
                success=False,
                result=default_result,
                error=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

    def _run_scoring_phase(self, activity: ActivitySpec, rubric_results: Dict[str, Any], 
                          validity_results: Dict[str, Any], learner_activities: List[ActivityRecord], 
                          learner_id: str) -> PhaseResult:
        """
        Run the scoring phase using the scoring engine.
        This calculates skill scores based on the evaluation results.
        """
        start_time = datetime.now()
        try:
            # Create evaluation data structure for scoring engine
            evaluation_data = {
                'activity_id': activity.activity_id,
                'learner_id': learner_id,
                'target_skill': activity.target_skill,
                'aspect_scores': rubric_results.get('aspect_scores', []),
                'overall_score': rubric_results.get('overall_score', 0.0),
                'validity_modifier': validity_results.get('validity_modifier', 1.0),
                'target_evidence_volume': activity.target_evidence_volume,
                'activity_type': activity.activity_type,
                'activity_title': activity.title,
                'timestamp': datetime.now().isoformat()
            }
            
            # Create learner history structure
            learner_history = {
                'learner_id': learner_id,
                'activities': [record.__dict__ for record in learner_activities]
            }
            
            # Run scoring using the scoring engine
            # Ensure scoring engine has access to learner_manager for activity history
            if not hasattr(self.scoring_engine, 'learner_manager') or self.scoring_engine.learner_manager is None:
                self.scoring_engine.learner_manager = self.learner_manager
            
            scoring_result = self.scoring_engine.score_activity(learner_history, evaluation_data)
            
            # Update learner progress in database
            try:
                self.scoring_engine.update_learner_progress(learner_history, scoring_result, self.learner_manager)
            except Exception as e:
                self.logger.log_error('evaluation_pipeline', f'Failed to update learner progress: {str(e)}', str(e))
            
            # Convert scoring result to the expected format
            result = {
                'activity_score': evaluation_data['overall_score'],
                'target_evidence_volume': activity.target_evidence_volume,
                'validity_modifier': evaluation_data['validity_modifier'],
                'adjusted_evidence_volume': activity.target_evidence_volume * evaluation_data['validity_modifier'],
                'final_score': evaluation_data['overall_score'],
                'aspect_scores': evaluation_data['aspect_scores'],
                'scoring_rationale': f"Activity scored with {len(scoring_result.skill_scores)} skills evaluated"
            }
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return PhaseResult(
                phase='scoring',
                success=True,
                result=result,
                execution_time_ms=execution_time,
                tokens_used=0,  # Scoring doesn't use LLM tokens
                cost_estimate=0.0  # Scoring doesn't incur LLM costs
            )
            
        except Exception as e:
            # Return a default result even on failure
            default_result = {
                'activity_score': 0.0,
                'target_evidence_volume': activity.target_evidence_volume,
                'validity_modifier': 1.0,
                'adjusted_evidence_volume': activity.target_evidence_volume,
                'final_score': 0.0,
                'aspect_scores': [],
                'scoring_rationale': f'Scoring failed: {str(e)}'
            }
            return PhaseResult(
                phase='scoring',
                success=False,
                result=default_result,
                error=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                tokens_used=0,
                cost_estimate=0.0
            )

    def _run_intelligent_feedback(self, activity: ActivitySpec, context: Dict[str, Any]) -> PhaseResult:
        """
        NEW: Combined diagnostic intelligence and feedback generation phase.
        This replaces the separate diagnostic_intelligence and feedback_generation phases
        to reduce LLM calls and improve consistency.
        """
        start_time = datetime.now()
        try:
            # Prepare context for intelligent feedback (combines diagnostic + feedback context)
            enhanced_context = self.prompt_builder.prepare_context_data(context, 'intelligent_feedback')
            prompt_config = self.prompt_builder.build_prompt('intelligent_feedback', activity.activity_type, enhanced_context)
            response = self.llm_client.call_llm_with_fallback(
                system_prompt=prompt_config.system_prompt,
                user_prompt=prompt_config.user_prompt,
                phase='intelligent_feedback',
                expected_schema=prompt_config.output_schema
            )
            if response.success:
                # Parse JSON response using optimized parser
                try:
                    parsed_content = self._parse_llm_response(response.content)
                except Exception as e:
                    # Return a default result with both diagnostic and feedback components
                    parsed_content = {
                        'intelligent_feedback': {
                            'diagnostic_analysis': {
                                'strength_areas': ['Analysis failed due to parsing error'],
                                'improvement_areas': ['Analysis failed due to parsing error'],
                                'subskill_performance': []
                            },
                            'student_feedback': {
                                'performance_summary': {
                                    'overall_assessment': 'Analysis failed due to parsing error',
                                    'key_strengths': [],
                                    'primary_opportunities': [],
                                    'achievement_highlights': []
                                },
                                'actionable_guidance': {
                                    'immediate_next_steps': [],
                                    'recommendations': []
                                }
                            }
                        }
                    }
                
                result = self._validate_intelligent_feedback_result(parsed_content)
                # Add metadata with token information to the result
                if hasattr(response, 'metadata') and response.metadata:
                    result['metadata'] = response.metadata
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return PhaseResult(
                    phase='intelligent_feedback',
                    success=True,
                    result=result,
                    execution_time_ms=execution_time,
                    tokens_used=response.tokens_used,
                    cost_estimate=response.cost_estimate
                )
            else:
                # Return a default result even on failure to prevent iteration errors
                default_result = {
                    'intelligent_feedback': {
                        'diagnostic_analysis': {
                            'strength_areas': ['Analysis unavailable'],
                            'improvement_areas': ['Analysis unavailable'],
                            'subskill_performance': []
                        },
                        'student_feedback': {
                            'performance_summary': {
                                'overall_assessment': 'Analysis unavailable',
                                'key_strengths': [],
                                'primary_opportunities': [],
                                'achievement_highlights': []
                            },
                            'actionable_guidance': {
                                'immediate_next_steps': [],
                                'recommendations': []
                            }
                        }
                    }
                }
                return PhaseResult(
                    phase='intelligent_feedback',
                    success=False,
                    result=default_result,
                    error=f"LLM call failed: {response.error}",
                    execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
                )
        except Exception as e:
            # Return a default result even on exception to prevent iteration errors
            default_result = {
                'intelligent_feedback': {
                    'diagnostic_analysis': {
                        'strength_areas': ['Analysis unavailable due to error'],
                        'improvement_areas': ['Analysis unavailable due to error'],
                        'subskill_performance': []
                    },
                    'student_feedback': {
                        'performance_summary': {
                            'overall_assessment': 'Analysis unavailable due to error',
                            'key_strengths': [],
                            'primary_opportunities': [],
                            'achievement_highlights': []
                        },
                        'actionable_guidance': {
                            'immediate_next_steps': [],
                            'recommendations': []
                        }
                    }
                }
            }
            return PhaseResult(
                phase='intelligent_feedback',
                success=False,
                result=default_result,
                error=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

    def _get_skill_context(self, skill_id: str) -> Dict[str, Any]:
        """Get detailed context for a specific skill"""
        try:
            domain_model = self.config.get_domain_model()
            skills = domain_model.get('skills', {})
            
            if skill_id in skills:
                skill_data = skills[skill_id]
                return {
                    'skill_id': skill_id,
                    'skill_name': skill_data.get('name', 'Unknown Skill'),
                    'skill_description': skill_data.get('description', ''),
                    'cognitive_level': skill_data.get('cognitive_level', ''),
                    'depth_level': skill_data.get('depth_level', ''),
                    'competency_id': skill_data.get('competency_id', ''),
                    'subskills': skill_data.get('subskills', []),
                    'prerequisites': skill_data.get('prerequisites', [])
                }
            else:
                return {
                    'skill_id': skill_id,
                    'skill_name': 'Unknown Skill',
                    'skill_description': 'Skill not found in domain model',
                    'cognitive_level': '',
                    'depth_level': '',
                    'competency_id': '',
                    'subskills': [],
                    'prerequisites': []
                }
        except Exception as e:
            self.logger.log_error('evaluation_pipeline', f'Error getting skill context for {skill_id}: {str(e)}', str(e))
            return {
                'skill_id': skill_id,
                'skill_name': 'Error Loading Skill',
                'skill_description': f'Error loading skill data: {str(e)}',
                'cognitive_level': '',
                'depth_level': '',
                'competency_id': '',
                'subskills': [],
                'prerequisites': []
            }

    def _get_prerequisite_relationships(self, skill_id: str) -> Dict[str, Any]:
        """Get prerequisite relationships for a skill"""
        try:
            domain_model = self.config.get_domain_model()
            skills = domain_model.get('skills', {})
            
            if skill_id in skills:
                skill_data = skills[skill_id]
                prerequisites = skill_data.get('prerequisites', [])
                
                prerequisite_details = []
                for prereq_id in prerequisites:
                    if prereq_id in skills:
                        prereq_data = skills[prereq_id]
                        prerequisite_details.append({
                            'skill_id': prereq_id,
                            'skill_name': prereq_data.get('name', 'Unknown'),
                            'description': prereq_data.get('description', ''),
                            'relationship_type': 'prerequisite'
                        })
                
                return {
                    'skill_id': skill_id,
                    'prerequisites': prerequisite_details,
                    'prerequisite_count': len(prerequisites)
                }
            else:
                return {
                    'skill_id': skill_id,
                    'prerequisites': [],
                    'prerequisite_count': 0
                }
        except Exception as e:
            self.logger.log_error('evaluation_pipeline', f'Error getting prerequisite relationships for {skill_id}: {str(e)}', str(e))
            return {
                'skill_id': skill_id,
                'prerequisites': [],
                'prerequisite_count': 0
            }

    def _get_temporal_context(self, learner_activities: List[ActivityRecord]) -> Dict[str, Any]:
        """Get temporal context for trend analysis"""
        try:
            if not learner_activities:
                return {
                    'activity_count': 0,
                    'time_span_days': 0,
                    'recent_activity': False,
                    'activity_frequency': 'none'
                }
            
            # Calculate time span
            timestamps = [activity.evaluation_timestamp for activity in learner_activities if hasattr(activity, 'evaluation_timestamp')]
            if timestamps:
                earliest = min(timestamps)
                latest = max(timestamps)
                time_span = (latest - earliest).days
            else:
                time_span = 0
            
            # Determine activity frequency
            activity_count = len(learner_activities)
            if activity_count == 0:
                frequency = 'none'
            elif activity_count <= 3:
                frequency = 'low'
            elif activity_count <= 10:
                frequency = 'moderate'
            else:
                frequency = 'high'
            
            # Check for recent activity (within last 7 days)
            recent_activity = False
            if timestamps:
                latest_activity = max(timestamps)
                days_since_last = (datetime.now() - latest_activity).days
                recent_activity = days_since_last <= 7
            
            return {
                'activity_count': activity_count,
                'time_span_days': time_span,
                'recent_activity': recent_activity,
                'activity_frequency': frequency,
                'latest_activity_days_ago': days_since_last if timestamps else None
            }
        except Exception as e:
            self.logger.log_error('evaluation_pipeline', f'Error getting temporal context: {str(e)}', str(e))
            return {
                'activity_count': 0,
                'time_span_days': 0,
                'recent_activity': False,
                'activity_frequency': 'unknown'
            }

    def _get_motivational_context(self, learner) -> Dict[str, Any]:
        """Get motivational context for feedback generation with enhanced learner-appropriate guidance"""
        try:
            # Extract motivational factors from learner profile
            motivational_factors = {
                'learning_style': getattr(learner, 'learning_style', 'unknown'),
                'motivation_level': getattr(learner, 'motivation_level', 'moderate'),
                'preferred_feedback_style': getattr(learner, 'preferred_feedback_style', 'balanced'),
                'confidence_level': getattr(learner, 'confidence_level', 'moderate'),
                'engagement_pattern': getattr(learner, 'engagement_pattern', 'consistent')
            }
            
            # Determine motivational approach based on learner characteristics
            if motivational_factors['motivation_level'] == 'high':
                approach = 'encouraging_achievement'
                feedback_style = 'growth_mindset_celebratory'
                language_guidance = 'Use encouraging language that celebrates progress while challenging to higher levels'
            elif motivational_factors['motivation_level'] == 'low':
                approach = 'supportive_guidance'
                feedback_style = 'gentle_encouragement'
                language_guidance = 'Use supportive language that builds confidence and focuses on small wins'
            else:
                approach = 'balanced_encouragement'
                feedback_style = 'constructive_growth'
                language_guidance = 'Use balanced language that acknowledges effort and provides clear next steps'
            
            # Enhanced learner-appropriate guidance
            learner_guidance = {
                'growth_mindset_language': [
                    'Use "developing" instead of "failing"',
                    'Use "not yet" instead of "can\'t"',
                    'Focus on progress and effort, not just outcomes',
                    'Frame challenges as opportunities for growth'
                ],
                'encouragement_techniques': [
                    'Celebrate small wins and incremental progress',
                    'Acknowledge effort and persistence',
                    'Provide specific examples of what good performance looks like',
                    'Connect feedback to real-world impact and application'
                ],
                'confidence_building': [
                    'Start with strengths and what the learner CAN do',
                    'Frame feedback as "next steps" rather than "corrections"',
                    'Provide multiple pathways for improvement',
                    'Acknowledge the complexity of the skill being developed'
                ],
                'actionable_guidance': [
                    'Provide specific, achievable next steps',
                    'Break down complex skills into manageable components',
                    'Offer concrete examples and strategies',
                    'Connect learning to practical application'
                ]
            }
            
            return {
                'motivational_factors': motivational_factors,
                'recommended_approach': approach,
                'feedback_style': feedback_style,
                'language_guidance': language_guidance,
                'learner_guidance': learner_guidance,
                'encouragement_style': 'positive_reinforcement',
                'feedback_tone': 'constructive_supportive',
                'growth_mindset_emphasis': True,
                'confidence_building_focus': True
            }
        except Exception as e:
            self.logger.log_error('motivational_context_error', f'Error getting motivational context: {str(e)}', 'evaluation_pipeline')
            return {
                'motivational_factors': {
                    'learning_style': 'unknown',
                    'motivation_level': 'moderate',
                    'preferred_feedback_style': 'balanced',
                    'confidence_level': 'moderate',
                    'engagement_pattern': 'consistent'
                },
                'recommended_approach': 'balanced_encouragement',
                'feedback_style': 'constructive_growth',
                'language_guidance': 'Use balanced language that acknowledges effort and provides clear next steps',
                'learner_guidance': {
                    'growth_mindset_language': [
                        'Use "developing" instead of "failing"',
                        'Use "not yet" instead of "can\'t"',
                        'Focus on progress and effort, not just outcomes'
                    ],
                    'encouragement_techniques': [
                        'Celebrate small wins and incremental progress',
                        'Acknowledge effort and persistence'
                    ],
                    'confidence_building': [
                        'Start with strengths and what the learner CAN do',
                        'Frame feedback as "next steps" rather than "corrections"'
                    ],
                    'actionable_guidance': [
                        'Provide specific, achievable next steps',
                        'Break down complex skills into manageable components'
                    ]
                },
                'encouragement_style': 'positive_reinforcement',
                'feedback_tone': 'constructive_supportive',
                'growth_mindset_emphasis': True,
                'confidence_building_focus': True
            }

    def _get_leveling_framework(self) -> Dict[str, Any]:
        """Get leveling framework based on domain model cognitive and depth levels"""
        try:
            return {
                'cognitive_levels': {
                    'L1': {
                        'name': 'Remember',
                        'description': 'Recall and recognize information',
                        'verbs': ['define', 'identify', 'list', 'name', 'recall', 'recognize']
                    },
                    'L2': {
                        'name': 'Understand',
                        'description': 'Comprehend and interpret information',
                        'verbs': ['explain', 'summarize', 'paraphrase', 'classify', 'compare', 'contrast']
                    },
                    'L3': {
                        'name': 'Apply',
                        'description': 'Use information in new situations',
                        'verbs': ['implement', 'execute', 'solve', 'use', 'demonstrate', 'apply']
                    },
                    'L4': {
                        'name': 'Analyze',
                        'description': 'Break down information into components',
                        'verbs': ['analyze', 'examine', 'investigate', 'compare', 'organize', 'deconstruct']
                    },
                    'L5': {
                        'name': 'Evaluate',
                        'description': 'Make judgments based on criteria',
                        'verbs': ['evaluate', 'assess', 'judge', 'critique', 'appraise', 'validate']
                    },
                    'L6': {
                        'name': 'Create',
                        'description': 'Generate new ideas or products',
                        'verbs': ['create', 'design', 'develop', 'construct', 'produce', 'generate']
                    }
                },
                'depth_levels': {
                    'D1': {
                        'name': 'Foundation',
                        'description': 'Basic understanding and application',
                        'complexity': 'low'
                    },
                    'D2': {
                        'name': 'Intermediate',
                        'description': 'Moderate complexity and integration',
                        'complexity': 'medium'
                    },
                    'D3': {
                        'name': 'Advanced',
                        'description': 'High complexity and synthesis',
                        'complexity': 'high'
                    }
                }
            }
        except Exception as e:
            self.logger.log_error('leveling_framework_error', f'Error getting leveling framework: {str(e)}', 'evaluation_pipeline')
            return {
                'cognitive_levels': {},
                'depth_levels': {}
            }

    def _analyze_response_characteristics(self, activity_transcript: Dict[str, Any]) -> Dict[str, Any]:
        response_text = str(activity_transcript.get('learner_response', ''))
        return {
            'word_count': len(response_text.split()),
            'character_count': len(response_text),
            'paragraph_count': response_text.count('\n\n') + 1,
            'has_code': any(marker in response_text for marker in ['def ', 'function', 'class ', '{', '}', ';']),
            'response_length_category': 'short' if len(response_text) < 100 else 
                                      'medium' if len(response_text) < 500 else 'long',
            'completion_time_minutes': activity_transcript.get('completion_time_minutes', 0)
        }

    def _prepare_historical_data(self, learner_activities: List[ActivityRecord]) -> Dict[str, Any]:
        """Prepare historical performance data for trend analysis. Defensive: always returns a list."""
        if learner_activities is None:
            self.logger.log_debug('evaluation_pipeline', 'No learner_activities provided to _prepare_historical_data; defaulting to empty list.')
            learner_activities = []
        else:
            self.logger.log_debug('evaluation_pipeline', f'learner_activities received in _prepare_historical_data: {learner_activities}')
        if learner_activities is None or not learner_activities:
            return {
                'activity_count': 0,
                'date_range': {
                    'earliest': None,
                    'latest': None
                },
                'score_trend': [],
                'activity_types': [],
                'performance_patterns': []
            }
        
        sorted_activities = sorted(learner_activities, key=lambda x: x.timestamp)
        historical_data = {
            'activity_count': len(sorted_activities),
            'date_range': {
                'earliest': sorted_activities[0].timestamp if sorted_activities else None,
                'latest': sorted_activities[-1].timestamp if sorted_activities else None
            },
            'score_trend': [],
            'activity_types': [],
            'performance_patterns': []
        }
        for activity in sorted_activities:
            if activity.scored and 'scoring' in activity.evaluation_result and activity.evaluation_result['scoring'] is not None:
                scoring_data = activity.evaluation_result['scoring']
                if 'skill_scores' in scoring_data and scoring_data['skill_scores'] is not None:
                    sks = scoring_data['skill_scores']
                    if sks is None:
                        sks = {}
                    elif isinstance(sks, list):
                        try:
                            sks = {k['skill_id']: k for k in sks if isinstance(k, dict) and 'skill_id' in k}
                        except Exception:
                            self.logger.log_error('historical_data', 'Malformed skill_scores list in history; cannot convert to dict', str(sks))
                            sks = {}
                    elif not isinstance(sks, dict):
                        sks = {}
                    
                    # Add defensive check before iteration
                    if sks and isinstance(sks, dict):
                        try:
                            for skill_id, skill_score in sks.items():
                                historical_data['score_trend'].append({
                                    'timestamp': activity.timestamp,
                                    'skill_id': skill_id,
                                    'cumulative_score': skill_score.get('cumulative_score', 0.0),
                                    'activity_id': activity.activity_id
                                })
                        except Exception as e:
                            self.logger.log_error('historical_data', f'Failed to iterate skill_scores: {e}', str(sks))
            activity_spec = activity.activity_transcript.get('activity_spec', {})
            activity_type = activity_spec.get('activity_type', 'unknown')
            historical_data['activity_types'].append({
                'timestamp': activity.timestamp,
                'type': activity_type,
                'activity_id': activity.activity_id
            })
        return historical_data

    def _determine_performance_context(self, skill_scores: Dict[str, Any]) -> Dict[str, Any]:
        if not skill_scores:
            return {'level': 'no_data', 'description': 'No scoring data available'}
        
        primary_score = next(iter(skill_scores.values()))
        
        # Handle both SkillScore objects and dictionaries
        if hasattr(primary_score, 'cumulative_score'):
            # SkillScore object
            cumulative_score = primary_score.cumulative_score
            overall_status = getattr(primary_score, 'overall_status', 'unknown')
        elif isinstance(primary_score, dict):
            # Dictionary format
            cumulative_score = primary_score.get('cumulative_score', 0.0)
            overall_status = primary_score.get('overall_status', 'unknown')
        else:
            cumulative_score = 0.0
            overall_status = 'unknown'
        
        if cumulative_score >= 0.8:
            level = 'high'
            description = 'Strong performance demonstrating mastery'
        elif cumulative_score >= 0.6:
            level = 'moderate'
            description = 'Good performance with room for growth'
        elif cumulative_score >= 0.4:
            level = 'developing'
            description = 'Developing performance showing progress'
        else:
            level = 'emerging'
            description = 'Emerging performance requiring support'
        
        return {
            'level': level,
            'description': description,
            'score': cumulative_score,
            'gate_status': overall_status
        }

    def _extract_autoscored_result(self, activity: ActivitySpec) -> float:
        return 0.75

    def _update_learner_progress(self, learner_id: str, skill_scores: Dict[str, Any]) -> None:
        try:
            # Defensive: convert list-type skill_scores to dict
            if skill_scores is None:
                skill_scores = {}
            elif isinstance(skill_scores, list):
                try:
                    skill_scores = {k['skill_id']: k for k in skill_scores if isinstance(k, dict) and 'skill_id' in k}
                except Exception:
                    self.logger.log_error('scoring', 'Malformed skill_scores list; cannot convert to dict', str(skill_scores))
            if not isinstance(skill_scores, dict):
                skill_scores = {}
            for skill_id, skill_score in skill_scores.items():
                if hasattr(skill_score, 'cumulative_score'):
                    from learner_manager import SkillProgress
                    progress = SkillProgress(
                        skill_id=skill_id,
                        learner_id=learner_id,
                        skill_name=getattr(skill_score, 'skill_name', skill_id),
                        cumulative_score=skill_score.cumulative_score,
                        total_adjusted_evidence=getattr(skill_score, 'total_evidence', 0.0),
                        activity_count=getattr(skill_score, 'activity_count', 1),
                        gate_1_status=getattr(skill_score, 'gate_1_status', 'unknown'),
                        gate_2_status=getattr(skill_score, 'gate_2_status', 'unknown'),
                        overall_status=getattr(skill_score, 'overall_status', 'unknown'),
                        confidence_interval_lower=getattr(skill_score, 'confidence_lower', None),
                        confidence_interval_upper=getattr(skill_score, 'confidence_upper', None),
                        standard_error=getattr(skill_score, 'standard_error', None),
                        last_updated=datetime.now(timezone.utc).isoformat()
                    )
                    self.learner_manager.update_skill_progress(progress)
        except Exception as e:
            self.logger.log_error('evaluation_pipeline', f'Failed to update learner progress: {str(e)}', str(e))

    def _save_evaluation_record(self, activity_id: str, learner_id: str, 
                               activity_transcript: Dict[str, Any], evaluation_results: Dict[str, Any]) -> None:
        try:
            record = ActivityRecord(
                activity_id=activity_id,
                learner_id=learner_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                evaluation_result=evaluation_results,
                activity_transcript=activity_transcript,
                scored=True
            )
            self.learner_manager.add_activity_record(record)
        except Exception as e:
            self.logger.log_error('evaluation_pipeline', f'Failed to save evaluation record: {str(e)}', str(e))

    def _validate_rubric_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.log_debug('rubric_validation', f"Validating rubric result: {json.dumps(result, indent=2)}")
        if isinstance(result, str):
            try:
                result = json.loads(result)
                self.logger.log_debug('rubric_validation', "Parsed string result to JSON")
            except json.JSONDecodeError as e:
                self.logger.log_error('json_parse_error', f"Failed to parse rubric result as JSON: {str(e)}", 'rubric_validation')
                raise ValueError(f"Invalid JSON in rubric result: {str(e)}")
        
        # Handle new schema format with aspects array
        if 'aspects' in result:
            # Validate aspects array
            aspects = result['aspects']
            if isinstance(aspects, list):
                validated_aspects = []
                for aspect in aspects:
                    if isinstance(aspect, dict):
                        validated_aspect = {
                            'aspect_name': aspect.get('aspect_name', 'Unknown Aspect'),
                            'aspect_score': aspect.get('aspect_score', 0.5),
                            'scoring_reasoning': aspect.get('scoring_reasoning', 'No rationale provided')
                        }
                        # Ensure score is valid
                        score = validated_aspect['aspect_score']
                        if isinstance(score, str):
                            try:
                                score = float(score)
                                validated_aspect['aspect_score'] = score
                            except ValueError:
                                validated_aspect['aspect_score'] = 0.5
                        if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
                            validated_aspect['aspect_score'] = 0.5
                        validated_aspects.append(validated_aspect)
                result['aspects'] = validated_aspects
            else:
                result['aspects'] = []
        
        # Handle component_score
        if 'component_score' not in result:
            # Calculate from aspects if available
            if 'aspects' in result and isinstance(result['aspects'], list) and len(result['aspects']) > 0:
                total_score = sum(aspect.get('aspect_score', 0) for aspect in result['aspects'])
                result['component_score'] = total_score / len(result['aspects'])
            else:
                result['component_score'] = 0.5
        
        # Validate component_score
        component_score = result['component_score']
        if isinstance(component_score, str):
            try:
                component_score = float(component_score)
                result['component_score'] = component_score
            except ValueError:
                result['component_score'] = 0.5
        if not isinstance(component_score, (int, float)) or not 0.0 <= component_score <= 1.0:
            result['component_score'] = 0.5
        
        # Handle scoring_rationale
        if 'scoring_rationale' not in result:
            result['scoring_rationale'] = "Evaluation completed with comprehensive assessment"
        
        self.logger.log_debug('rubric_validation', f"Validation successful. Final result: {json.dumps(result, indent=2)}")
        return result

    def _validate_combined_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.log_debug('combined_validation', f"Validating combined result: {json.dumps(result, indent=2)}")
        if isinstance(result, str):
            try:
                result = json.loads(result)
                self.logger.log_debug('combined_validation', "Parsed string result to JSON")
            except json.JSONDecodeError as e:
                self.logger.log_error('json_parse_error', f"Failed to parse combined result as JSON: {str(e)}", 'combined_validation')
                raise ValueError(f"Invalid JSON in combined result: {str(e)}")
        
        # Validate aspect_scores
        if 'aspect_scores' not in result:
            result['aspect_scores'] = []
        elif not isinstance(result['aspect_scores'], list):
            result['aspect_scores'] = []
        
        # Validate overall_score
        if 'overall_score' not in result:
            result['overall_score'] = 0.5
        elif not isinstance(result['overall_score'], (int, float)):
            result['overall_score'] = 0.5
        else:
            result['overall_score'] = max(0.0, min(1.0, float(result['overall_score'])))
        
        # Validate rationale
        if 'rationale' not in result:
            result['rationale'] = 'Default evaluation rationale'
        
        # Validate validity_modifier
        if 'validity_modifier' not in result:
            result['validity_modifier'] = 1.0
        elif not isinstance(result['validity_modifier'], (int, float)):
            result['validity_modifier'] = 1.0
        else:
            result['validity_modifier'] = max(0.0, min(1.0, float(result['validity_modifier'])))
        
        # Validate validity_analysis
        if 'validity_analysis' not in result:
            result['validity_analysis'] = 'Default validity analysis'
        
        # Validate optional fields
        if 'validity_reason' not in result:
            result['validity_reason'] = 'Default validity reason'
        if 'evidence_quality' not in result:
            result['evidence_quality'] = 'Default evidence quality'
        if 'assistance_impact' not in result:
            result['assistance_impact'] = 'Default assistance impact'
        if 'evidence_volume_assessment' not in result:
            result['evidence_volume_assessment'] = 'Default evidence volume assessment'
        if 'assessment_confidence' not in result:
            result['assessment_confidence'] = 'Low'
        if 'key_observations' not in result:
            result['key_observations'] = ['Default observations']
        elif not isinstance(result['key_observations'], list):
            result['key_observations'] = ['Invalid observations format']
        
        self.logger.log_debug('combined_validation', f"Validation successful. Final result: {json.dumps(result, indent=2)}")
        return result

    def _validate_validity_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.log_debug('validity_validation', f"Validating validity result: {json.dumps(result, indent=2)}")
        if isinstance(result, str):
            try:
                result = json.loads(result)
                self.logger.log_debug('validity_validation', "Parsed string result to JSON")
            except json.JSONDecodeError as e:
                self.logger.log_error('json_parse_error', f"Failed to parse validity result as JSON: {str(e)}", 'validity_validation')
                raise ValueError(f"Invalid JSON in validity result: {str(e)}")
        
        # Handle validity_modifier
        if 'validity_modifier' not in result:
            result['validity_modifier'] = 1.0
        
        # Validate validity_modifier
        validity_modifier = result['validity_modifier']
        if isinstance(validity_modifier, str):
            try:
                validity_modifier = float(validity_modifier)
                result['validity_modifier'] = validity_modifier
            except ValueError:
                result['validity_modifier'] = 1.0
        if not isinstance(validity_modifier, (int, float)) or not 0.0 <= validity_modifier <= 1.0:
            result['validity_modifier'] = 1.0
        
        # Handle rationale
        if 'rationale' not in result:
            result['rationale'] = "Validity assessment completed"
        
        # Handle assistance_impact_analysis
        if 'assistance_impact_analysis' not in result:
            result['assistance_impact_analysis'] = {
                'overall_impact_level': 'minimal',
                'total_assistance_events': 0,
                'assistance_breakdown': {}
            }
        
        assistance = result['assistance_impact_analysis']
        if not isinstance(assistance, dict):
            assistance = {}
            result['assistance_impact_analysis'] = assistance
        
        if 'overall_impact_level' not in assistance:
            assistance['overall_impact_level'] = 'minimal'
        if 'total_assistance_events' not in assistance:
            assistance['total_assistance_events'] = 0
        if 'assistance_breakdown' not in assistance:
            assistance['assistance_breakdown'] = {}
        
        self.logger.log_debug('validity_validation', f"Validation successful. Final result: {json.dumps(result, indent=2)}")
        return result

    def _validate_diagnostic_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        # Defensive: ensure result is a dictionary
        if not isinstance(result, dict):
            self.logger.log_error('diagnostic_validation', f"Expected dict but got {type(result)}: {result}")
            # Return a minimal valid structure
            return {
                'diagnostic_intelligence': {
                    'strength_areas': [],
                    'improvement_areas': [],
                    'subskill_performance': []
                }
            }
        
        # Handle new schema format
        if 'diagnostic_intelligence' not in result:
            result['diagnostic_intelligence'] = {}
        
        diagnostic = result['diagnostic_intelligence']
        if not isinstance(diagnostic, dict):
            diagnostic = {}
            result['diagnostic_intelligence'] = diagnostic
        
        # Handle missing fields gracefully
        if 'strength_areas' not in diagnostic:
            diagnostic['strength_areas'] = []
        if 'improvement_areas' not in diagnostic:
            diagnostic['improvement_areas'] = []
        if 'subskill_performance' not in diagnostic:
            diagnostic['subskill_performance'] = []
        
        return result

    def _validate_trend_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        # Defensive: ensure result is a dictionary
        if not isinstance(result, dict):
            self.logger.log_error('trend_validation', f"Expected dict but got {type(result)}: {result}")
            return {'trend_analysis': {'performance_trajectory': {'direction': 'stable'}}}
        
        # Handle new schema format
        if 'trend_analysis' not in result:
            result['trend_analysis'] = {}
        
        trend_analysis = result['trend_analysis']
        if not isinstance(trend_analysis, dict):
            trend_analysis = {}
            result['trend_analysis'] = trend_analysis
        
        # Ensure performance_trajectory exists
        if 'performance_trajectory' not in trend_analysis:
            trend_analysis['performance_trajectory'] = {
                'direction': 'stable',
                'magnitude': 'minimal',
                'confidence': 0.5,
                'trajectory_description': 'No trend data available'
            }
        
        # Ensure historical_patterns exists
        if 'historical_patterns' not in trend_analysis:
            trend_analysis['historical_patterns'] = {
                'consistent_strengths': [],
                'recurring_challenges': []
            }
        
        # Ensure historical_performance exists
        if 'historical_performance' not in trend_analysis:
            trend_analysis['historical_performance'] = {
                'activity_count': 0,
                'performance_summary': 'No historical data available'
            }
        
        return result

    def _validate_feedback_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        # Defensive: ensure result is a dictionary
        if not isinstance(result, dict):
            self.logger.log_error('feedback_validation', f"Expected dict but got {type(result)}: {result}")
            return {
                'feedback_generation': {
                    'performance_summary': {
                        'overall_assessment': 'Evaluation completed',
                        'key_strengths': [],
                        'primary_opportunities': [],
                        'achievement_highlights': []
                    },
                    'actionable_guidance': {
                        'immediate_next_steps': [],
                        'recommendations': []
                    }
                }
            }
        
        # Handle new schema format
        if 'feedback_generation' not in result:
            result['feedback_generation'] = {}
        
        feedback_gen = result['feedback_generation']
        if not isinstance(feedback_gen, dict):
            feedback_gen = {}
            result['feedback_generation'] = feedback_gen
        
        # Ensure performance_summary exists
        if 'performance_summary' not in feedback_gen:
            feedback_gen['performance_summary'] = {
                'overall_assessment': 'Evaluation completed',
                'key_strengths': [],
                'primary_opportunities': [],
                'achievement_highlights': []
            }
        
        # Ensure actionable_guidance exists
        if 'actionable_guidance' not in feedback_gen:
            feedback_gen['actionable_guidance'] = {
                'immediate_next_steps': [],
                'recommendations': []
            }
        
        return result

    def _validate_intelligent_feedback_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        # Defensive: ensure result is a dictionary
        if not isinstance(result, dict):
            self.logger.log_error('intelligent_feedback_validation', f"Expected dict but got {type(result)}: {result}")
            return {
                'intelligent_feedback': {
                    'backend_intelligence': {
                        'overview': 'Analysis unavailable',
                        'strengths': ['Analysis unavailable'],
                        'weaknesses': ['Analysis unavailable'],
                        'subskill_ratings': []
                    },
                    'learner_feedback': {
                        'overall': 'Analysis unavailable',
                        'strengths': ['Analysis unavailable'],
                        'opportunities': ['Analysis unavailable']
                    }
                }
            }
        
        # Handle new schema format
        if 'intelligent_feedback' not in result:
            result['intelligent_feedback'] = {}
        
        intelligent_feedback = result['intelligent_feedback']
        if not isinstance(intelligent_feedback, dict):
            intelligent_feedback = {}
            result['intelligent_feedback'] = intelligent_feedback
        
        # Ensure backend_intelligence exists (for evaluation view)
        if 'backend_intelligence' not in intelligent_feedback:
            intelligent_feedback['backend_intelligence'] = {
                'overview': 'Analysis completed',
                'strengths': [],
                'weaknesses': [],
                'subskill_ratings': []
            }
        
        # Ensure learner_feedback exists (for both evaluation and learner views)
        if 'learner_feedback' not in intelligent_feedback:
            intelligent_feedback['learner_feedback'] = {
                'overall': 'Evaluation completed',
                'strengths': [],
                'opportunities': []
            }
        
        return result

    def _create_failed_result(self, activity_id: str, learner_id: str, timestamp: str, error: str) -> EvaluationResult:
        return EvaluationResult(
            activity_id=activity_id,
            learner_id=learner_id,
            evaluation_timestamp=timestamp,
            pipeline_phases=[],
            final_skill_scores={},
            overall_success=False,
            total_execution_time_ms=0,
            total_cost_estimate=0.0,
            error_summary=error
        )

    def restart_pipeline_from_phase(self, evaluation_result: EvaluationResult, 
                                  restart_phase: str) -> EvaluationResult:
        try:
            # Updated to reflect new pipeline structure
            valid_restart_phases = ['combined', 'scoring', 'intelligent_feedback', 'trend']
            if restart_phase not in valid_restart_phases:
                raise ValueError(f"Invalid restart phase: {restart_phase}. Must be one of {valid_restart_phases}")
            self.logger.log_system_event('evaluation_pipeline', 'pipeline_restart', 
                                       f'Restarting pipeline from {restart_phase}',
                                       {'activity_id': evaluation_result.activity_id, 
                                        'learner_id': evaluation_result.learner_id})
            return evaluation_result
        except Exception as e:
            self.logger.log_error('evaluation_pipeline', f'Pipeline restart failed: {str(e)}', str(e))
            return evaluation_result

    def get_pipeline_status(self, activity_id: str, learner_id: str) -> Dict[str, Any]:
        return {
            'pipeline_phases': [phase.value for phase in PipelinePhase],
            'rubric_required_types': list(self.rubric_required_types),
            'autoscored_types': list(self.autoscored_types),
            'max_retries': self.max_retries,
            'phase_timeout_seconds': self.phase_timeout_seconds,
            'modules_initialized': {
                'config_manager': self.config is not None,
                'llm_client': self.llm_client is not None,
                'prompt_builder': self.prompt_builder is not None,
                'scoring_engine': self.scoring_engine is not None,
                'learner_manager': self.learner_manager is not None,
                'activity_manager': self.activity_manager is not None
        }
        }

    def validate_pipeline_readiness(self, activity_id: str, learner_id: str) -> Dict[str, Any]:
        validation_results = {
            'ready': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        try:
            activity = self.activity_manager.get_activity(activity_id)
            if not activity:
                validation_results['errors'].append(f"Activity not found: {activity_id}")
                validation_results['ready'] = False
            else:
                validation_results['checks']['activity_loaded'] = True
                validation_results['checks']['activity_type'] = activity.activity_type
            learner = self.learner_manager.get_learner(learner_id)
            if not learner:
                validation_results['errors'].append(f"Learner not found: {learner_id}")
                validation_results['ready'] = False
            else:
                validation_results['checks']['learner_loaded'] = True
            llm_status = self.llm_client.get_provider_status()
            available_providers = [provider for provider, status in llm_status.items() if status.get('available')]
            if not available_providers:
                validation_results['errors'].append("No LLM providers available")
                validation_results['ready'] = False
            else:
                validation_results['checks']['available_providers'] = available_providers
            domain_model = self.config.get_domain_model()
            if not domain_model:
                validation_results['warnings'].append("Domain model not loaded")
            else:
                validation_results['checks']['domain_model_loaded'] = True
            thresholds = self.config.get_scoring_thresholds()
            if not thresholds:
                validation_results['warnings'].append("Scoring thresholds not configured")
            else:
                validation_results['checks']['scoring_thresholds'] = True
        except Exception as e:
            validation_results['errors'].append(f"Validation error: {str(e)}")
            validation_results['ready'] = False
        return validation_results

    def get_pipeline_statistics(self) -> Dict[str, Any]:
        try:
            eval_stats = self.logger.get_evaluation_stats()
            llm_stats = {
                'available_providers': list(self.llm_client.get_available_providers()),
                'provider_status': self.llm_client.get_provider_status()
            }
            activity_stats = self.activity_manager.get_activity_stats()
            learner_stats = self.learner_manager.get_database_stats()
            return {
                'evaluation_statistics': eval_stats,
                'llm_statistics': llm_stats,
                'activity_statistics': activity_stats,
                'learner_statistics': learner_stats,
                'pipeline_configuration': {
                    'rubric_required_types': list(self.rubric_required_types),
                    'autoscored_types': list(self.autoscored_types),
                    'max_retries': self.max_retries,
                    'phase_timeout_seconds': self.phase_timeout_seconds
                }
            }
        except Exception as e:
            self.logger.log_error('evaluation_pipeline', f'Failed to get pipeline statistics: {str(e)}', str(e))
            return {'error': str(e)}
        
    def run_pipeline_test(self, test_mode: str = 'connectivity') -> Dict[str, Any]:
        test_results = {
            'test_mode': test_mode,
            'overall_success': True,
            'test_results': {},
            'errors': []
        }
        try:
            if test_mode == 'connectivity':
                for provider in self.llm_client.get_available_providers():
                    try:
                        connection_test = self.llm_client.test_connection(provider)
                        test_results['test_results'][f'{provider}_connectivity'] = connection_test
                        if not connection_test.get('success'):
                            test_results['overall_success'] = False
                    except Exception as e:
                        test_results['test_results'][f'{provider}_connectivity'] = {'success': False, 'error': str(e)}
                        test_results['overall_success'] = False
            elif test_mode == 'prompt_validation':
                configurations = self.prompt_builder.get_available_configurations()
                for phase, activity_types in configurations.items():
                    for activity_type in activity_types:
                        try:
                            test_context = {
                                'activity_spec': {'activity_id': 'test', 'activity_type': activity_type},
                                'activity_transcript': {'learner_response': 'test response'},
                                'target_skill_context': {'skill_id': 'test_skill'}
                            }
                            if phase == 'rubric':
                                test_context['rubric_details'] = {'aspects': [{'name': 'test', 'weight': 1.0}]}
                            elif phase == 'validity':
                                test_context['assistance_log'] = []
                                test_context['response_analysis'] = {'word_count': 10}
                            enhanced_context = self.prompt_builder.prepare_context_data(test_context, phase)
                            config = self.prompt_builder.build_prompt(phase, activity_type, enhanced_context)
                            validation = self.prompt_builder.validate_prompt_configuration(config)
                            test_key = f'{activity_type}_{phase}_prompt'
                            test_results['test_results'][test_key] = {
                                'success': validation['valid'],
                                'errors': validation['errors'],
                                'warnings': validation['warnings']
                            }
                            if not validation['valid']:
                                test_results['overall_success'] = False
                        except Exception as e:
                            test_key = f'{activity_type}_{phase}_prompt'
                            test_results['test_results'][test_key] = {'success': False, 'error': str(e)}
                            test_results['overall_success'] = False
            elif test_mode == 'full_integration':
                test_results['test_results']['full_integration'] = {
                    'success': False,
                    'message': 'Full integration test not yet implemented'
                }
                test_results['overall_success'] = False
        except Exception as e:
            test_results['errors'].append(str(e))
            test_results['overall_success'] = False
        return test_results

    def create_evaluation_summary(self, evaluation_result: EvaluationResult) -> Dict[str, Any]:
        summary = {
            'evaluation_overview': {
                'activity_id': evaluation_result.activity_id,
                'learner_id': evaluation_result.learner_id,
                'timestamp': evaluation_result.evaluation_timestamp,
                'success': evaluation_result.overall_success,
                'total_time_seconds': evaluation_result.total_execution_time_ms / 1000,
                'estimated_cost': evaluation_result.total_cost_estimate
            },
            'phase_results': {},
            'skill_scores': {},
            'recommendations': [],
            'next_steps': []
        }
        try:
            # Defensive: convert list-type final_skill_scores to dict
            skill_scores = evaluation_result.final_skill_scores
            if skill_scores is None:
                skill_scores = {}
            elif isinstance(skill_scores, list):
                try:
                    skill_scores = {k['skill_id']: k for k in skill_scores if isinstance(k, dict) and 'skill_id' in k}
                except Exception:
                    self.logger.log_error('summary', 'Malformed final_skill_scores list; cannot convert to dict', str(skill_scores))
            if not isinstance(skill_scores, dict):
                skill_scores = {}
            # Summarize each phase
            for phase_result in evaluation_result.pipeline_phases:
                phase_summary = {
                    'success': phase_result.success,
                    'execution_time_ms': phase_result.execution_time_ms,
                    'tokens_used': phase_result.tokens_used,
                    'cost_estimate': phase_result.cost_estimate
                }
                if phase_result.error:
                    phase_summary['error'] = phase_result.error
                if phase_result.result:
                    if phase_result.phase == 'rubric_evaluation':
                        phase_summary['overall_score'] = phase_result.result.get('overall_score')
                        phase_summary['aspect_count'] = len(phase_result.result.get('aspect_scores', {}))
                    elif phase_result.phase == 'validity_analysis':
                        phase_summary['validity_modifier'] = phase_result.result.get('validity_modifier')
                    elif phase_result.phase == 'intelligent_feedback':
                        intelligent_data = phase_result.result.get('intelligent_feedback', {})
                        backend = intelligent_data.get('backend_intelligence', {})
                        feedback = intelligent_data.get('learner_feedback', {})
                        phase_summary['strengths_count'] = len(backend.get('strengths', []))
                        phase_summary['development_areas_count'] = len(backend.get('weaknesses', []))
                        phase_summary['has_feedback'] = bool(feedback.get('overall'))
                    elif phase_result.phase == 'trend_analysis':
                        phase_summary['performance_trajectory'] = phase_result.result.get('performance_trajectory')
                summary['phase_results'][phase_result.phase] = phase_summary
            # Summarize skill scores
            if skill_scores and isinstance(skill_scores, dict):
                try:
                    self.logger.log_debug('summary', f"Iterating skill_scores: type={type(skill_scores)}, value={repr(skill_scores)}")
                    for skill_id, skill_score in skill_scores.items():
                        if hasattr(skill_score, 'cumulative_score'):
                            summary['skill_scores'][skill_id] = {
                                'cumulative_score': skill_score.cumulative_score,
                                'gate_1_status': getattr(skill_score, 'gate_1_status', 'unknown'),
                                'gate_2_status': getattr(skill_score, 'gate_2_status', 'unknown'),
                                'overall_status': getattr(skill_score, 'overall_status', 'unknown'),
                                'evidence_volume': getattr(skill_score, 'total_evidence', 0.0)
                            }
                except Exception as e:
                    self.logger.log_error('summary', f'Failed to iterate skill_scores: {e}', str(skill_scores))
            # Extract recommendations from intelligent feedback and trend phases
            for phase_result in evaluation_result.pipeline_phases:
                if phase_result.success and phase_result.result:
                    if phase_result.phase == 'intelligent_feedback':
                        intelligent_data = phase_result.result.get('intelligent_feedback', {})
                        feedback = intelligent_data.get('learner_feedback', {})
                        # Extract opportunities as recommendations
                        opportunities = feedback.get('opportunities', '')
                        if opportunities:
                            summary['recommendations'].append(opportunities)
                        # Extract strengths as positive feedback
                        strengths = feedback.get('strengths', '')
                        if strengths:
                            summary['next_steps'].append(strengths)
            if not evaluation_result.overall_success:
                summary['error_information'] = {
                    'error_summary': evaluation_result.error_summary,
                    'failed_phases': [p.phase for p in evaluation_result.pipeline_phases if not p.success]
                }
        except Exception as e:
            summary['summary_generation_error'] = str(e)
            self.logger.log_error('evaluation_pipeline', f'Failed to create evaluation summary: {str(e)}', str(e))
        return summary

    def _parse_llm_response(self, response_content: Any) -> Dict[str, Any]:
        """Optimized JSON response parsing with better error handling"""
        try:
            if isinstance(response_content, str):
                # Clean the response content first
                content = response_content.strip()
                if not content:
                    raise ValueError("Empty response content")
                
                # Try to parse as JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown blocks
                    if content.startswith('```json') and content.endswith('```'):
                        json_content = content[7:-3].strip()
                        return json.loads(json_content)
                    elif content.startswith('```') and content.endswith('```'):
                        json_content = content[3:-3].strip()
                        return json.loads(json_content)
                    else:
                        raise ValueError(f"Invalid JSON format: {content[:100]}...")
            elif isinstance(response_content, dict):
                return response_content
            else:
                raise ValueError(f"Unexpected response type: {type(response_content)}")
                
        except Exception as e:
            self.logger.log_error('json_parse_error', f'Failed to parse LLM response: {e}. Content preview: {str(response_content)[:200]}', 'evaluation_pipeline')
            raise

    def _prepare_phase_specific_context(self, activity: ActivitySpec, learner, activity_transcript: Dict[str, Any], 
                                       learner_activities: List[ActivityRecord], phase: str, learner_id: str = None) -> Dict[str, Any]:
        """Prepare context data specific to each phase, avoiding redundant data loading"""
        
        # Core data used by most phases
        core_context = {
            'activity_spec': activity,
            'activity_transcript': activity_transcript
        }
        
        if phase == 'rubric':
            # Rubric evaluation needs: activity, transcript, skill context, domain model, rubric, leveling
            context = core_context.copy()
            target_skill = getattr(activity, 'target_skill', None)
            context.update({
                'target_skill_context': self._get_cached_skill_context(target_skill) if target_skill else {},
                'domain_model': self._get_cached_domain_model(),
                'rubric_details': getattr(activity, 'rubric', {}),
                'leveling_framework': self._get_cached_leveling_framework()
            })
            
        elif phase == 'validity':
            # Validity analysis needs: activity, transcript, assistance log, response analysis
            context = core_context.copy()
            context.update({
                'assistance_log': activity_transcript.get('assistance_provided', []),
                'response_analysis': self._analyze_response_characteristics(activity_transcript)
            })
            
        elif phase == 'diagnostic':
            # Diagnostic needs: activity, transcript, skill context, domain model, prerequisite relationships
            context = core_context.copy()
            target_skill = getattr(activity, 'target_skill', None)
            context.update({
                'target_skill_context': self._get_cached_skill_context(target_skill) if target_skill else {},
                'domain_model': self._get_cached_domain_model(),
                'prerequisite_relationships': self._get_cached_prerequisite_relationships(target_skill) if target_skill else {}
            })
            
        elif phase == 'trend':
            # Trend analysis needs: activity, transcript, historical data, temporal context
            context = core_context.copy()
            context.update({
                'historical_performance_data': self._get_cached_historical_data(learner_id, learner_activities),
                'temporal_context': self._get_cached_temporal_context(learner_id, learner_activities)
            })
            
        elif phase == 'combined':
            # Combined evaluation needs: activity, transcript, skill context, domain model, rubric, leveling, assistance log, response analysis
            context = core_context.copy()
            target_skill = getattr(activity, 'target_skill', None)
            context.update({
                'target_skill_context': self._get_cached_skill_context(target_skill) if target_skill else {},
                'domain_model': self._get_cached_domain_model(),
                'rubric_details': getattr(activity, 'rubric', {}),
                'leveling_framework': self._get_cached_leveling_framework(),
                'assistance_log': activity_transcript.get('assistance_provided', []),
                'response_analysis': self._analyze_response_characteristics(activity_transcript)
            })
            
        elif phase == 'intelligent_feedback':
            # Intelligent feedback needs: activity, transcript, skill context, domain model, prerequisite relationships, motivational context
            context = core_context.copy()
            target_skill = getattr(activity, 'target_skill', None)
            context.update({
                'target_skill_context': self._get_cached_skill_context(target_skill) if target_skill else {},
                'domain_model': self._get_cached_domain_model(),
                'prerequisite_relationships': self._get_cached_prerequisite_relationships(target_skill) if target_skill else {},
                'motivational_context': self._get_motivational_context(learner),
                'performance_context': {}
            })
            
        elif phase == 'feedback':
            # Feedback needs: activity, transcript, motivational context, performance context
            context = core_context.copy()
            context.update({
                'motivational_context': self._get_motivational_context(learner),
                'performance_context': {}
            })
            
        else:
            # Fallback to minimal context
            context = core_context.copy()
            
        return context

    def _prepare_phase_specific_context_with_results(self, base_context: Dict[str, Any], phase: str, 
                                                   previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for phases that need results from previous phases"""
        context = base_context.copy()
        
        if phase == 'diagnostic':
            # Add results from rubric and validity phases
            context.update({
                'rubric_evaluation_results': previous_results.get('rubric', {}),
                'validity_analysis_results': previous_results.get('validity', {})
            })
            
        elif phase == 'intelligent_feedback':
            # Add results from combined evaluation and scoring phases
            context.update({
                'rubric_evaluation_results': previous_results.get('phase_1a_rubric_evaluation', {}),
                'validity_analysis_results': previous_results.get('phase_1b_validity_analysis', {}),
                'scoring_results': previous_results.get('scoring', {}),
                'all_pipeline_results': previous_results
            })
            
        elif phase == 'trend':
            # Add results from intelligent feedback phase
            context.update({
                'current_diagnostic_results': previous_results.get('intelligent_feedback', {})
            })
            
        elif phase == 'feedback':
            # Add all previous results
            context.update({
                'all_pipeline_results': previous_results
            })
            
        return context

    def _get_cached_domain_model(self) -> Dict[str, Any]:
        """Get domain model with caching"""
        if self._domain_model_cache is None:
            self._domain_model_cache = self.config.get_domain_model()
        return self._domain_model_cache

    def _get_cached_leveling_framework(self) -> Dict[str, Any]:
        """Get leveling framework with caching"""
        if self._leveling_framework_cache is None:
            self._leveling_framework_cache = self._get_leveling_framework()
        return self._leveling_framework_cache

    def _get_cached_skill_context(self, skill_id: str) -> Dict[str, Any]:
        """Get skill context with caching"""
        if skill_id not in self._skill_context_cache:
            self._skill_context_cache[skill_id] = self._get_skill_context(skill_id)
        return self._skill_context_cache[skill_id]

    def _get_cached_prerequisite_relationships(self, skill_id: str) -> Dict[str, Any]:
        """Get prerequisite relationships with caching"""
        if skill_id not in self._prerequisite_cache:
            self._prerequisite_cache[skill_id] = self._get_prerequisite_relationships(skill_id)
        return self._prerequisite_cache[skill_id]

    def _get_cached_historical_data(self, learner_id: str, learner_activities: List[ActivityRecord]) -> Dict[str, Any]:
        """Get historical data with caching and summarization"""
        cache_key = f"{learner_id}_{len(learner_activities)}"
        
        if cache_key not in self._historical_data_cache:
            # Process and cache the historical data
            raw_data = self._prepare_historical_data(learner_activities)
            # Summarize the data to reduce payload size
            summarized_data = self._summarize_historical_data(raw_data)
            self._historical_data_cache[cache_key] = summarized_data
            
        return self._historical_data_cache[cache_key]

    def _get_cached_temporal_context(self, learner_id: str, learner_activities: List[ActivityRecord]) -> Dict[str, Any]:
        """Get temporal context with caching"""
        cache_key = f"{learner_id}_{len(learner_activities)}"
        
        if cache_key not in self._temporal_context_cache:
            self._temporal_context_cache[cache_key] = self._get_temporal_context(learner_activities)
            
        return self._temporal_context_cache[cache_key]

    def _summarize_historical_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize historical data to reduce payload size for LLM calls"""
        if not raw_data or raw_data.get('activity_count', 0) == 0:
            return raw_data
        
        # Keep essential summary data
        summarized = {
            'activity_count': raw_data.get('activity_count', 0),
            'date_range': raw_data.get('date_range', {}),
            'performance_summary': self._create_performance_summary(raw_data),
            'recent_trends': self._extract_recent_trends(raw_data),
            'activity_type_distribution': self._summarize_activity_types(raw_data)
        }
        
        return summarized

    def _create_performance_summary(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a performance summary from raw historical data"""
        score_trend = raw_data.get('score_trend', [])
        if not score_trend:
            return {'average_score': 0.0, 'trend_direction': 'stable', 'consistency': 'unknown'}
        
        # Calculate average score
        scores = [item.get('cumulative_score', 0.0) for item in score_trend]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Determine trend direction (simple linear trend)
        if len(scores) >= 2:
            recent_scores = scores[-3:]  # Last 3 scores
            if len(recent_scores) >= 2:
                if recent_scores[-1] > recent_scores[0]:
                    trend = 'improving'
                elif recent_scores[-1] < recent_scores[0]:
                    trend = 'declining'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        # Calculate consistency (standard deviation)
        if len(scores) >= 2:
            variance = sum((x - avg_score) ** 2 for x in scores) / len(scores)
            std_dev = variance ** 0.5
            if std_dev < 0.1:
                consistency = 'high'
            elif std_dev < 0.2:
                consistency = 'moderate'
            else:
                consistency = 'low'
        else:
            consistency = 'unknown'
        
        return {
            'average_score': round(avg_score, 3),
            'trend_direction': trend,
            'consistency': consistency,
            'total_activities': len(score_trend)
        }

    def _extract_recent_trends(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract recent performance trends (last 5 activities)"""
        score_trend = raw_data.get('score_trend', [])
        if not score_trend:
            return []
        
        # Get last 5 activities
        recent_activities = score_trend[-5:] if len(score_trend) > 5 else score_trend
        
        trends = []
        for activity in recent_activities:
            trends.append({
                'activity_id': activity.get('activity_id', 'unknown'),
                'skill_id': activity.get('skill_id', 'unknown'),
                'score': activity.get('cumulative_score', 0.0),
                'timestamp': activity.get('timestamp', 'unknown')
            })
        
        return trends

    def _summarize_activity_types(self, raw_data: Dict[str, Any]) -> Dict[str, int]:
        """Summarize activity type distribution"""
        activity_types = raw_data.get('activity_types', [])
        if not activity_types:
            return {}
        
        type_counts = {}
        for activity in activity_types:
            activity_type = activity.get('type', 'unknown')
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1
        
        return type_counts

    def _clear_historical_cache(self, learner_id: str):
        """Clear historical data cache for a specific learner when new data is added"""
        # Remove all cache entries for this learner
        keys_to_remove = [key for key in self._historical_data_cache.keys() if key.startswith(f"{learner_id}_")]
        for key in keys_to_remove:
            del self._historical_data_cache[key]
        
        # Also clear temporal context cache
        keys_to_remove = [key for key in self._temporal_context_cache.keys() if key.startswith(f"{learner_id}_")]
        for key in keys_to_remove:
            del self._temporal_context_cache[key]
        
        self.logger.log_debug('evaluation_pipeline', f'Cleared historical cache for learner: {learner_id}')