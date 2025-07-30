# Activity Transcript Schema Documentation

## Overview

This schema defines the complete structure for activity transcript data that captures learner interactions and responses during activity completion. The transcript serves as input to the evaluation pipeline and contains all necessary data for comprehensive assessment across all 5 activity types (CR, COD, RP, SR, BR).

## Purpose

- **Evaluation Pipeline Input**: Primary data structure consumed by `evaluation_pipeline.py`
- **Learner Response Capture**: Comprehensive recording of all learner interactions
- **Validity Analysis Support**: Detailed assistance tracking for evidence quality assessment
- **Interactive Activity State**: Session management for RP and BR activities
- **Performance Analytics**: Timing and engagement data for learning insights

## Complete JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["learner_id", "activity_id", "activity_transcript"],
  "properties": {
    "learner_id": {
      "type": "string",
      "description": "Unique identifier for the learner"
    },
    "activity_id": {
      "type": "string",
      "description": "Unique identifier for the activity"
    },
    "activity_transcript": {
      "type": "object",
      "required": ["activity_generation_output", "student_engagement"],
      "properties": {
        "activity_generation_output": {
          "type": "object",
          "description": "Complete activity structure from generation schema"
        },
        "student_engagement": {
          "type": "object",
          "required": [
            "start_timestamp",
            "submit_timestamp", 
            "completion_status",
            "component_responses",
            "timing_data",
            "assistance_log"
          ],
          "properties": {
            "start_timestamp": {
              "type": "string",
              "format": "date-time",
              "description": "ISO timestamp when learner started activity"
            },
            "submit_timestamp": {
              "type": "string", 
              "format": "date-time",
              "description": "ISO timestamp when learner submitted activity"
            },
            "completion_status": {
              "type": "string",
              "enum": ["completed", "partial", "abandoned", "timeout"],
              "description": "Overall completion status of activity"
            },
            "component_responses": {
              "type": "array",
              "items": {
                "$ref": "#/definitions/component_response"
              },
              "description": "Array of responses for each component"
            },
            "student_interactions": {
              "type": "array",
              "items": {
                "$ref": "#/definitions/interaction_event"
              },
              "description": "Detailed log of all user interactions"
            },
            "timing_data": {
              "$ref": "#/definitions/timing_data"
            },
            "assistance_log": {
              "type": "array",
              "items": {
                "$ref": "#/definitions/assistance_event"
              },
              "description": "Log of all assistance provided to learner"
            }
          }
        }
      }
    }
  },
  "definitions": {
    "component_response": {
      "type": "object",
      "required": [
        "component_id",
        "response_content",
        "response_timestamp",
        "component_completion_status"
      ],
      "properties": {
        "component_id": {
          "type": "string",
          "description": "ID matching component from activity generation"
        },
        "response_content": {
          "oneOf": [
            {
              "type": "string",
              "description": "Text response for CR activities"
            },
            {
              "type": "object",
              "description": "Structured response for complex activities"
            }
          ]
        },
        "response_timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "ISO timestamp of response submission"
        },
        "component_completion_status": {
          "type": "string",
          "enum": ["completed", "partial", "skipped"],
          "description": "Completion status for this component"
        },
        "response_metadata": {
          "$ref": "#/definitions/response_metadata"
        }
      }
    },
    "response_metadata": {
      "type": "object",
      "properties": {
        "line_count": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of lines in response"
        },
        "character_count": {
          "type": "integer", 
          "minimum": 0,
          "description": "Total character count including spaces"
        },
        "word_count": {
          "type": "integer",
          "minimum": 0, 
          "description": "Total word count"
        },
        "has_imports": {
          "type": "boolean",
          "description": "Whether code response contains import statements"
        },
        "has_functions": {
          "type": "boolean",
          "description": "Whether code response contains function definitions"
        },
        "syntax_valid": {
          "type": "boolean",
          "description": "Whether code response has valid syntax"
        },
        "execution_attempted": {
          "type": "boolean",
          "description": "Whether learner attempted to execute code"
        },
        "execution_successful": {
          "type": "boolean",
          "description": "Whether code execution was successful"
        },
        "response_language": {
          "type": "string",
          "description": "Programming language used (for COD activities)"
        },
        "revision_count": {
          "type": "integer",
          "minimum": 0,
          "description": "Number of times response was edited"
        },
        "time_spent_seconds": {
          "type": "integer",
          "minimum": 0,
          "description": "Total time spent on this component"
        }
      }
    },
    "interaction_event": {
      "type": "object",
      "required": ["timestamp", "interaction_type", "component_id"],
      "properties": {
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "ISO timestamp of interaction"
        },
        "interaction_type": {
          "type": "string",
          "enum": [
            "click", "type", "select", "submit", 
            "request_help", "navigation", "focus",
            "blur", "scroll", "copy", "paste"
          ],
          "description": "Type of user interaction"
        },
        "component_id": {
          "type": "string",
          "description": "Component where interaction occurred"
        },
        "interaction_data": {
          "type": "object",
          "properties": {
            "element_id": {
              "type": "string",
              "description": "Specific UI element identifier"
            },
            "action": {
              "type": "string", 
              "description": "Specific action performed"
            },
            "value": {
              "oneOf": [
                {"type": "string"},
                {"type": "object"}
              ],
              "description": "Value or data associated with interaction"
            },
            "cursor_position": {
              "type": "integer",
              "description": "Cursor position for text interactions"
            },
            "selection_range": {
              "type": "object",
              "properties": {
                "start": {"type": "integer"},
                "end": {"type": "integer"}
              },
              "description": "Text selection range"
            },
            "ui_state": {
              "type": "object",
              "description": "UI state at time of interaction"
            }
          }
        }
      }
    },
    "timing_data": {
      "type": "object",
      "required": ["total_duration_minutes", "component_durations"],
      "properties": {
        "total_duration_minutes": {
          "type": "integer",
          "minimum": 0,
          "description": "Total time spent on activity in minutes"
        },
        "component_durations": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/component_duration"
          },
          "description": "Time spent on each component"
        },
        "pause_periods": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/pause_period"
          },
          "description": "Periods of inactivity during activity"
        }
      }
    },
    "component_duration": {
      "type": "object",
      "required": ["component_id", "duration_seconds"],
      "properties": {
        "component_id": {
          "type": "string",
          "description": "Component identifier"
        },
        "duration_seconds": {
          "type": "integer",
          "minimum": 0,
          "description": "Total time spent on component"
        },
        "active_time_seconds": {
          "type": "integer",
          "minimum": 0,
          "description": "Time component had focus"
        },
        "idle_time_seconds": {
          "type": "integer", 
          "minimum": 0,
          "description": "Time component was idle"
        }
      }
    },
    "pause_period": {
      "type": "object",
      "required": ["start_timestamp", "end_timestamp", "duration_seconds"],
      "properties": {
        "start_timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "When pause began"
        },
        "end_timestamp": {
          "type": "string",
          "format": "date-time", 
          "description": "When activity resumed"
        },
        "duration_seconds": {
          "type": "integer",
          "minimum": 0,
          "description": "Length of pause in seconds"
        },
        "reason": {
          "type": "string",
          "enum": ["user_initiated", "system_timeout", "navigation_away"],
          "description": "Reason for pause"
        }
      }
    },
    "assistance_event": {
      "type": "object",
      "required": [
        "timestamp",
        "assistance_type",
        "assistance_content",
        "component_id"
      ],
      "properties": {
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "When assistance was provided"
        },
        "assistance_type": {
          "type": "string",
          "enum": [
            "hint", "clarification", "example", "syntax_help",
            "conceptual_guidance", "full_solution", "encouragement",
            "technical_support", "time_extension"
          ],
          "description": "Type of assistance provided"
        },
        "assistance_content": {
          "type": "string",
          "description": "Content of assistance provided"
        },
        "assistance_description": {
          "type": "string",
          "description": "Description of what assistance was provided"
        },
        "component_id": {
          "type": "string",
          "description": "Component where assistance was requested"
        },
        "assistance_context": {
          "type": "string",
          "description": "Context that triggered assistance request"
        },
        "assistance_rationale": {
          "type": "string",
          "description": "Why this assistance was provided"
        },
        "student_state_before": {
          "type": "string",
          "description": "Learner's state before assistance"
        },
        "student_response_after": {
          "type": "string",
          "description": "How learner responded after assistance"
        },
        "effectiveness_rating": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "How effective the assistance was (0-1)"
        }
      }
    }
  }
}
```

## Activity Type Specific Examples

### Constructed Response (CR) Example

```json
{
  "learner_id": "L001",
  "activity_id": "CR001",
  "activity_transcript": {
    "activity_generation_output": {
      // Complete activity structure from generation schema
    },
    "student_engagement": {
      "start_timestamp": "2025-01-15T14:30:00Z",
      "submit_timestamp": "2025-01-15T15:15:00Z", 
      "completion_status": "completed",
      "component_responses": [
        {
          "component_id": "CR001_main",
          "response_content": "The shift to remote work has fundamentally altered team collaboration dynamics in both positive and challenging ways. Based on the provided survey data, 78% of employees report increased flexibility and work-life balance, while productivity metrics show a 12% increase in individual task completion. However, collaboration scores decreased by 23%, indicating significant challenges in team coordination...",
          "response_timestamp": "2025-01-15T15:15:00Z",
          "component_completion_status": "completed",
          "response_metadata": {
            "line_count": 25,
            "character_count": 2847,
            "word_count": 492,
            "revision_count": 7,
            "time_spent_seconds": 2100
          }
        }
      ],
      "student_interactions": [
        {
          "timestamp": "2025-01-15T14:30:15Z",
          "interaction_type": "focus",
          "component_id": "CR001_main",
          "interaction_data": {
            "element_id": "response_textarea",
            "action": "start_typing"
          }
        },
        {
          "timestamp": "2025-01-15T14:45:32Z",
          "interaction_type": "request_help",
          "component_id": "CR001_main", 
          "interaction_data": {
            "action": "hint_request",
            "value": "How should I structure my analysis?"
          }
        }
      ],
      "timing_data": {
        "total_duration_minutes": 45,
        "component_durations": [
          {
            "component_id": "CR001_main",
            "duration_seconds": 2700,
            "active_time_seconds": 2100,
            "idle_time_seconds": 600
          }
        ],
        "pause_periods": [
          {
            "start_timestamp": "2025-01-15T14:50:00Z",
            "end_timestamp": "2025-01-15T15:00:00Z",
            "duration_seconds": 600,
            "reason": "user_initiated"
          }
        ]
      },
      "assistance_log": [
        {
          "timestamp": "2025-01-15T14:45:35Z",
          "assistance_type": "hint",
          "assistance_content": "Consider organizing your analysis into: 1) Positive impacts with supporting data, 2) Negative impacts with evidence, 3) Recommendations based on your findings",
          "assistance_description": "Structure guidance for analysis essay",
          "component_id": "CR001_main",
          "assistance_context": "Student asked for help structuring analysis",
          "assistance_rationale": "Providing scaffolding without giving away content",
          "student_state_before": "Had written introduction but seemed unsure of direction",
          "student_response_after": "Reorganized response with clear sections",
          "effectiveness_rating": 0.8
        }
      ]
    }
  }
}
```

### Role Play (RP) Example

```json
{
  "learner_id": "L001",
  "activity_id": "RP001",
  "activity_transcript": {
    "activity_generation_output": {
      // Complete activity structure from generation schema
    },
    "student_engagement": {
      "start_timestamp": "2025-01-15T10:00:00Z",
      "submit_timestamp": "2025-01-15T10:25:00Z",
      "completion_status": "completed",
      "component_responses": [
        {
          "component_id": "RP001_conversation",
          "response_content": {
            "conversation_log": [
              {
                "turn_id": 1,
                "timestamp": "2025-01-15T10:02:00Z",
                "speaker": "learner",
                "message": "Hi Sarah, thank you for taking the time to meet with me today. I understand you're looking for a custom inventory management solution for your business?",
                "message_metadata": {
                  "response_time_seconds": 45,
                  "message_type": "greeting_inquiry",
                  "communication_style": "professional"
                }
              },
              {
                "turn_id": 2,
                "timestamp": "2025-01-15T10:02:15Z", 
                "speaker": "ai_character",
                "message": "Yes, that's right. Our current system is just spreadsheets and it's getting really unwieldy. We have about 500 SKUs and 3 locations, and I'm spending way too much time trying to track everything manually.",
                "message_metadata": {
                  "character_state": "explaining_problem",
                  "information_revealed": ["current_system", "scale", "pain_points"]
                }
              },
              {
                "turn_id": 3,
                "timestamp": "2025-01-15T10:03:00Z",
                "speaker": "learner", 
                "message": "I can definitely understand how challenging that must be. Can you tell me more about your three locations - are they all retail stores, or do you have warehouses as well? And how do you currently handle transfers between locations?",
                "message_metadata": {
                  "response_time_seconds": 30,
                  "message_type": "clarifying_question",
                  "skills_demonstrated": ["active_listening", "requirement_gathering"]
                }
              }
            ],
            "session_summary": {
              "total_turns": 12,
              "conversation_duration_minutes": 23,
              "objectives_achieved": [
                "understood_business_model",
                "identified_key_requirements", 
                "established_technical_constraints"
              ],
              "key_information_gathered": [
                "3 retail locations + 1 warehouse",
                "500 SKUs across clothing and accessories",
                "Current manual processes taking 10 hours/week",
                "Budget range $15,000-$25,000",
                "Timeline requirement: 3 months"
              ]
            }
          },
          "response_timestamp": "2025-01-15T10:25:00Z",
          "component_completion_status": "completed",
          "response_metadata": {
            "conversation_turns": 12,
            "average_response_time_seconds": 35,
            "total_speaking_time_seconds": 420,
            "questions_asked": 8,
            "follow_up_questions": 3
          }
        }
      ],
      "timing_data": {
        "total_duration_minutes": 25,
        "component_durations": [
          {
            "component_id": "RP001_conversation",
            "duration_seconds": 1500,
            "active_time_seconds": 1380,
            "idle_time_seconds": 120
          }
        ]
      },
      "assistance_log": [
        {
          "timestamp": "2025-01-15T10:15:00Z",
          "assistance_type": "encouragement",
          "assistance_content": "You're doing great with your questions. Remember to also ask about their current pain points and what success would look like for them.",
          "assistance_description": "Guidance on conversation direction",
          "component_id": "RP001_conversation",
          "assistance_context": "Mid-conversation coaching",
          "effectiveness_rating": 0.7
        }
      ]
    }
  }
}
```

### Coding Exercise (COD) Example

```json
{
  "learner_id": "L001", 
  "activity_id": "COD001",
  "activity_transcript": {
    "activity_generation_output": {
      // Complete activity structure from generation schema
    },
    "student_engagement": {
      "start_timestamp": "2025-01-15T16:00:00Z",
      "submit_timestamp": "2025-01-15T16:45:00Z",
      "completion_status": "completed",
      "component_responses": [
        {
          "component_id": "COD001_implementation",
          "response_content": {
            "code": "def fibonacci_memo(n, memo={}):\n    \"\"\"Calculate nth Fibonacci number using memoization\"\"\"\n    if n in memo:\n        return memo[n]\n    \n    if n <= 1:\n        return n\n    \n    memo[n] = fibonacci_memo(n-1, memo) + fibonacci_memo(n-2, memo)\n    return memo[n]\n\n# Test the function\nfor i in range(10):\n    print(f\"F({i}) = {fibonacci_memo(i)}\")",
            "explanation": "I implemented the Fibonacci function using memoization to optimize performance. The memo dictionary stores previously calculated values to avoid redundant recursive calls. This reduces the time complexity from O(2^n) to O(n). I included a simple test loop to verify the implementation works correctly."
          },
          "response_timestamp": "2025-01-15T16:45:00Z",
          "component_completion_status": "completed",
          "response_metadata": {
            "line_count": 14,
            "character_count": 487,
            "word_count": 89,
            "has_imports": false,
            "has_functions": true,
            "syntax_valid": true,
            "execution_attempted": true,
            "execution_successful": true,
            "response_language": "python",
            "revision_count": 4,
            "time_spent_seconds": 2200
          }
        }
      ],
      "timing_data": {
        "total_duration_minutes": 45,
        "component_durations": [
          {
            "component_id": "COD001_implementation",
            "duration_seconds": 2700,
            "active_time_seconds": 2200,
            "idle_time_seconds": 500
          }
        ]
      },
      "assistance_log": [
        {
          "timestamp": "2025-01-15T16:20:00Z",
          "assistance_type": "syntax_help",
          "assistance_content": "Make sure your function signature includes the memo parameter with a default value",
          "assistance_description": "Syntax guidance for memoization pattern",
          "component_id": "COD001_implementation",
          "assistance_context": "Student had syntax error in function definition",
          "effectiveness_rating": 0.9
        }
      ]
    }
  }
}
```

### Selected Response (SR) Example

```json
{
  "learner_id": "L001",
  "activity_id": "SR001", 
  "activity_transcript": {
    "activity_generation_output": {
      // Complete activity structure from generation schema
    },
    "student_engagement": {
      "start_timestamp": "2025-01-15T13:00:00Z",
      "submit_timestamp": "2025-01-15T13:12:00Z",
      "completion_status": "completed",
      "component_responses": [
        {
          "component_id": "SR001_questions",
          "response_content": {
            "Q001": {"selected": "B", "confidence": 0.8},
            "Q002": {"selected": "A", "confidence": 0.9},
            "Q003": {"selected": "C", "confidence": 0.6},
            "Q004": {"selected": "B", "confidence": 0.7},
            "Q005": {"selected": "D", "confidence": 0.9}
          },
          "response_timestamp": "2025-01-15T13:12:00Z",
          "component_completion_status": "completed",
          "response_metadata": {
            "questions_answered": 5,
            "questions_skipped": 0,
            "average_time_per_question_seconds": 144,
            "revision_count": 2,
            "time_spent_seconds": 720
          }
        }
      ],
      "timing_data": {
        "total_duration_minutes": 12,
        "component_durations": [
          {
            "component_id": "SR001_questions", 
            "duration_seconds": 720,
            "active_time_seconds": 720,
            "idle_time_seconds": 0
          }
        ]
      },
      "assistance_log": []
    }
  }
}
```

### Branching Scenario (BR) Example

```json
{
  "learner_id": "L001",
  "activity_id": "BR001",
  "activity_transcript": {
    "activity_generation_output": {
      // Complete activity structure from generation schema
    },
    "student_engagement": {
      "start_timestamp": "2025-01-15T11:00:00Z",
      "submit_timestamp": "2025-01-15T11:30:00Z",
      "completion_status": "completed",
      "component_responses": [
        {
          "component_id": "BR001_decisions",
          "response_content": {
            "decision_path": [
              {
                "decision_point": "DP001",
                "option_selected": "OPT002",
                "timestamp": "2025-01-15T11:05:00Z",
                "reasoning": "Chose to escalate to manager because the issue seemed beyond my authority level"
              },
              {
                "decision_point": "DP002", 
                "option_selected": "OPT001",
                "timestamp": "2025-01-15T11:15:00Z",
                "reasoning": "Decided to gather more information before taking action"
              },
              {
                "decision_point": "DP003",
                "option_selected": "OPT003",
                "timestamp": "2025-01-15T11:25:00Z", 
                "reasoning": "Implemented the solution with team input to ensure buy-in"
              }
            ],
            "final_outcome": "successful_resolution",
            "path_score": 0.85
          },
          "response_timestamp": "2025-01-15T11:30:00Z",
          "component_completion_status": "completed",
          "response_metadata": {
            "decision_points_completed": 3,
            "average_decision_time_seconds": 300,
            "path_efficiency": 0.9,
            "time_spent_seconds": 1800
          }
        }
      ],
      "timing_data": {
        "total_duration_minutes": 30,
        "component_durations": [
          {
            "component_id": "BR001_decisions",
            "duration_seconds": 1800,
            "active_time_seconds": 1650,
            "idle_time_seconds": 150
          }
        ]
      },
      "assistance_log": [
        {
          "timestamp": "2025-01-15T11:20:00Z",
          "assistance_type": "clarification",
          "assistance_content": "Remember to consider the long-term impact of your decisions on team relationships",
          "assistance_description": "Guidance on decision-making criteria",
          "component_id": "BR001_decisions",
          "assistance_context": "Student seemed focused only on immediate outcomes",
          "effectiveness_rating": 0.7
        }
      ]
    }
  }
}
```

## Integration with Backend Modules

### evaluation_pipeline.py Integration

The Evaluation Pipeline uses this transcript schema as its primary input:

1. **Pipeline Entry Point**:
   ```python
   def run_evaluation_pipeline(activity_transcript: Dict) -> Dict:
       # Validates transcript against schema
       # Extracts components for each evaluation phase
       pass
   ```

2. **Component Response Processing**:
   ```python
   def process_component_responses(component_responses: List[Dict]):
       # Processes responses by activity type
       # Handles different response content structures
       pass
   ```

3. **Assistance Analysis**:
   ```python
   def analyze_assistance_impact(assistance_log: List[Dict]) -> float:
       # Calculates validity modifier based on assistance
       # Uses assistance type and effectiveness ratings
       pass
   ```

### learner_manager.py Integration

Learner Manager persists transcript data:

1. **Activity Record Storage**:
   ```python
   def add_activity_record(learner_id: str, transcript: Dict):
       # Stores complete transcript with evaluation results
       # Updates learner progress tracking
       pass
   ```

2. **Timing Analytics**:
   ```python
   def extract_timing_insights(timing_data: Dict) -> Dict:
       # Analyzes engagement patterns
       # Identifies learning behavior trends
       pass
   ```

## Validation Rules

### Required Data Validation
- All required fields must be present and properly typed
- Timestamps must be valid ISO 8601 format
- Completion status must align with component responses

### Timing Data Consistency
- `submit_timestamp` must be after `start_timestamp`
- Component durations must be realistic and sum appropriately
- Pause periods must not overlap with active periods

### Response Content Validation
- Response content must match expected format for activity type
- Metadata fields must be consistent with response content
- Interactive activities require properly structured conversation/decision logs

### Assistance Log Validation
- Assistance timestamps must fall within activity duration
- Assistance types must be appropriate for component context
- Effectiveness ratings must be between 0.0 and 1.0

This schema enables comprehensive capture of learner engagement data across all activity types, supporting detailed evaluation, validity analysis, and learning analytics throughout the Evaluator v16 pipeline.