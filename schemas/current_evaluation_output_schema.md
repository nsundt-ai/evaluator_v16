# Evaluation Output Schema Documentation

## Overview

This schema defines the complete structure for evaluation pipeline output, capturing results from all 5 evaluation phases (Rubric → Validity → Scoring → Diagnostic → Trend → Feedback). It serves as the definitive record of learner assessment and provides structured data for scoring engine integration, progress tracking, and feedback generation.

## Purpose

- **Evaluation Pipeline Output**: Complete results from `evaluation_pipeline.py`
- **Scoring Engine Input**: Structured data for dual-gate scoring calculations
- **Progress Tracking**: Comprehensive performance data for learner management
- **Diagnostic Intelligence**: Detailed insights for learning analytics
- **Feedback Generation**: Rich data for personalized learner feedback

## Complete JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["learner_id", "activity_id", "evaluation_output"],
  "properties": {
    "learner_id": {
      "type": "string",
      "description": "Unique identifier for the learner"
    },
    "activity_id": {
      "type": "string",
      "description": "Unique identifier for the activity"
    },
    "evaluation_timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO timestamp when evaluation was completed"
    },
    "evaluation_output": {
      "type": "object",
      "required": [
        "activity_record",
        "validity_analysis",
        "scoring_results",
        "diagnostic_intelligence",
        "feedback_generation"
      ],
      "properties": {
        "activity_record": {
          "$ref": "#/definitions/activity_record"
        },
        "validity_analysis": {
          "$ref": "#/definitions/validity_analysis"
        },
        "scoring_results": {
          "$ref": "#/definitions/scoring_results"
        },
        "diagnostic_intelligence": {
          "$ref": "#/definitions/diagnostic_intelligence"
        },
        "trend_analysis": {
          "$ref": "#/definitions/trend_analysis",
          "description": "Optional - only present when historical data available"
        },
        "feedback_generation": {
          "$ref": "#/definitions/feedback_generation"
        },
        "evaluation_metadata": {
          "$ref": "#/definitions/evaluation_metadata"
        }
      }
    }
  },
  "definitions": {
    "activity_record": {
      "type": "object",
      "required": [
        "activity_score",
        "completion_status",
        "duration_minutes",
        "activity_evidence_summary",
        "component_evaluations"
      ],
      "properties": {
        "activity_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Overall activity score (0-1)"
        },
        "completion_status": {
          "type": "string",
          "enum": ["completed", "partial", "abandoned", "timeout"],
          "description": "Activity completion status"
        },
        "duration_minutes": {
          "type": "integer",
          "minimum": 0,
          "description": "Total activity duration in minutes"
        },
        "activity_evidence_summary": {
          "type": "object",
          "required": [
            "target_activity_evidence_volume",
            "total_validity_adjusted_evidence_volume",
            "overall_validity_modifier",
            "component_count"
          ],
          "properties": {
            "target_activity_evidence_volume": {
              "type": "number",
              "minimum": 0.0,
              "description": "Total target evidence volume for activity"
            },
            "total_validity_adjusted_evidence_volume": {
              "type": "number", 
              "minimum": 0.0,
              "description": "Total evidence after validity adjustments"
            },
            "overall_validity_modifier": {
              "type": "number",
              "minimum": 0.0,
              "maximum": 1.0,
              "description": "Composite validity modifier across components"
            },
            "component_count": {
              "type": "integer",
              "minimum": 1,
              "description": "Number of components evaluated"
            },
            "evaluation_method_mix": {
              "type": "array",
              "items": {
                "type": "string",
                "enum": ["rubric_scored", "autoscored"]
              },
              "description": "Evaluation methods used across components"
            }
          }
        },
        "component_evaluations": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/component_evaluation"
          },
          "description": "Detailed evaluation for each component"
        }
      }
    },
    "component_evaluation": {
      "type": "object",
      "required": [
        "component_id",
        "component_type",
        "component_purpose",
        "component_score",
        "component_weight",
        "evaluation_method",
        "target_evidence_volume"
      ],
      "properties": {
        "component_id": {
          "type": "string",
          "description": "Component identifier from activity"
        },
        "component_type": {
          "type": "string",
          "description": "Type of component evaluated"
        },
        "component_purpose": {
          "type": "string",
          "description": "Educational purpose of component"
        },
        "component_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Component score (0-1)"
        },
        "component_weight": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Weight in overall activity score"
        },
        "evaluation_method": {
          "type": "string",
          "enum": ["rubric_scored", "autoscored"],
          "description": "Method used for evaluation"
        },
        "target_evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Target evidence volume for component"
        },
        "rubric_evaluation": {
          "$ref": "#/definitions/rubric_evaluation",
          "description": "Present for rubric-scored components (CR, COD, RP)"
        },
        "autoscored_evaluation": {
          "$ref": "#/definitions/autoscored_evaluation",
          "description": "Present for autoscored components (SR, BR)"
        },
        "subskill_performance": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/subskill_performance"
          },
          "description": "Performance breakdown by subskill"
        }
      }
    },
    "rubric_evaluation": {
      "type": "object",
      "required": [
        "aspects",
        "component_score",
        "scoring_rationale",
        "evaluation_confidence"
      ],
      "properties": {
        "aspects": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/aspect_evaluation"
          },
          "description": "Evaluation of each rubric aspect"
        },
        "component_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Weighted average of aspect scores"
        },
        "scoring_rationale": {
          "type": "string",
          "description": "Overall rationale for component score"
        },
        "evaluation_confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Confidence in evaluation quality"
        }
      }
    },
    "aspect_evaluation": {
      "type": "object",
      "required": [
        "aspect_id",
        "aspect_name", 
        "aspect_score",
        "aspect_weight",
        "weighted_aspect_score",
        "scoring_reasoning",
        "evidence_volume"
      ],
      "properties": {
        "aspect_id": {
          "type": "string",
          "description": "Aspect identifier from rubric"
        },
        "aspect_name": {
          "type": "string",
          "description": "Name of evaluated aspect"
        },
        "aspect_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Raw aspect score"
        },
        "aspect_weight": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Weight in component score"
        },
        "weighted_aspect_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Weighted contribution to component"
        },
        "scoring_reasoning": {
          "type": "string",
          "description": "Detailed reasoning for aspect score"
        },
        "evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Evidence volume generated by aspect"
        },
        "evidence_quality": {
          "type": "string",
          "enum": ["strong", "moderate", "weak", "none"],
          "description": "Quality assessment of evidence"
        },
        "performance_indicators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Specific performance indicators observed"
        },
        "improvement_areas": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Areas needing improvement"
        }
      }
    },
    "autoscored_evaluation": {
      "type": "object",
      "required": [
        "correct_responses",
        "total_responses", 
        "accuracy_percentage",
        "response_analysis"
      ],
      "properties": {
        "correct_responses": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of correct responses"
        },
        "total_responses": {
          "type": "integer",
          "minimum": 1,
          "description": "Total number of response opportunities"
        },
        "accuracy_percentage": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 100.0,
          "description": "Percentage of correct responses"
        },
        "response_analysis": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/response_analysis_item"
          },
          "description": "Analysis of individual responses"
        },
        "completion_time_analysis": {
          "type": "object",
          "properties": {
            "average_time_per_item_seconds": {
              "type": "number",
              "minimum": 0.0,
              "description": "Average time spent per response item"
            },
            "time_efficiency_rating": {
              "type": "string",
              "enum": ["very_fast", "fast", "normal", "slow", "very_slow"],
              "description": "Efficiency assessment relative to expected time"
            }
          }
        }
      }
    },
    "response_analysis_item": {
      "type": "object",
      "required": ["item_id", "response_given", "correct_response", "is_correct"],
      "properties": {
        "item_id": {
          "type": "string",
          "description": "Identifier for response item"
        },
        "response_given": {
          "type": "string",
          "description": "Learner's response"
        },
        "correct_response": {
          "type": "string",
          "description": "Correct/expected response"
        },
        "is_correct": {
          "type": "boolean",
          "description": "Whether response was correct"
        },
        "partial_credit": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Partial credit awarded if applicable"
        },
        "response_time_seconds": {
          "type": "number",
          "minimum": 0.0,
          "description": "Time spent on this response"
        },
        "difficulty_level": {
          "type": "string",
          "description": "Difficulty level of this item"
        }
      }
    },
    "subskill_performance": {
      "type": "object",
      "required": [
        "subskill_id",
        "subskill_name",
        "performance_score",
        "evidence_volume",
        "confidence_level"
      ],
      "properties": {
        "subskill_id": {
          "type": "string",
          "description": "Subskill identifier from domain model"
        },
        "subskill_name": {
          "type": "string",
          "description": "Human-readable subskill name"
        },
        "performance_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Performance score for this subskill"
        },
        "evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Evidence volume generated for subskill"
        },
        "confidence_level": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Confidence in performance assessment"
        },
        "improvement_priority": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Priority for skill development focus"
        }
      }
    },
    "validity_analysis": {
      "type": "object",
      "required": [
        "overall_validity_modifier",
        "component_validity_modifiers",
        "assistance_impact_analysis",
        "validity_rationale"
      ],
      "properties": {
        "overall_validity_modifier": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Composite validity modifier for entire activity"
        },
        "component_validity_modifiers": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/component_validity"
          },
          "description": "Validity analysis for each component"
        },
        "assistance_impact_analysis": {
          "$ref": "#/definitions/assistance_impact"
        },
        "validity_rationale": {
          "type": "string",
          "description": "Overall rationale for validity assessment"
        }
      }
    },
    "component_validity": {
      "type": "object",
      "required": [
        "component_id",
        "validity_modifier",
        "assistance_events_count",
        "impact_assessment"
      ],
      "properties": {
        "component_id": {
          "type": "string",
          "description": "Component identifier"
        },
        "validity_modifier": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Validity modifier for this component"
        },
        "assistance_events_count": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of assistance events for component"
        },
        "impact_assessment": {
          "type": "string",
          "enum": ["minimal", "moderate", "significant", "substantial"],
          "description": "Assessment of assistance impact level"
        },
        "assistance_breakdown": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/assistance_impact_item"
          },
          "description": "Breakdown of specific assistance impacts"
        }
      }
    },
    "assistance_impact": {
      "type": "object",
      "required": [
        "total_assistance_events",
        "assistance_categories",
        "overall_impact_level",
        "validity_implications"
      ],
      "properties": {
        "total_assistance_events": {
          "type": "integer",
          "minimum": 0,
          "description": "Total number of assistance events"
        },
        "assistance_categories": {
          "type": "object",
          "properties": {
            "hint": {"type": "integer", "minimum": 0},
            "clarification": {"type": "integer", "minimum": 0},
            "example": {"type": "integer", "minimum": 0},
            "syntax_help": {"type": "integer", "minimum": 0},
            "conceptual_guidance": {"type": "integer", "minimum": 0},
            "full_solution": {"type": "integer", "minimum": 0}
          },
          "description": "Count of assistance by category"
        },
        "overall_impact_level": {
          "type": "string",
          "enum": ["minimal", "moderate", "significant", "substantial"],
          "description": "Overall assessment of assistance impact"
        },
        "validity_implications": {
          "type": "string",
          "description": "Explanation of how assistance affects validity"
        }
      }
    },
    "assistance_impact_item": {
      "type": "object",
      "required": ["assistance_type", "frequency", "impact_level"],
      "properties": {
        "assistance_type": {
          "type": "string",
          "description": "Type of assistance provided"
        },
        "frequency": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of times this assistance was provided"
        },
        "impact_level": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Impact on validity (0=no impact, 1=complete invalidation)"
        },
        "justification": {
          "type": "string",
          "description": "Rationale for impact assessment"
        }
      }
    },
    "scoring_results": {
      "type": "object",
      "required": [
        "dual_gate_results",
        "evidence_calculations",
        "skill_contributions",
        "scoring_metadata"
      ],
      "properties": {
        "dual_gate_results": {
          "$ref": "#/definitions/dual_gate_results"
        },
        "evidence_calculations": {
          "$ref": "#/definitions/evidence_calculations"
        },
        "skill_contributions": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/skill_contribution"
          },
          "description": "Contributions to each targeted skill"
        },
        "scoring_metadata": {
          "$ref": "#/definitions/scoring_metadata"
        }
      }
    },
    "dual_gate_results": {
      "type": "object",
      "required": [
        "performance_score",
        "evidence_volume",
        "gate_1_status",
        "gate_2_status",
        "overall_progression_impact"
      ],
      "properties": {
        "performance_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Performance score for Gate 1 assessment"
        },
        "evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Validity-adjusted evidence volume for Gate 2"
        },
        "gate_1_status": {
          "type": "string",
          "enum": ["passed", "failed"],
          "description": "Gate 1 status (performance ≥ 0.75)"
        },
        "gate_2_status": {
          "type": "string",
          "enum": ["passed", "failed"],
          "description": "Gate 2 status (evidence ≥ threshold)"
        },
        "overall_progression_impact": {
          "type": "string",
          "enum": ["significant_progress", "moderate_progress", "minimal_progress", "no_progress"],
          "description": "Impact on learner skill progression"
        },
        "gate_thresholds": {
          "type": "object",
          "properties": {
            "gate_1_threshold": {
              "type": "number",
              "description": "Performance threshold for Gate 1"
            },
            "gate_2_threshold": {
              "type": "number", 
              "description": "Evidence threshold for Gate 2"
            }
          }
        }
      }
    },
    "evidence_calculations": {
      "type": "object",
      "required": [
        "base_evidence_volume",
        "validity_adjusted_evidence",
        "decay_factor_applied",
        "final_evidence_contribution"
      ],
      "properties": {
        "base_evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Raw evidence volume before adjustments"
        },
        "validity_adjusted_evidence": {
          "type": "number",
          "minimum": 0.0,
          "description": "Evidence after validity modifier applied"
        },
        "decay_factor_applied": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Decay factor based on activity position"
        },
        "final_evidence_contribution": {
          "type": "number",
          "minimum": 0.0,
          "description": "Final evidence added to learner profile"
        },
        "calculation_details": {
          "type": "object",
          "properties": {
            "activity_position": {
              "type": "integer",
              "minimum": 1,
              "description": "Position in learner's activity sequence"
            },
            "decay_formula": {
              "type": "string",
              "description": "Formula used for decay calculation"
            }
          }
        }
      }
    },
    "skill_contribution": {
      "type": "object",
      "required": [
        "skill_id",
        "skill_name",
        "evidence_contribution",
        "performance_impact",
        "progression_status"
      ],
      "properties": {
        "skill_id": {
          "type": "string",
          "description": "Skill identifier from domain model"
        },
        "skill_name": {
          "type": "string",
          "description": "Human-readable skill name"
        },
        "evidence_contribution": {
          "type": "number",
          "minimum": 0.0,
          "description": "Evidence volume contributed to this skill"
        },
        "performance_impact": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Performance contribution to skill average"
        },
        "progression_status": {
          "type": "string",
          "enum": ["advancing", "maintaining", "struggling"],
          "description": "Impact on skill progression"
        },
        "subskill_breakdown": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/subskill_contribution"
          },
          "description": "Contribution breakdown by subskill"
        }
      }
    },
    "subskill_contribution": {
      "type": "object",
      "required": ["subskill_id", "evidence_volume", "performance_score"],
      "properties": {
        "subskill_id": {
          "type": "string",
          "description": "Subskill identifier"
        },
        "evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Evidence volume for subskill"
        },
        "performance_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Performance score for subskill"
        }
      }
    },
    "scoring_metadata": {
      "type": "object",
      "properties": {
        "scoring_algorithm_version": {
          "type": "string",
          "description": "Version of scoring algorithm used"
        },
        "calculation_timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "When scoring calculations were performed"
        },
        "confidence_intervals": {
          "type": "object",
          "properties": {
            "performance_lower": {"type": "number"},
            "performance_upper": {"type": "number"},
            "evidence_lower": {"type": "number"},
            "evidence_upper": {"type": "number"}
          }
        }
      }
    },
    "diagnostic_intelligence": {
      "type": "object",
      "required": [
        "performance_insights",
        "learning_behavior_analysis",
        "skill_development_recommendations",
        "diagnostic_confidence"
      ],
      "properties": {
        "performance_insights": {
          "$ref": "#/definitions/performance_insights"
        },
        "learning_behavior_analysis": {
          "$ref": "#/definitions/learning_behavior_analysis"
        },
        "skill_development_recommendations": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/development_recommendation"
          },
          "description": "Targeted skill development recommendations"
        },
        "diagnostic_confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Confidence in diagnostic analysis"
        },
        "prerequisite_analysis": {
          "$ref": "#/definitions/prerequisite_analysis"
        }
      }
    },
    "performance_insights": {
      "type": "object",
      "required": [
        "strength_areas",
        "improvement_areas",
        "performance_patterns",
        "competency_demonstrations"
      ],
      "properties": {
        "strength_areas": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Areas where learner demonstrated strength"
        },
        "improvement_areas": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Areas needing focused improvement"
        },
        "performance_patterns": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/performance_pattern"
          },
          "description": "Observable patterns in performance"
        },
        "competency_demonstrations": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/competency_demonstration"
          },
          "description": "Specific demonstrations of competency"
        }
      }
    },
    "performance_pattern": {
      "type": "object",
      "required": ["pattern_type", "description", "evidence"],
      "properties": {
        "pattern_type": {
          "type": "string",
          "enum": [
            "consistent_strength", "emerging_strength", "inconsistent_performance",
            "declining_performance", "improvement_trend", "plateau_pattern"
          ],
          "description": "Type of performance pattern observed"
        },
        "description": {
          "type": "string",
          "description": "Detailed description of the pattern"
        },
        "evidence": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Specific evidence supporting pattern identification"
        },
        "implications": {
          "type": "string",
          "description": "Educational implications of this pattern"
        }
      }
    },
    "competency_demonstration": {
      "type": "object",
      "required": ["competency_area", "demonstration_level", "supporting_evidence"],
      "properties": {
        "competency_area": {
          "type": "string",
          "description": "Area of competency demonstrated"
        },
        "demonstration_level": {
          "type": "string",
          "enum": ["exemplary", "proficient", "developing", "emerging"],
          "description": "Level of competency demonstrated"
        },
        "supporting_evidence": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Specific evidence of competency demonstration"
        },
        "next_level_indicators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "What would indicate progression to next level"
        }
      }
    },
    "learning_behavior_analysis": {
      "type": "object",
      "required": [
        "engagement_level",
        "problem_solving_approach",
        "help_seeking_behavior",
        "persistence_indicators"
      ],
      "properties": {
        "engagement_level": {
          "type": "string",
          "enum": ["high", "moderate", "low"],
          "description": "Overall engagement assessment"
        },
        "problem_solving_approach": {
          "type": "string",
          "description": "Description of learner's problem-solving approach"
        },
        "help_seeking_behavior": {
          "type": "object",
          "properties": {
            "appropriateness": {
              "type": "string",
              "enum": ["highly_appropriate", "appropriate", "somewhat_appropriate", "inappropriate"]
            },
            "frequency": {
              "type": "string", 
              "enum": ["too_frequent", "appropriate", "too_infrequent"]
            },
            "effectiveness": {
              "type": "string",
              "description": "How effectively learner used help"
            }
          }
        },
        "persistence_indicators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Observable indicators of persistence and effort"
        },
        "metacognitive_awareness": {
          "type": "string",
          "description": "Assessment of learner's metacognitive awareness"
        }
      }
    },
    "development_recommendation": {
      "type": "object",
      "required": [
        "recommendation_type",
        "target_skill_area",
        "priority_level",
        "specific_actions"
      ],
      "properties": {
        "recommendation_type": {
          "type": "string",
          "enum": [
            "skill_building", "concept_review", "practice_increase",
            "strategy_change", "prerequisite_work", "enrichment"
          ],
          "description": "Type of development recommendation"
        },
        "target_skill_area": {
          "type": "string",
          "description": "Specific skill area to target"
        },
        "priority_level": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Priority level for this recommendation"
        },
        "specific_actions": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Specific actionable steps for improvement"
        },
        "timeline_recommendation": {
          "type": "string",
          "description": "Recommended timeline for addressing this area"
        },
        "success_indicators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "How to recognize successful improvement"
        }
      }
    },
    "prerequisite_analysis": {
      "type": "object",
      "properties": {
        "prerequisite_gaps_identified": {
          "type": "boolean",
          "description": "Whether prerequisite gaps were identified"
        },
        "missing_prerequisites": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/missing_prerequisite"
          },
          "description": "Specific prerequisite gaps identified"
        },
        "foundation_strength": {
          "type": "string",
          "enum": ["strong", "adequate", "weak", "insufficient"],
          "description": "Overall assessment of prerequisite foundation"
        }
      }
    },
    "missing_prerequisite": {
      "type": "object",
      "required": ["prerequisite_skill", "evidence_of_gap", "impact_level"],
      "properties": {
        "prerequisite_skill": {
          "type": "string",
          "description": "Prerequisite skill that appears to be missing"
        },
        "evidence_of_gap": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Evidence suggesting this prerequisite gap"
        },
        "impact_level": {
          "type": "string",
          "enum": ["critical", "significant", "moderate", "minor"],
          "description": "Impact of this gap on current learning"
        },
        "remediation_suggestions": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Suggestions for addressing this gap"
        }
      }
    },
    "trend_analysis": {
      "type": "object",
      "required": [
        "performance_trajectory",
        "learning_velocity",
        "consistency_analysis",
        "predictive_insights"
      ],
      "properties": {
        "performance_trajectory": {
          "$ref": "#/definitions/performance_trajectory"
        },
        "learning_velocity": {
          "$ref": "#/definitions/learning_velocity"
        },
        "consistency_analysis": {
          "$ref": "#/definitions/consistency_analysis"
        },
        "predictive_insights": {
          "$ref": "#/definitions/predictive_insights"
        },
        "historical_context": {
          "$ref": "#/definitions/historical_context"
        }
      }
    },
    "performance_trajectory": {
      "type": "object",
      "required": ["direction", "magnitude", "confidence"],
      "properties": {
        "direction": {
          "type": "string",
          "enum": ["improving", "stable", "declining", "fluctuating"],
          "description": "Overall direction of performance change"
        },
        "magnitude": {
          "type": "string",
          "enum": ["significant", "moderate", "minimal"],
          "description": "Magnitude of performance change"
        },
        "confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Statistical confidence in trajectory assessment"
        },
        "trend_data_points": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of activities used in trend analysis"
        },
        "trajectory_description": {
          "type": "string",
          "description": "Detailed description of performance trajectory"
        }
      }
    },
    "learning_velocity": {
      "type": "object",
      "required": ["velocity_rating", "skill_acquisition_rate"],
      "properties": {
        "velocity_rating": {
          "type": "string",
          "enum": ["accelerating", "steady", "slowing", "stagnant"],
          "description": "Assessment of learning velocity"
        },
        "skill_acquisition_rate": {
          "type": "number",
          "description": "Quantitative measure of skill acquisition rate"
        },
        "velocity_factors": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Factors influencing learning velocity"
        },
        "projected_timeline": {
          "type": "string",
          "description": "Projected timeline for skill mastery"
        }
      }
    },
    "consistency_analysis": {
      "type": "object",
      "required": ["consistency_rating", "variability_assessment"],
      "properties": {
        "consistency_rating": {
          "type": "string",
          "enum": ["highly_consistent", "consistent", "somewhat_variable", "highly_variable"],
          "description": "Assessment of performance consistency"
        },
        "variability_assessment": {
          "type": "string",
          "description": "Analysis of performance variability patterns"
        },
        "stability_indicators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Indicators of performance stability or instability"
        }
      }
    },
    "predictive_insights": {
      "type": "object",
      "properties": {
        "mastery_probability": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Probability of achieving mastery in target timeframe"
        },
        "risk_factors": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Factors that might impede progress"
        },
        "success_factors": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Factors supporting continued progress"
        },
        "intervention_recommendations": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Recommended interventions based on trends"
        }
      }
    },
    "historical_context": {
      "type": "object",
      "properties": {
        "activities_analyzed": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of historical activities included"
        },
        "time_span_days": {
          "type": "integer",
          "minimum": 0,
          "description": "Time span of historical data in days"
        },
        "data_completeness": {
          "type": "string",
          "enum": ["complete", "mostly_complete", "partial", "limited"],
          "description": "Completeness of historical data"
        }
      }
    },
    "feedback_generation": {
      "type": "object",
      "required": [
        "performance_summary",
        "detailed_insights",
        "actionable_guidance"
      ],
      "properties": {
        "performance_summary": {
          "$ref": "#/definitions/performance_summary"
        },
        "detailed_insights": {
          "$ref": "#/definitions/detailed_insights"
        },
        "actionable_guidance": {
          "$ref": "#/definitions/actionable_guidance"
        },
        "motivation_elements": {
          "$ref": "#/definitions/motivation_elements"
        }
      }
    },
    "performance_summary": {
      "type": "object",
      "required": [
        "overall_assessment",
        "key_strengths",
        "primary_opportunities",
        "achievement_highlights"
      ],
      "properties": {
        "overall_assessment": {
          "type": "string",
          "description": "Comprehensive overall assessment of performance"
        },
        "key_strengths": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Primary strengths demonstrated"
        },
        "primary_opportunities": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Key opportunities for improvement"
        },
        "achievement_highlights": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Notable achievements in this activity"
        },
        "progress_recognition": {
          "type": "string",
          "description": "Recognition of learner's progress and effort"
        }
      }
    },
    "detailed_insights": {
      "type": "object",
      "properties": {
        "competency_development": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/competency_insight"
          },
          "description": "Detailed insights on competency development"
        },
        "subskill_feedback": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/subskill_feedback"
          },
          "description": "Specific feedback on subskill performance"
        },
        "learning_behavior_insights": {
          "$ref": "#/definitions/behavior_insights"
        }
      }
    },
    "competency_insight": {
      "type": "object",
      "required": [
        "skill_name",
        "skill_id",
        "current_level",
        "progress_description"
      ],
      "properties": {
        "skill_name": {
          "type": "string",
          "description": "Name of the skill/competency"
        },
        "skill_id": {
          "type": "string",
          "description": "Skill identifier"
        },
        "current_level": {
          "type": "string",
          "description": "Current performance level"
        },
        "progress_description": {
          "type": "string",
          "description": "Description of progress in this skill"
        },
        "specific_demonstrations": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Specific ways skill was demonstrated"
        },
        "growth_areas": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Areas for continued growth"
        },
        "next_development_focus": {
          "type": "string",
          "description": "Recommended focus for next development"
        }
      }
    },
    "subskill_feedback": {
      "type": "object",
      "required": [
        "subskill_name",
        "subskill_id",
        "performance_level",
        "evidence_observed"
      ],
      "properties": {
        "subskill_name": {
          "type": "string",
          "description": "Name of the subskill"
        },
        "subskill_id": {
          "type": "string",
          "description": "Subskill identifier"
        },
        "performance_level": {
          "type": "string",
          "description": "Performance level assessment"
        },
        "evidence_observed": {
          "type": "string",
          "description": "Specific evidence of subskill demonstration"
        },
        "encouragement": {
          "type": "string",
          "description": "Encouraging feedback for this subskill"
        },
        "development_guidance": {
          "type": "string",
          "description": "Guidance for further development"
        }
      }
    },
    "behavior_insights": {
      "type": "object",
      "properties": {
        "problem_solving_approach": {
          "type": "string",
          "description": "Insights about problem-solving approach"
        },
        "engagement_quality": {
          "type": "string",
          "description": "Assessment of engagement quality"
        },
        "independence_level": {
          "type": "string",
          "description": "Assessment of independence in learning"
        },
        "persistence_demonstration": {
          "type": "string",
          "description": "Evidence of persistence and effort"
        },
        "help_seeking_effectiveness": {
          "type": "string",
          "description": "Assessment of help-seeking behavior"
        }
      }
    },
    "actionable_guidance": {
      "type": "object",
      "required": ["immediate_next_steps", "practice_recommendations"],
      "properties": {
        "immediate_next_steps": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/next_step"
          },
          "description": "Immediate actionable next steps"
        },
        "practice_recommendations": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/practice_recommendation"
          },
          "description": "Specific practice recommendations"
        },
        "study_strategies": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/study_strategy"
          },
          "description": "Recommended study strategies"
        }
      }
    },
    "next_step": {
      "type": "object",
      "required": ["action", "rationale"],
      "properties": {
        "action": {
          "type": "string",
          "description": "Specific action to take"
        },
        "rationale": {
          "type": "string",
          "description": "Why this action is recommended"
        },
        "resources": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Recommended resources for this action"
        },
        "timeline": {
          "type": "string",
          "description": "Recommended timeline for action"
        },
        "success_indicators": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "How to recognize success"
        }
      }
    },
    "practice_recommendation": {
      "type": "object",
      "required": ["skill_focus", "recommended_activities"],
      "properties": {
        "skill_focus": {
          "type": "string",
          "description": "Skill area to focus practice on"
        },
        "recommended_activities": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Specific activities for practice"
        },
        "practice_strategies": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Strategies for effective practice"
        },
        "difficulty_progression": {
          "type": "string",
          "description": "How to progress difficulty over time"
        }
      }
    },
    "study_strategy": {
      "type": "object",
      "required": ["strategy_type", "strategy_description"],
      "properties": {
        "strategy_type": {
          "type": "string",
          "enum": ["conceptual_review", "practical_application", "peer_collaboration", "self_assessment"],
          "description": "Type of study strategy"
        },
        "strategy_description": {
          "type": "string",
          "description": "Detailed description of strategy"
        },
        "implementation_guidance": {
          "type": "string",
          "description": "How to implement this strategy"
        },
        "expected_benefits": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Expected benefits of this strategy"
        }
      }
    },
    "motivation_elements": {
      "type": "object",
      "properties": {
        "encouragement_messages": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Motivational messages based on performance"
        },
        "progress_celebration": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Recognition of progress and achievement"
        },
        "confidence_building": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Elements designed to build confidence"
        }
      }
    },
    "evaluation_metadata": {
      "type": "object",
      "properties": {
        "pipeline_version": {
          "type": "string",
          "description": "Version of evaluation pipeline used"
        },
        "llm_provider_info": {
          "type": "object",
          "properties": {
            "provider": {"type": "string"},
            "model": {"type": "string"},
            "api_version": {"type": "string"}
          }
        },
        "processing_time_seconds": {
          "type": "number",
          "minimum": 0.0,
          "description": "Total processing time for evaluation"
        },
        "evaluation_phases_completed": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "rubric_evaluation",
              "validity_analysis", 
              "scoring_calculation",
              "diagnostic_intelligence",
              "trend_analysis",
              "feedback_generation"
            ]
          },
          "description": "Phases successfully completed"
        },
        "quality_indicators": {
          "type": "object",
          "properties": {
            "response_completeness": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "evaluation_consistency": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "diagnostic_depth": {"type": "number", "minimum": 0.0, "maximum": 1.0}
          }
        }
      }
    }
  }
}
```

## Activity Type Examples

### Constructed Response (CR) Evaluation Output

```json
{
  "learner_id": "L001",
  "activity_id": "CR001", 
  "evaluation_timestamp": "2025-01-15T15:30:00Z",
  "evaluation_output": {
    "activity_record": {
      "activity_score": 0.78,
      "completion_status": "completed",
      "duration_minutes": 45,
      "activity_evidence_summary": {
        "target_activity_evidence_volume": 25.0,
        "total_validity_adjusted_evidence_volume": 18.5,
        "overall_validity_modifier": 0.9,
        "component_count": 1,
        "evaluation_method_mix": ["rubric_scored"]
      },
      "component_evaluations": [
        {
          "component_id": "CR001_main",
          "component_type": "constructed_response",
          "component_purpose": "analysis_demonstration",
          "component_score": 0.78,
          "component_weight": 1.0,
          "evaluation_method": "rubric_scored",
          "target_evidence_volume": 25.0,
          "rubric_evaluation": {
            "aspects": [
              {
                "aspect_id": "analysis_depth",
                "aspect_name": "Depth of Analysis",
                "aspect_score": 0.82,
                "aspect_weight": 0.4,
                "weighted_aspect_score": 0.328,
                "scoring_reasoning": "Demonstrates solid understanding of remote work impacts with good use of provided data. Analysis shows consideration of multiple perspectives and addresses both benefits and challenges systematically.",
                "evidence_volume": 10.5,
                "evidence_quality": "strong",
                "performance_indicators": [
                  "Used quantitative data effectively",
                  "Considered multiple stakeholder perspectives",
                  "Drew connections between different impact areas"
                ],
                "improvement_areas": [
                  "Could deepen analysis of long-term implications",
                  "Opportunity to explore additional data relationships"
                ]
              },
              {
                "aspect_id": "evidence_use",
                "aspect_name": "Use of Evidence",
                "aspect_score": 0.75,
                "aspect_weight": 0.3,
                "weighted_aspect_score": 0.225,
                "scoring_reasoning": "Good integration of survey data and productivity metrics. Evidence supports main arguments well, though some claims could benefit from additional data support.",
                "evidence_volume": 8.0,
                "evidence_quality": "moderate",
                "performance_indicators": [
                  "Accurately cited specific statistics",
                  "Connected evidence to arguments effectively"
                ],
                "improvement_areas": [
                  "Could analyze data more critically",
                  "Opportunity to address potential data limitations"
                ]
              }
            ],
            "component_score": 0.78,
            "scoring_rationale": "Strong analysis demonstrating good understanding of the topic with effective use of evidence. Response shows analytical thinking and ability to synthesize information from multiple sources.",
            "evaluation_confidence": 0.85
          },
          "subskill_performance": [
            {
              "subskill_id": "SS001",
              "subskill_name": "Data Analysis",
              "performance_score": 0.80,
              "evidence_volume": 12.0,
              "confidence_level": "high",
              "improvement_priority": "medium"
            },
            {
              "subskill_id": "SS003",
              "subskill_name": "Critical Thinking",
              "performance_score": 0.76,
              "evidence_volume": 6.5,
              "confidence_level": "medium",
              "improvement_priority": "high"
            }
          ]
        }
      ]
    },
    "validity_analysis": {
      "overall_validity_modifier": 0.9,
      "component_validity_modifiers": [
        {
          "component_id": "CR001_main",
          "validity_modifier": 0.9,
          "assistance_events_count": 1,
          "impact_assessment": "minimal",
          "assistance_breakdown": [
            {
              "assistance_type": "hint",
              "frequency": 1,
              "impact_level": 0.1,
              "justification": "Structural guidance provided without revealing content"
            }
          ]
        }
      ],
      "assistance_impact_analysis": {
        "total_assistance_events": 1,
        "assistance_categories": {
          "hint": 1,
          "clarification": 0,
          "example": 0,
          "syntax_help": 0,
          "conceptual_guidance": 0,
          "full_solution": 0
        },
        "overall_impact_level": "minimal",
        "validity_implications": "Single hint about structure does not significantly compromise the validity of the analytical content or reasoning demonstrated."
      },
      "validity_rationale": "Minimal assistance provided focused on organizational structure rather than content. The analytical thinking and evidence use demonstrated remain valid indicators of learner capability."
    },
    "scoring_results": {
      "dual_gate_results": {
        "performance_score": 0.78,
        "evidence_volume": 18.5,
        "gate_1_status": "passed",
        "gate_2_status": "failed",
        "overall_progression_impact": "moderate_progress",
        "gate_thresholds": {
          "gate_1_threshold": 0.75,
          "gate_2_threshold": 30.0
        }
      },
      "evidence_calculations": {
        "base_evidence_volume": 20.5,
        "validity_adjusted_evidence": 18.5,
        "decay_factor_applied": 1.0,
        "final_evidence_contribution": 18.5,
        "calculation_details": {
          "activity_position": 1,
          "decay_formula": "0.9^(position-1)"
        }
      },
      "skill_contributions": [
        {
          "skill_id": "S001",
          "skill_name": "Analytical Reasoning",
          "evidence_contribution": 18.5,
          "performance_impact": 0.78,
          "progression_status": "advancing",
          "subskill_breakdown": [
            {
              "subskill_id": "SS001",
              "evidence_volume": 12.0,
              "performance_score": 0.80
            },
            {
              "subskill_id": "SS003", 
              "evidence_volume": 6.5,
              "performance_score": 0.76
            }
          ]
        }
      ],
      "scoring_metadata": {
        "scoring_algorithm_version": "v2.1",
        "calculation_timestamp": "2025-01-15T15:30:15Z",
        "confidence_intervals": {
          "performance_lower": 0.73,
          "performance_upper": 0.83,
          "evidence_lower": 16.2,
          "evidence_upper": 20.8
        }
      }
    },
    "diagnostic_intelligence": {
      "performance_insights": {
        "strength_areas": [
          "Data interpretation and analysis",
          "Systematic thinking approach",
          "Evidence-based reasoning"
        ],
        "improvement_areas": [
          "Critical evaluation of data limitations",
          "Long-term impact analysis",
          "Integration of multiple data sources"
        ],
        "performance_patterns": [
          {
            "pattern_type": "consistent_strength",
            "description": "Shows consistent ability to work with quantitative data",
            "evidence": [
              "Accurate interpretation of survey statistics",
              "Appropriate use of productivity metrics"
            ],
            "implications": "Learner has solid foundation for data-driven analysis"
          }
        ],
        "competency_demonstrations": [
          {
            "competency_area": "Analytical Reasoning",
            "demonstration_level": "proficient",
            "supporting_evidence": [
              "Systematic approach to problem analysis",
              "Integration of multiple data sources",
              "Recognition of different perspectives"
            ],
            "next_level_indicators": [
              "More critical evaluation of data quality",
              "Deeper exploration of causal relationships"
            ]
          }
        ]
      },
      "learning_behavior_analysis": {
        "engagement_level": "high",
        "problem_solving_approach": "Systematic and methodical, showing good planning and organization",
        "help_seeking_behavior": {
          "appropriateness": "appropriate",
          "frequency": "appropriate",
          "effectiveness": "Used structural guidance effectively to organize thinking"
        },
        "persistence_indicators": [
          "Completed full response despite complexity",
          "Revised approach after receiving guidance",
          "Maintained focus throughout extended writing task"
        ],
        "metacognitive_awareness": "Shows good awareness of task requirements and able to self-regulate approach"
      },
      "skill_development_recommendations": [
        {
          "recommendation_type": "skill_building",
          "target_skill_area": "Critical Data Analysis",
          "priority_level": "high",
          "specific_actions": [
            "Practice evaluating data quality and limitations",
            "Work on identifying potential biases in data sources",
            "Develop skills in comparing conflicting data sets"
          ],
          "timeline_recommendation": "Focus on this over next 2-3 activities",
          "success_indicators": [
            "Questions data reliability in responses",
            "Acknowledges limitations in analysis",
            "Compares multiple data interpretations"
          ]
        }
      ],
      "prerequisite_analysis": {
        "prerequisite_gaps_identified": false,
        "foundation_strength": "strong",
        "missing_prerequisites": []
      },
      "diagnostic_confidence": 0.85
    },
    "feedback_generation": {
      "performance_summary": {
        "overall_assessment": "Strong analytical performance demonstrating good understanding of complex workplace dynamics and effective use of data to support arguments.",
        "key_strengths": [
          "Systematic approach to analysis",
          "Effective use of quantitative data",
          "Recognition of multiple perspectives"
        ],
        "primary_opportunities": [
          "Deeper critical evaluation of data",
          "More comprehensive long-term impact analysis"
        ],
        "achievement_highlights": [
          "Successfully integrated survey data and productivity metrics",
          "Demonstrated balanced consideration of positive and negative impacts",
          "Organized analysis in clear, logical structure"
        ],
        "progress_recognition": "Your analytical skills are developing well, and your ability to work with data is a real strength."
      },
      "detailed_insights": {
        "competency_development": [
          {
            "skill_name": "Analytical Reasoning",
            "skill_id": "S001",
            "current_level": "Proficient",
            "progress_description": "Showing consistent growth in analytical thinking with good integration of evidence",
            "specific_demonstrations": [
              "Systematic breakdown of complex workplace impacts",
              "Effective synthesis of quantitative and qualitative information"
            ],
            "growth_areas": [
              "Critical evaluation of data sources",
              "Long-term trend analysis"
            ],
            "next_development_focus": "Building critical evaluation skills for data quality assessment"
          }
        ],
        "subskill_feedback": [
          {
            "subskill_name": "Data Analysis",
            "subskill_id": "SS001",
            "performance_level": "Strong",
            "evidence_observed": "Accurately interpreted statistical data and used it effectively to support arguments",
            "encouragement": "Your comfort with data analysis is evident and serves you well",
            "development_guidance": "Continue building on this strength by practicing with more complex datasets"
          }
        ],
        "learning_behavior_insights": {
          "problem_solving_approach": "You approach complex problems systematically, which is an excellent foundation for analytical work",
          "engagement_quality": "High engagement evident through thorough completion and thoughtful organization",
          "independence_level": "Good independence with appropriate help-seeking when needed",
          "persistence_demonstration": "Maintained focus through challenging analytical task",
          "help_seeking_effectiveness": "Used guidance effectively to improve organization without compromising original thinking"
        }
      },
      "actionable_guidance": {
        "immediate_next_steps": [
          {
            "action": "Practice questioning data reliability",
            "rationale": "This will strengthen your critical thinking and make your analyses more sophisticated",
            "resources": ["Critical thinking guides", "Data literacy resources"],
            "timeline": "Practice with next 2-3 analytical tasks",
            "success_indicators": [
              "Questions data sources in your analysis",
              "Acknowledges analytical limitations"
            ]
          }
        ],
        "practice_recommendations": [
          {
            "skill_focus": "Critical Data Analysis",
            "recommended_activities": [
              "Analyze datasets with known limitations",
              "Compare conflicting research findings",
              "Practice identifying data biases"
            ],
            "practice_strategies": [
              "Always ask 'What might this data not show?'",
              "Look for alternative explanations",
              "Consider sample size and methodology"
            ],
            "difficulty_progression": "Start with obviously flawed datasets, progress to subtle bias identification"
          }
        ],
        "study_strategies": [
          {
            "strategy_type": "conceptual_review",
            "strategy_description": "Review examples of data analysis with different quality levels",
            "implementation_guidance": "Study both strong and weak analytical examples to identify differences",
            "expected_benefits": [
              "Better recognition of analysis quality",
              "Improved critical evaluation skills"
            ]
          }
        ]
      },
      "motivation_elements": {
        "encouragement_messages": [
          "Your analytical thinking is a real strength - keep building on this foundation!",
          "The systematic way you approach complex problems will serve you well"
        ],
        "progress_celebration": [
          "Excellent integration of multiple data sources in your analysis",
          "Great job maintaining focus through this complex analytical task"
        ],
        "confidence_building": [
          "You clearly have the foundational skills for strong analytical work",
          "Your data interpretation skills are developing very well"
        ]
      }
    },
    "evaluation_metadata": {
      "pipeline_version": "v16.1.0",
      "llm_provider_info": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_version": "2024-06-01"
      },
      "processing_time_seconds": 45.7,
      "evaluation_phases_completed": [
        "rubric_evaluation",
        "validity_analysis",
        "scoring_calculation", 
        "diagnostic_intelligence",
        "feedback_generation"
      ],
      "quality_indicators": {
        "response_completeness": 0.92,
        "evaluation_consistency": 0.88,
        "diagnostic_depth": 0.85
      }
    }
  }
}
```

## Integration with Backend Modules

### evaluation_pipeline.py Integration

The Evaluation Pipeline produces this output structure:

1. **Pipeline Orchestration**:
   ```python
   def run_evaluation_pipeline(activity_transcript: Dict) -> Dict:
       # Returns complete evaluation_output matching this schema
       pass
   ```

2. **Phase Integration**:
   ```python
   def integrate_phase_results(phases_results: Dict) -> Dict:
       # Combines results from all 5 phases into unified structure
       pass
   ```

### scoring_engine.py Integration

Scoring Engine consumes evaluation output for dual-gate calculations:

1. **Dual-Gate Processing**:
   ```python
   def calculate_dual_gate_scores(evaluation_output: Dict) -> Dict:
       # Uses scoring_results section for learner progress updates
       pass
   ```

2. **Evidence Volume Management**:
   ```python
   def apply_evidence_decay(evidence_volume: float, position: int) -> float:
       # Uses evidence_calculations for decay application
       pass
   ```

### learner_manager.py Integration

Learner Manager persists evaluation results:

1. **Progress Updates**:
   ```python
   def update_learner_progress(learner_id: str, evaluation_output: Dict):
       # Updates skill progress using diagnostic and scoring results
       pass
   ```

2. **Historical Tracking**:
   ```python
   def add_activity_evaluation(learner_id: str, evaluation: Dict):
       # Stores complete evaluation for trend analysis
       pass
   ```

## Validation Rules

### Data Consistency Validation
- Activity scores must be between 0.0 and 1.0
- Component weights must sum to 1.0 across activity
- Aspect weights must sum to 1.0 within rubrics
- Evidence volumes must be non-negative

### Evaluation Method Alignment
- Rubric evaluation must be present for CR, COD, RP activities
- Autoscored evaluation must be present for SR, BR activities
- Evaluation method in components must match activity generation

### Dual-Gate Scoring Validation
- Gate 1 status must align with performance score (≥0.75 = passed)
- Gate 2 status must align with evidence volume vs. threshold
- Evidence calculations must show proper decay factor application

### LLM Output Quality Validation
- All required rationales and reasoning must be present
- Diagnostic insights must be substantive and actionable
- Feedback must be appropriate for performance level
- Confidence levels must reflect evaluation quality

## Role Play (RP) Evaluation Output Example

```json
{
  "learner_id": "L001",
  "activity_id": "RP001",
  "evaluation_timestamp": "2025-01-10T11:45:00Z",
  "evaluation_output": {
    "activity_record": {
      "activity_score": 0.85,
      "completion_status": "completed",
      "duration_minutes": 25,
      "activity_evidence_summary": {
        "target_activity_evidence_volume": 15.0,
        "total_validity_adjusted_evidence_volume": 14.25,
        "overall_validity_modifier": 0.95,
        "component_count": 1,
        "evaluation_method_mix": ["rubric_scored"]
      },
      "component_evaluations": [
        {
          "component_id": "RP001_conversation",
          "component_type": "role_play_conversation",
          "component_purpose": "communication_skill_practice",
          "component_score": 0.85,
          "component_weight": 1.0,
          "evaluation_method": "rubric_scored",
          "target_evidence_volume": 15.0,
          "rubric_evaluation": {
            "aspects": [
              {
                "aspect_id": "questioning_technique",
                "aspect_name": "Questioning Technique",
                "aspect_score": 0.88,
                "aspect_weight": 0.4,
                "weighted_aspect_score": 0.352,
                "scoring_reasoning": "Excellent use of open-ended questions to gather information. Demonstrated good progression from general to specific inquiries.",
                "evidence_volume": 6.5,
                "evidence_quality": "strong",
                "performance_indicators": [
                  "Asked relevant discovery questions",
                  "Used follow-up questions effectively",
                  "Maintained professional tone throughout"
                ],
                "improvement_areas": [
                  "Could explore more probing questions for deeper insights"
                ]
              },
              {
                "aspect_id": "active_listening",
                "aspect_name": "Active Listening",
                "aspect_score": 0.82,
                "aspect_weight": 0.35,
                "weighted_aspect_score": 0.287,
                "scoring_reasoning": "Good demonstration of active listening through appropriate responses and follow-up questions based on client input.",
                "evidence_volume": 5.5,
                "evidence_quality": "strong",
                "performance_indicators": [
                  "Responded appropriately to client concerns",
                  "Built on information provided by client"
                ],
                "improvement_areas": [
                  "Could demonstrate more explicit acknowledgment of client feelings"
                ]
              }
            ],
            "component_score": 0.85,
            "scoring_rationale": "Strong communication skills demonstrated throughout the role play with effective questioning and listening techniques.",
            "evaluation_confidence": 0.90
          },
          "subskill_performance": [
            {
              "subskill_id": "SS015",
              "subskill_name": "Active Listening",
              "performance_score": 0.82,
              "evidence_volume": 5.5,
              "confidence_level": "high",
              "improvement_priority": "medium"
            },
            {
              "subskill_id": "SS016",
              "subskill_name": "Questioning Techniques",
              "performance_score": 0.88,
              "evidence_volume": 6.5,
              "confidence_level": "high",
              "improvement_priority": "low"
            }
          ]
        }
      ]
    },
    "validity_analysis": {
      "overall_validity_modifier": 0.95,
      "component_validity_modifiers": [
        {
          "component_id": "RP001_conversation",
          "validity_modifier": 0.95,
          "assistance_events_count": 1,
          "impact_assessment": "minimal",
          "assistance_breakdown": [
            {
              "assistance_type": "encouragement",
              "frequency": 1,
              "impact_level": 0.05,
              "justification": "Mid-conversation encouragement provided general guidance without specific content"
            }
          ]
        }
      ],
      "assistance_impact_analysis": {
        "total_assistance_events": 1,
        "assistance_categories": {
          "hint": 0,
          "clarification": 0,
          "example": 0,
          "syntax_help": 0,
          "conceptual_guidance": 0,
          "full_solution": 0
        },
        "overall_impact_level": "minimal",
        "validity_implications": "Minimal coaching provided mid-conversation. The communication skills and techniques demonstrated remain valid."
      },
      "validity_rationale": "Single encouragement comment provided general direction without compromising the authenticity of communication skills demonstrated."
    },
    "scoring_results": {
      "dual_gate_results": {
        "performance_score": 0.85,
        "evidence_volume": 14.25,
        "gate_1_status": "passed",
        "gate_2_status": "failed",
        "overall_progression_impact": "moderate_progress",
        "gate_thresholds": {
          "gate_1_threshold": 0.75,
          "gate_2_threshold": 30.0
        }
      },
      "evidence_calculations": {
        "base_evidence_volume": 15.0,
        "validity_adjusted_evidence": 14.25,
        "decay_factor_applied": 1.0,
        "final_evidence_contribution": 14.25,
        "calculation_details": {
          "activity_position": 1,
          "decay_formula": "0.9^(position-1)"
        }
      },
      "skill_contributions": [
        {
          "skill_id": "S005",
          "skill_name": "Professional Communication",
          "evidence_contribution": 14.25,
          "performance_impact": 0.85,
          "progression_status": "advancing",
          "subskill_breakdown": [
            {
              "subskill_id": "SS015",
              "evidence_volume": 5.5,
              "performance_score": 0.82
            },
            {
              "subskill_id": "SS016",
              "evidence_volume": 6.5,
              "performance_score": 0.88
            }
          ]
        }
      ],
      "scoring_metadata": {
        "scoring_algorithm_version": "v2.1",
        "calculation_timestamp": "2025-01-10T11:45:15Z"
      }
    },
    "diagnostic_intelligence": {
      "performance_insights": {
        "strength_areas": [
          "Questioning techniques",
          "Professional communication style",
          "Information gathering approach"
        ],
        "improvement_areas": [
          "Emotional intelligence in responses",
          "Deeper probing techniques",
          "Explicit acknowledgment skills"
        ],
        "performance_patterns": [
          {
            "pattern_type": "consistent_strength",
            "description": "Shows consistent professional communication skills",
            "evidence": [
              "Maintained appropriate tone throughout conversation",
              "Structured questions logically"
            ],
            "implications": "Strong foundation for client-facing roles"
          }
        ],
        "competency_demonstrations": [
          {
            "competency_area": "Professional Communication",
            "demonstration_level": "proficient",
            "supporting_evidence": [
              "Effective use of open-ended questions",
              "Good conversation flow management",
              "Professional and respectful tone"
            ],
            "next_level_indicators": [
              "More sophisticated emotional intelligence",
              "Advanced probing techniques"
            ]
          }
        ]
      },
      "learning_behavior_analysis": {
        "engagement_level": "high",
        "problem_solving_approach": "Structured and professional approach to information gathering",
        "help_seeking_behavior": {
          "appropriateness": "appropriate",
          "frequency": "appropriate",
          "effectiveness": "Minimal assistance used effectively"
        },
        "persistence_indicators": [
          "Maintained engagement throughout full conversation",
          "Continued asking questions to gather complete information"
        ],
        "metacognitive_awareness": "Good awareness of conversation objectives and client needs"
      },
      "skill_development_recommendations": [
        {
          "recommendation_type": "skill_building",
          "target_skill_area": "Emotional Intelligence in Communication",
          "priority_level": "medium",
          "specific_actions": [
            "Practice acknowledging client emotions explicitly",
            "Work on reading non-verbal communication cues",
            "Develop empathetic response techniques"
          ],
          "timeline_recommendation": "Focus on this in next 2-3 communication activities",
          "success_indicators": [
            "Uses empathetic language in responses",
            "Acknowledges client concerns explicitly",
            "Adapts communication style to client needs"
          ]
        }
      ],
      "prerequisite_analysis": {
        "prerequisite_gaps_identified": false,
        "foundation_strength": "strong",
        "missing_prerequisites": []
      },
      "diagnostic_confidence": 0.90
    },
    "feedback_generation": {
      "performance_summary": {
        "overall_assessment": "Excellent communication performance demonstrating strong professional skills and effective information gathering techniques.",
        "key_strengths": [
          "Outstanding questioning techniques",
          "Professional communication style",
          "Structured approach to information gathering"
        ],
        "primary_opportunities": [
          "Enhanced emotional intelligence in responses",
          "More sophisticated probing techniques"
        ],
        "achievement_highlights": [
          "Successfully gathered all key client requirements",
          "Maintained professional tone throughout",
          "Demonstrated excellent listening skills"
        ],
        "progress_recognition": "Your communication skills are developing excellently, particularly your ability to ask the right questions."
      },
      "detailed_insights": {
        "competency_development": [
          {
            "skill_name": "Professional Communication",
            "skill_id": "S005",
            "current_level": "Proficient",
            "progress_description": "Strong foundation in professional communication with particular strength in questioning techniques",
            "specific_demonstrations": [
              "Excellent use of open-ended questions to gather requirements",
              "Professional and respectful tone throughout conversation"
            ],
            "growth_areas": [
              "Emotional intelligence in client interactions",
              "Advanced probing techniques for deeper insights"
            ],
            "next_development_focus": "Building emotional intelligence to enhance client rapport"
          }
        ],
        "subskill_feedback": [
          {
            "subskill_name": "Questioning Techniques",
            "subskill_id": "SS016",
            "performance_level": "Excellent",
            "evidence_observed": "Used a variety of open-ended questions effectively to gather comprehensive client information",
            "encouragement": "Your questioning skills are a real strength - you know how to ask the right questions!",
            "development_guidance": "Continue building on this strength by practicing more sophisticated probing techniques"
          },
          {
            "subskill_name": "Active Listening",
            "subskill_id": "SS015",
            "performance_level": "Strong",
            "evidence_observed": "Demonstrated good listening through appropriate follow-up questions and responses",
            "encouragement": "You show good awareness of what clients are telling you",
            "development_guidance": "Work on more explicit acknowledgment of client emotions and concerns"
          }
        ],
        "learning_behavior_insights": {
          "problem_solving_approach": "You approach client interactions systematically, which is excellent for professional communication",
          "engagement_quality": "High engagement throughout the conversation with good energy",
          "independence_level": "Strong independence with minimal need for guidance",
          "persistence_demonstration": "Maintained focus and continued gathering information throughout the conversation",
          "help_seeking_effectiveness": "Used minimal guidance effectively without compromising natural conversation flow"
        }
      },
      "actionable_guidance": {
        "immediate_next_steps": [
          {
            "action": "Practice acknowledging client emotions",
            "rationale": "This will help build stronger rapport and demonstrate deeper empathy",
            "resources": ["Emotional intelligence guides", "Client communication resources"],
            "timeline": "Practice in next client interaction activity",
            "success_indicators": [
              "Uses phrases like 'I understand that must be frustrating'",
              "Acknowledges client concerns before moving to next question"
            ]
          }
        ],
        "practice_recommendations": [
          {
            "skill_focus": "Emotional Intelligence",
            "recommended_activities": [
              "Role plays with emotionally challenging clients",
              "Practice sessions focusing on empathetic responses",
              "Communication scenarios with stressed clients"
            ],
            "practice_strategies": [
              "Listen for emotional undertones in client responses",
              "Practice acknowledging feelings before addressing facts",
              "Use reflective listening techniques"
            ],
            "difficulty_progression": "Start with straightforward emotional scenarios, progress to complex multi-layered situations"
          }
        ],
        "study_strategies": [
          {
            "strategy_type": "practical_application",
            "strategy_description": "Practice real-world client interaction scenarios with emotional components",
            "implementation_guidance": "Focus on scenarios where clients express frustration, concern, or excitement",
            "expected_benefits": [
              "Enhanced ability to build client rapport",
              "More sophisticated communication skills"
            ]
          }
        ]
      },
      "motivation_elements": {
        "encouragement_messages": [
          "Your communication skills are really impressive - clients would feel heard and understood!",
          "The way you structure your questions shows real professional maturity"
        ],
        "progress_celebration": [
          "Excellent job gathering all the key client information systematically",
          "Your professional tone created a great foundation for client trust"
        ],
        "confidence_building": [
          "You have the core skills for excellent client communication",
          "Your questioning technique is already at a professional level"
        ]
      }
    },
    "evaluation_metadata": {
      "pipeline_version": "v16.1.0",
      "llm_provider_info": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_version": "2024-06-01"
      },
      "processing_time_seconds": 38.2,
      "evaluation_phases_completed": [
        "rubric_evaluation",
        "validity_analysis",
        "scoring_calculation",
        "diagnostic_intelligence",
        "feedback_generation"
      ],
      "quality_indicators": {
        "response_completeness": 0.95,
        "evaluation_consistency": 0.92,
        "diagnostic_depth": 0.88
      }
    }
  }
}
```

## Selected Response (SR) Evaluation Output Example

```json
{
  "learner_id": "L001",
  "activity_id": "SR001",
  "evaluation_timestamp": "2025-01-15T13:30:00Z",
  "evaluation_output": {
    "activity_record": {
      "activity_score": 0.80,
      "completion_status": "completed",
      "duration_minutes": 12,
      "activity_evidence_summary": {
        "target_activity_evidence_volume": 10.0,
        "total_validity_adjusted_evidence_volume": 10.0,
        "overall_validity_modifier": 1.0,
        "component_count": 1,
        "evaluation_method_mix": ["autoscored"]
      },
      "component_evaluations": [
        {
          "component_id": "SR001_questions",
          "component_type": "multiple_choice_set",
          "component_purpose": "knowledge_check",
          "component_score": 0.80,
          "component_weight": 1.0,
          "evaluation_method": "autoscored",
          "target_evidence_volume": 10.0,
          "autoscored_evaluation": {
            "correct_responses": 4,
            "total_responses": 5,
            "accuracy_percentage": 80.0,
            "response_analysis": [
              {
                "item_id": "Q001",
                "response_given": "B",
                "correct_response": "B",
                "is_correct": true,
                "partial_credit": 1.0,
                "response_time_seconds": 45,
                "difficulty_level": "medium"
              },
              {
                "item_id": "Q002",
                "response_given": "A",
                "correct_response": "A",
                "is_correct": true,
                "partial_credit": 1.0,
                "response_time_seconds": 30,
                "difficulty_level": "easy"
              },
              {
                "item_id": "Q003",
                "response_given": "C",
                "correct_response": "D",
                "is_correct": false,
                "partial_credit": 0.0,
                "response_time_seconds": 90,
                "difficulty_level": "hard"
              },
              {
                "item_id": "Q004",
                "response_given": "B",
                "correct_response": "B",
                "is_correct": true,
                "partial_credit": 1.0,
                "response_time_seconds": 60,
                "difficulty_level": "medium"
              },
              {
                "item_id": "Q005",
                "response_given": "D",
                "correct_response": "D",
                "is_correct": true,
                "partial_credit": 1.0,
                "response_time_seconds": 35,
                "difficulty_level": "easy"
              }
            ],
            "completion_time_analysis": {
              "average_time_per_item_seconds": 52.0,
              "time_efficiency_rating": "normal"
            }
          },
          "subskill_performance": [
            {
              "subskill_id": "SS008",
              "subskill_name": "Programming Fundamentals",
              "performance_score": 0.80,
              "evidence_volume": 10.0,
              "confidence_level": "high",
              "improvement_priority": "medium"
            }
          ]
        }
      ]
    },
    "validity_analysis": {
      "overall_validity_modifier": 1.0,
      "component_validity_modifiers": [
        {
          "component_id": "SR001_questions",
          "validity_modifier": 1.0,
          "assistance_events_count": 0,
          "impact_assessment": "minimal",
          "assistance_breakdown": []
        }
      ],
      "assistance_impact_analysis": {
        "total_assistance_events": 0,
        "assistance_categories": {
          "hint": 0,
          "clarification": 0,
          "example": 0,
          "syntax_help": 0,
          "conceptual_guidance": 0,
          "full_solution": 0
        },
        "overall_impact_level": "minimal",
        "validity_implications": "No assistance provided during assessment."
      },
      "validity_rationale": "Independent completion with no assistance maintains full validity of knowledge assessment."
    },
    "scoring_results": {
      "dual_gate_results": {
        "performance_score": 0.80,
        "evidence_volume": 10.0,
        "gate_1_status": "passed",
        "gate_2_status": "failed",
        "overall_progression_impact": "moderate_progress",
        "gate_thresholds": {
          "gate_1_threshold": 0.75,
          "gate_2_threshold": 25.0
        }
      },
      "evidence_calculations": {
        "base_evidence_volume": 10.0,
        "validity_adjusted_evidence": 10.0,
        "decay_factor_applied": 1.0,
        "final_evidence_contribution": 10.0
      },
      "skill_contributions": [
        {
          "skill_id": "S008",
          "skill_name": "Programming Knowledge",
          "evidence_contribution": 10.0,
          "performance_impact": 0.80,
          "progression_status": "advancing",
          "subskill_breakdown": [
            {
              "subskill_id": "SS008",
              "evidence_volume": 10.0,
              "performance_score": 0.80
            }
          ]
        }
      ],
      "scoring_metadata": {
        "scoring_algorithm_version": "v2.1",
        "calculation_timestamp": "2025-01-15T13:30:15Z"
      }
    },
    "diagnostic_intelligence": {
      "performance_insights": {
        "strength_areas": [
          "Basic programming concepts",
          "Easy to medium difficulty questions",
          "Time management in assessments"
        ],
        "improvement_areas": [
          "Complex programming concepts",
          "Advanced algorithmic thinking",
          "Problem-solving under time pressure"
        ],
        "performance_patterns": [
          {
            "pattern_type": "difficulty_dependent",
            "description": "Performance varies with question difficulty - strong on easy/medium, weaker on hard questions",
            "evidence": [
              "100% accuracy on easy questions",
              "66% accuracy on medium questions",
              "0% accuracy on hard questions"
            ],
            "implications": "May need more practice with advanced concepts"
          }
        ],
        "competency_demonstrations": [
          {
            "competency_area": "Programming Fundamentals",
            "demonstration_level": "developing",
            "supporting_evidence": [
              "Good understanding of basic concepts",
              "Appropriate time management"
            ],
            "next_level_indicators": [
              "Improved performance on complex questions",
              "Better problem-solving strategies"
            ]
          }
        ]
      },
      "learning_behavior_analysis": {
        "engagement_level": "moderate",
        "problem_solving_approach": "Direct approach to questions without excessive deliberation",
        "help_seeking_behavior": {
          "appropriateness": "appropriate",
          "frequency": "appropriate",
          "effectiveness": "Did not seek help, completed independently"
        },
        "persistence_indicators": [
          "Completed all questions",
          "Spent appropriate time on difficult questions"
        ],
        "metacognitive_awareness": "Shows reasonable self-regulation in time management"
      },
      "skill_development_recommendations": [
        {
          "recommendation_type": "concept_review",
          "target_skill_area": "Advanced Programming Concepts",
          "priority_level": "high",
          "specific_actions": [
            "Review complex algorithmic concepts",
            "Practice with challenging programming problems",
            "Study advanced data structures"
          ],
          "timeline_recommendation": "Focus on this over next 2-3 study sessions",
          "success_indicators": [
            "Improved performance on hard questions",
            "Better understanding of complex algorithms"
          ]
        }
      ],
      "prerequisite_analysis": {
        "prerequisite_gaps_identified": true,
        "foundation_strength": "adequate",
        "missing_prerequisites": [
          {
            "prerequisite_skill": "Advanced Algorithmic Thinking",
            "evidence_of_gap": [
              "Incorrect answer on complex algorithm question",
              "Extended time spent on advanced concepts"
            ],
            "impact_level": "moderate",
            "remediation_suggestions": [
              "Review algorithmic complexity concepts",
              "Practice with advanced problem-solving patterns"
            ]
          }
        ]
      },
      "diagnostic_confidence": 0.85
    },
    "feedback_generation": {
      "performance_summary": {
        "overall_assessment": "Solid understanding of fundamental programming concepts with room for growth in more advanced areas.",
        "key_strengths": [
          "Strong grasp of basic programming principles",
          "Good time management during assessment",
          "Consistent performance on familiar concepts"
        ],
        "primary_opportunities": [
          "Advanced algorithmic thinking",
          "Complex problem-solving strategies",
          "Performance on challenging material"
        ],
        "achievement_highlights": [
          "Perfect accuracy on foundational concepts",
          "Efficient completion of straightforward questions",
          "Independent work without assistance"
        ],
        "progress_recognition": "Your foundation in programming concepts is solid - now it's time to tackle more advanced challenges!"
      },
      "detailed_insights": {
        "competency_development": [
          {
            "skill_name": "Programming Knowledge",
            "skill_id": "S008",
            "current_level": "Developing",
            "progress_description": "Good foundation in basic concepts with need for advancement in complex areas",
            "specific_demonstrations": [
              "Correct understanding of fundamental programming principles",
              "Appropriate problem-solving pace"
            ],
            "growth_areas": [
              "Advanced algorithmic concepts",
              "Complex problem-solving strategies"
            ],
            "next_development_focus": "Building advanced programming problem-solving skills"
          }
        ],
        "subskill_feedback": [
          {
            "subskill_name": "Programming Fundamentals",
            "subskill_id": "SS008",
            "performance_level": "Good",
            "evidence_observed": "Demonstrated solid understanding of basic programming concepts with 80% accuracy overall",
            "encouragement": "Your foundation in programming is strong - you clearly understand the core concepts!",
            "development_guidance": "Focus next on more advanced concepts and complex problem-solving scenarios"
          }
        ],
        "learning_behavior_insights": {
          "problem_solving_approach": "You approach problems directly and efficiently, which is good for time management",
          "engagement_quality": "Good engagement with steady focus throughout the assessment",
          "independence_level": "Excellent - completed assessment entirely independently",
          "persistence_demonstration": "Good persistence, spending appropriate time even on challenging questions",
          "help_seeking_effectiveness": "Shows good independence by working through questions without assistance"
        }
      },
      "actionable_guidance": {
        "immediate_next_steps": [
          {
            "action": "Review advanced algorithmic concepts",
            "rationale": "This will help bridge the gap between your strong foundation and more complex programming challenges",
            "resources": ["Algorithm textbooks", "Advanced programming tutorials", "Complex problem sets"],
            "timeline": "Spend focused time over next 2 weeks",
            "success_indicators": [
              "Improved performance on complex programming questions",
              "Better understanding of algorithmic efficiency"
            ]
          }
        ],
        "practice_recommendations": [
          {
            "skill_focus": "Advanced Programming Concepts",
            "recommended_activities": [
              "Complex algorithm implementation exercises",
              "Advanced data structure problems",
              "Programming challenge platforms"
            ],
            "practice_strategies": [
              "Start with guided examples of complex algorithms",
              "Practice breaking down complex problems into steps",
              "Work on time complexity analysis"
            ],
            "difficulty_progression": "Begin with moderately complex problems, gradually increase to advanced challenges"
          }
        ],
        "study_strategies": [
          {
            "strategy_type": "conceptual_review",
            "strategy_description": "Study advanced programming concepts with focus on understanding rather than memorization",
            "implementation_guidance": "Review concepts, then immediately practice with hands-on coding problems",
            "expected_benefits": [
              "Stronger foundation for complex programming",
              "Better problem-solving confidence"
            ]
          }
        ]
      },
      "motivation_elements": {
        "encouragement_messages": [
          "Your programming foundation is really solid - you're ready for the next level of challenges!",
          "The consistency in your basic concept understanding shows you have good learning habits"
        ],
        "progress_celebration": [
          "Perfect performance on fundamental concepts shows mastery of the basics",
          "Great job completing the entire assessment independently"
        ],
        "confidence_building": [
          "You have the foundation needed for advanced programming success",
          "Your approach to problems shows good logical thinking skills"
        ]
      }
    },
    "evaluation_metadata": {
      "pipeline_version": "v16.1.0",
      "llm_provider_info": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_version": "2024-06-01"
      },
      "processing_time_seconds": 28.5,
      "evaluation_phases_completed": [
        "validity_analysis",
        "scoring_calculation",
        "diagnostic_intelligence",
        "feedback_generation"
      ],
      "quality_indicators": {
        "response_completeness": 0.98,
        "evaluation_consistency": 0.94,
        "diagnostic_depth": 0.82
      }
    }
  }
}
```

This schema enables comprehensive evaluation output capture across all activity types and evaluation phases, supporting the complete Evaluator v16 assessment and learning analytics pipeline.