# Learner Profile Schema Documentation

## Overview

This schema defines the complete structure for learner profile data managed by the `learner_manager.py` backend module. It encompasses learner demographics, complete activity history, skill progress tracking with dual-gate scoring, and competency development over time. This serves as the persistent data store for all learner-related information in the Evaluator v16 system.

## Purpose

- **Learner Data Persistence**: Complete learner information managed by `learner_manager.py`
- **Progress Tracking**: Comprehensive skill and competency progression with dual-gate scoring
- **Historical Record**: Complete activity history with evaluation results
- **Analytics Foundation**: Rich data structure for learning analytics and trend analysis
- **Scoring Engine Integration**: Current state data for dual-gate calculations

## Complete JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["learner_id", "created", "last_updated", "profile", "activities", "skill_progress", "competency_progress", "metadata"],
  "properties": {
    "learner_id": {
      "type": "string",
      "description": "Unique identifier for the learner",
      "pattern": "^L[0-9]{3,}$"
    },
    "created": {
      "type": "string",
      "format": "date-time",
      "description": "ISO timestamp when learner profile was created"
    },
    "last_updated": {
      "type": "string",
      "format": "date-time",
      "description": "ISO timestamp of last profile update"
    },
    "profile": {
      "$ref": "#/definitions/learner_profile"
    },
    "activities": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/activity_reference"
      },
      "description": "References to completed activities"
    },
    "skill_progress": {
      "type": "object",
      "patternProperties": {
        "^S[0-9]{3}$": {
          "$ref": "#/definitions/skill_progress_record"
        }
      },
      "description": "Progress tracking for each skill (keyed by skill ID)"
    },
    "competency_progress": {
      "type": "object",
      "patternProperties": {
        "^C[0-9]{3}$": {
          "$ref": "#/definitions/competency_progress_record"
        }
      },
      "description": "Progress tracking for each competency (keyed by competency ID)"
    },
    "metadata": {
      "$ref": "#/definitions/learner_metadata"
    }
  },
  "definitions": {
    "learner_profile": {
      "type": "object",
      "required": ["name", "email", "enrollment_date", "status", "experience_level"],
      "properties": {
        "name": {
          "type": "string",
          "description": "Learner's display name"
        },
        "email": {
          "type": "string",
          "format": "email",
          "description": "Learner's email address (can be simulated for testing)"
        },
        "enrollment_date": {
          "type": "string",
          "format": "date-time",
          "description": "ISO timestamp of enrollment"
        },
        "status": {
          "type": "string",
          "enum": ["active", "inactive", "suspended", "graduated"],
          "description": "Current learner status"
        },
        "background": {
          "type": "string",
          "description": "Learner background information"
        },
        "experience_level": {
          "type": "string",
          "enum": ["beginner", "intermediate", "advanced"],
          "description": "Overall experience level assessment"
        },
        "learning_goals": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Stated learning objectives"
        },
        "preferred_difficulty": {
          "type": "string",
          "enum": ["adaptive", "challenging", "supportive"],
          "description": "Preferred difficulty level"
        }
      }
    },
    "activity_reference": {
      "type": "object",
      "required": ["activity_id", "completion_timestamp", "evaluation_result"],
      "properties": {
        "activity_id": {
          "type": "string",
          "description": "Activity identifier"
        },
        "completion_timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "When activity was completed"
        },
        "activity_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Overall activity score"
        },
        "completion_status": {
          "type": "string",
          "enum": ["completed", "partial", "abandoned", "timeout"],
          "description": "How the activity was completed"
        },
        "duration_minutes": {
          "type": "integer",
          "minimum": 0,
          "description": "Time spent on activity"
        },
        "evaluation_result": {
          "type": "object",
          "description": "Complete evaluation output from evaluation pipeline"
        },
        "activity_transcript": {
          "type": "object", 
          "description": "Complete activity transcript with learner responses"
        },
        "scored": {
          "type": "boolean",
          "description": "Whether dual-gate scoring has been applied"
        }
      }
    },
    "skill_progress_record": {
      "type": "object",
      "required": [
        "skill_name",
        "cumulative_score", 
        "total_adjusted_evidence",
        "activity_count",
        "gate_1_status",
        "gate_2_status",
        "overall_status",
        "last_updated"
      ],
      "properties": {
        "skill_name": {
          "type": "string",
          "description": "Human-readable skill name"
        },
        "competency_id": {
          "type": "string",
          "description": "Parent competency for this skill"
        },
        "cumulative_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Running average of performance scores"
        },
        "total_adjusted_evidence": {
          "type": "number",
          "minimum": 0.0,
          "description": "Total evidence volume with decay applied"
        },
        "activity_count": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of activities targeting this skill"
        },
        "gate_1_status": {
          "type": "string",
          "enum": ["passed", "approaching", "developing", "needs_improvement"],
          "description": "Performance gate status (≥0.75 = passed)"
        },
        "gate_2_status": {
          "type": "string",
          "enum": ["passed", "approaching", "developing", "insufficient_evidence"],
          "description": "Evidence volume gate status (≥threshold = passed)"
        },
        "overall_status": {
          "type": "string",
          "enum": ["mastered", "progressing", "developing", "not_started"],
          "description": "Combined assessment of skill mastery"
        },
        "last_activity_date": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "When skill was last practiced"
        },
        "last_updated": {
          "type": "string",
          "format": "date-time",
          "description": "When skill progress was last updated"
        },
        "activities": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/skill_activity_record"
          },
          "description": "Detailed record of activities targeting this skill"
        },
        "confidence_interval_lower": {
          "type": ["number", "null"],
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Lower bound of performance confidence interval"
        },
        "confidence_interval_upper": {
          "type": ["number", "null"],
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Upper bound of performance confidence interval"
        },
        "standard_error": {
          "type": ["number", "null"],
          "minimum": 0.0,
          "description": "Standard error of performance estimate"
        },
        "subskill_breakdown": {
          "type": "object",
          "patternProperties": {
            "^SS[0-9]{3}$": {
              "$ref": "#/definitions/subskill_progress"
            }
          },
          "description": "Progress breakdown by constituent subskills"
        }
      }
    },
    "skill_activity_record": {
      "type": "object",
      "required": [
        "activity_id",
        "activity_score",
        "target_evidence_volume",
        "validity_modifier",
        "adjusted_evidence_volume",
        "timestamp"
      ],
      "properties": {
        "activity_id": {
          "type": "string",
          "description": "Activity identifier"
        },
        "activity_score": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Performance score from this activity"
        },
        "target_evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Target evidence volume for this skill"
        },
        "validity_modifier": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Validity adjustment based on assistance"
        },
        "adjusted_evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Evidence volume after validity adjustment"
        },
        "sem": {
          "type": "number",
          "minimum": 0.0,
          "description": "Standard error of measurement for this activity"
        },
        "decay_factor": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Decay factor applied based on activity position"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "When activity was completed"
        },
        "activity_type": {
          "type": "string",
          "enum": ["CR", "COD", "RP", "SR", "BR"],
          "description": "Type of activity"
        },
        "completion_status": {
          "type": "string",
          "enum": ["completed", "partial", "abandoned", "timeout"],
          "description": "How activity was completed"
        }
      }
    },
    "subskill_progress": {
      "type": "object",
      "required": [
        "subskill_name",
        "performance_level",
        "evidence_count",
        "last_demonstrated"
      ],
      "properties": {
        "subskill_name": {
          "type": "string",
          "description": "Human-readable subskill name"
        },
        "performance_level": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Average performance level for this subskill"
        },
        "evidence_count": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of activities providing evidence"
        },
        "last_demonstrated": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "When subskill was last demonstrated"
        },
        "trend": {
          "type": "string",
          "enum": ["improving", "stable", "declining", "insufficient_data"],
          "description": "Performance trend over time"
        },
        "confidence_level": {
          "type": "string",
          "enum": ["high", "medium", "low"],
          "description": "Confidence in performance assessment"
        }
      }
    },
    "competency_progress_record": {
      "type": "object",
      "required": [
        "competency_name",
        "skills_completed",
        "total_skills",
        "completion_fraction",
        "constituent_skills"
      ],
      "properties": {
        "competency_name": {
          "type": "string",
          "description": "Human-readable competency name"
        },
        "skills_completed": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of skills that have passed both gates"
        },
        "total_skills": {
          "type": "integer",
          "minimum": 1,
          "description": "Total number of skills in this competency"
        },
        "completion_fraction": {
          "type": "string",
          "pattern": "^[0-9]+/[0-9]+$",
          "description": "Completion fraction in 'completed/total' format"
        },
        "completion_percentage": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 100.0,
          "description": "Completion percentage"
        },
        "constituent_skills": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^S[0-9]{3}$"
          },
          "description": "Skill IDs that comprise this competency"
        },
        "competency_level": {
          "type": "string",
          "enum": ["not_started", "developing", "progressing", "advanced", "mastered"],
          "description": "Overall competency development level"
        },
        "estimated_completion": {
          "type": ["string", "null"],
          "format": "date",
          "description": "Estimated date of competency mastery"
        },
        "last_progress_update": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "When competency progress was last updated"
        }
      }
    },
    "learner_metadata": {
      "type": "object",
      "required": [
        "total_activities",
        "total_time_minutes",
        "last_activity_date"
      ],
      "properties": {
        "total_activities": {
          "type": "integer",
          "minimum": 0,
          "description": "Total number of activities completed"
        },
        "total_time_minutes": {
          "type": "integer",
          "minimum": 0,
          "description": "Total time spent on activities"
        },
        "last_activity_date": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "When learner last completed an activity"
        },
        "average_session_duration": {
          "type": "number",
          "minimum": 0.0,
          "description": "Average time per activity session"
        },
        "completion_rate": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Rate of successful activity completion"
        },
        "streak_current": {
          "type": "integer",
          "minimum": 0,
          "description": "Current consecutive days with activity"
        },
        "streak_longest": {
          "type": "integer",
          "minimum": 0,
          "description": "Longest consecutive day streak"
        },
        "learning_analytics": {
          "$ref": "#/definitions/learning_analytics"
        }
      }
    },
    "learning_analytics": {
      "type": "object",
      "properties": {
        "engagement_patterns": {
          "type": "object",
          "properties": {
            "preferred_time_of_day": {
              "type": "string",
              "description": "Time period with highest engagement"
            },
            "session_frequency": {
              "type": "string",
              "enum": ["daily", "frequent", "regular", "sporadic", "infrequent"],
              "description": "Pattern of learning session frequency"
            },
            "break_patterns": {
              "type": "object",
              "properties": {
                "average_break_days": {"type": "number", "minimum": 0.0},
                "longest_break_days": {"type": "integer", "minimum": 0}
              }
            }
          }
        },
        "performance_trends": {
          "type": "object",
          "properties": {
            "overall_trajectory": {
              "type": "string",
              "enum": ["improving", "stable", "declining", "fluctuating"],
              "description": "Overall performance trend"
            },
            "recent_trend": {
              "type": "string",
              "enum": ["improving", "stable", "declining"],
              "description": "Trend over recent activities"
            },
            "consistency_score": {
              "type": "number",
              "minimum": 0.0,
              "maximum": 1.0,
              "description": "How consistent performance has been"
            }
          }
        },
        "learning_behavior": {
          "type": "object",
          "properties": {
            "help_seeking_frequency": {
              "type": "string",
              "enum": ["frequent", "moderate", "occasional", "rare"],
              "description": "How often learner seeks assistance"
            },
            "persistence_rating": {
              "type": "string",
              "enum": ["high", "medium", "low"],
              "description": "Assessment of learner persistence"
            },
            "challenge_preference": {
              "type": "string",
              "enum": ["seeks_challenge", "balanced", "prefers_support"],
              "description": "Learner's relationship with difficulty"
            }
          }
        },
        "skill_development_velocity": {
          "type": "object",
          "properties": {
            "fast_developing_skills": {
              "type": "array",
              "items": {"type": "string"},
              "description": "Skills showing rapid progress"
            },
            "slow_developing_skills": {
              "type": "array", 
              "items": {"type": "string"},
              "description": "Skills requiring more focus"
            },
            "average_mastery_time_days": {
              "type": "number",
              "minimum": 0.0,
              "description": "Average time to achieve skill mastery"
            }
          }
        }
      }
    }
  }
}
```

## Learner Profile Examples

### Complete Learner Profile Example

```json
{
  "learner_id": "L001",
  "created": "2024-12-01T10:00:00Z",
  "last_updated": "2025-01-15T15:45:00Z",
  "profile": {
    "name": "Alex Chen",
    "email": "alex.chen@example.edu",
    "enrollment_date": "2024-12-01T10:00:00Z",
    "status": "active",
    "background": "Computer Science undergraduate with some programming experience",
    "experience_level": "intermediate",
    "learning_goals": [
      "Master analytical reasoning skills",
      "Develop professional communication abilities",
      "Build systematic problem-solving approach"
    ],
    "preferred_difficulty": "challenging"
  },
  "activities": [
    {
      "activity_id": "CR001",
      "completion_timestamp": "2025-01-15T15:15:00Z",
      "activity_score": 0.78,
      "completion_status": "completed",
      "duration_minutes": 45,
      "evaluation_result": {
        // Complete evaluation output from evaluation pipeline
        "activity_record": {
          "activity_score": 0.78,
          "completion_status": "completed",
          "duration_minutes": 45
        },
        "diagnostic_intelligence": {
          "performance_insights": {
            "strength_areas": ["Data analysis", "Systematic thinking"],
            "improvement_areas": ["Critical evaluation", "Long-term analysis"]
          }
        }
      },
      "activity_transcript": {
        // Complete transcript from activity interaction
        "student_engagement": {
          "start_timestamp": "2025-01-15T14:30:00Z",
          "submit_timestamp": "2025-01-15T15:15:00Z",
          "completion_status": "completed"
        }
      },
      "scored": true
    },
    {
      "activity_id": "RP001", 
      "completion_timestamp": "2025-01-10T11:30:00Z",
      "activity_score": 0.85,
      "completion_status": "completed",
      "duration_minutes": 25,
      "evaluation_result": {
        "activity_record": {
          "activity_score": 0.85,
          "completion_status": "completed"
        }
      },
      "scored": true
    }
  ],
  "skill_progress": {
    "S001": {
      "skill_name": "Analytical Reasoning",
      "competency_id": "C001",
      "cumulative_score": 0.815,
      "total_adjusted_evidence": 28.5,
      "activity_count": 2,
      "gate_1_status": "passed",
      "gate_2_status": "approaching",
      "overall_status": "progressing",
      "last_activity_date": "2025-01-15T15:15:00Z",
      "last_updated": "2025-01-15T15:45:00Z",
      "activities": [
        {
          "activity_id": "RP001",
          "activity_score": 0.85,
          "target_evidence_volume": 15.0,
          "validity_modifier": 0.95,
          "adjusted_evidence_volume": 14.25,
          "sem": 0.12,
          "decay_factor": 0.9,
          "timestamp": "2025-01-10T11:30:00Z",
          "activity_type": "RP",
          "completion_status": "completed"
        },
        {
          "activity_id": "CR001",
          "activity_score": 0.78,
          "target_evidence_volume": 20.5,
          "validity_modifier": 0.9,
          "adjusted_evidence_volume": 18.45,
          "sem": 0.08,
          "decay_factor": 1.0,
          "timestamp": "2025-01-15T15:15:00Z",
          "activity_type": "CR",
          "completion_status": "completed"
        }
      ],
      "confidence_interval_lower": 0.73,
      "confidence_interval_upper": 0.90,
      "standard_error": 0.045,
      "subskill_breakdown": {
        "SS001": {
          "subskill_name": "Data Analysis",
          "performance_level": 0.82,
          "evidence_count": 2,
          "last_demonstrated": "2025-01-15T15:15:00Z",
          "trend": "improving",
          "confidence_level": "high"
        },
        "SS003": {
          "subskill_name": "Critical Thinking", 
          "performance_level": 0.77,
          "evidence_count": 2,
          "last_demonstrated": "2025-01-15T15:15:00Z",
          "trend": "stable",
          "confidence_level": "medium"
        }
      }
    },
    "S005": {
      "skill_name": "Professional Communication",
      "competency_id": "C002",
      "cumulative_score": 0.85,
      "total_adjusted_evidence": 14.25,
      "activity_count": 1,
      "gate_1_status": "passed",
      "gate_2_status": "insufficient_evidence",
      "overall_status": "developing",
      "last_activity_date": "2025-01-10T11:30:00Z",
      "last_updated": "2025-01-10T11:45:00Z",
      "activities": [
        {
          "activity_id": "RP001",
          "activity_score": 0.85,
          "target_evidence_volume": 15.0,
          "validity_modifier": 0.95,
          "adjusted_evidence_volume": 14.25,
          "sem": 0.10,
          "decay_factor": 1.0,
          "timestamp": "2025-01-10T11:30:00Z",
          "activity_type": "RP",
          "completion_status": "completed"
        }
      ],
      "confidence_interval_lower": 0.75,
      "confidence_interval_upper": 0.95,
      "standard_error": 0.10,
      "subskill_breakdown": {
        "SS015": {
          "subskill_name": "Active Listening",
          "performance_level": 0.88,
          "evidence_count": 1,
          "last_demonstrated": "2025-01-10T11:30:00Z",
          "trend": "insufficient_data",
          "confidence_level": "medium"
        },
        "SS016": {
          "subskill_name": "Questioning Techniques",
          "performance_level": 0.82,
          "evidence_count": 1,
          "last_demonstrated": "2025-01-10T11:30:00Z", 
          "trend": "insufficient_data",
          "confidence_level": "medium"
        }
      }
    }
  },
  "competency_progress": {
    "C001": {
      "competency_name": "Analytical and Critical Thinking",
      "skills_completed": 0,
      "total_skills": 4,
      "completion_fraction": "0/4",
      "completion_percentage": 0.0,
      "constituent_skills": ["S001", "S002", "S003", "S004"],
      "competency_level": "developing",
      "estimated_completion": null,
      "last_progress_update": "2025-01-15T15:45:00Z"
    },
    "C002": {
      "competency_name": "Professional Communication",
      "skills_completed": 0,
      "total_skills": 3,
      "completion_fraction": "0/3",
      "completion_percentage": 0.0,
      "constituent_skills": ["S005", "S006", "S007"],
      "competency_level": "developing",
      "estimated_completion": null,
      "last_progress_update": "2025-01-10T11:45:00Z"
    }
  },
  "metadata": {
    "total_activities": 2,
    "total_time_minutes": 70,
    "last_activity_date": "2025-01-15T15:15:00Z",
    "average_session_duration": 35.0,
    "completion_rate": 1.0,
    "streak_current": 2,
    "streak_longest": 2,
    "learning_analytics": {
      "engagement_patterns": {
        "preferred_time_of_day": "afternoon",
        "session_frequency": "regular",
        "break_patterns": {
          "average_break_days": 2.5,
          "longest_break_days": 5
        }
      },
      "performance_trends": {
        "overall_trajectory": "improving",
        "recent_trend": "stable",
        "consistency_score": 0.85
      },
      "learning_behavior": {
        "help_seeking_frequency": "moderate",
        "persistence_rating": "high",
        "challenge_preference": "seeks_challenge"
      },
      "skill_development_velocity": {
        "fast_developing_skills": ["S005"],
        "slow_developing_skills": [],
        "average_mastery_time_days": null
      }
    }
  }
}
```

### Skill Progress Detail Example

```json
{
  "S001": {
    "skill_name": "Analytical Reasoning",
    "competency_id": "C001",
    "cumulative_score": 0.742,
    "total_adjusted_evidence": 45.8,
    "activity_count": 4,
    "gate_1_status": "approaching",
    "gate_2_status": "passed",
    "overall_status": "progressing", 
    "last_activity_date": "2025-01-20T14:30:00Z",
    "last_updated": "2025-01-20T14:45:00Z",
    "activities": [
      {
        "activity_id": "CR001",
        "activity_score": 0.68,
        "target_evidence_volume": 25.0,
        "validity_modifier": 0.85,
        "adjusted_evidence_volume": 19.125,
        "sem": 0.12,
        "decay_factor": 0.729,
        "timestamp": "2024-12-15T10:00:00Z",
        "activity_type": "CR",
        "completion_status": "completed"
      },
      {
        "activity_id": "COD001",
        "activity_score": 0.72,
        "target_evidence_volume": 20.0,
        "validity_modifier": 0.90,
        "adjusted_evidence_volume": 14.58,
        "sem": 0.10,
        "decay_factor": 0.81,
        "timestamp": "2025-01-05T16:20:00Z",
        "activity_type": "COD",
        "completion_status": "completed"
      },
      {
        "activity_id": "CR002", 
        "activity_score": 0.79,
        "target_evidence_volume": 22.0,
        "validity_modifier": 0.95,
        "adjusted_evidence_volume": 18.81,
        "sem": 0.08,
        "decay_factor": 0.9,
        "timestamp": "2025-01-12T11:45:00Z",
        "activity_type": "CR",
        "completion_status": "completed"
      },
      {
        "activity_id": "CR003",
        "activity_score": 0.83,
        "target_evidence_volume": 28.0,
        "validity_modifier": 0.92,
        "adjusted_evidence_volume": 25.76,
        "sem": 0.06,
        "decay_factor": 1.0,
        "timestamp": "2025-01-20T14:30:00Z",
        "activity_type": "CR", 
        "completion_status": "completed"
      }
    ],
    "confidence_interval_lower": 0.68,
    "confidence_interval_upper": 0.81,
    "standard_error": 0.033,
    "subskill_breakdown": {
      "SS001": {
        "subskill_name": "Data Analysis",
        "performance_level": 0.78,
        "evidence_count": 4,
        "last_demonstrated": "2025-01-20T14:30:00Z",
        "trend": "improving",
        "confidence_level": "high"
      },
      "SS002": {
        "subskill_name": "Pattern Recognition",
        "performance_level": 0.71,
        "evidence_count": 3,
        "last_demonstrated": "2025-01-12T11:45:00Z",
        "trend": "stable",
        "confidence_level": "medium"
      },
      "SS003": {
        "subskill_name": "Critical Thinking",
        "performance_level": 0.74,
        "evidence_count": 4,
        "last_demonstrated": "2025-01-20T14:30:00Z",
        "trend": "improving",
        "confidence_level": "high"
      }
    }
  }
}
```

## Integration with Backend Modules

### learner_manager.py Integration

The Learner Manager module directly manages this schema:

1. **Profile Management**:
   ```python
   def create_learner_profile(profile_data: Dict) -> Dict:
       # Creates new learner profile matching this schema
       return new_learner_profile
   
   def update_learner_profile(learner_id: str, updates: Dict) -> bool:
       # Updates existing profile maintaining schema compliance
       pass
   ```

2. **Activity History Management**:
   ```python
   def add_activity_record(learner_id: str, activity_record: Dict) -> bool:
       # Adds activity to learner's history
       # Updates metadata totals and timestamps
       pass
   ```

3. **Skill Progress Updates**:
   ```python
   def update_skill_progress(learner_id: str, skill_results: Dict) -> bool:
       # Updates skill progress with dual-gate calculations
       # Maintains activity history and evidence calculations
       pass
   ```

### scoring_engine.py Integration

Scoring Engine uses learner profile for dual-gate calculations:

1. **Progress Calculation**:
   ```python
   def calculate_skill_progress(learner_profile: Dict, new_results: Dict) -> Dict:
       # Uses existing skill_progress to calculate updates
       # Applies evidence decay based on activity position
       pass
   ```

2. **Gate Status Assessment**:
   ```python
   def assess_dual_gates(skill_progress: Dict) -> Dict:
       # Evaluates Gate 1 (performance ≥ 0.75) and Gate 2 (evidence ≥ threshold)
       # Updates gate_1_status, gate_2_status, overall_status
       pass
   ```

### evaluation_pipeline.py Integration

Evaluation Pipeline updates learner profiles with results:

1. **Result Integration**:
   ```python
   def integrate_evaluation_results(learner_id: str, evaluation_output: Dict):
       # Adds evaluation results to learner profile
       # Triggers skill progress updates
       pass
   ```

## Data Management Features

### SQLite Integration

The learner manager supports SQLite persistence:

1. **Table Structure**:
   ```sql
   CREATE TABLE learners (
       learner_id TEXT PRIMARY KEY,
       profile_data TEXT,  -- JSON serialized profile
       created_timestamp TEXT,
       last_updated_timestamp TEXT
   );
   
   CREATE TABLE skill_progress (
       learner_id TEXT,
       skill_id TEXT,
       progress_data TEXT,  -- JSON serialized progress
       last_updated TEXT,
       PRIMARY KEY (learner_id, skill_id)
   );
   ```

2. **Atomic Updates**:
   ```python
   def atomic_profile_update(learner_id: str, updates: Dict) -> bool:
       # Ensures all profile updates are atomic
       # Maintains referential integrity
       pass
   ```

### Evidence Decay Implementation

```python
def apply_evidence_decay(activities: List[Dict]) -> List[Dict]:
    """Apply position-based evidence decay using 0.9^(position-1) formula"""
    for i, activity in enumerate(activities):
        position = len(activities) - i  # Most recent = position 1
        decay_factor = 0.9 ** (position - 1)
        activity['decay_factor'] = decay_factor
        activity['decayed_evidence'] = activity['adjusted_evidence_volume'] * decay_factor
    return activities
