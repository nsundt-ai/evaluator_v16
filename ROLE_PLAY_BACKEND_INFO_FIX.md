# Role Play Backend Information Exposure Fix

## Problem Description

The role play activities were exposing backend coaching information to students, including:

1. **Character Profile**: Detailed character background and personality information meant for the AI system
2. **Scenario Context**: Backend coaching instructions and context meant for the AI system  
3. **Objectives**: Backend coaching objectives meant for the AI system

This information was being displayed in:
- Activity instructions shown to students
- Initial role play conversation messages

## Root Cause

The issue was in `app.py` where backend information from the activity's `content` section was being added to the student-facing instructions:

```python
# Lines 1588-1591 (BEFORE FIX)
if 'scenario_context' in content:
    instructions = f"**Scenario Context:** {content['scenario_context']}\n\n{instructions}"
if 'character_profile' in content:
    instructions = f"{instructions}\n\n**Character Profile:** {content['character_profile']}"
if 'objectives' in content:
    # ... objectives display code
```

And in the role play conversation initialization:

```python
# Lines 2816-2817 (BEFORE FIX)  
character_profile = content.get('character_profile', 'AI Character')
scenario_context = content.get('scenario_context', 'General conversation')
initial_message = f"Hello! I'm {character_profile}. {scenario_context}"
```

## Solution

### 1. Removed Backend Information from Student Instructions

Commented out the code that was exposing backend information to students:

```python
# Lines 1588-1591 (AFTER FIX)
# Remove backend information from student view
# if 'scenario_context' in content:
#     instructions = f"**Scenario Context:** {content['scenario_context']}\n\n{instructions}"
# if 'character_profile' in content:
#     instructions = f"{instructions}\n\n**Character Profile:** {content['character_profile']}"
# if 'objectives' in content:
#     # ... objectives display code
```

### 2. Enhanced Role Play Conversation Initialization

Instead of exposing backend information directly, the system now generates an in-character introduction using the backend information internally:

```python
# Lines 2816-2830 (AFTER FIX)
# Get character info from activity - use character profile for AI persona
content = activity.get('content', {})
character_profile = content.get('character_profile', 'AI Character')
scenario_context = content.get('scenario_context', 'General conversation')

# Generate initial message in character persona using backend info internally
try:
    initial_prompt = f"""You are an AI character in a role-playing educational scenario. 

CHARACTER PROFILE: {character_profile}
SCENARIO: {scenario_context}

Generate a brief, natural introduction message (1-2 sentences) as this character would introduce themselves in this scenario. Keep it conversational and in-character. Respond with only the character's introduction message, no extra formatting or explanations."""
    
    # Use the backend to generate the initial message
    backend = init_backend()
    llm_response = backend['llm_client'].call_llm_with_fallback(
        system_prompt="You are a helpful AI character in an educational role-playing scenario.",
        user_prompt=initial_prompt,
        phase='role_play'
    )
    
    if llm_response and hasattr(llm_response, 'success') and llm_response.success:
        initial_message = llm_response.content
    else:
        # Fallback to generic character introduction
        initial_message = f"Hello! I'm here to help you with this role play activity. How can I assist you today?"
        
except Exception as e:
    # Fallback to generic greeting if there's an error
    initial_message = "Hello! I'm here to help you with this role play activity. How can I assist you today?"
```

### 3. Maintained Proper Student-Facing Content

The system already correctly uses student-facing content from `activity_generation_output.components[0].student_facing_content`, which includes:

- **stem**: Main task description
- **scenario**: Student-facing scenario description
- **given**: Given information for students
- **instructions**: Detailed instructions for students

## Backend Information Usage

The backend information (character_profile, scenario_context, objectives) is properly used internally by the AI system for:

1. **AI Character Generation**: The role play prompt generation correctly uses backend information to create appropriate AI responses
2. **Character Persona**: The initial message is generated in the character's persona using backend information
3. **Evaluation**: The evaluation system uses backend information for assessment
4. **Internal Processing**: Backend information guides the AI's behavior without exposing it to students

## Files Modified

- `app.py`: Lines 1588-1591 and 2816-2830

## Testing

The fix ensures that:
- Students only see appropriate, student-facing content
- Backend coaching information remains hidden from students
- AI characters introduce themselves in their proper persona
- AI system continues to function properly using backend information internally
- Role play activities maintain their educational effectiveness and immersion

## Example of Fixed Output

**BEFORE FIX:**
```
Problem Framing Workshop Role Play
Type: RP
Complexity: L2-D1
Target Skill: S002
Time Estimate: 30 min

📋 Activity Instructions

**Scenario Context:** Informal coaching session with junior PM who is struggling to translate technical complaints into user-centered problems. Alex is eager to learn but tends to think in technical terms rather than user impact.

**Character Profile:** Alex Kim, Junior Product Manager - 1 year experience, engineering background, analytical mindset, enthusiastic about learning. Tends to focus on technical solutions rather than user problems.

**Objectives:**
• Guide Alex to think from user perspective rather than technical perspective
• Help reframe technical complaints as user experience problems
• Teach problem statement construction through collaborative dialogue
• Build Alex's confidence in user-centered problem framing

💬 Role Play Conversation
Hello! I'm Alex Kim, Junior Product Manager - 1 year experience, engineering background, analytical mindset, enthusiastic about learning. Tends to focus on technical solutions rather than user problems.. Informal coaching session with junior PM who is struggling to translate technical complaints into user-centered problems. Alex is eager to learn but tends to think in technical terms rather than user impact.
```

**AFTER FIX:**
```
Problem Framing Workshop Role Play
Type: RP
Complexity: L2-D1
Target Skill: S002
Time Estimate: 30 min

📋 Activity Instructions

**Task:** Coach a junior product manager on reframing a technical complaint into a user-centered problem statement. Use a collaborative approach to guide their learning and build their problem framing skills.

**Scenario:** You're mentoring Alex Kim, a junior PM with an engineering background who tends to think in technical terms. Alex has received a complaint from the development team: 'The API response times are terrible - some queries take 8+ seconds. The database architecture is outdated and we need to refactor the entire backend to improve performance.' Alex wants to write this up as a problem statement but is focused on the technical solution rather than the user impact.

**Instructions:** Guide Alex through reframing this technical complaint into a user-centered problem statement. Use short, conversational exchanges to: 1) Help Alex think from the user perspective, 2) Identify the real user friction caused by slow performance, 3) Collaboratively construct an actionable problem statement, 4) Build Alex's confidence in user-centered thinking. Keep your responses brief and coaching-focused.

**Given Information:** Technical complaint: API response times of 8+ seconds, outdated database architecture, backend refactoring needed. Alex has engineering background and thinks technically rather than user-centered.

💬 Role Play Conversation
Hi! I'm Alex Kim, and I'm really excited to work on this problem statement with you. I got this technical complaint from the dev team about API response times, and I want to make sure I'm framing it right for our stakeholders.
``` 