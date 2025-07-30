# Activity Generation Schema Documentation

## Overview

This schema defines the complete structure for activity JSON files that are loaded and validated by the `activity_manager.py` backend module. It serves as the contract for activity data across all 5 supported activity types (CR, COD, RP, SR, BR) and enables runtime validation, proper data flow, and system integration.

## Purpose

- **Runtime Validation**: JSON schema validation in `activity_manager.py`
- **Data Structure Contract**: Ensures consistency between activity creation and evaluation
- **API Documentation**: Defines expected structure for activity generation pipeline
- **Integration Guide**: Enables proper data flow from activity selection through evaluation

## Complete JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["learner_id", "activity_id", "activity_generation_output"],
  "properties": {
    "learner_id": {
      "type": "string",
      "description": "Unique identifier for the learner"
    },
    "activity_id": {
      "type": "string", 
      "description": "Unique identifier for the activity",
      "pattern": "^[A-Z]{2,3}[0-9]{3}$"
    },
    "activity_generation_output": {
      "type": "object",
      "required": [
        "activity_type",
        "activity_type_variant", 
        "activity_purpose",
        "l_d_complexity",
        "evaluation_method",
        "components"
      ],
      "properties": {
        "activity_type": {
          "type": "string",
          "enum": [
            "instructional_content",
            "selected_response", 
            "constructed_response",
            "coding_exercise",
            "role_play",
            "branching_scenario"
          ],
          "description": "Primary activity classification"
        },
        "activity_type_variant": {
          "type": "string",
          "description": "Specific variant within activity type"
        },
        "activity_purpose": {
          "type": "string",
          "enum": ["instructional", "guided", "challenge"],
          "description": "Learning objective purpose"
        },
        "l_d_complexity": {
          "type": "string",
          "pattern": "^L[1-4]-D[1-4]$",
          "description": "Cognitive level (L1-L4) and depth level (D1-D4)"
        },
        "evaluation_method": {
          "type": "string",
          "enum": ["rubric_scored", "autoscored", "mixed"],
          "description": "Method for evaluating learner responses"
        },
        "components": {
          "type": "array",
          "minItems": 1,
          "items": {
            "$ref": "#/definitions/component"
          },
          "description": "Array of activity components"
        }
      }
    }
  },
  "definitions": {
    "component": {
      "type": "object",
      "required": [
        "component_id",
        "component_type", 
        "component_purpose",
        "component_weight",
        "student_facing_content",
        "subskill_targeting"
      ],
      "properties": {
        "component_id": {
          "type": "string",
          "description": "Unique identifier for component within activity"
        },
        "component_type": {
          "type": "string",
          "description": "Type of component (matches activity type patterns)"
        },
        "component_purpose": {
          "type": "string", 
          "description": "Educational purpose of this component"
        },
        "component_weight": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Weight of component in final score (must sum to 1.0)"
        },
        "student_facing_content": {
          "$ref": "#/definitions/student_content"
        },
        "scoring_rubric": {
          "$ref": "#/definitions/rubric",
          "description": "Required for rubric_scored activities (CR, COD, RP)"
        },
        "subskill_targeting": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/subskill_target"
          }
        },
        "interactive_configuration": {
          "$ref": "#/definitions/interactive_config",
          "description": "Required for interactive activities (RP, BR)"
        }
      }
    },
    "student_content": {
      "type": "object",
      "required": ["stem", "instructions", "response_format", "time_estimate"],
      "properties": {
        "stem": {
          "type": "string",
          "description": "Main problem or question statement"
        },
        "scenario": {
          "type": "string",
          "description": "Context or background scenario"
        },
        "given": {
          "type": "string",
          "description": "Given information or constraints"
        },
        "instructions": {
          "type": "string",
          "description": "Detailed instructions for learner response"
        },
        "response_format": {
          "type": "string",
          "description": "Expected format for learner response"
        },
        "assessment_information": {
          "type": "string",
          "description": "Information about how response will be evaluated"
        },
        "time_estimate": {
          "type": "integer",
          "minimum": 1,
          "description": "Estimated completion time in minutes"
        }
      }
    },
    "rubric": {
      "type": "object",
      "required": ["rubric_id", "target_component_evidence_volume", "aspects"],
      "properties": {
        "rubric_id": {
          "type": "string",
          "description": "Unique identifier for rubric"
        },
        "target_component_evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Target evidence volume for this component"
        },
        "aspects": {
          "type": "array",
          "minItems": 1,
          "items": {
            "$ref": "#/definitions/rubric_aspect"
          }
        }
      }
    },
    "rubric_aspect": {
      "type": "object",
      "required": [
        "aspect_id",
        "aspect_name", 
        "aspect_description",
        "aspect_weight",
        "target_evidence_volume",
        "primary_subskills",
        "anchor_points"
      ],
      "properties": {
        "aspect_id": {
          "type": "string",
          "description": "Unique identifier for rubric aspect"
        },
        "aspect_name": {
          "type": "string",
          "description": "Name of the aspect being evaluated"
        },
        "aspect_description": {
          "type": "string",
          "description": "Detailed description of what this aspect measures"
        },
        "aspect_weight": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Weight of aspect in component (must sum to 1.0)"
        },
        "target_evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Target evidence volume for this aspect"
        },
        "primary_subskills": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Primary subskills assessed by this aspect"
        },
        "secondary_subskills": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Secondary subskills assessed by this aspect"
        },
        "anchor_points": {
          "type": "object",
          "required": [
            "range_0_75_to_1_00",
            "range_0_50_to_0_74", 
            "range_0_25_to_0_49",
            "range_0_00_to_0_24"
          ],
          "properties": {
            "range_0_75_to_1_00": {
              "type": "string",
              "description": "Description of exemplary performance (0.75-1.00)"
            },
            "range_0_50_to_0_74": {
              "type": "string", 
              "description": "Description of proficient performance (0.50-0.74)"
            },
            "range_0_25_to_0_49": {
              "type": "string",
              "description": "Description of developing performance (0.25-0.49)"
            },
            "range_0_00_to_0_24": {
              "type": "string",
              "description": "Description of inadequate performance (0.00-0.24)"
            }
          }
        }
      }
    },
    "subskill_target": {
      "type": "object",
      "required": ["subskill_id", "weight_in_component", "target_evidence_volume"],
      "properties": {
        "subskill_id": {
          "type": "string",
          "description": "Subskill identifier from domain model"
        },
        "weight_in_component": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Weight of this subskill in component"
        },
        "target_evidence_volume": {
          "type": "number",
          "minimum": 0.0,
          "description": "Target evidence volume for this subskill"
        }
      }
    },
    "interactive_config": {
      "type": "object",
      "properties": {
        "role_play": {
          "$ref": "#/definitions/role_play_config"
        },
        "branching_scenario": {
          "$ref": "#/definitions/branching_config"
        }
      }
    },
    "role_play_config": {
      "type": "object",
      "required": [
        "character_profile",
        "scenario_context",
        "conversation_objectives",
        "success_criteria"
      ],
      "properties": {
        "character_profile": {
          "type": "string",
          "description": "AI character background and personality"
        },
        "scenario_context": {
          "type": "string", 
          "description": "Setting and context for role play"
        },
        "conversation_objectives": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Learning objectives for conversation"
        },
        "success_criteria": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Criteria for successful completion"
        },
        "conversation_turns_limit": {
          "type": "integer",
          "minimum": 1,
          "description": "Maximum conversation turns allowed"
        }
      }
    },
    "branching_config": {
      "type": "object",
      "required": ["initial_scenario", "decision_points", "outcome_paths"],
      "properties": {
        "initial_scenario": {
          "type": "string",
          "description": "Starting scenario description"
        },
        "decision_points": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/decision_point"
          }
        },
        "outcome_paths": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/outcome_path"
          }
        }
      }
    },
    "decision_point": {
      "type": "object", 
      "required": ["point_id", "scenario_text", "options"],
      "properties": {
        "point_id": {
          "type": "string",
          "description": "Unique identifier for decision point"
        },
        "scenario_text": {
          "type": "string",
          "description": "Scenario text at this decision point"
        },
        "options": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/decision_option"
          }
        }
      }
    },
    "decision_option": {
      "type": "object",
      "required": ["option_id", "option_text", "consequence_path"],
      "properties": {
        "option_id": {
          "type": "string",
          "description": "Unique identifier for option"
        },
        "option_text": {
          "type": "string",
          "description": "Text displayed for this option"
        },
        "consequence_path": {
          "type": "string",
          "description": "Path identifier for consequences"
        }
      }
    },
    "outcome_path": {
      "type": "object",
      "required": ["path_id", "path_description", "scoring_impact"],
      "properties": {
        "path_id": {
          "type": "string",
          "description": "Unique identifier for outcome path"
        },
        "path_description": {
          "type": "string",
          "description": "Description of consequences"
        },
        "scoring_impact": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Impact on final score"
        }
      }
    }
  }
}
```

## Activity Type Examples

### Constructed Response (CR) Example

```json
{
  "learner_id": "L001",
  "activity_id": "CR001",
  "activity_generation_output": {
    "activity_type": "constructed_response",
    "activity_type_variant": "analysis_essay",
    "activity_purpose": "challenge",
    "l_d_complexity": "L3-D3",
    "evaluation_method": "rubric_scored",
    "components": [
      {
        "component_id": "CR001_main",
        "component_type": "constructed_response",
        "component_purpose": "analysis_demonstration",
        "component_weight": 1.0,
        "student_facing_content": {
          "stem": "Analyze the impact of remote work policies on team collaboration and productivity.",
          "scenario": "Your company is evaluating permanent remote work options post-pandemic.",
          "given": "Employee survey data and productivity metrics from 2019-2023",
          "instructions": "Write a 500-800 word analysis that evaluates both positive and negative impacts, supported by evidence.",
          "response_format": "Structured essay with introduction, analysis, and recommendations",
          "assessment_information": "Responses evaluated on analysis depth, evidence use, and recommendation quality",
          "time_estimate": 45
        },
        "scoring_rubric": {
          "rubric_id": "CR001_analysis_rubric",
          "target_component_evidence_volume": 25.0,
          "aspects": [
            {
              "aspect_id": "analysis_depth",
              "aspect_name": "Depth of Analysis",
              "aspect_description": "Quality and thoroughness of impact analysis",
              "aspect_weight": 0.4,
              "target_evidence_volume": 10.0,
              "primary_subskills": ["SS001", "SS003"],
              "secondary_subskills": ["SS002"],
              "anchor_points": {
                "range_0_75_to_1_00": "Comprehensive analysis with nuanced understanding of multiple perspectives",
                "range_0_50_to_0_74": "Good analysis covering main impacts with some detail",
                "range_0_25_to_0_49": "Surface-level analysis with limited depth",
                "range_0_00_to_0_24": "Minimal or no meaningful analysis"
              }
            }
          ]
        },
        "subskill_targeting": [
          {
            "subskill_id": "SS001",
            "weight_in_component": 0.5,
            "target_evidence_volume": 12.5
          },
          {
            "subskill_id": "SS003", 
            "weight_in_component": 0.3,
            "target_evidence_volume": 7.5
          }
        ]
      }
    ]
  }
}
```

### Role Play (RP) Example

```json
{
  "learner_id": "L001",
  "activity_id": "RP001", 
  "activity_generation_output": {
    "activity_type": "role_play",
    "activity_type_variant": "client_consultation",
    "activity_purpose": "guided",
    "l_d_complexity": "L2-D2",
    "evaluation_method": "rubric_scored",
    "components": [
      {
        "component_id": "RP001_conversation",
        "component_type": "role_play_conversation",
        "component_purpose": "communication_skill_practice",
        "component_weight": 1.0,
        "student_facing_content": {
          "stem": "Conduct a client consultation to understand their project requirements",
          "scenario": "New client meeting to discuss a potential software development project",
          "instructions": "Lead a professional consultation conversation to gather requirements",
          "response_format": "Real-time conversation with AI client",
          "time_estimate": 20
        },
        "interactive_configuration": {
          "role_play": {
            "character_profile": "Sarah Chen, small business owner seeking custom inventory software",
            "scenario_context": "Initial consultation call to discuss software needs",
            "conversation_objectives": [
              "Understand client's business requirements",
              "Identify technical constraints",
              "Establish project scope and timeline"
            ],
            "success_criteria": [
              "Asks relevant discovery questions",
              "Demonstrates active listening", 
              "Provides clear explanations"
            ],
            "conversation_turns_limit": 15
          }
        },
        "subskill_targeting": [
          {
            "subskill_id": "SS005",
            "weight_in_component": 0.6,
            "target_evidence_volume": 15.0
          }
        ]
      }
    ]
  }
}
```

### Selected Response (SR) Example

```json
{
  "learner_id": "L001", 
  "activity_id": "SR001",
  "activity_generation_output": {
    "activity_type": "selected_response",
    "activity_type_variant": "multiple_choice_assessment",
    "activity_purpose": "instructional",
    "l_d_complexity": "L1-D1", 
    "evaluation_method": "autoscored",
    "components": [
      {
        "component_id": "SR001_questions",
        "component_type": "multiple_choice_set",
        "component_purpose": "knowledge_check",
        "component_weight": 1.0,
        "student_facing_content": {
          "stem": "Test your understanding of fundamental programming concepts",
          "instructions": "Select the best answer for each question",
          "response_format": "Multiple choice selection",
          "time_estimate": 15
        },
        "subskill_targeting": [
          {
            "subskill_id": "SS008",
            "weight_in_component": 1.0,
            "target_evidence_volume": 10.0
          }
        ]
      }
    ]
  }
}
```

## Integration with Backend Modules

### activity_manager.py Integration

The Activity Manager module uses this schema for:

1. **File Loading Validation**:
   ```python
   def validate_activity_structure(self, activity_data: Dict) -> bool:
       # Validates against this JSON schema
       return jsonschema.validate(activity_data, ACTIVITY_GENERATION_SCHEMA)
   ```

2. **Component Weight Validation**:
   ```python
   def validate_component_weights(self, components: List[Dict]) -> bool:
       total_weight = sum(c.get('component_weight', 0) for c in components)
       return abs(total_weight - 1.0) < 0.001
   ```

3. **Interactive Session Management**:
   ```python
   def create_interactive_session(self, activity_id: str, learner_id: str):
       # Uses interactive_configuration from schema
       pass
   ```

### Data Flow Integration

1. **Activity Selection** → Activity Manager validates against this schema
2. **Activity Interaction** → Uses student_facing_content structure  
3. **Evaluation Pipeline** → Consumes validated activity structure
4. **Scoring Engine** → Uses component weights and subskill targeting

## Validation Rules

### Required Field Validation
- All `required` fields must be present
- Component weights must sum to exactly 1.0
- Aspect weights within rubrics must sum to exactly 1.0
- Activity IDs must follow pattern: 2-3 letters + 3 digits

### Cross-Reference Validation
- All `subskill_id` values must exist in domain model
- Activity types must align with evaluation methods:
  - CR, COD, RP → rubric_scored
  - SR, BR → autoscored

### Interactive Activity Validation
- RP activities must include `role_play` configuration
- BR activities must include `branching_scenario` configuration
- Interactive configs must be complete with all required fields

### Evidence Volume Consistency
- Target evidence volumes must be realistic for activity type
- Component evidence should aggregate meaningfully
- Subskill evidence distribution should align with weights

This schema enables the complete activity generation and validation pipeline, supporting all 5 activity types with proper structure enforcement and backend integration.