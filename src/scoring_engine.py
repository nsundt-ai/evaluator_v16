"""
Scoring Engine for Evaluator v16
Implements position-based decay Bayesian scoring with dual-gate system.
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from src.logger import get_logger

@dataclass
class SkillScore:
    """Individual skill scoring result"""
    skill_id: str
    skill_name: str
    cumulative_score: float
    total_adjusted_evidence: float
    activity_count: int
    gate_1_status: str  # passed, approaching, developing, needs_improvement
    gate_2_status: str  # passed, approaching, developing, needs_improvement
    overall_status: str  # mastered, approaching, developing, needs_improvement
    standard_error: float
    confidence_interval: Tuple[float, float]
    last_updated: str

@dataclass 
class ScoringResult:
    """Complete scoring result for an activity"""
    activity_id: str
    learner_id: str
    skill_scores: Dict[str, SkillScore]
    timestamp: str
    total_skills_evaluated: int
    skills_mastered: int
    overall_progress: float

class ScoringEngine:
    """Dual-gate scoring engine with position-based decay"""
    
    def __init__(self, config_manager=None, learner_manager=None):
        self.config_manager = config_manager
        self.learner_manager = learner_manager
        self.logger = get_logger()
        
        # Load scoring configuration
        if config_manager:
            self.scoring_config = config_manager.get_scoring_config()
            self.domain_model = config_manager.get_domain_model()
        else:
            self.scoring_config = self._get_default_scoring_config()
            self.domain_model = {}
        
        # Extract key parameters
        scoring_params = self.scoring_config.get('scoring_parameters', {})
        self.decay_factor = scoring_params.get('decay_factor', 0.9)
        self.prior_mean = scoring_params.get('prior_mean', 0.0)
        
        # Thresholds
        gate_thresholds = self.scoring_config.get('gate_thresholds', {})
        self.performance_thresholds = gate_thresholds.get('performance', {})
        self.evidence_thresholds = gate_thresholds.get('evidence', {})
    
    def score_activity(self, learner_history: Dict, new_evaluation: Dict) -> ScoringResult:
        """Score a new activity against learner's history"""
        learner_id = learner_history.get('learner_id')
        activity_id = new_evaluation.get('activity_id')
        
        self.logger.log_system_event('scoring_engine', 'scoring_started', f"Scoring activity {activity_id} for learner {learner_id}")
        
        # Get skills targeted by this activity
        targeted_skills = self._extract_targeted_skills(new_evaluation)
        
        # Score each skill
        skill_scores = {}
        for skill_id in targeted_skills:
            try:
                skill_score = self._score_individual_skill(
                    learner_history, 
                    skill_id, 
                    new_evaluation
                )
                skill_scores[skill_id] = skill_score
                
                # Add to activity history table
                self._add_activity_history_record(
                    learner_id, skill_id, new_evaluation, skill_score
                )
                
            except Exception as e:
                import traceback
                self.logger.log_error('scoring_engine', f"Error scoring skill {skill_id}: {str(e)}", str(e))
                self.logger.log_error('scoring_engine', f"Full traceback: {traceback.format_exc()}", traceback.format_exc())
                raise e
        
        # Calculate overall metrics
        total_skills = len(skill_scores)
        skills_mastered = sum(1 for score in skill_scores.values() if score.overall_status == 'mastered')
        overall_progress = skills_mastered / total_skills if total_skills > 0 else 0.0
        
        result = ScoringResult(
            activity_id=activity_id,
            learner_id=learner_id,
            skill_scores=skill_scores,
            timestamp=datetime.utcnow().isoformat(),
            total_skills_evaluated=total_skills,
            skills_mastered=skills_mastered,
            overall_progress=overall_progress
        )
        
        self.logger.log_system_event('scoring_engine', 'scoring_complete', f"Scoring complete: {skills_mastered}/{total_skills} skills mastered")
        
        return result
    
    def _score_individual_skill(self, learner_history: Dict, skill_id: str, 
                               new_evaluation: Dict) -> SkillScore:
        """Score individual skill using position-based decay Bayesian model"""
        
        # Get skill name from domain model
        skill_name = self._get_skill_name(skill_id)
        
        # Get historical activities for this skill
        historical_activities = self._get_historical_activities_for_skill(
            learner_history, skill_id
        )
        
        # Extract skill evaluation data from new activity
        new_skill_data = self._extract_skill_evaluation(new_evaluation, skill_id)
        
        # Combine historical and new activity data
        all_activities = historical_activities + [new_skill_data]
        all_activities.sort(key=lambda x: x['timestamp'])  # Ensure chronological order
        
        # Calculate cumulative score using position-based decay
        cumulative_score = self._calculate_cumulative_score(all_activities)
        
        # Calculate total adjusted evidence
        total_evidence = self._calculate_total_evidence(all_activities)
        
        # Determine gate statuses
        gate_1_status = self._determine_performance_gate_status(cumulative_score)
        gate_2_status = self._determine_evidence_gate_status(total_evidence)
        
        # Determine overall status
        overall_status = self._determine_overall_status(gate_1_status, gate_2_status)
        
        # Calculate confidence metrics
        standard_error = self._calculate_standard_error(all_activities)
        confidence_interval = self._calculate_confidence_interval(
            cumulative_score, standard_error
        )
        
        return SkillScore(
            skill_id=skill_id,
            skill_name=skill_name,
            cumulative_score=cumulative_score,
            total_adjusted_evidence=total_evidence,
            activity_count=len(all_activities),
            gate_1_status=gate_1_status,
            gate_2_status=gate_2_status,
            overall_status=overall_status,
            standard_error=standard_error,
            confidence_interval=confidence_interval,
            last_updated=datetime.utcnow().isoformat()
        )
    
    def _calculate_cumulative_score(self, activities: List[Dict]) -> float:
        """Calculate weighted average score with evidence-based decay"""
        if not activities:
            return self.prior_mean
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        # Process activities from most recent to oldest
        for i, activity in enumerate(activities):
            # Calculate adjusted evidence for this activity
            target_evidence = activity.get('target_evidence', 0.0)
            validity_modifier = activity.get('validity_modifier', 1.0)
            adjusted_evidence = target_evidence * validity_modifier
            
            # Calculate decay based on evidence accumulated SINCE this activity was completed
            # For the most recent activity (i=0), no evidence has accumulated since it was completed
            # For older activities, decay increases based on evidence accumulated since they were completed
            if i == 0:
                # Most recent activity: no decay
                evidence_based_decay = 1.0
            else:
                # Older activities: calculate evidence accumulated since this activity was completed
                evidence_accumulated_since = 0.0
                for j in range(i):
                    # Sum evidence from all activities that came after this one
                    older_activity = activities[j]
                    older_target_evidence = older_activity.get('target_evidence', 0.0)
                    older_validity_modifier = older_activity.get('validity_modifier', 1.0)
                    older_adjusted_evidence = older_target_evidence * older_validity_modifier
                    evidence_accumulated_since += older_adjusted_evidence
                
                # Apply decay based on evidence accumulated since this activity was completed
                evidence_based_decay = self.decay_factor ** evidence_accumulated_since
            
            # Weight for this activity: adjusted_evidence * evidence_based_decay
            weight = adjusted_evidence * evidence_based_decay
            
            # Update running sums
            weighted_sum += activity.get('performance_score', 0.0) * weight
            total_weight += weight
        
        if total_weight == 0:
            return self.prior_mean
        
        return weighted_sum / total_weight
    
    def _calculate_total_evidence(self, activities: List[Dict]) -> float:
        """Calculate total validity-adjusted evidence"""
        total_evidence = 0.0
        
        for activity in activities:
            target_evidence = activity.get('target_evidence', 0.0)
            validity_modifier = activity.get('validity_modifier', 1.0)
            
            adjusted_evidence = target_evidence * validity_modifier
            total_evidence += adjusted_evidence
        
        return total_evidence
    
    def _determine_performance_gate_status(self, score: float) -> str:
        """Determine Gate 1 (performance) status"""
        thresholds = self.performance_thresholds
        
        if score >= thresholds.get('at_level', 0.75):
            return 'passed'
        elif score >= thresholds.get('approaching', 0.65):
            return 'approaching'
        elif score >= thresholds.get('developing', 0.50):
            return 'developing'
        else:
            return 'needs_improvement'
    
    def _determine_evidence_gate_status(self, evidence: float) -> str:
        """Determine Gate 2 (evidence volume) status"""
        thresholds = self.evidence_thresholds
        
        if evidence >= thresholds.get('sufficient', 30.0):
            return 'passed'
        elif evidence >= thresholds.get('approaching', 20.0):
            return 'approaching'
        elif evidence >= thresholds.get('developing', 10.0):
            return 'developing'
        else:
            return 'needs_improvement'
    
    def _determine_overall_status(self, gate_1_status: str, gate_2_status: str) -> str:
        """Determine overall mastery status based on both gates"""
        # Both gates must be 'passed' for mastery
        if gate_1_status == 'passed' and gate_2_status == 'passed':
            return 'mastered'
        
        # Determine overall level based on the lower of the two gates
        status_hierarchy = ['needs_improvement', 'developing', 'approaching', 'passed']
        
        gate_1_level = status_hierarchy.index(gate_1_status)
        gate_2_level = status_hierarchy.index(gate_2_status)
        
        overall_level = min(gate_1_level, gate_2_level)
        overall_status = status_hierarchy[overall_level]
        
        # Convert 'passed' to 'approaching' if both gates aren't passed
        if overall_status == 'passed':
            overall_status = 'approaching'
        
        return overall_status
    
    def _calculate_standard_error(self, activities: List[Dict]) -> float:
        """Calculate Standard Error of Measurement"""
        if len(activities) < 2:
            return 0.15  # Default SEM for single activity
        
        # Simple SEM calculation: decreases with more activities and evidence
        n_activities = len(activities)
        total_evidence = sum(a.get('target_evidence', 0) for a in activities)
        
        # Base SEM that decreases with sample size and evidence
        base_sem = 0.20
        activity_factor = 1 / math.sqrt(n_activities)
        evidence_factor = 1 / math.sqrt(max(total_evidence, 1))
        
        sem = base_sem * activity_factor * evidence_factor
        
        # Cap between reasonable bounds
        return max(0.05, min(0.25, sem))
    
    def _calculate_confidence_interval(self, score: float, sem: float) -> Tuple[float, float]:
        """Calculate 95% confidence interval"""
        # 95% CI: ±1.96 * SEM
        margin = 1.96 * sem
        
        lower = max(0.0, score - margin)
        upper = min(1.0, score + margin)
        
        return (lower, upper)
    
    def _extract_targeted_skills(self, evaluation: Dict) -> List[str]:
        """Extract skills targeted by the activity"""
        # Look in various places for skill information
        skill_ids = []
        
        # Check evaluation results
        if 'evaluation_results' in evaluation:
            results = evaluation['evaluation_results']
            
            # Phase 1A - Rubric Evaluation
            if 'phase_1a_rubric_evaluation' in results:
                rubric_results = results['phase_1a_rubric_evaluation']
                skill_evaluations = rubric_results.get('skill_evaluations', {})
                # Defensive: ensure skill_evaluations is a dictionary
                if skill_evaluations and isinstance(skill_evaluations, dict):
                    skill_ids.extend(skill_evaluations.keys())
        
        # Check activity specification
        if 'activity_generation_output' in evaluation:
            activity_spec = evaluation['activity_generation_output']
            skills_targeted = activity_spec.get('skills_targeted', [])
            if skills_targeted:
                skill_ids.extend(skills_targeted)
        
        # Check for target_skill in activity spec
        if 'activity_generation_output' in evaluation:
            activity_spec = evaluation['activity_generation_output']
            target_skill = activity_spec.get('target_skill')
            if target_skill:
                if isinstance(target_skill, str):
                    skill_ids.append(target_skill)
                elif isinstance(target_skill, dict) and 'skill_id' in target_skill:
                    skill_ids.append(target_skill['skill_id'])
        
        # Check for target_skill at root level (from evaluation pipeline)
        if 'target_skill' in evaluation:
            target_skill = evaluation['target_skill']
            if target_skill:
                if isinstance(target_skill, str):
                    skill_ids.append(target_skill)
                elif isinstance(target_skill, dict) and 'skill_id' in target_skill:
                    skill_ids.append(target_skill['skill_id'])
        
        # If no skills found, use default
        if not skill_ids:
            skill_ids = ['S009']  # Default skill ID
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(skill_ids))
    
    def _extract_skill_evaluation(self, evaluation: Dict, skill_id: str) -> Dict:
        """Extract skill-specific evaluation data from activity"""
        skill_data = {
            'skill_id': skill_id,
            'timestamp': evaluation.get('timestamp', datetime.utcnow().isoformat()),
            'performance_score': 0.0,
            'target_evidence': 0.0,
            'validity_modifier': 1.0
        }
        
        # Extract from evaluation results - handle both old and new formats
        if 'evaluation_results' in evaluation:
            results = evaluation['evaluation_results']
            
            # First try to get data from combined evaluation (new format)
            if 'phase_1_combined_evaluation' in results:
                combined = results['phase_1_combined_evaluation']
                
                # Get performance score directly from combined result
                if 'overall_score' in combined:
                    skill_data['performance_score'] = float(combined['overall_score'])
                
                # Get validity modifier directly from combined result
                skill_data['validity_modifier'] = combined.get('validity_modifier', 1.0)
                
                # Get target evidence volume from combined result
                skill_data['target_evidence'] = combined.get('target_evidence_volume', 0.0)
            
            # Fallback to old separate phases format
            else:
                # Get performance score from Phase 1A
                if 'phase_1a_rubric_evaluation' in results:
                    rubric = results['phase_1a_rubric_evaluation']
                    skill_evaluations = rubric.get('skill_evaluations', {})
                    if skill_evaluations and skill_id in skill_evaluations:
                        skill_eval = skill_evaluations[skill_id]
                        skill_data['performance_score'] = skill_eval.get('numeric_score', 0.0)
                        skill_data['target_evidence'] = skill_eval.get('target_evidence', 0.0)
                
                # Get validity modifier from Phase 1B
                if 'phase_1b_validity_analysis' in results:
                    validity = results['phase_1b_validity_analysis']
                    skill_data['validity_modifier'] = validity.get('validity_modifier', 1.0)
        
        # Handle new pipeline format where results are in pipeline_phases
        elif 'pipeline_phases' in evaluation:
            phases = evaluation['pipeline_phases']
            
            # Look for combined_evaluation phase
            for phase in phases:
                if phase.get('phase') == 'combined_evaluation' and phase.get('success'):
                    result = phase.get('result', {})
                    
                    # Get performance score from combined evaluation
                    if 'overall_score' in result:
                        skill_data['performance_score'] = float(result['overall_score'])
                    
                    # Get validity modifier from combined evaluation
                    skill_data['validity_modifier'] = result.get('validity_modifier', 1.0)
                    
                    # Get target evidence volume from combined evaluation
                    skill_data['target_evidence'] = result.get('target_evidence_volume', 0.0)
                    break
            
            # If no combined_evaluation found, look for scoring phase
            if skill_data['performance_score'] == 0.0:
                for phase in phases:
                    if phase.get('phase') == 'scoring' and phase.get('success'):
                        result = phase.get('result', {})
                        
                        # Get performance score from scoring phase
                        if 'activity_score' in result:
                            skill_data['performance_score'] = float(result['activity_score'])
                        
                        # Get target evidence volume from scoring phase
                        skill_data['target_evidence'] = result.get('target_evidence_volume', 0.0)
                        
                        # Get validity modifier from scoring phase
                        skill_data['validity_modifier'] = result.get('validity_modifier', 1.0)
                        break
        
        # If no specific skill data found, try to get overall scores
        if skill_data['performance_score'] == 0.0:
            if 'evaluation_results' in evaluation:
                results = evaluation['evaluation_results']
                # Try combined evaluation first
                if 'phase_1_combined_evaluation' in results:
                    combined = results['phase_1_combined_evaluation']
                    if 'overall_score' in combined:
                        skill_data['performance_score'] = float(combined['overall_score'])
                # Fallback to old format
                elif 'phase_1a_rubric_evaluation' in results:
                    rubric = results['phase_1a_rubric_evaluation']
                    if 'overall_score' in rubric:
                        skill_data['performance_score'] = float(rubric['overall_score'])
                    if 'target_evidence_volume' in rubric:
                        skill_data['target_evidence'] = float(rubric['target_evidence_volume'])
            
            # Also check pipeline_phases format
            elif 'pipeline_phases' in evaluation:
                phases = evaluation['pipeline_phases']
                for phase in phases:
                    if phase.get('phase') == 'combined_evaluation' and phase.get('success'):
                        result = phase.get('result', {})
                        if 'overall_score' in result:
                            skill_data['performance_score'] = float(result['overall_score'])
                        break
        
        # Also check for target evidence volume at the root level (from evaluation pipeline)
        if skill_data['target_evidence'] == 0.0 and 'target_evidence_volume' in evaluation:
            skill_data['target_evidence'] = float(evaluation['target_evidence_volume'])
        
        return skill_data
    
    def _get_historical_activities_for_skill(self, learner_history: Dict, 
                                           skill_id: str) -> List[Dict]:
        """Get historical activities that evaluated this skill"""
        historical_activities = []
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
                        'cumulative_evidence_weight': record['cumulative_evidence_weight'],
                        'decay_factor': record['decay_factor']
                    })
                return historical_activities
            except Exception as e:
                self.logger.log_error('scoring_engine', f"Failed to get historical activities from database: {str(e)}", str(e))
        
        # Fallback to learner_history dictionary
        activities = learner_history.get('activities', [])
        
        for activity in activities:
            # Skip if not scored yet
            if not activity.get('scored', False):
                continue
            
            # Extract skill data from this historical activity
            skill_data = self._extract_skill_evaluation(activity, skill_id)
            
            # Only include if this skill was actually evaluated
            if skill_data['target_evidence'] > 0:
                historical_activities.append(skill_data)
        
        return historical_activities
    
    def _get_skill_name(self, skill_id: str) -> str:
        """Get human-readable skill name from domain model"""
        competencies = self.domain_model.get('competencies', {})
        
        # Defensive: ensure competencies is a dictionary
        if not isinstance(competencies, dict):
            competencies = {}
        
        for competency_id, competency_data in competencies.items():
            skills = competency_data.get('skills', {})
            if skill_id in skills:
                return skills[skill_id].get('name', skill_id)
        
        return skill_id  # Fallback to ID if name not found
    
    def update_learner_progress(self, learner_history: Dict, 
                               scoring_result: ScoringResult, 
                               learner_manager=None) -> Dict:
        """Update learner's skill progress with new scores"""
        # Ensure skill_progress exists
        if 'skill_progress' not in learner_history:
            learner_history['skill_progress'] = {}
        
        skill_progress = learner_history['skill_progress']
        
        # Defensive: ensure skill_scores is a dict
        skill_scores = scoring_result.skill_scores
        if isinstance(skill_scores, list):
            # Convert list to dict if possible
            try:
                skill_scores = {k['skill_id']: k for k in skill_scores if isinstance(k, dict) and 'skill_id' in k}
            except Exception:
                self.logger.log_error('scoring_engine', f"Malformed skill_scores list in scoring result: {skill_scores}", str(skill_scores))
                skill_scores = {}
        elif not isinstance(skill_scores, dict):
            skill_scores = {}
            
        # Update each skill
        for skill_id, skill_score in skill_scores.items():
            skill_progress[skill_id] = {
                'skill_name': skill_score.skill_name,
                'cumulative_score': skill_score.cumulative_score,
                'total_adjusted_evidence': skill_score.total_adjusted_evidence,
                'activity_count': skill_score.activity_count,
                'gate_1_status': skill_score.gate_1_status,
                'gate_2_status': skill_score.gate_2_status,
                'overall_status': skill_score.overall_status,
                'standard_error': skill_score.standard_error,
                'confidence_interval': skill_score.confidence_interval,
                'last_updated': skill_score.last_updated
            }
            
            # Update database if learner_manager is provided
            if learner_manager:
                try:
                    from learner_manager import SkillProgress
                    progress = SkillProgress(
                        skill_id=skill_id,
                        learner_id=scoring_result.learner_id,
                        skill_name=skill_score.skill_name,
                        cumulative_score=skill_score.cumulative_score,
                        total_adjusted_evidence=skill_score.total_adjusted_evidence,
                        activity_count=skill_score.activity_count,
                        gate_1_status=skill_score.gate_1_status,
                        gate_2_status=skill_score.gate_2_status,
                        overall_status=skill_score.overall_status,
                        confidence_interval_lower=skill_score.confidence_interval[0] if skill_score.confidence_interval else None,
                        confidence_interval_upper=skill_score.confidence_interval[1] if skill_score.confidence_interval else None,
                        standard_error=skill_score.standard_error,
                        last_updated=skill_score.last_updated
                    )
                    learner_manager.update_skill_progress(progress)
                except Exception as e:
                    self.logger.log_error('scoring_engine', f"Failed to update skill progress in database for skill {skill_id}: {str(e)}", str(e))
        
        # Update learner metadata
        learner_history['last_updated'] = datetime.utcnow().isoformat()
        
        return learner_history
    
    def get_skill_progress_summary(self, learner_history: Dict) -> Dict[str, Any]:
        """Get summary of learner's skill progress"""
        skill_progress = learner_history.get('skill_progress', {})
        
        if not skill_progress:
            return {
                'total_skills': 0,
                'skills_mastered': 0,
                'skills_approaching': 0,
                'skills_developing': 0,
                'skills_needs_improvement': 0,
                'overall_progress': 0.0,
                'average_score': 0.0
            }
        
        status_counts = {
            'mastered': 0,
            'approaching': 0,
            'developing': 0,
            'needs_improvement': 0
        }
        
        total_score = 0.0
        
        for skill_data in skill_progress.values():
            status = skill_data.get('overall_status', 'needs_improvement')
            status_counts[status] = status_counts.get(status, 0) + 1
            total_score += skill_data.get('cumulative_score', 0.0)
        
        total_skills = len(skill_progress)
        average_score = total_score / total_skills if total_skills > 0 else 0.0
        overall_progress = status_counts['mastered'] / total_skills if total_skills > 0 else 0.0
        
        return {
            'total_skills': total_skills,
            'skills_mastered': status_counts['mastered'],
            'skills_approaching': status_counts['approaching'],
            'skills_developing': status_counts['developing'],
            'skills_needs_improvement': status_counts['needs_improvement'],
            'overall_progress': overall_progress,
            'average_score': average_score
        }
    
    def _get_default_scoring_config(self) -> Dict[str, Any]:
        """Get default scoring configuration"""
        return {
            "algorithm": {
                "type": "position_based_decay",
                "decay_factor": 0.9,
                "prior_mean": 0.0
            },
            "thresholds": {
                "performance": {
                    "at_level": 0.75,
                    "approaching": 0.65,
                    "developing": 0.50
                },
                "evidence": {
                    "sufficient": 30.0,
                    "approaching": 20.0,
                    "developing": 10.0
                }
            }
        }

    def _add_activity_history_record(self, learner_id: str, skill_id: str, 
                                    evaluation: Dict, skill_score: SkillScore):
        """Add new row to activity history table with evidence-based decay"""
        try:
            # Extract data from evaluation
            skill_data = self._extract_skill_evaluation(evaluation, skill_id)
            
            # Get activity metadata
            activity_id = evaluation.get('activity_id', 'unknown')
            completion_timestamp = evaluation.get('timestamp', datetime.utcnow().isoformat())
            activity_type = evaluation.get('activity_type', 'Unknown')
            activity_title = evaluation.get('activity_title', 'Unknown Activity')
            
            # Calculate adjusted evidence
            adjusted_evidence = skill_data['target_evidence'] * skill_data['validity_modifier']
            
            # Get cumulative evidence weight from previous activities (BEFORE adding current activity)
            # This ensures we don't include the current activity in the cumulative calculation
            cumulative_evidence_weight = self._get_cumulative_evidence_weight(learner_id, skill_id)
            
            # Store the actual decay factor from settings (not the calculated decay)
            # The decay factor for this activity is the current setting value
            current_decay_factor = self.decay_factor
            
            # Calculate evidence-based decay for this specific activity
            # For the CURRENT activity (most recent), it should have the LEAST decay
            # The decay is based on how much evidence has accumulated since this activity was completed
            # Since this is the current activity, no evidence has accumulated since it was completed, so decay = 1.0
            evidence_based_decay = 1.0  # Current activity has no decay
            
            # Calculate decay-adjusted evidence volume for this activity
            decay_adjusted_evidence = adjusted_evidence * evidence_based_decay
            
            # For cumulative performance, we need to calculate it based on all activities up to this point
            # including the current activity
            all_activities_up_to_now = self._get_historical_activities_for_skill(
                {'learner_id': learner_id, 'activities': []}, skill_id
            )
            
            # Get activities in chronological order for cumulative calculation
            if hasattr(self, 'learner_manager') and self.learner_manager:
                chronological_activities = self.learner_manager.get_activity_history_chronological(learner_id, skill_id)
                # Convert to the format expected by _calculate_cumulative_score
                all_activities_up_to_now = []
                for record in chronological_activities:
                    all_activities_up_to_now.append({
                        'target_evidence': record['target_evidence_volume'],
                        'validity_modifier': record['validity_modifier'],
                        'performance_score': record['performance_score'],
                        'cumulative_evidence_weight': record['cumulative_evidence_weight'],
                        'timestamp': record['completion_timestamp']
                    })
            
            # Add current activity to the list for cumulative calculation
            current_activity_data = {
                'target_evidence': skill_data['target_evidence'],
                'validity_modifier': skill_data['validity_modifier'],
                'performance_score': skill_data['performance_score'],
                'cumulative_evidence_weight': cumulative_evidence_weight,
                'timestamp': completion_timestamp
            }
            all_activities_up_to_now.append(current_activity_data)
            
            # Calculate cumulative performance at this point in time
            cumulative_performance_at_time = self._calculate_cumulative_score(all_activities_up_to_now)
            
            # Add to database if learner_manager is available
            if hasattr(self, 'learner_manager') and self.learner_manager:
                # For the first activity, cumulative evidence should equal adjusted evidence
                # For subsequent activities, it should be the sum of all previous adjusted evidence
                # If cumulative_evidence_weight is 0, this is the first activity
                if cumulative_evidence_weight == 0.0:
                    cumulative_evidence = adjusted_evidence
                else:
                    cumulative_evidence = cumulative_evidence_weight + adjusted_evidence
                
                self.learner_manager.add_activity_history_record(
                    learner_id=learner_id,
                    activity_id=activity_id,
                    skill_id=skill_id,
                    completion_timestamp=completion_timestamp,
                    activity_type=activity_type,
                    activity_title=activity_title,
                    performance_score=skill_data['performance_score'],
                    target_evidence_volume=skill_data['target_evidence'],
                    validity_modifier=skill_data['validity_modifier'],
                    adjusted_evidence_volume=adjusted_evidence,
                    cumulative_evidence_weight=decay_adjusted_evidence,  # Store decay-adjusted evidence as evidence weight
                    decay_factor=current_decay_factor,  # Store the actual decay factor from settings
                    decay_adjusted_evidence_volume=decay_adjusted_evidence,
                    cumulative_performance=cumulative_performance_at_time,  # Cumulative at this point in time
                    cumulative_evidence=cumulative_evidence,
                    evaluation_result=evaluation,
                    activity_transcript=evaluation.get('activity_transcript', {})
                )
            
        except Exception as e:
            self.logger.log_error('scoring_engine', f"Failed to add activity history record: {str(e)}", str(e))

    def _get_cumulative_evidence_weight(self, learner_id: str, skill_id: str) -> float:
        """Get cumulative evidence weight for evidence-based decay calculation"""
        try:
            if hasattr(self, 'learner_manager') and self.learner_manager:
                # Get all previous activities for this skill (excluding current activity)
                # For the first activity, this should return 0.0
                activities = self.learner_manager.get_activity_history_for_learner_skill(learner_id, skill_id)
                
                # Calculate cumulative evidence weight from previous activities only
                # This should be the sum of all activities that were completed BEFORE the current activity
                cumulative_weight = 0.0
                for activity in activities:
                    adjusted_evidence = activity.get('adjusted_evidence_volume', 0.0)
                    cumulative_weight += adjusted_evidence
                
                return cumulative_weight
            return 0.0
        except Exception as e:
            self.logger.log_error('scoring_engine', f"Failed to get cumulative evidence weight: {str(e)}", str(e))
            return 0.0

    def update_configuration(self, config_manager=None):
        """Update the scoring engine configuration dynamically"""
        if config_manager:
            self.config_manager = config_manager
            self.scoring_config = config_manager.get_scoring_config()
            self.domain_model = config_manager.get_domain_model()
        
        # Extract key parameters
        scoring_params = self.scoring_config.get('scoring_parameters', {})
        self.decay_factor = scoring_params.get('decay_factor', 0.9)
        self.prior_mean = scoring_params.get('prior_mean', 0.0)
        
        # Thresholds
        gate_thresholds = self.scoring_config.get('gate_thresholds', {})
        self.performance_thresholds = gate_thresholds.get('performance', {})
        self.evidence_thresholds = gate_thresholds.get('evidence', {})
        
        self.logger.log_system_event('scoring_engine', 'configuration_updated', 
                                   f'Updated decay_factor to {self.decay_factor}')

    def recalculate_all_activities_with_new_decay(self, learner_id: str = None):
        """
        Recalculate all existing activities with the current decay factor.
        This applies the new decay factor retroactively to all activities.
        
        Args:
            learner_id: Optional specific learner ID. If None, recalculates for all learners.
        """
        try:
            if not hasattr(self, 'learner_manager') or not self.learner_manager:
                self.logger.log_error('scoring_engine', 'Learner manager not available for recalculation', 'missing_learner_manager')
                return False
            
            # Get all learners if specific learner not provided
            if learner_id:
                learners = [self.learner_manager.get_learner(learner_id)]
                if not learners[0]:
                    self.logger.log_error('scoring_engine', f'Learner not found: {learner_id}', 'learner_not_found')
                    return False
            else:
                learners = self.learner_manager.list_learners()
            
            total_updated = 0
            
            for learner in learners:
                if not learner:
                    continue
                    
                # Get all skills for this learner
                skill_progress = self.learner_manager.get_skill_progress(learner.learner_id)
                
                for skill_id in skill_progress.keys():
                    # Get all activities for this skill in chronological order
                    activities = self.learner_manager.get_activity_history_chronological(learner.learner_id, skill_id)
                    
                    if not activities:
                        continue
                    
                    # Recalculate each activity with the new decay factor
                    # activities is in chronological order (oldest first), so we need to process in reverse
                    for i, activity in enumerate(activities):
                        # Calculate evidence accumulated since this activity was completed
                        evidence_accumulated_since = 0.0
                        
                        # Sum evidence from all activities that came AFTER this one (more recent activities)
                        # Since activities is chronological (oldest first), more recent activities have higher indices
                        for j in range(i + 1, len(activities)):
                            more_recent_activity = activities[j]
                            evidence_accumulated_since += more_recent_activity['adjusted_evidence_volume']
                        
                        # Calculate new decay-adjusted evidence
                        if i == len(activities) - 1:  # Most recent activity (last in chronological list)
                            evidence_based_decay = 1.0
                        else:
                            evidence_based_decay = self.decay_factor ** evidence_accumulated_since
                        
                        new_decay_adjusted_evidence = activity['adjusted_evidence_volume'] * evidence_based_decay
                        
                        # Update the database record
                        success = self.learner_manager.update_activity_decay_adjusted_evidence(
                            learner.learner_id,
                            activity['activity_id'],
                            skill_id,
                            new_decay_adjusted_evidence,
                            evidence_based_decay
                        )
                        
                        if success:
                            total_updated += 1
            
            self.logger.log_system_event('scoring_engine', 'retroactive_decay_recalculation',
                                       f'Recalculated decay for {total_updated} activities with decay factor {self.decay_factor}')
            return True
            
        except Exception as e:
            self.logger.log_error('scoring_engine', f'Failed to recalculate activities with new decay: {str(e)}', str(e))
            return False

# Utility functions
def create_scoring_engine(config_manager=None) -> ScoringEngine:
    """Factory function to create scoring engine"""
    return ScoringEngine(config_manager)

def score_activity_quick(learner_history: Dict, evaluation: Dict) -> ScoringResult:
    """Utility function for quick scoring"""
    engine = ScoringEngine()
    return engine.score_activity(learner_history, evaluation)