```

### Dual-Gate Scoring Implementation

```python
def evaluate_dual_gates(skill_progress: Dict) -> Dict:
    """Evaluate both performance and evidence gates"""
    performance_score = skill_progress['cumulative_score']
    evidence_volume = skill_progress['total_adjusted_evidence']
    
    # Gate 1: Performance threshold
    gate_1_passed = performance_score >= 0.75
    
    # Gate 2: Evidence threshold (skill-dependent)
    evidence_threshold = get_evidence_threshold(skill_progress['skill_id'])
    gate_2_passed = evidence_volume >= evidence_threshold
    
    return {
        'gate_1_status': 'passed' if gate_1_passed else determine_gate_1_level(performance_score),
        'gate_2_status': 'passed' if gate_2_passed else determine_gate_2_level(evidence_volume, evidence_threshold),
        'overall_status': determine_overall_status(gate_1_passed, gate_2_passed)
    }
```

## Validation Rules

### Schema Compliance
- All required fields must be present and properly typed
- Learner IDs must follow pattern: L + 3+ digits
- Skill/Competency IDs must match domain model references
- Timestamps must be valid ISO 8601 format

### Data Consistency
- Activity references must have corresponding evaluation results
- Skill progress must be consistent with activity history
- Competency progress must reflect constituent skill statuses
- Evidence volumes must be non-negative

### Dual-Gate Logic Validation
- Gate statuses must align with score/evidence thresholds
- Overall status must reflect both gate conditions
- Evidence decay must be properly applied by activity position

### Performance Metrics Validation
- Cumulative scores must be between 0.0 and 1.0
- Activity counts must match activity array lengths
- Timestamps must be chronologically consistent
- Confidence intervals must be properly bounded

This schema enables comprehensive learner data management across the complete Evaluator v16 system, supporting persistent progress tracking, sophisticated skill assessment with dual-gate scoring, and rich learning analytics for personalized education delivery.