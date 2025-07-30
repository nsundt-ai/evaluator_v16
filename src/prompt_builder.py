"""
Evaluator v16 - Prompt Builder Module

Handles dynamic assembly of the 23 distinct prompt configurations for the evaluation pipeline.
Includes proper variable substitution, context integration, and validation.

Author: Generated for Evaluator v16 Project
Version: 1.0.0
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from pathlib import Path

from config_manager import ConfigManager
from logger import get_logger


@dataclass
class PromptConfiguration:
    """Complete prompt configuration for LLM calls"""
    phase_name: str
    activity_type: str
    system_prompt: str
    user_prompt: str
    output_schema: Dict[str, Any]
    llm_config: Dict[str, Any]
    validation_rules: List[str]


class PromptBuilder:
    """
    Assembles dynamic prompts for all 23 evaluation configurations.
    Handles variable substitution, context integration, and template validation.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize PromptBuilder with configuration and templates.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = get_logger()
        self.domain_model = self.config.get_domain_model()
        
        # Load prompt templates and components
        self._init_prompt_components()
        self._init_prompt_templates()
        self._init_llm_configurations()
        self._init_output_schemas()
        
        # Valid phases and types
        self.valid_phases = {'combined', 'rubric', 'validity', 'diagnostic', 'trend', 'feedback', 'intelligent_feedback'}
        self.valid_activity_types = {'CR', 'COD', 'RP', 'SR', 'BR'}
        self.rubric_required_types = {'CR', 'COD', 'RP'}
        
        self.logger.log_system_event('prompt_builder', 'initialized', 
                                    'Prompt builder initialized with 23 configurations')

    def _init_prompt_components(self) -> None:
        """Initialize reusable prompt components"""
        self.prompt_components = {
                            'universal': {
                    'system_role': """You are an expert educational evaluator. Provide precise, evidence-based evaluations for competency assessment.""",
                    
                    'evaluation_philosophy': """EVALUATION PHILOSOPHY:
- Evidence-based assessment tied to learning objectives
- Consistency and fairness across evaluations
- Actionable insights for learner growth
- Balance rigor with developmental support""",
                    
                    'domain_focus': """DOMAIN FOCUS:
Professional skill development framework:
- COMPETENCIES: Top-level areas (C001-C004)
- SKILLS: Specific components (S001-S016) 
- SUBSKILLS: Granular elements (SS001-SS055)""",
                    
                    'single_skill_focus': """SINGLE SKILL FOCUS:
Each evaluation targets ONE primary skill with its component subskills.""",
                    
                    'critical_guidelines': """CRITICAL REQUIREMENTS:
- Output must be valid JSON format only
- All scores must be between 0.0 and 1.0
- Provide specific evidence for judgments
- Reference specific parts of learner responses""",
                    
                    'json_format_warning': """CRITICAL JSON OUTPUT REQUIREMENT:
Your response must be ONLY valid JSON. Begin with { and end with }. No text before or after."""
                },
            
            'phase_specific': {
                'rubric_evaluation': {
                    'description': """RUBRIC EVALUATION PHASE:
Evaluate learner responses against the provided rubric, scoring each aspect and providing detailed rationale for scoring decisions.""",
                    
                    'objectives': [
                        "Score each rubric aspect on a 0.0-1.0 scale",
                        "Provide specific evidence from learner response",
                        "Identify strengths and areas for improvement",
                        "Ensure scoring consistency with rubric criteria"
                    ],
                    
                    'process_steps': [
                        "1. Review activity requirements and rubric criteria",
                        "2. Analyze learner response against each rubric aspect",
                        "3. Assign scores based on evidence and criteria alignment",
                        "4. Document specific examples supporting each score",
                        "5. Provide constructive rationale for all scoring decisions"
                    ]
                },
                
                'validity_analysis': {
                    'description': """VALIDITY ANALYSIS PHASE:
Analyze assistance provided to the learner and calculate a validity modifier that reflects the impact on score reliability.""",
                    
                    'assistance_categories': [
                        "no_impact: No meaningful assistance provided (modifier: 1.0)",
                        "minimal_guidance: General encouragement or clarification (modifier: 0.9-1.0)",
                        "moderate_assistance: Specific hints or direction (modifier: 0.7-0.9)",
                        "substantial_help: Detailed guidance affecting approach (modifier: 0.4-0.7)",
                        "major_intervention: Direct solution elements provided (modifier: 0.1-0.4)",
                        "invalidating_assistance: Response primarily teacher-generated (modifier: 0.0-0.1)"
                    ],
                    
                    'calculation_rules': [
                        "Consider both severity and proportion of response affected",
                        "Multiple assistance instances compound the impact",
                        "Weight by how much assistance affected the final response",
                        "Factor in timing - later assistance has more impact"
                    ]
                },
                
                'diagnostic_intelligence': {
                    'description': """DIAGNOSTIC INTELLIGENCE PHASE:
Generate deep insights about learner performance, identifying specific strengths, development areas, and learning patterns.""",
                    
                    'analysis_areas': [
                        "Subskill-level performance breakdown",
                        "Competency progression indicators",
                        "Learning pattern identification",
                        "Prerequisite skill assessment",
                        "Development priority recommendations"
                    ]
                },
                
                'trend_analysis': {
                    'description': """TREND ANALYSIS PHASE:
Analyze historical performance data to identify trends, predict future performance, and provide personalized recommendations.""",
                    
                    'trajectory_categories': [
                        "improving: Consistent upward performance trend",
                        "stable_high: Consistent high performance",
                        "stable_moderate: Consistent moderate performance", 
                        "plateauing: Performance has leveled off",
                        "declining: Downward performance trend",
                        "inconsistent: Highly variable performance"
                    ]
                },
                
                'feedback_generation': {
                    'description': """FEEDBACK GENERATION PHASE:
Synthesize all evaluation results into comprehensive, motivational, and actionable student-facing feedback.""",
                    
                    'tone_guidelines': [
                        "Celebratory for high performance",
                        "Encouraging for developing performance", 
                        "Supportive for challenged performance",
                        "Motivational regardless of level"
                    ]
                },
                
                'intelligent_feedback': {
                    'description': """INTELLIGENT FEEDBACK PHASE:
Combined diagnostic intelligence and student-facing feedback generation in a single phase.
Generate both analytical insights for backend review and motivational feedback for student consumption.""",
                    
                    'diagnostic_objectives': [
                        "Map performance to specific subskills and competencies",
                        "Identify demonstrated vs. missing competencies",
                        "Analyze performance patterns and behaviors",
                        "Determine development priorities",
                        "Connect to prerequisite dependencies",
                        "Provide objective analysis for backend review"
                    ],
                    
                    'diagnostic_tone_guidelines': [
                        "Use third person ('the learner') for all diagnostic content",
                        "Maintain objective, analytical tone",
                        "Focus on facts and evidence, not motivation",
                        "Use technical language appropriate for backend review",
                        "Avoid encouraging or motivational language in diagnostic sections"
                    ],
                    
                    'student_feedback_objectives': [
                        "Generate concise, encouraging feedback for student consumption",
                        "Write in second person ('you') for student-facing content",
                        "Provide one clear overall assessment paragraph",
                        "Include one short paragraph on strengths",
                        "Include one short paragraph on opportunities",
                        "Provide exactly one actionable recommendation",
                        "Use growth mindset language and encouraging tone",
                        "Keep content concise and focused"
                    ],
                    
                    'student_feedback_tone_guidelines': [
                        "Write in second person ('you') for student-facing content",
                        "Use encouraging, growth-oriented language",
                        "Celebrate progress and effort",
                        "Frame challenges as opportunities for growth",
                        "Provide specific, actionable guidance",
                        "Use 'developing' vs 'failing' language",
                        "Keep paragraphs short and focused",
                        "Maintain motivational tone throughout"
                    ],
                    
                    'learner_appropriate_guidelines': [
                        "Focus on what the learner CAN do and what they're developing",
                        "Use 'yet' language (e.g., 'You haven't mastered this yet')",
                        "Celebrate small wins and progress, not just perfect performance",
                        "Provide specific examples of what good performance looks like",
                        "Frame feedback as 'next steps' rather than 'corrections'",
                        "Acknowledge the complexity of the skill being developed",
                        "Connect feedback to real-world application and impact",
                        "Provide multiple pathways for improvement",
                        "Use encouraging language that maintains motivation",
                        "Balance constructive feedback with positive reinforcement"
                    ]
                }
            }
        }

    def _init_prompt_templates(self) -> None:
        """Initialize the 23 prompt template configurations"""
        self.prompt_templates = {}
        
        # Phase 1: Combined Evaluation (5 combinations: all types)
        for activity_type in ['CR', 'COD', 'RP', 'SR', 'BR']:
            self.prompt_templates[f"{activity_type}_combined"] = {
                'system_components': [
                    'universal.system_role',
                    'universal.evaluation_philosophy',
                    'universal.domain_focus',
                    'universal.single_skill_focus',
                    'phase_specific.combined_evaluation.description',
                    f'type_specific.{activity_type.lower()}_combined',
                    'universal.critical_guidelines',
                    'universal.json_format_warning'
                ],
                'required_variables': [
                    'activity_spec', 'activity_transcript', 'domain_model', 'target_skill_context',
                    'rubric_details', 'leveling_framework', 'assistance_log', 'response_analysis'
                ],
                'user_prompt_template': """ACTIVITY: {activity_spec}
RESPONSE: {activity_transcript}
SKILL: {target_skill_context}
RUBRIC: {rubric_details}
ASSISTANCE: {assistance_log}
ANALYSIS: {response_analysis}

COMBINED EVALUATION TASK: 
1. Evaluate the learner's response against the rubric, scoring each aspect with specific evidence
2. Simultaneously assess validity and evidence quality, considering assistance impact
3. Provide integrated insights about evidence sufficiency and assessment confidence
4. Note evidence volume concerns directly through the evaluation process

Return ONLY a JSON object with this exact structure:
{{
  "aspect_scores": [
    {{
      "aspect_id": "string",
      "aspect_name": "string", 
      "score": 0.0-1.0,
      "rationale": "string",
      "evidence_references": ["string"],
      "subskill_evidence": {{}}
    }}
  ],
  "overall_score": 0.0-1.0,
  "rationale": "string",
  "validity_modifier": 0.0-1.0,
  "validity_analysis": "string",
  "validity_reason": "string",
  "evidence_quality": "string",
  "assistance_impact": "string",
  "evidence_volume_assessment": "string",
  "assessment_confidence": "string",
  "key_observations": ["string"]
}}"""
            }
        
        # Phase 1A: Rubric Evaluation (DEPRECATED - 3 combinations: CR, COD, RP)
        for activity_type in ['CR', 'COD', 'RP']:
            self.prompt_templates[f"{activity_type}_rubric"] = {
                'system_components': [
                    'universal.system_role',
                    'universal.evaluation_philosophy',
                    'universal.domain_focus',
                    'universal.single_skill_focus',
                    f'type_specific.{activity_type.lower()}_rubric',
                    'phase_specific.rubric_evaluation.description',
                    'universal.critical_guidelines',
                    'universal.json_format_warning'
                ],
                'required_variables': [
                    'activity_spec', 'activity_transcript', 'domain_model', 'target_skill_context',
                    'rubric_details', 'leveling_framework'
                ],
                'user_prompt_template': """ACTIVITY: {activity_spec}
RESPONSE: {activity_transcript}
SKILL: {target_skill_context}
RUBRIC: {rubric_details}

Evaluate against rubric. Score each aspect 0.0-1.0 with rationale based on evidence."""
            }
        
        # Phase 1B: Validity Analysis (DEPRECATED - 5 combinations: all types)
        for activity_type in ['CR', 'COD', 'RP', 'SR', 'BR']:
            self.prompt_templates[f"{activity_type}_validity"] = {
                'system_components': [
                    'universal.system_role',
                    'universal.evaluation_philosophy',
                    'phase_specific.validity_analysis.description',
                    f'type_specific.{activity_type.lower()}_validity',
                    'universal.critical_guidelines',
                    'universal.json_format_warning'
                ],
                'required_variables': [
                    'activity_spec', 'activity_transcript', 'assistance_log', 'response_analysis'
                ],
                'user_prompt_template': """ACTIVITY: {activity_spec}
RESPONSE: {activity_transcript}
ASSISTANCE: {assistance_log}
ANALYSIS: {response_analysis}

Calculate validity modifier (0.0-1.0) based on assistance impact.

Return ONLY a JSON object with this exact structure:
{{
  "validity_modifier": 0.0-1.0,
  "validity_analysis": "string"
}}"""
            }
        
        # Phase 3: Diagnostic Intelligence (5 combinations: all types)
        for activity_type in ['CR', 'COD', 'RP', 'SR', 'BR']:
            self.prompt_templates[f"{activity_type}_diagnostic"] = {
                'system_components': [
                    'universal.system_role',
                    'universal.evaluation_philosophy',
                    'universal.domain_focus',
                    'universal.single_skill_focus',
                    'phase_specific.diagnostic_intelligence.description',
                    f'type_specific.{activity_type.lower()}_diagnostic',
                    'universal.critical_guidelines',
                    'universal.json_format_warning'
                ],
                'required_variables': [
                    'activity_spec', 'activity_transcript', 'domain_model', 'target_skill_context',
                    'rubric_evaluation_results', 'validity_analysis_results', 'prerequisite_relationships'
                ],
                'user_prompt_template': """ACTIVITY SPECIFICATION:
{activity_spec}

LEARNER RESPONSE:
{activity_transcript}

DOMAIN MODEL:
{domain_model}

TARGET SKILL CONTEXT:
{target_skill_context}

PREREQUISITE RELATIONSHIPS:
{prerequisite_relationships}

RUBRIC EVALUATION RESULTS:
{rubric_evaluation_results}

VALIDITY ANALYSIS RESULTS:
{validity_analysis_results}

DIAGNOSTIC INTELLIGENCE TASK: Please analyze learner performance and generate diagnostic insights about strengths, development areas, and learning patterns."""
            }
        
        # Phase 4: Trend Analysis (5 combinations: all types)
        for activity_type in ['CR', 'COD', 'RP', 'SR', 'BR']:
            self.prompt_templates[f"{activity_type}_trend"] = {
                'system_components': [
                    'universal.system_role',
                    'universal.evaluation_philosophy',
                    'universal.domain_focus',
                    'phase_specific.trend_analysis.description',
                    f'type_specific.{activity_type.lower()}_trend',
                    'universal.critical_guidelines',
                    'universal.json_format_warning'
                ],
                'required_variables': [
                    'activity_spec', 'activity_transcript', 'historical_performance_data',
                    'current_diagnostic_results', 'temporal_context'
                ],
                'user_prompt_template': """CURRENT ACTIVITY:
{activity_spec}

CURRENT RESPONSE:
{activity_transcript}

HISTORICAL PERFORMANCE DATA:
{historical_performance_data}

CURRENT DIAGNOSTIC RESULTS:
{current_diagnostic_results}

TEMPORAL CONTEXT:
{temporal_context}

TREND ANALYSIS TASK: Please analyze performance trends over time and generate personalized recommendations based on historical patterns and current performance."""
            }
        
        # Phase 5: Feedback Generation (5 combinations: all types)
        for activity_type in ['CR', 'COD', 'RP', 'SR', 'BR']:
            self.prompt_templates[f"{activity_type}_feedback"] = {
                'system_components': [
                    'universal.system_role',
                    'universal.evaluation_philosophy',
                    'phase_specific.feedback_generation.description',
                    f'type_specific.{activity_type.lower()}_feedback',
                    'universal.critical_guidelines',
                    'universal.json_format_warning'
                ],
                'required_variables': [
                    'activity_spec', 'activity_transcript', 'all_pipeline_results',
                    'performance_context', 'motivational_context'
                ],
                'user_prompt_template': """ACTIVITY SPECIFICATION:
{activity_spec}

LEARNER RESPONSE:
{activity_transcript}

COMPLETE EVALUATION RESULTS:
{all_pipeline_results}

PERFORMANCE CONTEXT:
{performance_context}

MOTIVATIONAL CONTEXT:
{motivational_context}

FEEDBACK GENERATION TASK: Please synthesize all evaluation results into comprehensive, motivational, and actionable student-facing feedback."""
            }
        
        # Phase 4: Intelligent Feedback (5 combinations: all types) - NEW COMBINED PHASE
        for activity_type in ['CR', 'COD', 'RP', 'SR', 'BR']:
            self.prompt_templates[f"{activity_type}_intelligent_feedback"] = {
                'system_components': [
                    'universal.system_role',
                    'universal.evaluation_philosophy',
                    'universal.domain_focus',
                    'universal.single_skill_focus',
                    'phase_specific.intelligent_feedback.description',
                    'phase_specific.intelligent_feedback.diagnostic_objectives',
                    'phase_specific.intelligent_feedback.diagnostic_tone_guidelines',
                    'phase_specific.intelligent_feedback.student_feedback_objectives',
                    'phase_specific.intelligent_feedback.student_feedback_tone_guidelines',
                    'phase_specific.intelligent_feedback.learner_appropriate_guidelines',
                    f'type_specific.{activity_type.lower()}_diagnostic',
                    f'type_specific.{activity_type.lower()}_feedback',
                    'universal.critical_guidelines',
                    'universal.json_format_warning'
                ],
                'required_variables': [
                    'activity_spec', 'activity_transcript', 'rubric_evaluation_results',
                    'validity_analysis_results', 'target_skill_context', 'prerequisite_relationships',
                    'performance_context', 'motivational_context'
                ],
                'user_prompt_template': """ACTIVITY SPECIFICATION:
{activity_spec}

LEARNER RESPONSE:
{activity_transcript}

RUBRIC EVALUATION RESULTS:
{rubric_evaluation_results}

VALIDITY ANALYSIS RESULTS:
{validity_analysis_results}

TARGET SKILL CONTEXT:
{target_skill_context}

PREREQUISITE RELATIONSHIPS:
{prerequisite_relationships}

PERFORMANCE CONTEXT:
{performance_context}

MOTIVATIONAL CONTEXT:
{motivational_context}

INTELLIGENT FEEDBACK TASK: 
Please perform a combined analysis that includes:

1. BACKEND INTELLIGENCE (FOR EVALUATION VIEW):
   - Provide an analytical overview of performance
   - Identify specific strengths with evidence
   - Identify specific weaknesses with evidence
   - Create subskill ratings table with performance levels
   - Use third person ('the learner') for all backend content
   - Maintain objective, analytical tone for evaluation review
   - Focus on facts and evidence, not motivation

2. LEARNER FEEDBACK (FOR BOTH EVALUATION AND LEARNER VIEWS):
   - Generate student-friendly, motivational feedback
   - Write in second person ('you') for learner-facing content
   - Provide one clear overall assessment
   - Include strengths in encouraging, non-bulleted format
   - Include opportunities in growth-oriented, non-bulleted format
   - Use growth mindset language and encouraging tone
   - Keep content concise and focused

IMPORTANT: 
- Backend intelligence should use third person ('the learner') and maintain objective tone
- Learner feedback should use second person ('you') and be encouraging/motivational
- Learner feedback should be non-bulleted, flowing paragraphs
- Both sections should be drawn from the same intelligence but rendered differently

Return ONLY a JSON object with this exact structure:
{{
  "intelligent_feedback": {{
    "backend_intelligence": {{
      "overview": "string",
      "strengths": ["string"],
      "weaknesses": ["string"],
      "subskill_ratings": [
        {{
          "subskill_name": "string",
          "performance_level": "proficient|developing|needs_improvement",
          "development_priority": "high|medium|low"
        }}
      ]
    }},
    "learner_feedback": {{
      "overall": "string",
      "strengths": "string",
      "opportunities": "string"
    }}
  }}
}}"""
            }

    def _init_llm_configurations(self) -> None:
        """Initialize LLM configuration settings for each phase"""
        self.llm_configs = {
            'combined': {
                'temperature': 0.1,
                'max_tokens': 6000,
                'top_p': 0.9
            },
            'rubric': {
                'temperature': 0.1,
                'max_tokens': 2000,
                'top_p': 0.9
            },
            'validity': {
                'temperature': 0.3,
                'max_tokens': 1000,
                'top_p': 0.9
            },
            'diagnostic': {
                'temperature': 0.6,
                'max_tokens': 2000,
                'top_p': 0.9
            },
            'trend': {
                'temperature': 0.5,
                'max_tokens': 1500,
                'top_p': 0.9
            },
            'feedback': {
                'temperature': 0.8,
                'max_tokens': 2500,
                'top_p': 0.9
            },
            'intelligent_feedback': {
                'temperature': 0.7,
                'max_tokens': 4000,
                'top_p': 0.9
            }
        }

    def _init_output_schemas(self) -> None:
        """Initialize output schemas for each phase"""
        self.output_schemas = {
                            'combined': {
                    'type': 'object',
                    'required': ['aspect_scores', 'overall_score', 'rationale', 'validity_modifier', 'validity_analysis'],
                    'properties': {
                        'aspect_scores': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'aspect_id': {'type': 'string'},
                                    'aspect_name': {'type': 'string'},
                                    'score': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0},
                                    'rationale': {'type': 'string'},
                                    'evidence_references': {'type': 'array', 'items': {'type': 'string'}},
                                    'subskill_evidence': {'type': 'object'}
                                },
                                'required': ['aspect_id', 'aspect_name', 'score', 'rationale']
                            }
                        },
                        'overall_score': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0},
                        'rationale': {'type': 'string'},
                        'validity_modifier': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0},
                        'validity_analysis': {'type': 'string'},
                        'validity_reason': {'type': 'string'},
                        'evidence_quality': {'type': 'string'},
                        'assistance_impact': {'type': 'string'},
                        'evidence_volume_assessment': {'type': 'string'},
                        'assessment_confidence': {'type': 'string'},
                        'key_observations': {'type': 'array', 'items': {'type': 'string'}}
                    }
                },
            'rubric': {
                'type': 'object',
                'required': ['aspects', 'component_score', 'scoring_rationale'],
                'properties': {
                    'aspects': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'aspect_name': {'type': 'string'},
                                'aspect_score': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0},
                                'scoring_reasoning': {'type': 'string'}
                            }
                        },
                        'description': 'Array of rubric aspects with scores and rationale'
                    },
                    'component_score': {
                        'type': 'number',
                        'minimum': 0.0,
                        'maximum': 1.0,
                        'description': 'Overall weighted component score'
                    },
                    'scoring_rationale': {
                        'type': 'string',
                        'description': 'Comprehensive explanation of overall assessment'
                    }
                }
            },
            'validity': {
                'type': 'object',
                'required': ['validity_modifier', 'rationale', 'assistance_impact_analysis'],
                'properties': {
                    'validity_modifier': {
                        'type': 'number',
                        'minimum': 0.0,
                        'maximum': 1.0,
                        'description': 'Validity modifier based on assistance impact'
                    },
                    'rationale': {
                        'type': 'string',
                        'description': 'Detailed explanation of validity assessment'
                    },
                    'assistance_impact_analysis': {
                        'type': 'object',
                        'properties': {
                            'overall_impact_level': {'type': 'string', 'enum': ['minimal', 'moderate', 'significant']},
                            'total_assistance_events': {'type': 'integer'},
                            'assistance_breakdown': {'type': 'object'}
                        },
                        'description': 'Analysis of assistance impact on response validity'
                    }
                }
            },
            'diagnostic': {
                'type': 'object',
                'required': ['diagnostic_intelligence'],
                'properties': {
                    'diagnostic_intelligence': {
                        'type': 'object',
                        'properties': {
                            'strength_areas': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Areas where learner demonstrated strength'
                            },
                            'improvement_areas': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Areas needing improvement'
                            },
                            'subskill_performance': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'subskill_name': {'type': 'string'},
                                        'performance_level': {'type': 'string', 'enum': ['proficient', 'developing', 'needs_improvement']},
                                        'development_priority': {'type': 'string', 'enum': ['high', 'medium', 'low']}
                                    }
                                },
                                'description': 'Detailed subskill performance breakdown'
                            }
                        }
                    }
                }
            },
            'trend': {
                'type': 'object',
                'required': ['trend_analysis'],
                'properties': {
                    'trend_analysis': {
                        'type': 'object',
                        'properties': {
                            'historical_performance': {
                                'type': 'object',
                                'properties': {
                                    'activity_count': {'type': 'integer'},
                                    'date_range': {'type': 'object'},
                                    'performance_summary': {'type': 'string'}
                                }
                            },
                            'performance_trajectory': {
                                'type': 'object',
                                'properties': {
                                    'direction': {'type': 'string', 'enum': ['improving', 'stable', 'declining']},
                                    'magnitude': {'type': 'string', 'enum': ['significant', 'moderate', 'minimal']},
                                    'confidence': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0},
                                    'trajectory_description': {'type': 'string'}
                                },
                                'description': 'Overall performance trajectory analysis'
                            },
                            'historical_patterns': {
                                'type': 'object',
                                'properties': {
                                    'consistent_strengths': {'type': 'array', 'items': {'type': 'string'}},
                                    'recurring_challenges': {'type': 'array', 'items': {'type': 'string'}}
                                },
                                'description': 'Historical performance patterns'
                            }
                        }
                    }
                }
            },
            'feedback': {
                'type': 'object',
                'required': ['feedback_generation'],
                'properties': {
                    'feedback_generation': {
                        'type': 'object',
                        'properties': {
                            'performance_summary': {
                                'type': 'object',
                                'properties': {
                                    'overall_assessment': {'type': 'string'},
                                    'key_strengths': {'type': 'array', 'items': {'type': 'string'}},
                                    'primary_opportunities': {'type': 'array', 'items': {'type': 'string'}},
                                    'achievement_highlights': {'type': 'array', 'items': {'type': 'string'}}
                                }
                            },
                            'actionable_guidance': {
                                'type': 'object',
                                'properties': {
                                    'immediate_next_steps': {
                                        'type': 'array',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'action': {'type': 'string'},
                                                'rationale': {'type': 'string'}
                                            }
                                        }
                                    },
                                    'recommendations': {'type': 'array', 'items': {'type': 'string'}}
                                }
                            }
                        }
                    }
                }
            },
            'intelligent_feedback': {
                'type': 'object',
                'required': ['intelligent_feedback'],
                'properties': {
                    'intelligent_feedback': {
                        'type': 'object',
                        'properties': {
                            'backend_intelligence': {
                                'type': 'object',
                                'properties': {
                                    'overview': {
                                        'type': 'string',
                                        'description': 'Analytical overview of performance'
                                    },
                                    'strengths': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                        'description': 'Specific strengths with evidence'
                                    },
                                    'weaknesses': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                        'description': 'Specific weaknesses with evidence'
                                    },
                                    'subskill_ratings': {
                                        'type': 'array',
                                        'items': {
                                            'type': 'object',
                                            'properties': {
                                                'subskill_name': {'type': 'string'},
                                                'performance_level': {'type': 'string', 'enum': ['proficient', 'developing', 'needs_improvement']},
                                                'development_priority': {'type': 'string', 'enum': ['high', 'medium', 'low']}
                                            }
                                        },
                                        'description': 'Subskill performance ratings table'
                                    }
                                },
                                'required': ['overview', 'strengths', 'weaknesses', 'subskill_ratings']
                            },
                            'learner_feedback': {
                                'type': 'object',
                                'properties': {
                                    'overall': {'type': 'string'},
                                    'strengths': {'type': 'string'},
                                    'opportunities': {'type': 'string'}
                                },
                                'required': ['overall', 'strengths', 'opportunities']
                            }
                        }
                    }
                }
            }
        }

    def build_prompt(self, phase_name: str, activity_type: str, context_data: Dict[str, Any]) -> PromptConfiguration:
        """
        Build complete prompt configuration for a specific phase-activity combination.
        
        Args:
            phase_name: Evaluation phase (rubric, validity, diagnostic, trend, feedback)
            activity_type: Activity type (CR, COD, RP, SR, BR)
            context_data: Dictionary with all required context variables
            
        Returns:
            PromptConfiguration instance ready for LLM call
        """
        try:
            # Validate inputs
            if phase_name not in self.valid_phases:
                raise ValueError(f"Invalid phase: {phase_name}. Must be one of {self.valid_phases}")
            
            if activity_type not in self.valid_activity_types:
                raise ValueError(f"Invalid activity type: {activity_type}. Must be one of {self.valid_activity_types}")
            
            # Check if this combination is valid
            template_key = f"{activity_type}_{phase_name}"
            if template_key not in self.prompt_templates:
                raise ValueError(f"No template found for {template_key}")
            
            template = self.prompt_templates[template_key]
            
            # Validate required variables
            missing_vars = []
            for var in template['required_variables']:
                if var not in context_data:
                    missing_vars.append(var)
            
            if missing_vars:
                raise ValueError(f"Missing required context variables: {missing_vars}")
            
            # Build system prompt
            system_prompt = self._build_system_prompt(template['system_components'], activity_type)
            
            # Build user prompt with variable substitution
            user_prompt = self._substitute_variables(template['user_prompt_template'], context_data)
            
            # Get configuration
            llm_config = self.llm_configs.get(phase_name, {})
            output_schema = self.output_schemas.get(phase_name, {})
            validation_rules = self._get_validation_rules(phase_name)
            
            config = PromptConfiguration(
                phase_name=phase_name,
                activity_type=activity_type,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_schema,
                llm_config=llm_config,
                validation_rules=validation_rules
            )
            
            self.logger.log_system_event('prompt_builder', 'prompt_built', 
                                       f'Prompt built for {template_key}',
                                       {'phase': phase_name, 'activity_type': activity_type})
            
            return config
            
        except Exception as e:
            self.logger.log_error('prompt_builder', f'Failed to build prompt for {phase_name}_{activity_type}: {str(e)}',
                                str(e), {'phase': phase_name, 'activity_type': activity_type})
            raise

    def _build_system_prompt(self, components: List[str], activity_type: str) -> str:
        """Build system prompt from component list"""
        system_parts = []
        
        for component_path in components:
            if component_path.startswith('type_specific.'):
                # Add activity-type-specific content
                type_content = self._get_type_specific_content(component_path, activity_type)
                if type_content:
                    system_parts.append(type_content)
            else:
                # Get standard component
                content = self._get_nested_component(component_path)
                if content:
                    system_parts.append(content)
        
        return "\n\n".join(system_parts)

    def _get_nested_component(self, path: str) -> str:
        """Get component by dot-notation path"""
        parts = path.split('.')
        current = self.prompt_components
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return ""
        
        if isinstance(current, list):
            return "\n".join(current)
        elif isinstance(current, str):
            return current
        else:
            return str(current)

    def _get_type_specific_content(self, component_path: str, activity_type: str) -> str:
        """Get activity-type-specific prompt content"""
        type_specific_content = {
            'CR': {
                'rubric': "For Constructed Response activities, focus on written expression, content accuracy, and critical thinking demonstration.",
                'validity': "For CR activities, consider assistance with writing, structure, content ideas, and factual corrections.",
                'diagnostic': "For CR activities, analyze writing skills, content knowledge, and reasoning processes.",
                'trend': "For CR activities, track improvements in writing quality, content depth, and analytical thinking.",
                'feedback': "For CR activities, provide specific feedback on writing mechanics, content development, and reasoning."
            },
            'COD': {
                'rubric': "For Coding Exercise activities, focus on code correctness, efficiency, style, and problem-solving approach.",
                'validity': "For COD activities, consider assistance with syntax, logic, debugging, and algorithm design.",
                'diagnostic': "For COD activities, analyze programming concepts, problem-solving strategies, and coding practices.",
                'trend': "For COD activities, track improvements in code quality, problem-solving efficiency, and technical skills.",
                'feedback': "For COD activities, provide specific feedback on code structure, logic, and programming best practices."
            },
            'RP': {
                'rubric': "For Role Play activities, focus on communication skills, scenario engagement, and objective achievement.",
                'validity': "For RP activities, consider assistance with dialogue suggestions, character guidance, and scenario navigation.",
                'diagnostic': "For RP activities, analyze communication patterns, interpersonal skills, and scenario management.",
                'trend': "For RP activities, track improvements in communication effectiveness and scenario handling.",
                'feedback': "For RP activities, provide feedback on communication skills and scenario engagement."
            },
            'SR': {
                'validity': "For Single Response activities, consider assistance with option evaluation, reasoning, and answer selection.",
                'diagnostic': "For SR activities, analyze knowledge application and decision-making processes.",
                'trend': "For SR activities, track accuracy patterns and reasoning consistency.",
                'feedback': "For SR activities, provide feedback on reasoning processes and knowledge application."
            },
            'BR': {
                'validity': "For Branching Response activities, consider assistance with decision evaluation and path selection.",
                'diagnostic': "For BR activities, analyze decision-making patterns and scenario navigation skills.",
                'trend': "For BR activities, track improvements in decision quality and scenario outcomes.",
                'feedback': "For BR activities, provide feedback on decision-making processes and scenario management."
            }
        }
        
        # Extract the specific content type from the path
        content_type = component_path.split('.')[-1]
        
        return type_specific_content.get(activity_type, {}).get(content_type, "")

    def _substitute_variables(self, template: str, context_data: Dict[str, Any]) -> str:
        """Substitute template variables with actual values"""
        result = template
        
        for var_name, var_value in context_data.items():
            placeholder = f"{{{var_name}}}"
            
            # Convert value to string if needed
            if isinstance(var_value, (dict, list)):
                # Handle dataclass objects that might be in the data
                try:
                    var_str = json.dumps(var_value, indent=2, ensure_ascii=False, default=str)
                except (TypeError, ValueError):
                    # Fallback for non-serializable objects
                    var_str = str(var_value)
            else:
                var_str = str(var_value)
            
            result = result.replace(placeholder, var_str)
        
        return result

    def _get_validation_rules(self, phase_name: str) -> List[str]:
        """Get validation rules for a specific phase"""
        validation_rules = {
            'rubric': [
                'score_range_0_to_1',
                'required_rationale',
                'aspect_coverage',
                'evidence_specificity'
            ],
            'validity': [
                'validity_range_0_to_1',
                'assistance_categorization',
                'impact_justification'
            ],
            'diagnostic': [
                'strength_identification',
                'development_area_identification',
                'pattern_analysis',
                'recommendation_specificity'
            ],
            'trend': [
                'trajectory_classification',
                'historical_analysis',
                'prediction_reasoning',
                'recommendation_personalization'
            ],
            'feedback': [
                'tone_appropriateness',
                'achievement_recognition',
                'actionable_guidance',
                'motivation_integration'
            ]
        }
        
        return validation_rules.get(phase_name, [])

    def validate_prompt_configuration(self, config: PromptConfiguration) -> Dict[str, Any]:
        """
        Validate a prompt configuration for completeness and correctness.
        
        Args:
            config: PromptConfiguration to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        
        try:
            # Check required fields
            required_fields = ['phase_name', 'activity_type', 'system_prompt', 'user_prompt']
            for field in required_fields:
                value = getattr(config, field, None)
                if not value:
                    validation_results['errors'].append(f"Missing or empty {field}")
                    validation_results['valid'] = False
                else:
                    validation_results['checks'][field] = 'present'
            
            # Check phase and type validity
            if config.phase_name not in self.valid_phases:
                validation_results['errors'].append(f"Invalid phase: {config.phase_name}")
                validation_results['valid'] = False
            
            if config.activity_type not in self.valid_activity_types:
                validation_results['errors'].append(f"Invalid activity type: {config.activity_type}")
                validation_results['valid'] = False
            
            # Check for template variable remnants
            remaining_vars = []
            for text in [config.system_prompt, config.user_prompt]:
                import re
                vars_found = re.findall(r'\{([^}]+)\}', text)
                remaining_vars.extend(vars_found)
            
            if remaining_vars:
                validation_results['warnings'].append(f"Unsubstituted variables found: {remaining_vars}")
            
            # Check prompt length
            total_length = len(config.system_prompt) + len(config.user_prompt)
            validation_results['checks']['total_prompt_length'] = total_length
            
            if total_length > 50000:  # Rough token estimate
                validation_results['warnings'].append(f"Prompt may be too long: {total_length} characters")
            
            # Check output schema
            if not config.output_schema:
                validation_results['warnings'].append("No output schema defined")
            else:
                validation_results['checks']['output_schema'] = 'present'
            
            # Check LLM config
            if not config.llm_config:
                validation_results['warnings'].append("No LLM config defined")
            else:
                validation_results['checks']['llm_config'] = 'present'
            
        except Exception as e:
            validation_results['errors'].append(f"Validation error: {str(e)}")
            validation_results['valid'] = False
        
        return validation_results

    def get_available_configurations(self) -> Dict[str, List[str]]:
        """
        Get all available prompt configurations.
        
        Returns:
            Dictionary mapping phases to available activity types
        """
        configurations = {}
        
        for template_key in self.prompt_templates.keys():
            activity_type, phase_name = template_key.split('_', 1)
            
            if phase_name not in configurations:
                configurations[phase_name] = []
            
            if activity_type not in configurations[phase_name]:
                configurations[phase_name].append(activity_type)
        
        return configurations

    def get_prompt_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about prompt configurations.
        
        Returns:
            Dictionary with prompt builder statistics
        """
        return {
            'total_configurations': len(self.prompt_templates),
            'phases': list(self.valid_phases),
            'activity_types': list(self.valid_activity_types),
            'configurations_by_phase': self.get_available_configurations(),
            'component_counts': {
                'universal': len(self.prompt_components['universal']),
                'phase_specific': len(self.prompt_components['phase_specific']),
                'llm_configs': len(self.llm_configs),
                'output_schemas': len(self.output_schemas)
            }
        }

    def prepare_context_data(self, base_context: Dict[str, Any], phase_name: str) -> Dict[str, Any]:
        """
        Prepare context data with phase-specific additions and domain model integration.
        
        Args:
            base_context: Base context data
            phase_name: Current evaluation phase
            
        Returns:
            Enhanced context data ready for prompt building
        """
        context = base_context.copy()
        
        # Always add domain model if not present
        if 'domain_model' not in context:
            context['domain_model'] = self.domain_model
        
        # Add leveling framework
        if 'leveling_framework' not in context:
            context['leveling_framework'] = {
                'cognitive_levels': {
                    'L1': 'Remember - Recall facts and basic concepts',
                    'L2': 'Understand - Explain ideas or concepts', 
                    'L3': 'Apply - Use information in new situations',
                    'L4': 'Analyze - Draw connections among ideas'
                },
                'depth_levels': {
                    'D1': 'Recognition - Identify and recall',
                    'D2': 'Comprehension - Understand and explain',
                    'D3': 'Application - Use and implement', 
                    'D4': 'Analysis - Examine and evaluate'
                }
            }
        
        # Phase-specific context additions
        if phase_name == 'diagnostic' and 'prerequisite_relationships' not in context:
            # Add prerequisite relationships from domain model
            context['prerequisite_relationships'] = self._extract_prerequisites(context.get('target_skill_context', {}))
        
        if phase_name == 'trend' and 'temporal_context' not in context:
            # Add temporal analysis context
            context['temporal_context'] = {
                'analysis_timeframe': 'last_6_months',
                'minimum_activities_for_trend': 3,
                'trend_confidence_threshold': 0.7
            }
        
        if phase_name == 'feedback' and 'motivational_context' not in context:
            # Add motivational context
            context['motivational_context'] = {
                'learner_effort_level': 'moderate',
                'progress_indicators': [],
                'encouragement_focus': 'growth_mindset'
            }
        
        return context

    def _extract_prerequisites(self, skill_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract prerequisite relationships for diagnostic analysis"""
        skill_id = skill_context.get('skill_id', '')
        
        # Get prerequisite info from domain model
        prerequisites = {}
        
        if 'skills' in self.domain_model:
            for skill in self.domain_model['skills']:
                if skill.get('skill_id') == skill_id:
                    prerequisites = {
                        'direct_prerequisites': skill.get('prerequisite_skills', []),
                        'subskill_dependencies': skill.get('subskill_dependencies', []),
                        'competency_context': skill.get('parent_competency', '')
                    }
                    break
        
        return prerequisites