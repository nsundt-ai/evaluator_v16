"""
Evaluator v16 - Streamlit Application
Main application with 50/50 split layout: Learner View (left) and Evaluation Management (right).

Author: Generated for Evaluator v16 Project  
Version: 1.0.0
"""

import streamlit as st
import json
import traceback
import time
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def display_activity_history_tables(learner_id: str, backend: Dict, current_activity_result: Dict = None):
    """Display activity history tables for all skills that have activity history"""
    try:
        # Get all skills that have activity history for this learner
        with backend['learner_manager']._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get skills from activity_history table
            cursor.execute('''
                SELECT DISTINCT skill_id 
                FROM activity_history 
                WHERE learner_id = ?
                ORDER BY skill_id
            ''', (learner_id,))
            skills_with_history = [row['skill_id'] for row in cursor.fetchall()]
            
            # Also get skills from activity_records table to show all completed activities
            cursor.execute('''
                SELECT DISTINCT ar.activity_id, COALESCE(ah.skill_id, 'S009') as skill_id
                FROM activity_records ar
                LEFT JOIN activity_history ah ON ar.activity_id = ah.activity_id AND ar.learner_id = ah.learner_id
                WHERE ar.learner_id = ?
                ORDER BY skill_id
            ''', (learner_id,))
            
            activity_skills = [row['skill_id'] for row in cursor.fetchall()]
            
            # Combine both sets of skills
            all_skills = list(set(skills_with_history + activity_skills))
            all_skills.sort()
        
        # If we have a current activity result, make sure its skill is included
        current_skill_id = None
        if current_activity_result:
            current_skill_id = current_activity_result.get('target_skill') or current_activity_result.get('skill_id', 'S009')
            if current_skill_id not in all_skills:
                all_skills.append(current_skill_id)
                all_skills.sort()  # Keep them ordered
        
        if not all_skills:
            st.info("No activity history found for any skills yet.")
            return
        
        # Display a table for each skill
        for skill_id in all_skills:
            try:
                display_single_skill_table(learner_id, skill_id, backend)
            except Exception as e:
                st.error(f"Error displaying table for skill {skill_id}: {str(e)}")
                continue
            
    except Exception as e:
        st.error(f"Error displaying activity history tables: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")

def display_single_skill_table(learner_id: str, skill_id: str, backend: Dict):
    """Display activity history table for a single skill with proper mathematical functioning"""
    try:
        # Get skill name from domain model
        domain_model = backend['config'].get_config('domain_model')
        skill_name = f"Skill {skill_id}"
        if domain_model and 'skills' in domain_model:
            for skill in domain_model['skills']:
                if skill.get('id') == skill_id:
                    skill_name = skill.get('name', f"Skill {skill_id}")
                    break
        
        # Display skill header
        st.markdown(f"### 📊 {skill_id}: {skill_name}")
        st.divider()
        
        # Get all activity records for this skill (only scored activities)
        with backend['learner_manager']._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get scored activities from activity_history
            cursor.execute('''
                SELECT activity_id, completion_timestamp, activity_title,
                       performance_score, cumulative_performance,
                       target_evidence_volume, adjusted_evidence_volume, cumulative_evidence,
                       validity_modifier, decay_factor, cumulative_evidence_weight,
                       decay_adjusted_evidence_volume
                FROM activity_history
                WHERE learner_id = ? AND skill_id = ?
                ORDER BY completion_timestamp DESC
            ''', (learner_id, skill_id))
            
            all_activity_records = cursor.fetchall()
        
        # Process all activity records
        all_records = []
        
        for record in all_activity_records:
            # Determine if this activity has been scored based on performance score
            is_scored = record['performance_score'] is not None and record['performance_score'] >= 0
            
            # Handle the case where decay_adjusted_evidence_volume might not exist in older records
            try:
                decay_adjusted_evidence_volume = record['decay_adjusted_evidence_volume']
            except (KeyError, IndexError):
                decay_adjusted_evidence_volume = 0.0
            
            all_records.append({
                'activity_id': record['activity_id'],
                'activity_title': record['activity_title'],
                'performance_score': record['performance_score'],
                'cumulative_performance': record['cumulative_performance'],
                'target_evidence_volume': record['target_evidence_volume'],
                'adjusted_evidence_volume': record['adjusted_evidence_volume'],
                'decay_adjusted_evidence_volume': decay_adjusted_evidence_volume,
                'cumulative_evidence': record['cumulative_evidence'],
                'validity_modifier': record['validity_modifier'],
                'decay_factor': record['decay_factor'],
                'cumulative_evidence_weight': record['cumulative_evidence_weight'],
                'completion_timestamp': record['completion_timestamp'],
                'scored': is_scored
            })
        
        if not all_records:
            st.info(f"No activity records found for skill {skill_id}")
            return
        
        # Create DataFrame for display
        import pandas as pd
        from datetime import datetime
        
        # Prepare data for display
        display_data = []
        
        # Pre-calculate all decay-adjusted evidence weights for cumulative calculation
        decay_adjusted_weights = []
        for i, record in enumerate(all_records):
            # Calculate the actual decay factor applied to this activity
            base_decay_factor = backend['scoring_engine'].decay_factor
            
            # For the most recent activity (first row), no decay
            # For older activities, calculate evidence accumulated since they were completed
            if i == 0:
                # Most recent activity: no decay
                actual_decay_factor = 1.0
            else:
                # Calculate evidence accumulated since this activity was completed
                evidence_accumulated_since = 0.0
                for j in range(i):
                    # Sum evidence from all activities that came before this one (more recent)
                    more_recent_record = all_records[j]
                    if more_recent_record['adjusted_evidence_volume'] is not None:
                        evidence_accumulated_since += more_recent_record['adjusted_evidence_volume']
                
                # Apply decay based on evidence accumulated since this activity was completed
                actual_decay_factor = base_decay_factor ** evidence_accumulated_since
            
            # Calculate the decay-adjusted evidence weight by applying the decay factor
            decay_adjusted_evidence = record['adjusted_evidence_volume'] * actual_decay_factor
            decay_adjusted_weights.append(decay_adjusted_evidence)
        
        # Now process each record with proper cumulative evidence calculation
        for i, record in enumerate(all_records):
            # Initialize variables
            decay_adjusted_evidence = decay_adjusted_weights[i]
            decay_adjusted_evidence_display = f"{decay_adjusted_evidence:.1f}"
            
            # Format scores as percentages
            # All activities are scored since they're from activity_history
            performance_score = f"{record['performance_score']:.1%}"
            cumulative_performance = f"{record['cumulative_performance']:.1%}"
            
            # Format evidence volumes
            target_evidence = f"{record['target_evidence_volume']:.1f}"
            adjusted_evidence = f"{record['adjusted_evidence_volume']:.1f}"
            
            # Calculate cumulative evidence: total of all adjusted evidence (same for all activities)
            cumulative_evidence_sum = sum(record['adjusted_evidence_volume'] for record in all_records)
            
            cumulative_evidence = f"{cumulative_evidence_sum:.1f}"
            
            # Format validity modifier
            validity_modifier = f"{record['validity_modifier']:.2f}"
            
            # Calculate the actual decay factor applied to this activity
            base_decay_factor = backend['scoring_engine'].decay_factor
            
            # For the most recent activity (first row), no decay
            # For older activities, calculate evidence accumulated since they were completed
            if i == 0:
                # Most recent activity: no decay
                actual_decay_factor = 1.0
            else:
                # Calculate evidence accumulated since this activity was completed
                evidence_accumulated_since = 0.0
                for j in range(i):
                    # Sum evidence from all activities that came before this one (more recent)
                    more_recent_record = all_records[j]
                    if more_recent_record['adjusted_evidence_volume'] is not None:
                        evidence_accumulated_since += more_recent_record['adjusted_evidence_volume']
                
                # Apply decay based on evidence accumulated since this activity was completed
                actual_decay_factor = base_decay_factor ** evidence_accumulated_since
            
            # Show both the base decay factor and the calculated decay factor
            decay_factor_info = f"{base_decay_factor:.3f} → {actual_decay_factor:.3f}"
            
            # Make cumulative values bold for the most recent row (i == 0)
            if i == 0:  # Most recent row (first row since data is ordered DESC)
                if is_scored:
                    cumulative_performance = f"**{cumulative_performance}**"
                    cumulative_evidence = f"**{cumulative_evidence}**"
                    decay_adjusted_evidence_display = f"**{decay_adjusted_evidence_display}**"
            
            # Format timestamp
            timestamp = format_timestamp(record['completion_timestamp'])
            
            display_data.append({
                'Activity': record['activity_title'],
                'Performance Score': performance_score,
                'Cumulative Performance': cumulative_performance,
                'Target Evidence': target_evidence,
                'Adjusted Evidence': adjusted_evidence,
                '↑ Cumulative Evidence': cumulative_evidence,
                'Validity Modifier': validity_modifier,
                'Decay Factor': decay_factor_info,
                'Evidence Weight': decay_adjusted_evidence_display,
                'Completed': timestamp,
                'Status': '✅ Scored'
            })
        
        # Show summary statistics for scored activities
        scored_records = [r for r in all_records if r['scored']]
        if scored_records:
            col1, col2 = st.columns(2)
            
            with col1:
                latest_performance = scored_records[0]['cumulative_performance']
                st.metric("Current Performance", f"{latest_performance:.1%}")
            
            with col2:
                # Calculate current evidence volume consistently with activity table
                current_evidence_volume = sum(record['adjusted_evidence_volume'] for record in all_records)
                st.metric("Current Evidence Volume", f"{current_evidence_volume:.1f}")
        
        # Create DataFrame and display
        df = pd.DataFrame(display_data)
        
        # Display the table with proper formatting
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Activity': st.column_config.TextColumn('Activity', width='medium'),
                'Performance Score': st.column_config.TextColumn('Performance Score', width='small'),
                'Cumulative Performance': st.column_config.TextColumn('Cumulative Performance', width='small'),
                'Target Evidence': st.column_config.TextColumn('Target Evidence', width='small'),
                'Adjusted Evidence': st.column_config.TextColumn('Adjusted Evidence', width='small'),
                '↑ Cumulative Evidence': st.column_config.TextColumn('Cumulative Evidence', width='small'),
                'Validity Modifier': st.column_config.TextColumn('Validity Modifier', width='small'),
                'Decay Factor': st.column_config.TextColumn('Decay Factor', width='small'),
                'Evidence Weight': st.column_config.TextColumn('Evidence Weight', width='small'),
                'Completed': st.column_config.TextColumn('Completed', width='small'),
                'Status': st.column_config.TextColumn('Status', width='small')
            }
        )
        
        
    except Exception as e:
        st.error(f"Error displaying skill table: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")

def display_activity_history_table(learner_id: str, skill_id: str, backend: Dict):
    """Legacy function - now calls the new single skill table function"""
    display_single_skill_table(learner_id, skill_id, backend)

def create_evaluation_summary_card(result: Dict[str, Any]) -> None:
    """Create a summary card showing evaluation metrics"""
    
    # Calculate total metrics from pipeline phases
    total_execution_time = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    
    # Extract metrics from pipeline phases
    if 'pipeline_phases' in result and result['pipeline_phases']:
        if isinstance(result['pipeline_phases'], dict):
            # Handle dictionary format
            for phase_name, phase_data in result['pipeline_phases'].items():
                if isinstance(phase_data, dict):
                    total_execution_time += phase_data.get('execution_time', 0)
                    total_cost += phase_data.get('cost_estimate', 0)
                    
                    # Extract token information from metadata if available
                    if 'result' in phase_data and isinstance(phase_data['result'], dict):
                        metadata = phase_data['result'].get('metadata', {})
                        # Handle different provider token field names
                        if 'input_tokens' in metadata:
                            total_input_tokens += metadata['input_tokens']
                        elif 'prompt_tokens' in metadata:
                            total_input_tokens += metadata['prompt_tokens']
                        
                        if 'output_tokens' in metadata:
                            total_output_tokens += metadata['output_tokens']
                        elif 'completion_tokens' in metadata:
                            total_output_tokens += metadata['completion_tokens']
                    
                    # Fallback: use tokens_used if metadata is not available
                    # For older evaluations that don't have detailed token breakdown
                    if total_input_tokens == 0 and total_output_tokens == 0:
                        tokens_used = phase_data.get('tokens_used', 0)
                        if tokens_used > 0:
                            # Estimate: typically output tokens are about 1/3 of total tokens
                            estimated_output = tokens_used // 3
                            estimated_input = tokens_used - estimated_output
                            total_input_tokens += estimated_input
                            total_output_tokens += estimated_output
        elif isinstance(result['pipeline_phases'], list):
            # Handle list format
            for phase in result['pipeline_phases']:
                if hasattr(phase, 'execution_time_ms'):
                    total_execution_time += phase.execution_time_ms / 1000
                if hasattr(phase, 'cost_estimate'):
                    total_cost += phase.cost_estimate or 0
                if hasattr(phase, 'result') and phase.result:
                    metadata = phase.result.get('metadata', {})
                    # Handle different provider token field names
                    if 'input_tokens' in metadata:
                        total_input_tokens += metadata['input_tokens']
                    elif 'prompt_tokens' in metadata:
                        total_input_tokens += metadata['prompt_tokens']
                    
                    if 'output_tokens' in metadata:
                        total_output_tokens += metadata['output_tokens']
                    elif 'completion_tokens' in metadata:
                        total_output_tokens += metadata['completion_tokens']
                
                # Fallback: use tokens_used if metadata is not available
                # For older evaluations that don't have detailed token breakdown
                if total_input_tokens == 0 and total_output_tokens == 0:
                    tokens_used = getattr(phase, 'tokens_used', 0)
                    if tokens_used > 0:
                        # Estimate: typically output tokens are about 1/3 of total tokens
                        estimated_output = tokens_used // 3
                        estimated_input = tokens_used - estimated_output
                        total_input_tokens += estimated_input
                        total_output_tokens += estimated_output
    
    # Fallback to overall metrics if available
    if total_execution_time == 0 and 'total_execution_time_ms' in result:
        total_execution_time = result['total_execution_time_ms'] / 1000
    if total_cost == 0 and 'total_cost_estimate' in result:
        total_cost = result['total_cost_estimate']
    
    # Create the summary card
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    ">
        <h3 style="margin: 0 0 15px 0; color: white; text-align: center;">📊 Evaluation Summary</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Create metrics columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "⏱️ Time Elapsed",
            f"{total_execution_time:.1f}s",
            help="Total execution time for all evaluation phases"
        )
    
    with col2:
        st.metric(
            "📥 Input Tokens",
            f"{total_input_tokens:,}",
            help="Total input tokens consumed across all LLM calls"
        )
    
    with col3:
        st.metric(
            "📤 Output Tokens", 
            f"{total_output_tokens:,}",
            help="Total output tokens generated across all LLM calls"
        )
    
    with col4:
        st.metric(
            "💰 Estimated Cost",
            f"${total_cost:.4f}",
            help="Estimated cost based on current API rates"
        )
    


def display_phase_results(phase_name: str, result: dict, backend: Dict = None):
    """Display phase-specific results showing only the required outputs"""
    
    # Ensure result is a dictionary
    if not isinstance(result, dict):
        st.error(f"Invalid result format for {phase_name}: {type(result)}")
        return
    
    if phase_name == "rubric_evaluation":
        # Display rubric table with scoring column and rationale column
        st.subheader("📊 Rubric Evaluation Results")
        
        # Handle the actual JSON structure from the output
        if 'evaluation' in result:
            evaluation = result['evaluation']
            
            # Extract aspect scores
            if 'aspect_scores' in evaluation:
                aspect_scores = evaluation['aspect_scores']
                aspect_data = []
                
                if isinstance(aspect_scores, dict):
                    for aspect_name, score_data in aspect_scores.items():
                        if isinstance(score_data, dict):
                            score = score_data.get('score', 0)
                            rationale = score_data.get('rationale', 'No rationale provided')
                        else:
                            score = score_data
                            rationale = 'No rationale provided'
                        
                        aspect_data.append([aspect_name.replace('_', ' ').title(), f"{score:.1%}", rationale])
                elif isinstance(aspect_scores, list):
                    for aspect in aspect_scores:
                        if isinstance(aspect, dict):
                            aspect_name = aspect.get('aspect_name', 'Unknown Aspect')
                            score = aspect.get('score', 0)
                            rationale = aspect.get('rationale', 'No rationale provided')
                            aspect_data.append([aspect_name.replace('_', ' ').title(), f"{score:.1%}", rationale])
                
                if aspect_data:
                    # Display each aspect with expandable rationale sections
                    for aspect_name, score, rationale in aspect_data:
                        with st.expander(f"**{aspect_name}** - {score}", expanded=False):
                            st.markdown(f"**Score:** {score}")
                            st.markdown("**Rationale:**")
                            st.write(rationale)
            
            # Show overall score
            if 'overall_score' in evaluation:
                overall_score = evaluation['overall_score']
                st.metric("Overall Component Score", f"{overall_score:.1%}")
            
            # Show comments if available
            if 'comments' in evaluation:
                st.subheader("Overall Assessment")
                st.write(evaluation['comments'])
        
        # Handle component_score at root level
        if 'component_score' in result:
            component_score = result['component_score']
            st.metric("Component Score", f"{component_score:.1%}")
        
        # Handle scoring_rationale at root level
        if 'scoring_rationale' in result:
            st.subheader("Scoring Rationale")
            st.write(result['scoring_rationale'])
    
    elif phase_name == "validity_analysis":
        # Display validity modifier
        st.subheader("🔍 Validity Analysis Results")
        
        # Show validity modifier
        if 'validity_modifier' in result:
            validity_modifier = result['validity_modifier']
            if isinstance(validity_modifier, (int, float)):
                st.metric("Validity Modifier", f"{validity_modifier:.2f}")
            else:
                st.metric("Validity Modifier", str(validity_modifier))
        
        # Show validity analysis if available
        if 'validity_analysis' in result:
            st.subheader("Validity Assessment")
            st.write(result['validity_analysis'])
        
        # Show validity rationale if available
        if 'rationale' in result:
            st.subheader("Assessment Rationale")
            st.write(result['rationale'])
        
        # Show assistance impact analysis if available
        if 'assistance_impact_analysis' in result:
            assistance = result['assistance_impact_analysis']
            if isinstance(assistance, dict):
                st.subheader("Assistance Impact Analysis")
                col1, col2 = st.columns(2)
                with col1:
                    if 'overall_impact_level' in assistance:
                        st.metric("Impact Level", assistance['overall_impact_level'].title())
                with col2:
                    if 'total_assistance_events' in assistance:
                        st.metric("Total Events", assistance['total_assistance_events'])
    
    elif phase_name == "scoring":
        # Display activity history tables for all skills instead of basic scoring results
        st.subheader("📈 Activity History & Scoring Results")
        # Get current learner and activity info
        if hasattr(st.session_state, "current_learner") and st.session_state.current_learner:
            learner_id = st.session_state.current_learner.learner_id
        else:
            learner_id = "unknown"
        
        # Display activity history tables for all skills that have history
        display_activity_history_tables(learner_id, backend, result)
    
    elif phase_name == "diagnostic_intelligence":
        # Display diagnostic intelligence results
        st.subheader("🧠 Diagnostic Intelligence Results")
        
        # Handle different possible structures
        diagnostic_data = result.get('diagnostic_intelligence', result)
        
        # Show subskill performance if available
        if 'subskill_performance' in diagnostic_data:
            st.subheader("Subskill Performance")
            subskills = diagnostic_data['subskill_performance']
            if isinstance(subskills, list):
                subskill_data = []
                for subskill in subskills:
                    if isinstance(subskill, dict):
                        name = subskill.get('subskill_name', 'Unknown')
                        level = subskill.get('performance_level', 'Unknown')
                        priority = subskill.get('development_priority', 'Unknown')
                        subskill_data.append([name, level, priority])
                
                if subskill_data:
                    import pandas as pd
                    df = pd.DataFrame(subskill_data, columns=['Subskill', 'Performance Level', 'Development Priority'])
                    st.dataframe(df, use_container_width=True)
        
        # Show diagnostic insights if available
        if 'diagnostic_insights' in diagnostic_data:
            insights = diagnostic_data['diagnostic_insights']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Strengths")
                strengths = insights.get('strengths', [])
                if isinstance(strengths, list) and strengths:
                    for strength in strengths:
                        st.write(f"• {strength}")
                else:
                    st.write("No strengths identified")
            
            with col2:
                st.subheader("Areas for Development")
                development_areas = insights.get('development_areas', [])
                if isinstance(development_areas, list) and development_areas:
                    for area in development_areas:
                        if isinstance(area, dict):
                            area_name = area.get('area', 'Unknown Area')
                            description = area.get('description', '')
                            recommendation = area.get('recommendation', '')
                            st.write(f"• **{area_name}**")
                            st.write(f"  {description}")
                            if recommendation:
                                st.write(f"  *Recommendation: {recommendation}*")
                        else:
                            st.write(f"• {area}")
                else:
                    st.write("No areas for development identified")
            
            # Show learning patterns if available
            if 'learning_patterns' in insights:
                st.subheader("Learning Patterns")
                patterns = insights.get('learning_patterns', [])
                if isinstance(patterns, list) and patterns:
                    for pattern in patterns:
                        if isinstance(pattern, dict):
                            pattern_name = pattern.get('pattern', 'Unknown Pattern')
                            description = pattern.get('description', '')
                            recommendation = pattern.get('recommendation', '')
                            st.write(f"• **{pattern_name}**")
                            st.write(f"  {description}")
                            if recommendation:
                                st.write(f"  *Recommendation: {recommendation}*")
                        else:
                            st.write(f"• {pattern}")
            
            # Show overall summary if available
            if 'overall_summary' in insights:
                st.subheader("Overall Summary")
                st.write(insights['overall_summary'])
        
        # Handle simple structure (strengths, development_areas, recommendations)
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Strength Areas")
                strengths = diagnostic_data.get('strengths', [])
                if isinstance(strengths, list) and strengths:
                    for strength in strengths:
                        st.write(f"• {strength}")
                else:
                    st.write("No strengths identified")
            
            with col2:
                st.subheader("Improvement Areas")
                development_areas = diagnostic_data.get('development_areas', [])
                if isinstance(development_areas, list) and development_areas:
                    for area in development_areas:
                        st.write(f"• {area}")
                else:
                    st.write("No improvement areas identified")
            
            # Show recommendations if available
            if 'recommendations' in diagnostic_data:
                st.subheader("Recommendations")
                recommendations = diagnostic_data['recommendations']
                if isinstance(recommendations, list) and recommendations:
                    for i, rec in enumerate(recommendations, 1):
                        st.write(f"{i}. {rec}")
        
        # Show any other diagnostic fields
        for key, value in diagnostic_data.items():
            if key not in ['subskill_performance', 'diagnostic_insights', 'strengths', 'development_areas', 'recommendations'] and isinstance(value, (dict, list)):
                st.subheader(key.replace('_', ' ').title())
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        st.write(f"**{subkey.replace('_', ' ').title()}:** {subvalue}")
                elif isinstance(value, list):
                    for item in value:
                        st.write(f"• {item}")
    
    elif phase_name == "intelligent_feedback":
        # Display intelligent feedback results with two sections
        st.subheader("🧠💬 Intelligent Feedback Results")
        
        # Handle the intelligent_feedback structure
        intelligent_data = result.get('intelligent_feedback', result)
        
        # Display Backend Intelligence section (for evaluation view)
        if 'backend_intelligence' in intelligent_data:
            backend = intelligent_data['backend_intelligence']
            
            st.markdown("### 🔍 Backend Intelligence")
            
            # Show overview
            if 'overview' in backend:
                st.subheader("📋 Overview")
                st.write(backend['overview'])
            
            # Show strengths and weaknesses
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Strengths")
                strengths = backend.get('strengths', [])
                if isinstance(strengths, list) and strengths:
                    for strength in strengths:
                        st.write(f"• {strength}")
                else:
                    st.write("No strengths identified")
            
            with col2:
                st.subheader("📈 Weaknesses")
                weaknesses = backend.get('weaknesses', [])
                if isinstance(weaknesses, list) and weaknesses:
                    for weakness in weaknesses:
                        st.write(f"• {weakness}")
                else:
                    st.write("No weaknesses identified")
            
            # Show subskill ratings table
            if 'subskill_ratings' in backend:
                st.subheader("📊 Subskill Ratings Table")
                subskills = backend['subskill_ratings']
                if isinstance(subskills, list):
                    subskill_data = []
                    for subskill in subskills:
                        if isinstance(subskill, dict):
                            name = subskill.get('subskill_name', 'Unknown')
                            level = subskill.get('performance_level', 'Unknown')
                            priority = subskill.get('development_priority', 'Unknown')
                            subskill_data.append([name, level, priority])
                    
                    if subskill_data:
                        import pandas as pd
                        df = pd.DataFrame(subskill_data, columns=['Subskill', 'Performance Level', 'Development Priority'])
                        st.dataframe(df, use_container_width=True)
        
        # Display Learner Feedback section (for both evaluation and learner views)
        if 'learner_feedback' in intelligent_data:
            feedback = intelligent_data['learner_feedback']
            
            st.markdown("### 👤 Learner Feedback")
            
            # Show overall assessment
            if 'overall' in feedback:
                st.subheader("📋 Overall")
                st.info(feedback['overall'])
            
            # Show strengths and opportunities
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🏆 Strengths")
                strengths = feedback.get('strengths', '')
                if strengths:
                    st.write(strengths)
                else:
                    st.write("Strengths being analyzed...")
            
            with col2:
                st.subheader("🚀 Opportunities")
                opportunities = feedback.get('opportunities', '')
                if opportunities:
                    st.write(opportunities)
                else:
                    st.write("Opportunities being analyzed...")
    
    elif phase_name == "trend_analysis":
        # Display trend analysis - FEATURE DISABLED
        st.subheader("📈 Trend Analysis Results")
        
        # Check if this is the disabled result
        trend_data = result.get('trend_analysis', result)
        
        # Check for disabled feature indicators
        if (isinstance(trend_data, dict) and 
            (trend_data.get('trend_analysis', '').startswith('Trend Analysis Disabled') or
             'feature_disabled' in str(trend_data).lower() or
             trend_data.get('performance_trajectory') == 'stable' and len(trend_data) <= 3)):
            
            # Show disabled feature message
            st.info("💡 **Trend Analysis Feature Disabled**")
            st.write("This feature has been disabled while the logic and strategy are still in development.")
            st.write("**Reason:** Logic and strategy still in development")
            
            # Show what would normally be analyzed
            with st.expander("📊 What Trend Analysis Would Show"):
                st.write("When enabled, trend analysis would provide:")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("• **Performance Trajectory**")
                    st.write("• **Learning Velocity**")
                    st.write("• **Growth Patterns**")
                with col2:
                    st.write("• **Historical Trends**")
                    st.write("• **Improvement Areas**")
                    st.write("• **Personalized Recommendations**")
            
            return
        
        # Handle the actual JSON structure from the output (for when feature is enabled)
        if 'evaluation' in result:
            evaluation = result['evaluation']
            
            # Show competency assessment if available
            if 'competency_assessment' in evaluation:
                assessment = evaluation['competency_assessment']
                st.subheader("Competency Assessment")
                
                if 'overall_score' in assessment:
                    overall_score = assessment['overall_score']
                    st.metric("Overall Score", f"{overall_score:.1%}")
                
                if 'aspect_scores' in assessment:
                    aspect_scores = assessment['aspect_scores']
                    aspect_data = []
                    for aspect, score in aspect_scores.items():
                        aspect_data.append([aspect.replace('_', ' ').title(), f"{score:.1%}"])
                    
                    if aspect_data:
                        import pandas as pd
                        df = pd.DataFrame(aspect_data, columns=['Aspect', 'Score'])
                        st.dataframe(df, use_container_width=True)
            
            # Show diagnostic summary if available
            if 'diagnostic_summary' in evaluation:
                diagnostic = evaluation['diagnostic_summary']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Strengths")
                    strengths = diagnostic.get('strengths', [])
                    if isinstance(strengths, list) and strengths:
                        for strength in strengths:
                            st.write(f"• {strength}")
                    else:
                        st.write("No strengths identified")
                
                with col2:
                    st.subheader("Development Areas")
                    development_areas = diagnostic.get('development_areas', [])
                    if isinstance(development_areas, list) and development_areas:
                        for area in development_areas:
                            if isinstance(area, dict):
                                area_name = area.get('area', 'Unknown Area')
                                description = area.get('description', '')
                                recommendation = area.get('recommendation', '')
                                st.write(f"• **{area_name}**")
                                st.write(f"  {description}")
                                if recommendation:
                                    st.write(f"  *Recommendation: {recommendation}*")
                            else:
                                st.write(f"• {area}")
                    else:
                        st.write("No development areas identified")
        
        # Handle the trend_analysis section
        if 'performance_trajectory' in trend_data:
            trajectory = trend_data['performance_trajectory']
            if isinstance(trajectory, dict):
                st.subheader("Performance Trajectory")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if 'direction' in trajectory:
                        st.metric("Direction", trajectory['direction'].title())
                with col2:
                    if 'magnitude' in trajectory:
                        st.metric("Magnitude", trajectory['magnitude'].title())
                with col3:
                    if 'confidence' in trajectory:
                        st.metric("Confidence", f"{trajectory['confidence']:.1%}")
                if 'trajectory_description' in trajectory:
                    st.write("**Description:**", trajectory['trajectory_description'])
            else:
                st.metric("Performance Trajectory", str(trajectory))
        
        # Show historical patterns if available
        if 'historical_patterns' in trend_data:
            patterns = trend_data['historical_patterns']
            if isinstance(patterns, dict):
                col1, col2 = st.columns(2)
                with col1:
                    if 'consistent_strengths' in patterns:
                        st.subheader("Consistent Strengths")
                        strengths = patterns['consistent_strengths']
                        if isinstance(strengths, list):
                            for strength in strengths:
                                st.write(f"• {strength}")
                with col2:
                    if 'recurring_challenges' in patterns:
                        st.subheader("Recurring Challenges")
                        challenges = patterns['recurring_challenges']
                        if isinstance(challenges, list):
                            for challenge in challenges:
                                st.write(f"• {challenge}")
        
        # Show historical performance summary if available
        if 'historical_performance' in trend_data:
            historical = trend_data['historical_performance']
            if isinstance(historical, dict):
                st.subheader("Historical Performance")
                if 'activity_count' in historical:
                    st.metric("Total Activities", historical['activity_count'])
                if 'performance_pattern' in historical:
                    st.write("**Performance Pattern:**", historical['performance_pattern'])
                if 'engagement_pattern' in historical:
                    st.write("**Engagement Pattern:**", historical['engagement_pattern'])
        
        # Show personalized recommendations if available
        if 'personalized_recommendations' in trend_data:
            recommendations = trend_data['personalized_recommendations']
            if isinstance(recommendations, list) and recommendations:
                st.subheader("Personalized Recommendations")
                for i, rec in enumerate(recommendations, 1):
                    if isinstance(rec, dict):
                        recommendation = rec.get('recommendation', '')
                        rationale = rec.get('rationale', '')
                        st.write(f"{i}. **{recommendation}**")
                        if rationale:
                            st.write(f"   *Rationale: {rationale}*")
                    else:
                        st.write(f"{i}. {rec}")
    
    elif phase_name == "combined_evaluation":
        # Display combined evaluation results (rubric + validity analysis)
        st.subheader("📊 Combined Evaluation Results")
        
        # Display aspect scores in a table
        if 'aspect_scores' in result:
            aspect_scores = result['aspect_scores']
            if isinstance(aspect_scores, list) and aspect_scores:
                aspect_data = []
                for aspect in aspect_scores:
                    if isinstance(aspect, dict):
                        aspect_name = aspect.get('aspect_name', 'Unknown Aspect')
                        score = aspect.get('score', 0)
                        rationale = aspect.get('rationale', 'No rationale provided')
                        aspect_data.append([aspect_name, f"{score:.1%}", rationale])
                
                if aspect_data:
                    # Display each aspect with expandable rationale sections
                    for aspect_name, score, rationale in aspect_data:
                        with st.expander(f"**{aspect_name}** - {score}", expanded=False):
                            st.markdown(f"**Score:** {score}")
                            st.markdown("**Rationale:**")
                            st.write(rationale)
        
        # Display overall score
        if 'overall_score' in result:
            overall_score = result['overall_score']
            st.metric("Overall Score", f"{overall_score:.1%}")
        
        # Display overall rationale
        if 'rationale' in result:
            st.subheader("Overall Assessment")
            st.write(result['rationale'])
        
        # Display validity information
        col1, col2 = st.columns(2)
        
        with col1:
            if 'validity_modifier' in result:
                validity_modifier = result['validity_modifier']
                st.metric("Validity Modifier", f"{validity_modifier:.2f}")
            
            if 'validity_analysis' in result:
                st.subheader("Validity Analysis")
                st.write(result['validity_analysis'])
        
        with col2:
            if 'evidence_quality' in result:
                st.subheader("Evidence Quality")
                st.write(result['evidence_quality'])
            
            if 'assistance_impact' in result:
                st.subheader("Assistance Impact")
                st.write(result['assistance_impact'])
        
        # Display evidence volume assessment
        if 'evidence_volume_assessment' in result:
            st.subheader("Evidence Volume Assessment")
            st.write(result['evidence_volume_assessment'])
        
        # Display assessment confidence
        if 'assessment_confidence' in result:
            st.subheader("Assessment Confidence")
            st.write(result['assessment_confidence'])
        
        # Display key observations
        if 'key_observations' in result:
            st.subheader("Key Observations")
            observations = result['key_observations']
            if isinstance(observations, list):
                for observation in observations:
                    st.write(f"• {observation}")
    
    elif phase_name == "feedback_generation":
        # Display student-facing feedback with strengths and opportunities (weaknesses framed as opportunities)
        st.subheader("💬 Feedback Generation Results")
        
        # Handle the actual JSON structure from the output
        if 'feedback' in result:
            feedback = result['feedback']
            
            # Show overall summary
            if 'overall_summary' in feedback:
                st.subheader("Overall Assessment")
                st.write(feedback['overall_summary'])
            
            # Show strengths and opportunities in two columns
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Key Strengths")
                strengths = feedback.get('strengths', [])
                if isinstance(strengths, list) and strengths:
                    for strength in strengths:
                        st.write(f"• {strength}")
                else:
                    st.write("No strengths identified")
            
            with col2:
                st.subheader("Primary Opportunities")
                areas_for_improvement = feedback.get('areas_for_improvement', [])
                if isinstance(areas_for_improvement, list) and areas_for_improvement:
                    for area in areas_for_improvement:
                        if isinstance(area, dict):
                            area_name = area.get('area', 'Unknown Area')
                            feedback_text = area.get('feedback', '')
                            st.write(f"• **{area_name}**")
                            st.write(f"  {feedback_text}")
                        else:
                            st.write(f"• {area}")
                else:
                    st.write("No opportunities identified")
            
            # Show motivational message if available
            if 'motivational_message' in feedback:
                st.subheader("Motivational Message")
                st.write(feedback['motivational_message'])
            
            # Show actionable recommendations if available
            if 'actionable_recommendations' in feedback:
                st.subheader("Actionable Recommendations")
                recommendations = feedback['actionable_recommendations']
                if isinstance(recommendations, list):
                    for i, rec in enumerate(recommendations, 1):
                        st.write(f"{i}. {rec}")
            
            # Show next steps if available
            if 'next_steps' in feedback:
                st.subheader("Next Steps")
                st.write(feedback['next_steps'])
        
        # Handle nested structure from schema
        feedback_data = result.get('feedback_generation', result)
        
        # Show performance summary if available
        if 'performance_summary' in feedback_data:
            performance = feedback_data['performance_summary']
            if isinstance(performance, dict):
                st.subheader("Performance Summary")
                
                if 'overall_assessment' in performance:
                    st.write("**Overall Assessment:**")
                    st.write(performance['overall_assessment'])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'key_strengths' in performance:
                        st.write("**Key Strengths:**")
                        strengths = performance['key_strengths']
                        if isinstance(strengths, list):
                            for strength in strengths:
                                st.write(f"• {strength}")
                
                with col2:
                    if 'primary_opportunities' in performance:
                        st.write("**Primary Opportunities:**")
                        opportunities = performance['primary_opportunities']
                        if isinstance(opportunities, list):
                            for opportunity in opportunities:
                                st.write(f"• {opportunity}")
                
                if 'achievement_highlights' in performance:
                    st.write("**Achievement Highlights:**")
                    highlights = performance['achievement_highlights']
                    if isinstance(highlights, list):
                        for highlight in highlights:
                            st.write(f"• {highlight}")
                
                # Actionable guidance
                if 'actionable_guidance' in student_feedback:
                    guidance = student_feedback['actionable_guidance']
                    
                    # Immediate next steps
                    if 'immediate_next_steps' in guidance and guidance['immediate_next_steps']:
                        st.write("**Immediate Next Steps:**")
                        for step in guidance['immediate_next_steps']:
                            st.write(f"• {step}")
                    
                    # Recommendations
                    if 'recommendations' in guidance and guidance['recommendations']:
                        st.write("**Recommendations:**")
                        for rec in guidance['recommendations']:
                            st.write(f"• {rec}")
                
                # Show diagnostic analysis if available
                elif 'diagnostic_analysis' in feedback_data:
                    diagnostic = feedback_data['diagnostic_analysis']
                    
                    if 'strength_areas' in diagnostic and diagnostic['strength_areas']:
                        st.write("**Strengths:**")
                        for strength in diagnostic['strength_areas']:
                            st.write(f"• {strength}")
                    
                    if 'improvement_areas' in diagnostic and diagnostic['improvement_areas']:
                        st.write("**Areas for Improvement:**")
                        for area in diagnostic['improvement_areas']:
                            st.write(f"• {area}")
                    
                    if 'subskill_performance' in diagnostic:
                        st.write("**Subskill Performance:**")
                        for subskill in diagnostic['subskill_performance']:
                            st.write(f"• {subskill.get('subskill_name', 'Unknown')}: {subskill.get('performance_level', 'Unknown')}")
                
                # Fallback to simple feedback display
                else:
                    st.write("Feedback analysis completed successfully.")
    else:
        # Generic display for unknown phases
        st.json(result)

# Import all backend modules
try:
    from src.config_manager import ConfigManager
    from src.llm_client import LLMClient
    from src.prompt_builder import PromptBuilder
    from src.scoring_engine import ScoringEngine
    from src.learner_manager import LearnerManager
    from src.activity_manager import ActivityManager
    from src.evaluation_pipeline import EvaluationPipeline, PipelinePhase
    from src.logger import get_logger
except ImportError as e:
    st.error(f"Failed to import backend modules: {e}")
    st.error("Please ensure all backend modules are present in the src/ directory")
    st.stop()

st.set_page_config(
    page_title="Evaluator v16 - Educational Assessment Pipeline",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add custom CSS for better styling and visual differentiation
st.markdown("""
<style>
    /* Adjust main content area */
    .main .block-container {
        transition: max-width 0.3s ease, padding 0.3s ease;
        max-width: 95vw !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    /* Sidebar section styling */
    .sidebar-section {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #dee2e6;
    }
    
    /* Main layout styling */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
</style>

<script>
// Function to handle sidebar width
function adjustSidebarWidth() {
    const sidebar = document.querySelector('section[data-testid="stSidebar"]');
    const collapseButton = document.querySelector('[data-testid="collapsedControl"]');
    
    if (sidebar && collapseButton) {
        const isCollapsed = collapseButton.getAttribute('aria-expanded') === 'false';
        
        if (isCollapsed) {
            // Remove width constraints when collapsed
            sidebar.style.minWidth = '';
            sidebar.style.maxWidth = '';
            sidebar.style.width = '';
            sidebar.style.display = 'none';
        } else {
            // Set width when expanded
            sidebar.style.minWidth = '500px';
            sidebar.style.maxWidth = '600px';
            sidebar.style.width = '500px';
            sidebar.style.display = 'block';
        }
    }
}

// Set up observer to watch for sidebar state changes
function setupSidebarObserver() {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'aria-expanded') {
                setTimeout(adjustSidebarWidth, 50); // Shorter delay
            }
        });
    });
    
    // Start observing the collapse button
    const collapseButton = document.querySelector('[data-testid="collapsedControl"]');
    if (collapseButton) {
        observer.observe(collapseButton, { attributes: true });
        // Initial setup
        setTimeout(adjustSidebarWidth, 50);
    }
}

// Run when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupSidebarObserver);
} else {
    setupSidebarObserver();
}

// Also run after a short delay to catch any late-loading elements
setTimeout(setupSidebarObserver, 1000);
</script>
""", unsafe_allow_html=True)

# Add the rest of the CSS styling
st.markdown("""
<style>
    /* Column alignment fixes for Student Progress View */
    [data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
    }
    
    [data-testid="column"] > div {
        flex: 1 !important;
        min-height: 0 !important;
    }
    
    /* Ensure equal height columns in split view */
    .main .block-container [data-testid="column"] {
        align-items: stretch !important;
    }
    
    /* Left column styling - Learner View (polished student interface) */
    [data-testid="column"]:first-child {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 8px;
        padding: 0.5rem;
        border: 2px solid #dee2e6;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Right column styling - Backend Output (monospace, technical appearance) */
    [data-testid="column"]:last-child {
        background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
        border-radius: 8px;
        padding: 0.5rem;
        border: 2px solid #4a5568;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
        position: relative;
    }
    
    /* Terminal-like cursor effect for right column */
    [data-testid="column"]:last-child::before {
        content: '';
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        width: 6px;
        height: 12px;
        background: #68d391;
        animation: blink 1s infinite;
        border-radius: 2px;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    
    /* Override font for all elements in right column */
    [data-testid="column"]:last-child * {
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
    }
    
    /* Right column text styling */
    [data-testid="column"]:last-child h1,
    [data-testid="column"]:last-child h2,
    [data-testid="column"]:last-child h3,
    [data-testid="column"]:last-child p,
    [data-testid="column"]:last-child div,
    [data-testid="column"]:last-child span {
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
        color: #e2e8f0 !important;
        line-height: 1.4 !important;
    }
    
    /* Right column terminal-like styling for all content */
    [data-testid="column"]:last-child .stAlert,
    [data-testid="column"]:last-child .stSuccess,
    [data-testid="column"]:last-child .stError,
    [data-testid="column"]:last-child .stWarning {
        background: #1a202c !important;
        border: 1px solid #4a5568 !important;
        color: #e2e8f0 !important;
        border-radius: 4px !important;
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
        padding: 0.75rem !important;
    }
    
    /* Right column specific alert colors with terminal theme */
    [data-testid="column"]:last-child .stSuccess {
        border-left: 4px solid #38a169 !important;
        background: #22543d !important;
    }
    
    [data-testid="column"]:last-child .stError {
        border-left: 4px solid #e53e3e !important;
        background: #742a2a !important;
    }
    
    [data-testid="column"]:last-child .stWarning {
        border-left: 4px solid #d69e2e !important;
        background: #744210 !important;
    }
    
    /* Right column headers with terminal-like styling */
    [data-testid="column"]:last-child h1,
    [data-testid="column"]:last-child h2,
    [data-testid="column"]:last-child h3 {
        color: #68d391 !important;
        border-bottom: 1px solid #4a5568;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    
    /* Right column info boxes with dark theme */
    [data-testid="column"]:last-child .stAlert {
        background: #2d3748 !important;
        border: 1px solid #4a5568 !important;
        color: #e2e8f0 !important;
    }
    
    /* Right column success/error messages */
    [data-testid="column"]:last-child .stSuccess {
        background: #22543d !important;
        border: 1px solid #38a169 !important;
        color: #68d391 !important;
    }
    
    [data-testid="column"]:last-child .stError {
        background: #742a2a !important;
        border: 1px solid #e53e3e !important;
        color: #fc8181 !important;
    }
    
    [data-testid="column"]:last-child .stWarning {
        background: #744210 !important;
        border: 1px solid #d69e2e !important;
        color: #f6e05e !important;
    }
    
    /* Right column buttons with terminal styling */
    [data-testid="column"]:last-child .stButton > button {
        background: #4a5568 !important;
        border: 1px solid #718096 !important;
        color: #e2e8f0 !important;
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
    }
    
    [data-testid="column"]:last-child .stButton > button:hover {
        background: #718096 !important;
        border: 1px solid #a0aec0 !important;
    }
    
    /* Right column expanders with dark theme */
    [data-testid="column"]:last-child .streamlit-expanderHeader {
        background: #2d3748 !important;
        border: 1px solid #4a5568 !important;
        color: #68d391 !important;
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
    }
    
    /* Right column progress bars */
    [data-testid="column"]:last-child .stProgress > div > div {
        background: #4a5568 !important;
    }
    
    [data-testid="column"]:last-child .stProgress > div > div > div {
        background: #68d391 !important;
    }
    
    /* Right column terminal-like background pattern */
    [data-testid="column"]:last-child {
        background-image: 
            linear-gradient(135deg, #2d3748 0%, #1a202c 100%),
            repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                rgba(104, 211, 145, 0.03) 2px,
                rgba(104, 211, 145, 0.03) 4px
            ) !important;
    }
    
    /* Right column dataframes with terminal styling */
    [data-testid="column"]:last-child .stDataFrame {
        background: #1a202c !important;
        border: 1px solid #4a5568 !important;
        border-radius: 4px !important;
    }
    
    [data-testid="column"]:last-child .stDataFrame table {
        background: #1a202c !important;
        color: #e2e8f0 !important;
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
    }
    
    [data-testid="column"]:last-child .stDataFrame th {
        background: #2d3748 !important;
        color: #68d391 !important;
        border: 1px solid #4a5568 !important;
    }
    
    [data-testid="column"]:last-child .stDataFrame td {
        background: #1a202c !important;
        color: #e2e8f0 !important;
        border: 1px solid #4a5568 !important;
    }
    
    /* Right column JSON styling for better readability */
    [data-testid="column"]:last-child .stJson {
        background: #1a202c !important;
        border: 1px solid #4a5568 !important;
        border-radius: 6px !important;
        padding: 1rem !important;
    }
    
    [data-testid="column"]:last-child .stJson pre {
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
        color: #e2e8f0 !important;
        background: #1a202c !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Right column code blocks */
    [data-testid="column"]:last-child code {
        background: #2d3748 !important;
        color: #68d391 !important;
        padding: 0.2rem 0.4rem !important;
        border-radius: 4px !important;
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace !important;
    }
    
    /* Left column styling - clean, modern interface */
    [data-testid="column"]:first-child h1,
    [data-testid="column"]:first-child h2,
    [data-testid="column"]:first-child h3 {
        color: #2d3748 !important;
        font-weight: 600;
    }
    
    /* Left column content styling - modern, clean appearance */
    [data-testid="column"]:first-child .stAlert {
        background: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        color: #495057 !important;
        border-radius: 8px !important;
    }
    
    [data-testid="column"]:first-child .stSuccess {
        background: #d4edda !important;
        border: 1px solid #c3e6cb !important;
        color: #155724 !important;
    }
    
    [data-testid="column"]:first-child .stError {
        background: #f8d7da !important;
        border: 1px solid #f5c6cb !important;
        color: #721c24 !important;
    }
    
    [data-testid="column"]:first-child .stWarning {
        background: #fff3cd !important;
        border: 1px solid #ffeaa7 !important;
        color: #856404 !important;
    }
    
    [data-testid="column"]:first-child .stButton > button {
        background: #007bff !important;
        border: 1px solid #0056b3 !important;
        color: white !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }
    
    [data-testid="column"]:first-child .stButton > button:hover {
        background: #0056b3 !important;
        border: 1px solid #004085 !important;
    }
    
    [data-testid="column"]:first-child .streamlit-expanderHeader {
        background: #e9ecef !important;
        border: 1px solid #dee2e6 !important;
        color: #495057 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
    }
    
    [data-testid="column"]:first-child .stProgress > div > div {
        background: #e9ecef !important;
    }
    
    [data-testid="column"]:first-child .stProgress > div > div > div {
        background: #007bff !important;
    }
    
    /* Left column text styling */
    [data-testid="column"]:first-child p,
    [data-testid="column"]:first-child div,
    [data-testid="column"]:first-child span {
        color: #495057 !important;
        line-height: 1.6 !important;
    }
    
    /* Left column modern background with subtle pattern */
    [data-testid="column"]:first-child {
        background-image: 
            linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%),
            repeating-linear-gradient(
                45deg,
                transparent,
                transparent 10px,
                rgba(102, 126, 234, 0.02) 10px,
                rgba(102, 126, 234, 0.02) 20px
            ) !important;
    }
    
    /* Student Progress View specific alignment */
    .student-progress-view [data-testid="column"] {
        min-height: 600px !important;
        display: flex !important;
        flex-direction: column !important;
    }
    
    .student-progress-view [data-testid="column"] > div {
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    
    /* Ensure content starts at the same height in both columns */
    .student-progress-view [data-testid="column"] .stMarkdown:first-child {
        margin-top: 0 !important;
    }
    
    /* Left column dataframes with modern styling */
    [data-testid="column"]:first-child .stDataFrame {
        background: white !important;
        border: 1px solid #dee2e6 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
    }
    
    [data-testid="column"]:first-child .stDataFrame table {
        background: white !important;
        color: #495057 !important;
    }
    
    [data-testid="column"]:first-child .stDataFrame th {
        background: #f8f9fa !important;
        color: #495057 !important;
        border: 1px solid #dee2e6 !important;
        font-weight: 600 !important;
    }
    
    [data-testid="column"]:first-child .stDataFrame td {
        background: white !important;
        color: #495057 !important;
        border: 1px solid #dee2e6 !important;
    }
    
    /* Metric containers */
    .metric-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .phase-header {
        background: #e3f2fd;
        padding: 0.75rem;
        border-radius: 6px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    
    .success-metric {
        background: #e8f5e8;
        border-left: 4px solid #4caf50;
    }
    
    .warning-metric {
        background: #fff3e0;
        border-left: 4px solid #ff9800;
    }
    
    .error-metric {
        background: #ffebee;
        border-left: 4px solid #f44336;
    }
    
    /* Dataframe styling */
    .dataframe {
        border: 1px solid #ddd;
        border-radius: 6px;
        overflow: hidden;
    }
    
    .stDataFrame {
        border: 1px solid #ddd;
        border-radius: 6px;
    }
    
    /* Visual separator between columns */
    .main .block-container {
        background: linear-gradient(90deg, #f8f9fa 50%, #2d3748 50%);
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        [data-testid="column"]:first-child,
        [data-testid="column"]:last-child {
            margin-bottom: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False

# Force debug mode to be disabled by default
st.session_state.debug_mode = False

@st.cache_resource(ttl=60)  # Cache for 60 seconds to allow for updates
def init_backend():
    try:
        config = ConfigManager()
        llm_client = LLMClient(config)
        prompt_builder = PromptBuilder(config)  
        learner_manager = LearnerManager(config)
        scoring_engine = ScoringEngine(config, learner_manager)
        activity_manager = ActivityManager(config)
        logger = get_logger()
        pipeline = EvaluationPipeline(
            config, llm_client, prompt_builder,
            scoring_engine, learner_manager, activity_manager
        )
        return {
            'config': config,
            'llm_client': llm_client,
            'prompt_builder': prompt_builder,
            'scoring_engine': scoring_engine,
            'learner_manager': learner_manager,
            'activity_manager': activity_manager,
            'pipeline': pipeline,
            'logger': logger
        }
    except Exception as e:
        st.error(f"Backend initialization failed: {e}")
        st.error(f"Traceback: {traceback.format_exc()}")
        st.stop()

def format_activity_for_ui(activity):
    try:
        if hasattr(activity, '__dict__'):
            a = activity.__dict__
        elif isinstance(activity, dict):
            a = activity
        else:
            # If activity is not a dict or object with __dict__, create a basic structure
            st.error(f"Unexpected activity type: {type(activity)}. Activity: {activity}")
            return {
                'activity_id': str(activity) if activity else 'unknown',
                'title': 'Untitled Activity',
                'activity_type': 'Unknown',
                'description': 'No description available',
                'l_d_complexity': 'L1-D1',
                'target_skill': {'skill_name': 'Unknown'},
                'estimated_time_minutes': 30,
                'components': []
            }
        
        # Extract instructions and components from the nested structure
        instructions = 'No instructions provided.'
        components = []
        
        # Try to get instructions from activity_generation_output structure
        if 'activity_generation_output' in a:
            ag_output = a['activity_generation_output']
            if 'components' in ag_output and ag_output['components']:
                first_component = ag_output['components'][0]
                if 'student_facing_content' in first_component:
                    sfc = first_component['student_facing_content']
                    instructions = sfc.get('instructions', 'No instructions provided.')
                    # Also extract other useful content
                    if 'stem' in sfc:
                        instructions = f"**Task:** {sfc['stem']}\n\n**Instructions:** {instructions}"
                    if 'scenario' in sfc:
                        instructions = f"**Scenario:** {sfc['scenario']}\n\n{instructions}"
                    if 'given' in sfc:
                        instructions = f"{instructions}\n\n**Given Information:** {sfc['given']}"
                
                # Extract components for multiple choice questions
                if a.get('activity_type') == 'SR' or (ag_output and ag_output.get('activity_type') == 'selected_response'):
                    # Try to extract from activity_generation_output first
                    if ag_output and 'components' in ag_output:
                        for comp in ag_output['components']:
                            if 'question' in comp:
                                question_data = comp['question']
                                component_data = {
                                    'stem': question_data.get('question_text', 'Question text not available'),
                                    'options': [option.get('text', 'Option text not available') for option in question_data.get('options', [])]
                                }
                                components.append(component_data)
                            elif 'student_facing_content' in comp:
                                sfc = comp['student_facing_content']
                                component_data = {
                                    'stem': sfc.get('stem', 'Question text not available'),
                                    'options': [option.get('text', 'Option text not available') if isinstance(option, dict) else str(option) for option in comp.get('options', [])]
                                }
                                components.append(component_data)
                
                # Extract role play scenario information
                elif a.get('activity_type') == 'RP' or (ag_output and ag_output.get('activity_type') == 'role_play'):
                    # Extract role play specific content - only show student-facing content
                    if 'content' in a:
                        content = a['content']
                        # Remove backend information from student view
                        # if 'scenario_context' in content:
                        #     instructions = f"**Scenario Context:** {content['scenario_context']}\n\n{instructions}"
                        # if 'character_profile' in content:
                        #     instructions = f"{instructions}\n\n**Character Profile:** {content['character_profile']}"
                        # if 'objectives' in content:
                        #     objectives = content['objectives']
                        #     if isinstance(objectives, list):
                        #         objectives_text = "\n".join([f"• {obj}" for obj in objectives])
                        #         instructions = f"{instructions}\n\n**Objectives:**\n{objectives_text}"
                        #     else:
                        #         instructions = f"{instructions}\n\n**Objectives:** {objectives}"
                
                # Extract branching scenario information
                elif a.get('activity_type') == 'BR' or (ag_output and ag_output.get('activity_type') == 'branching_scenario'):
                    # Extract branching scenario specific content
                    if 'content' in a:
                        content = a['content']
                        if 'initial_scenario' in content:
                            instructions = f"**Initial Scenario:** {content['initial_scenario']}\n\n{instructions}"
                        if 'decision_points' in content:
                            instructions = f"{instructions}\n\n**Decision Points:** {content['decision_points']}"
                        if 'paths' in content:
                            instructions = f"{instructions}\n\n**Available Paths:** {content['paths']}"
                
                # Extract single response question information
                elif a.get('activity_type') == 'SR' or (ag_output and ag_output.get('activity_type') == 'selected_response'):
                    # Extract single response specific content
                    if 'content' in a:
                        content = a['content']
                        if 'question' in content:
                            instructions = f"**Question:** {content['question']}\n\n{instructions}"
                        if 'options' in content:
                            options = content['options']
                            if isinstance(options, list):
                                options_text = "\n".join([f"• {opt}" for opt in options])
                                instructions = f"{instructions}\n\n**Options:**\n{options_text}"
                            else:
                                instructions = f"{instructions}\n\n**Options:** {options}"
                
                # Extract coding exercise information
                elif a.get('activity_type') == 'COD' or (ag_output and ag_output.get('activity_type') == 'coding_exercise'):
                    # Extract coding exercise specific content
                    if 'content' in a:
                        content = a['content']
                        if 'problem_statement' in content:
                            instructions = f"**Problem Statement:** {content['problem_statement']}\n\n{instructions}"
                        if 'starter_code' in content:
                            instructions = f"{instructions}\n\n**Starter Code:**\n```python\n{content['starter_code']}\n```"
                        if 'test_cases' in content and content['test_cases']:
                            instructions = f"{instructions}\n\n**Test Cases:** {content['test_cases']}"
        
        # Fallback: If no components found, check content field
        if not components and 'content' in a:
            content = a['content']
            if 'question' in content and 'options' in content:
                component_data = {
                    'stem': content['question'],
                    'options': [option.get('text', 'Option text not available') for option in content['options']]
                }
                components.append(component_data)
        
        # Fallback to direct content if available
        if instructions == 'No instructions provided.' and 'content' in a:
            content = a['content']
            if 'response_guidelines' in content:
                instructions = content['response_guidelines']
            elif 'problem_statement' in content:
                instructions = content['problem_statement']
            elif 'prompt' in content:
                instructions = content['prompt']
                if 'response_guidelines' in content:
                    instructions += f"\n\n**Detailed Instructions:** {content['response_guidelines']}"
            elif 'question' in content:
                # For SR activities, provide general instructions
                instructions = "**Instructions:** Read the question carefully and select the most appropriate answer from the options provided."
        
        return {
            'activity_id': a.get('activity_id'),
            'title': a.get('title', 'Untitled'),
            'activity_type': a.get('activity_type', 'Unknown'),
            'description': a.get('description', ''),
            'l_d_complexity': f"{a.get('cognitive_level', 'L1')}-{a.get('depth_level', 'D1')}",
            'target_skill': {'skill_name': a.get('target_skill', 'Unknown')} 
        if isinstance(a.get('target_skill'), str) else (a.get('target_skill') or {'skill_name': 'Unknown'}),
            'estimated_time_minutes': a.get('estimated_time_minutes', a.get('metadata', {}).get('estimated_time', 30)),
            'instructions': instructions,
            'components': components,
            **a
        }
    except Exception as e:
        st.error(f"Error formatting activity: {e}")
        st.error(f"Activity type: {type(activity)}")
        st.error(f"Activity content: {activity}")
        return {
            'activity_id': 'error',
            'title': 'Error Loading Activity',
            'activity_type': 'Unknown',
            'description': f'Error: {str(e)}',
            'l_d_complexity': 'L1-D1',
            'target_skill': {'skill_name': 'Unknown'},
            'estimated_time_minutes': 30,
            'components': []
        }

def get_activity_type_badge_color(activity_type):
    colors = {
        'CR': 'blue',
        'COD': 'green', 
        'RP': 'orange',
        'SR': 'purple',
        'BR': 'red'
    }
    return colors.get(activity_type, 'gray')

def format_timestamp(timestamp_str):
    try:
        if timestamp_str and timestamp_str != 'Unknown':
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return 'Unknown'
    except:
        return 'Unknown'

def create_activity_card(activity, col):
    with col:
        with st.container():
            try:
                # Handle ActivitySpec objects (from activity manager)
                if hasattr(activity, '__dict__'):
                    # Convert ActivitySpec to dict format
                    # Get estimated_time from metadata
                    metadata = getattr(activity, 'metadata', {})
                    estimated_time = metadata.get('estimated_time', 30) if isinstance(metadata, dict) else 30
                    
                    activity_dict = {
                        'activity_id': getattr(activity, 'activity_id', 'unknown'),
                        'title': getattr(activity, 'title', 'Untitled'),
                        'activity_type': getattr(activity, 'activity_type', 'Unknown'),
                        'description': getattr(activity, 'description', ''),
                        'cognitive_level': getattr(activity, 'cognitive_level', 'L1'),
                        'depth_level': getattr(activity, 'depth_level', 'D1'),
                        'target_skill': getattr(activity, 'target_skill', 'Unknown'),
                        'content': getattr(activity, 'content', {}),
                        'activity_generation_output': getattr(activity, 'activity_generation_output', None),
                        'estimated_time_minutes': estimated_time
                    }
                elif isinstance(activity, dict):
                    activity_dict = activity
                else:
                    st.error(f"Invalid activity format: {type(activity)}")
                    return
                
                # Format the activity for display
                formatted_activity = format_activity_for_ui(activity_dict)
                
                st.markdown(f"### {formatted_activity.get('title', 'Untitled Activity')}")
                activity_type = formatted_activity.get('activity_type', 'Unknown')
                st.markdown(f"**{activity_type}** **{formatted_activity.get('l_d_complexity', 'L1-D1')}**")
                
                target_skill = formatted_activity.get('target_skill', {})
                if isinstance(target_skill, dict):
                    skill_name = target_skill.get('skill_name', 'Unknown')
                else:
                    skill_name = str(target_skill)
                
                st.markdown(f"**Target Skill:** {skill_name}")
                st.markdown(f"**Time Estimate:** {formatted_activity.get('estimated_time_minutes', 30)} min")
                
                # Show description if available
                description = formatted_activity.get('description', '')
                if description:
                    st.markdown(f"*{description}*")
                
                # Show instructions preview
                instructions = formatted_activity.get('instructions', '')
                if instructions:
                    # Truncate instructions for card view
                    preview = instructions[:150] + "..." if len(instructions) > 150 else instructions
                    with st.expander("📋 Instructions Preview"):
                        st.markdown(preview)
                
                # Activity interaction button
                activity_id = formatted_activity.get('activity_id')
                if activity_id:
                    if st.button(f"🎯 Start Activity", key=f"start_{activity_id}"):
                        st.session_state.current_activity = formatted_activity
                        st.rerun()
                
                st.divider()
                
            except Exception as e:
                st.error(f"Error creating activity card: {str(e)}")
                st.error(f"Activity: {activity}")

def display_competency_progress_view(learner_id: str, backend: Dict):
    """Display competency cards with skill progress for student view"""
    try:
        # Get domain model for competencies and skills
        domain_model = backend['config'].get_config('domain_model')
        if not domain_model:
            st.error("Domain model configuration not found.")
            return
            
        competencies = domain_model.get('competencies', [])
        skills = domain_model.get('skills', [])
        
        if not competencies:
            st.warning("No competencies found in domain model.")
            return
        
        # Create a mapping of competency ID to skills
        competency_skills = {}
        for skill in skills:
            comp_id = skill.get('competency')
            if comp_id:
                if comp_id not in competency_skills:
                    competency_skills[comp_id] = []
                competency_skills[comp_id].append(skill['id'])
        
        # Get skill progress for this learner
        try:
            skill_progress = backend['learner_manager'].get_skill_progress(learner_id)
        except Exception as e:
            st.error(f"Error getting skill progress: {str(e)}")
            skill_progress = {}
        
        if not skill_progress:
            st.info("No skill progress data available for this learner yet.")
            # Show empty competency cards
            for comp in competencies:
                comp_id = comp.get('id')
                comp_name = comp.get('name', f'Competency {comp_id}')
                comp_skills = competency_skills.get(comp_id, [])
                
                with st.expander(f"📚 {comp_name} (0/{len(comp_skills)} skills complete)", expanded=True):
                    st.markdown(f"**{comp_name}**")
                    st.markdown(f"*{comp.get('description', 'No description available.')}*")
                    
                    # Progress bar for overall competency
                    st.progress(0.0)
                    st.markdown(f"**0/{len(comp_skills)}** skills completed")
                    
                    # Display individual skills
                    st.markdown("### Individual Skills:")
                    for skill_id in comp_skills:
                        st.markdown(f"**🔴 Skill {skill_id}**")
                        perf_col, evid_col = st.columns(2)
                        with perf_col:
                            st.markdown("**Performance**")
                            st.progress(0.0)
                            st.markdown("*0.0% / 75%*")
                        with evid_col:
                            st.markdown("**Evidence**")
                            st.progress(0.0)
                            st.markdown("*0.0 / 30*")
                        st.markdown("<br>", unsafe_allow_html=True)
            return
        
        # Display each competency as a card
        for comp in competencies:
            comp_id = comp.get('id')
            comp_name = comp.get('name', f'Competency {comp_id}')
            comp_skills = competency_skills.get(comp_id, [])
            
            if not comp_skills:
                continue
            
            # Count completed skills (skills with cumulative_score >= 0.75)
            completed_skills = 0
            for skill_id in comp_skills:
                skill_data = skill_progress.get(skill_id)
                if skill_data:
                    try:
                        cumulative_score = getattr(skill_data, 'cumulative_score', 0)
                        if cumulative_score >= 0.75:
                            completed_skills += 1
                    except Exception as e:
                        st.error(f"Error accessing skill data for {skill_id}: {str(e)}")
                        continue
            
            total_skills = len(comp_skills)
            
            # Create competency card
            with st.expander(f"📚 {comp_name} ({completed_skills}/{total_skills} skills complete)", expanded=False):
                st.markdown(f"**{comp_name}**")
                st.markdown(f"*{comp.get('description', 'No description available.')}*")
                
                # Progress bar for overall competency
                progress_percent = (completed_skills / total_skills) * 100 if total_skills > 0 else 0
                st.progress(progress_percent / 100)
                st.markdown(f"**{completed_skills}/{total_skills}** skills completed")
                
                # Display individual skills
                st.markdown("### Individual Skills:")
                for skill_id in comp_skills:
                    skill_data = skill_progress.get(skill_id)
                    if skill_data:
                        try:
                            skill_name = getattr(skill_data, 'skill_name', f'Skill {skill_id}')
                            cumulative_score = getattr(skill_data, 'cumulative_score', 0)
                            cumulative_evidence = getattr(skill_data, 'total_adjusted_evidence', 0)
                            
                            # Determine skill status
                            if cumulative_score >= 0.75:
                                status_emoji = "✅"
                                status_color = "green"
                            elif cumulative_score >= 0.5:
                                status_emoji = "🟡"
                                status_color = "orange"
                            else:
                                status_emoji = "🔴"
                                status_color = "red"
                            
                            st.markdown(f"**{status_emoji} {skill_name}**")
                            
                            # Compact side-by-side layout for performance and evidence
                            perf_col, evid_col = st.columns(2)
                            
                            with perf_col:
                                st.markdown("**Performance**")
                                # Get threshold from scoring config
                                scoring_config = backend['config'].get_config('scoring_config')
                                performance_threshold = scoring_config.get('gate_thresholds', {}).get('gate_1_threshold', 0.75)
                                
                                # Compact progress bar with inline threshold
                                st.progress(cumulative_score)
                                st.markdown(f"*{cumulative_score:.1%} / {performance_threshold:.0%}*", help="Score / Threshold")
                            
                            with evid_col:
                                st.markdown("**Evidence**")
                                evidence_threshold = scoring_config.get('gate_thresholds', {}).get('gate_2_threshold', 30.0)
                                # Normalize evidence to 0-1 scale using threshold as max
                                evidence_progress = min(cumulative_evidence / evidence_threshold, 1.0)
                                
                                # Compact progress bar with inline threshold
                                st.progress(evidence_progress)
                                st.markdown(f"*{cumulative_evidence:.1f} / {evidence_threshold:.0f}*", help="Evidence / Threshold")
                        except Exception as e:
                            st.error(f"Error displaying skill {skill_id}: {str(e)}")
                            st.markdown(f"**🔴 Skill {skill_id}**")
                            perf_col, evid_col = st.columns(2)
                            with perf_col:
                                st.markdown("**Performance**")
                                st.progress(0.0)
                                st.markdown("*Error*")
                            with evid_col:
                                st.markdown("**Evidence**")
                                st.progress(0.0)
                                st.markdown("*Error*")
                    else:
                        # Skill not found in progress data
                        st.markdown(f"**🔴 Skill {skill_id}**")
                        perf_col, evid_col = st.columns(2)
                        with perf_col:
                            st.markdown("**Performance**")
                            st.progress(0.0)
                            st.markdown("*0.0% / 75%*")
                        with evid_col:
                            st.markdown("**Evidence**")
                            st.progress(0.0)
                            st.markdown("*0.0 / 30*")
                    
                    # Reduced spacing between skills
                    st.markdown("<br>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying competency progress: {str(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")

backend = init_backend()

# Initialize session state
if 'current_learner' not in st.session_state:
    st.session_state.current_learner = None
if 'current_activity' not in st.session_state:
    st.session_state.current_activity = None
if 'evaluation_queue' not in st.session_state:
    st.session_state.evaluation_queue = []
if 'pipeline_status' not in st.session_state:
    st.session_state.pipeline_status = {}
if 'evaluation_results' not in st.session_state:
    st.session_state.evaluation_results = {}

# Enhanced Sidebar with Three Sections
with st.sidebar:
    st.markdown("## 🎛️ Control Panel")
    
    # Note: View Mode Toggle moved to top of main content area
    
    # Section A: User Management
    with st.expander("👤 User Management", expanded=True):
        st.header("👤 Learner Selection")
        try:
            learners = backend['learner_manager'].list_learners()
            if learners:
                learner_options = [f"{l.name} ({l.learner_id})" for l in learners]
                
                # Set Sarah as default (index 0 if she exists)
                default_index = 0
                for i, l in enumerate(learners):
                    if 'sarah' in l.name.lower() or 'learner_002' in l.learner_id.lower():
                        default_index = i
                        break
                
                # Set current learner if not already set
                if not st.session_state.current_learner:
                    st.session_state.current_learner = learners[default_index]
                    backend['logger'].log_system_event('streamlit_ui', 'learner_selected', f"Default learner: {learners[default_index].name}")
                
                # Find current index based on session state
                current_index = 0
                if st.session_state.current_learner:
                    for i, l in enumerate(learners):
                        if l.learner_id == st.session_state.current_learner.learner_id:
                            current_index = i
                            break

                selected_learner = st.selectbox(
                    "Select Active Learner:",
                    options=learner_options,
                    index=current_index,
                    key="learner_selector",
                    help="Choose a learner to work with"
                )

                # Update session state when selection changes
                selected_index = learner_options.index(selected_learner)
                if 0 <= selected_index < len(learners):
                    new_learner = learners[selected_index]
                    if not st.session_state.current_learner or st.session_state.current_learner.learner_id != new_learner.learner_id:
                        st.session_state.current_learner = new_learner
                        backend['logger'].log_system_event('streamlit_ui', 'learner_selected', f"Selected learner: {new_learner.name}")
                        st.success(f"✅ Active: {new_learner.name}")
                        st.rerun()
                else:
                    st.session_state.current_learner = None
            else:
                st.warning("No learners found in database")
                st.session_state.current_learner = None
        except Exception as e:
            st.error(f"Error loading learners: {e}")
            st.error(f"Traceback: {traceback.format_exc()}")
            st.session_state.current_learner = None
        
        # Learner Management Section
        if st.session_state.current_learner:
            current_learner = st.session_state.current_learner
            st.info(f"Managing: {current_learner.name}")
            
            # Learner History Management
            st.subheader("�� Activity History")
            
            # Show total number of activities
            try:
                # Get total activity count
                with backend['learner_manager']._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) as count FROM activity_records WHERE learner_id = ?', (current_learner.learner_id,))
                    total_activities = cursor.fetchone()['count']
                
                st.metric("Total Activities", total_activities)
                
                if total_activities > 0:
                    # Reset history button with proper confirmation using session state
                    reset_key = f"reset_confirm_{current_learner.learner_id}"
                    
                    # Initialize session state
                    if reset_key not in st.session_state:
                        st.session_state[reset_key] = False
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("🗑️ Reset All Learner History", type="secondary", key=f"reset_btn_{current_learner.learner_id}"):
                            st.session_state[reset_key] = True
                    
                    # Show confirmation if reset was clicked
                    if st.session_state[reset_key]:
                        st.warning("⚠️ **WARNING: This will permanently delete ALL learner data!**")
                        
                        # Confirmation checkbox
                        confirmation = st.checkbox("✅ I understand this will permanently delete ALL learner data and cannot be undone", key=f"confirm_reset_{current_learner.learner_id}")
                        
                        col1, col2, col3 = st.columns([1, 1, 1])
                        with col1:
                            if st.button("🚨 CONFIRM RESET", type="primary", key=f"confirm_btn_{current_learner.learner_id}"):
                                st.write("🔍 Debug: CONFIRM RESET button clicked")
                                st.write(f"🔍 Debug: Confirmation checkbox state: {confirmation}")
                                
                                if confirmation:
                                    try:
                                        st.info(f"🔄 Resetting history for {current_learner.name} (ID: {current_learner.learner_id})...")
                                        st.write("🔍 Debug: Calling reset_learner_history...")
                                        success = backend['learner_manager'].reset_learner_history(current_learner.learner_id)
                                        st.write(f"🔍 Debug: Reset result: {success}")
                                        
                                        if success:
                                            st.success(f"✅ All learner history reset for {current_learner.name}")
                                            st.balloons()
                                            # Clear session state and rerun
                                            st.session_state[reset_key] = False
                                            st.rerun()
                                        else:
                                            st.error(f"❌ Failed to reset learner history")
                                    except Exception as e:
                                        st.error(f"❌ Failed to reset history: {str(e)}")
                                        st.exception(e)
                                else:
                                    st.error("❌ Please check the confirmation checkbox first")
                        
                        with col2:
                            if st.button("❌ Cancel", type="secondary", key=f"cancel_btn_{current_learner.learner_id}"):
                                st.session_state[reset_key] = False
                                st.rerun()
                        
                        if not confirmation:
                            st.info("ℹ️ Please check the confirmation checkbox above to enable the reset button")
                else:
                    st.write("No activity history to reset")
                    
            except Exception as e:
                st.error(f"Error checking activity history: {str(e)}")
        else:
            st.warning("No learner selected")
    
    # Section B: LLM Settings for Each Phase
    with st.expander("🤖 LLM Settings", expanded=True):
        st.header("🤖 LLM Configuration")
        
        # Get current LLM settings
        llm_config = backend['config'].get_config('llm_settings')
        providers = llm_config.get('providers', {})
        phases = llm_config.get('phases', {})
        
        # First LLM Call Settings (Summative Evaluation)
        st.subheader("🎯 First LLM Call (Summative Evaluation)")
        
        # Provider selection for first call
        primary_provider = st.selectbox(
            "Provider:",
            options=list(providers.keys()),
            index=list(providers.keys()).index(phases.get('combined_evaluation', {}).get('preferred_provider', 'openai')),
            key="primary_provider"
        )
        
        # Model selection for first call
        primary_models = providers.get(primary_provider, {}).get('available_models', [])
        primary_model = st.selectbox(
            "Model:",
            options=primary_models,
            index=primary_models.index(providers.get(primary_provider, {}).get('default_model', primary_models[0] if primary_models else '')),
            key="primary_model"
        )
        
        # Temperature and max tokens for first call
        col1, col2 = st.columns(2)
        with col1:
            primary_temp = st.slider(
                "Temperature:",
                min_value=0.0,
                max_value=1.0,
                value=phases.get('combined_evaluation', {}).get('temperature', 0.1),
                step=0.05,
                key="primary_temp"
            )
        with col2:
            primary_max_tokens = st.slider(
                "Max Tokens:",
                min_value=1000,
                max_value=8000,
                value=phases.get('combined_evaluation', {}).get('max_tokens', 6000),
                step=500,
                key="primary_max_tokens"
            )
        
        # Second LLM Call Settings (Feedback Generation)
        st.subheader("📊 Second LLM Call (Feedback Generation)")
        
        # Provider selection for second call
        secondary_provider = st.selectbox(
            "Provider:",
            options=list(providers.keys()),
            index=list(providers.keys()).index(phases.get('scoring', {}).get('preferred_provider', 'openai')),
            key="secondary_provider"
        )
        
        # Model selection for second call
        secondary_models = providers.get(secondary_provider, {}).get('available_models', [])
        secondary_model = st.selectbox(
            "Model:",
            options=secondary_models,
            index=secondary_models.index(providers.get(secondary_provider, {}).get('default_model', secondary_models[0] if secondary_models else '')),
            key="secondary_model"
        )
        
        # Temperature and max tokens for second call
        col1, col2 = st.columns(2)
        with col1:
            secondary_temp = st.slider(
                "Temperature:",
                min_value=0.0,
                max_value=1.0,
                value=phases.get('scoring', {}).get('temperature', 0.1),
                step=0.05,
                key="secondary_temp"
            )
        with col2:
            secondary_max_tokens = st.slider(
                "Max Tokens:",
                min_value=1000,
                max_value=8000,
                value=phases.get('scoring', {}).get('max_tokens', 4000),
                step=500,
                key="secondary_max_tokens"
            )
        
        # Apply LLM Settings Button
        if st.button("🔄 Apply LLM Settings", type="primary"):
            try:
                # Update the LLM configuration
                phases['combined_evaluation']['preferred_provider'] = primary_provider
                phases['combined_evaluation']['temperature'] = primary_temp
                phases['combined_evaluation']['max_tokens'] = primary_max_tokens
                
                phases['scoring']['preferred_provider'] = secondary_provider
                phases['scoring']['temperature'] = secondary_temp
                phases['scoring']['max_tokens'] = secondary_max_tokens
                
                # Update the config in memory and save
                backend['config'].configs['llm_settings'] = llm_config
                if backend['config'].save_config('llm_settings'):
                    st.success("✅ LLM settings updated successfully!")
                    # Clear cache to reload backend with new settings
                    st.cache_resource.clear()
                    st.rerun()
                else:
                    st.error("❌ Failed to save LLM settings")
                
            except Exception as e:
                st.error(f"❌ Failed to update LLM settings: {str(e)}")
    
    # Section C: Scoring Settings
    with st.expander("📊 Scoring Settings", expanded=True):
        st.header("📊 Scoring Configuration")
        
        # Get current scoring settings
        scoring_config = backend['config'].get_config('scoring_config')
        gate_thresholds = scoring_config.get('gate_thresholds', {})
        scoring_params = scoring_config.get('scoring_parameters', {})
        
        # Evidence Threshold (Gate 2)
        st.subheader("📈 Evidence Threshold")
        evidence_threshold = st.number_input(
            "Evidence Volume Threshold:",
            min_value=1.0,
            max_value=200.0,
            value=float(gate_thresholds.get('gate_2_threshold', 30.0)),
            step=0.1,
            format="%.1f",
            help="Total validity-adjusted evidence required for advancement"
        )
        
        # Score Threshold (Gate 1)
        st.subheader("🎯 Score Threshold")
        score_threshold = st.number_input(
            "Performance Threshold:",
            min_value=0.1,
            max_value=1.0,
            value=float(gate_thresholds.get('gate_1_threshold', 0.75)),
            step=0.01,
            format="%.3f",
            help="Cumulative score required for proficiency"
        )
        
        # Decay Factor
        st.subheader("📉 Decay Factor")
        decay_factor = st.number_input(
            "Position-based Decay:",
            min_value=0.1,
            max_value=1.0,
            value=float(scoring_params.get('decay_factor', 0.9)),
            step=0.001,
            format="%.3f",
            help="Decay rate for older activities (0.9^position)"
        )
        
        # Initialize previous decay factor in session state if not exists
        if 'previous_decay_factor' not in st.session_state:
            st.session_state.previous_decay_factor = decay_factor
        
        # Manual Retroactive Recalculation (for testing)
        if st.checkbox("Show manual recalculation options", value=False):
            st.subheader("🔄 Manual Retroactive Recalculation")
            st.write("Use this to manually trigger retroactive recalculation of all activities with the current decay factor.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Recalculate All Activities", type="secondary"):
                    with st.spinner("Recalculating all activities with current decay factor..."):
                        success = backend['scoring_engine'].recalculate_all_activities_with_new_decay()
                        if success:
                            st.success("✅ All activities updated with current decay factor!")
                            st.cache_resource.clear()
                            st.rerun()
                        else:
                            st.error("❌ Failed to update activities retroactively")
            
            with col2:
                if st.button("🔄 Recalculate Current Learner Only", type="secondary"):
                    if current_learner:
                        with st.spinner(f"Recalculating activities for {current_learner.name}..."):
                            success = backend['scoring_engine'].recalculate_all_activities_with_new_decay(current_learner.learner_id)
                            if success:
                                st.success(f"✅ Activities updated for {current_learner.name}!")
                                st.cache_resource.clear()
                                st.rerun()
                            else:
                                st.error("❌ Failed to update activities retroactively")
                    else:
                        st.warning("No learner selected")
        
        # Current Settings Display
        st.subheader("📋 Current Settings")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Evidence Threshold", f"{evidence_threshold:.1f}")
        with col2:
            st.metric("Score Threshold", f"{score_threshold:.2f}")
        with col3:
            st.metric("Decay Factor", f"{decay_factor:.2f}")
        
        # Apply Scoring Settings Button
        if st.button("🔄 Apply Scoring Settings", type="primary"):
            try:
                # Update the scoring configuration
                gate_thresholds['gate_2_threshold'] = evidence_threshold
                gate_thresholds['gate_1_threshold'] = score_threshold
                scoring_params['decay_factor'] = decay_factor
                
                # Update the config in memory and save
                backend['config'].configs['scoring_config'] = scoring_config
                if backend['config'].save_config('scoring_config'):
                    # Update the scoring engine configuration directly
                    backend['scoring_engine'].update_configuration(backend['config'])
                    
                    st.success("✅ Scoring settings updated successfully!")
                    
                    # Offer retroactive recalculation for decay factor changes
                    if 'previous_decay_factor' in st.session_state:
                        if st.session_state.previous_decay_factor != decay_factor:
                            st.info("🔄 Decay factor changed! Would you like to apply this change retroactively to all existing activities?")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Apply Retroactively", type="secondary"):
                                    with st.spinner("Recalculating all activities with new decay factor..."):
                                        success = backend['scoring_engine'].recalculate_all_activities_with_new_decay()
                                        if success:
                                            st.success("✅ All activities updated with new decay factor!")
                                            st.cache_resource.clear()
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to update activities retroactively")
                            
                            with col2:
                                if st.button("❌ Skip Retroactive Update", type="secondary"):
                                    st.info("New decay factor will only apply to future activities.")
                    
                    # Store current decay factor for next comparison
                    st.session_state.previous_decay_factor = decay_factor
                    
                    # Clear cache to reload backend with new settings
                    st.cache_resource.clear()
                    st.rerun()
                else:
                    st.error("❌ Failed to save scoring settings")
                
            except Exception as e:
                st.error(f"❌ Failed to update scoring settings: {str(e)}")
    
    # Debug mode toggle (moved to bottom)
    st.header("🔧 Debug Options")
    debug_mode = st.checkbox("Debug Mode", value=st.session_state.get('debug_mode', False))
    st.session_state.debug_mode = debug_mode
    
    # Add backend health check (only in debug mode)
    if debug_mode:
        st.subheader("🔧 Backend Health Check")
        if st.button("Test Backend Components"):
            try:
                # Test each component
                test_results = {}
                
                # Test config manager
                try:
                    config = backend['config']
                    test_results['Config Manager'] = "✅ Working"
                except Exception as e:
                    test_results['Config Manager'] = f"❌ Error: {str(e)}"
                
                # Test LLM client
                try:
                    llm = backend['llm_client']
                    providers = llm.get_available_providers()
                    test_results['LLM Client'] = f"✅ Available providers: {providers}"
                    
                    # Check API keys
                    api_status = {}
                    for provider in ['anthropic', 'openai', 'google']:
                        if llm._check_api_key(provider):
                            api_status[provider] = "✅ Configured"
                        else:
                            api_status[provider] = "❌ Missing API key"
                    test_results['API Keys'] = api_status
                    
                except Exception as e:
                    test_results['LLM Client'] = f"❌ Error: {str(e)}"
                
                # Test activity manager
                try:
                    activities = backend['activity_manager'].load_activities()
                    test_results['Activity Manager'] = f"✅ Loaded {len(activities)} activities"
                except Exception as e:
                    test_results['Activity Manager'] = f"❌ Error: {str(e)}"
                
                # Test learner manager
                try:
                    learners = backend['learner_manager'].list_learners()
                    test_results['Learner Manager'] = f"✅ Found {len(learners)} learners"
                except Exception as e:
                    test_results['Learner Manager'] = f"❌ Error: {str(e)}"
                
                # Test evaluation pipeline
                try:
                    pipeline = backend['pipeline']
                    test_results['Evaluation Pipeline'] = "✅ Initialized"
                except Exception as e:
                    test_results['Evaluation Pipeline'] = f"❌ Error: {str(e)}"
                
                # Display results
                for component, status in test_results.items():
                    if isinstance(status, dict):
                        st.write(f"**{component}:**")
                        for subcomponent, substatus in status.items():
                            st.write(f"  - {subcomponent}: {substatus}")
                    else:
                        st.write(f"**{component}:** {status}")
                        
            except Exception as e:
                st.error(f"Health check failed: {str(e)}")

# View Mode Toggle - Positioned at top without taking space
st.markdown("""
<style>
.view-mode-toggle {
    position: fixed !important;
    top: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 9999 !important;
    background: rgba(255, 255, 255, 0.95) !important;
    padding: 2px 8px !important;
    border-radius: 0 0 4px 4px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    border: 1px solid #e0e0e0 !important;
    backdrop-filter: blur(10px) !important;
    max-height: 28px !important;
    width: auto !important;
}
.view-mode-toggle .stRadio > div {
    margin: 0 !important;
    padding: 0 !important;
}
.view-mode-toggle .stRadio > div > div {
    display: flex !important;
    gap: 4px !important;
    align-items: center !important;
    margin: 0 !important;
    padding: 0 !important;
}
.view-mode-toggle .stRadio > div > div > label {
    margin: 0 !important;
    padding: 2px 6px !important;
    border-radius: 3px !important;
    font-size: 0.75rem !important;
    line-height: 1.2 !important;
    min-height: auto !important;
    height: auto !important;
}
.view-mode-toggle .stRadio > div > div > label > div {
    display: flex !important;
    align-items: center !important;
    gap: 2px !important;
    margin: 0 !important;
    padding: 0 !important;
}
.view-mode-toggle .stRadio > div > div > label > div > span {
    font-size: 0.75rem !important;
    line-height: 1.2 !important;
}
</style>
""", unsafe_allow_html=True)

# Add toggle in a container with the CSS class
st.markdown('<div class="view-mode-toggle">', unsafe_allow_html=True)
view_mode = st.radio(
    "Main Interface:",
    options=["📊 Learner & Evaluation", "🎓 Student Progress View"],
    key="view_mode_toggle",
    help="Switch between different interface layouts",
    label_visibility="collapsed"
)
st.markdown('</div>', unsafe_allow_html=True)



# Main layout based on view mode
if view_mode == "📊 Learner & Evaluation":
    # Original 50/50 split layout
    left_col, right_col = st.columns(2)

    # LEFT COLUMN - LEARNER VIEW
    with left_col:
        st.markdown("""
        <div style="text-align: center; padding: 0.3rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 6px; color: white; margin-bottom: 1rem;">
            <h2 style="margin: 0; font-size: 1.1rem;">Activity Menu</h2>
        </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.current_learner:
            st.warning("Please select a learner from the dropdown above to start.")
            st.info("💡 **How to get started:** Select a learner from the dropdown, then choose an activity to begin.")
        else:
            learner = st.session_state.current_learner
            st.success(f"👤 **Active Learner:** {getattr(learner, 'name', 'Unknown')}")
            
            # Show evaluation complete notification
            if st.session_state.get('evaluation_complete', False):
                st.success("🎉 **Evaluation Complete!** Your results are ready below.")
                # Clear the flag after showing the notification
                st.session_state.evaluation_complete = False
            
            # Force refresh if evaluation results were just updated
            if st.session_state.get('evaluation_results_updated', False):
                st.session_state.evaluation_results_updated = False
                st.rerun()
            
            # Show submitted activity if available
            if hasattr(st.session_state, 'submitted_activity') and st.session_state.submitted_activity:
                st.subheader("📝 Submitted Activity")
                submitted = st.session_state.submitted_activity
                activity_id = submitted.get('activity_id', 'Unknown')
                
                # Show student-facing feedback
                if activity_id in st.session_state.evaluation_results:
                    result = st.session_state.evaluation_results[activity_id]
                    
                    # Debug information
                    if st.session_state.get('debug_mode', False):
                        st.write("🔍 **Left Side Debug:**")
                        st.write(f"Activity ID: {activity_id}")
                        st.write(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                        st.write(f"Overall success: {result.get('overall_success', 'Not found')}")
                        st.write(f"Has final_skill_scores: {'final_skill_scores' in result}")
                        st.write(f"Has pipeline_phases: {'pipeline_phases' in result}")
                        if 'pipeline_phases' in result:
                            st.write(f"Pipeline phases type: {type(result['pipeline_phases'])}")
                            if isinstance(result['pipeline_phases'], dict):
                                st.write(f"Pipeline phases keys: {list(result['pipeline_phases'].keys())}")
                        st.write("---")
                    
                    # Check if evaluation was successful (either overall_success or successful pipeline phases)
                    evaluation_successful = result.get('overall_success', False)
                    
                    # If overall_success is not set, check if we have successful pipeline phases
                    if not evaluation_successful and 'pipeline_phases' in result:
                        if isinstance(result['pipeline_phases'], dict):
                            # Check if any phases completed successfully
                            for phase_name, phase_result in result['pipeline_phases'].items():
                                if phase_result.get('status') == 'completed':
                                    evaluation_successful = True
                                    break
                        elif isinstance(result['pipeline_phases'], list):
                            # Check if any phases completed successfully
                            for phase in result['pipeline_phases']:
                                if hasattr(phase, 'success') and phase.success:
                                    evaluation_successful = True
                                    break
                    
                    if evaluation_successful:
                        st.success("✅ **Evaluation Complete!**")
                        
                        # Show activity score
                        st.subheader("🎯 Your Performance")
                        
                        # Debug information for activity score
                        if st.session_state.get('debug_mode', False):
                            st.write("🔍 **Activity Score Debug:**")
                            st.write(f"Result keys: {list(result.keys())}")
                            st.write(f"Pipeline phases: {result.get('pipeline_phases', {}).keys() if 'pipeline_phases' in result else 'No pipeline phases'}")
                            if 'pipeline_phases' in result and 'combined_evaluation' in result['pipeline_phases']:
                                combined_eval = result['pipeline_phases']['combined_evaluation']
                                st.write(f"Combined evaluation: {combined_eval}")
                                if 'result' in combined_eval:
                                    st.write(f"Combined eval result keys: {list(combined_eval['result'].keys())}")
                            st.write("---")
                        
                        # Try to get activity score from combined evaluation
                        activity_score = None
                        if 'pipeline_phases' in result and 'combined_evaluation' in result['pipeline_phases']:
                            combined_eval = result['pipeline_phases']['combined_evaluation']
                            if combined_eval.get('status') == 'completed' and 'result' in combined_eval:
                                combined_result = combined_eval['result']
                                if 'overall_score' in combined_result:
                                    activity_score = combined_result['overall_score']
                                elif 'score' in combined_result:
                                    activity_score = combined_result['score']
                        
                        # Display activity score
                        if activity_score is not None:
                            score_pct = activity_score * 100
                            st.metric("Activity Score", f"{score_pct:.1f}%")
                        else:
                            st.info("📊 Activity score not available")
                        
                        # Show skill scores if available (for reference)
                        if 'final_skill_scores' in result:
                            skill_scores = result['final_skill_scores']
                            
                            # Debug information for skill scores
                            if st.session_state.get('debug_mode', False):
                                st.write("🔍 **Skill Scores Debug:**")
                                st.write(f"Skill scores type: {type(skill_scores)}")
                                st.write(f"Skill scores: {skill_scores}")
                                if isinstance(skill_scores, dict):
                                    st.write(f"Skill scores keys: {list(skill_scores.keys())}")
                                    for skill_id, skill_score in skill_scores.items():
                                        st.write(f"Skill {skill_id}: {skill_score}")
                                        st.write(f"  Type: {type(skill_score)}")
                                        if hasattr(skill_score, '__dict__'):
                                            st.write(f"  Attributes: {list(skill_score.__dict__.keys())}")
                                st.write("---")
                            
                            if skill_scores:
                                for skill_id, skill_score in skill_scores.items():
                                    if hasattr(skill_score, 'skill_name'):
                                        skill_name = skill_score.skill_name
                                    else:
                                        skill_name = skill_id
                                    
                                    col1, col2, col3 = st.columns([2, 1, 1])
                                    with col1:
                                        st.markdown(f"**{skill_name}**")
                                    with col2:
                                        score_pct = skill_score.cumulative_score * 100
                                        st.metric("Score", f"{score_pct:.1f}%")
                                    with col3:
                                        if skill_score.overall_status == 'mastered':
                                            st.success("🎉 Mastered")
                                        elif skill_score.overall_status == 'approaching':
                                            st.warning("📈 Approaching")
                                        elif skill_score.overall_status == 'developing':
                                            st.info("🔄 Developing")
                                        else:
                                            st.error("⚠️ Needs Improvement")
                            else:
                                st.info("📊 No skill scores available for this activity.")
                        
                        # Show intelligent feedback if available
                        if 'pipeline_phases' in result and result['pipeline_phases']:
                            # Debug information for feedback
                            if st.session_state.get('debug_mode', False):
                                st.write("🔍 **Feedback Debug:**")
                                st.write(f"Pipeline phases type: {type(result['pipeline_phases'])}")
                                if isinstance(result['pipeline_phases'], dict):
                                    st.write(f"Pipeline phases keys: {list(result['pipeline_phases'].keys())}")
                                    if 'intelligent_feedback' in result['pipeline_phases']:
                                        feedback_phase = result['pipeline_phases']['intelligent_feedback']
                                        st.write(f"Intelligent feedback phase: {feedback_phase}")
                                        st.write(f"  Status: {feedback_phase.get('status', 'Not found')}")
                                        if 'result' in feedback_phase:
                                            st.write(f"  Result keys: {list(feedback_phase['result'].keys())}")
                                st.write("---")
                            if isinstance(result['pipeline_phases'], list):
                                for phase in result['pipeline_phases']:
                                    if hasattr(phase, 'phase') and phase.phase == 'intelligent_feedback':
                                        if phase.success and phase.result:
                                            st.subheader("💡 Feedback")
                                            if 'feedback' in phase.result:
                                                st.write(phase.result['feedback'])
                                            elif 'diagnostic_insights' in phase.result:
                                                st.write(phase.result['diagnostic_insights'])
                            elif isinstance(result['pipeline_phases'], dict):
                                # Handle dictionary format
                                try:
                                    for phase_name, phase_result in result['pipeline_phases'].items():
                                        if phase_name == 'intelligent_feedback' and phase_result.get('status') == 'completed':
                                            if 'result' in phase_result:
                                                st.subheader("💡 Feedback")
                                                
                                                # Extract feedback data
                                                feedback_data = phase_result['result'].get('intelligent_feedback', {})
                                                
                                                # Show diagnostic analysis (backend view)
                                                if 'diagnostic_analysis' in feedback_data:
                                                    st.subheader("🔍 Diagnostic Analysis")
                                                    diagnostic = feedback_data['diagnostic_analysis']
                                                    
                                                    if 'strength_areas' in diagnostic and diagnostic['strength_areas']:
                                                        st.write("**Strength Areas:**")
                                                        for strength in diagnostic['strength_areas']:
                                                            st.write(f"• {strength}")
                                                    
                                                    if 'improvement_areas' in diagnostic and diagnostic['improvement_areas']:
                                                        st.write("**Improvement Areas:**")
                                                        for area in diagnostic['improvement_areas']:
                                                            st.write(f"• {area}")
                                                    
                                                    if 'subskill_performance' in diagnostic:
                                                        st.write("**Subskill Performance:**")
                                                        for subskill in diagnostic['subskill_performance']:
                                                            st.write(f"• {subskill.get('subskill_name', 'Unknown')}: {subskill.get('performance_level', 'Unknown')}")
                                                
                                                # Show learner feedback (student-facing view)
                                                if 'learner_feedback' in feedback_data:
                                                    st.markdown("### 👤 Learner Feedback")
                                                    learner_feedback = feedback_data['learner_feedback']
                                                    
                                                    # Show overall assessment
                                                    if 'overall' in learner_feedback:
                                                        st.subheader("📋 Overall")
                                                        st.info(learner_feedback['overall'])
                                                    
                                                    # Show strengths and opportunities
                                                    col1, col2 = st.columns(2)
                                                    
                                                    with col1:
                                                        st.subheader("🏆 Strengths")
                                                        strengths = learner_feedback.get('strengths', '')
                                                        if strengths:
                                                            st.write(strengths)
                                                        else:
                                                            st.write("Strengths being analyzed...")
                                                    
                                                    with col2:
                                                        st.subheader("🚀 Opportunities")
                                                        opportunities = learner_feedback.get('opportunities', '')
                                                        if opportunities:
                                                            st.write(opportunities)
                                                        else:
                                                            st.write("Opportunities being analyzed...")
                                                
                                                # Fallback to simple feedback display
                                                if 'backend_intelligence' not in feedback_data and 'learner_feedback' not in feedback_data:
                                                    st.write("Feedback analysis completed successfully.")
                                except AttributeError:
                                    # Fallback if items() fails - treat as list
                                    st.warning("⚠️ Pipeline phases format error in feedback display")
                                    for phase in result['pipeline_phases']:
                                        if hasattr(phase, 'phase') and phase.phase == 'intelligent_feedback':
                                            if phase.success and phase.result:
                                                st.subheader("💡 Feedback")
                                                if 'feedback' in phase.result:
                                                    st.write(phase.result['feedback'])
                                                elif 'diagnostic_insights' in phase.result:
                                                    st.write(phase.result['diagnostic_insights'])
                    else:
                        st.error("❌ **Evaluation Failed**")
                        if 'error_summary' in result:
                            st.error(f"Error: {result['error_summary']}")
                        else:
                            st.error("Evaluation did not complete successfully.")
                else:
                    st.info("⏳ Evaluation in progress. Check the right panel for updates.")
            
            # Activity Interaction (only show if no submitted activity)
            if not hasattr(st.session_state, 'submitted_activity') or not st.session_state.submitted_activity:
                if not st.session_state.current_activity:
                    # Show available activities
                    st.subheader("📚 Available Activities")
                    
                    # Load activities
                    try:
                        activities = backend['activity_manager'].load_activities()
                        if activities:
                            # Convert activities to list if it's a dict
                            if isinstance(activities, dict):
                                activities_list = list(activities.values())
                            else:
                                activities_list = activities
                            
                            # Display activities in a grid
                            cols = st.columns(2)
                            for i, activity in enumerate(activities_list):
                                col = cols[i % 2]
                                create_activity_card(activity, col)
                        else:
                            st.warning("No activities available.")
                    except Exception as e:
                        st.error(f"Error loading activities: {e}")
                        if st.session_state.get('debug_mode', False):
                            import traceback
                            st.error(f"Traceback: {traceback.format_exc()}")
                
                # Activity Interaction
                else:
                    activity = st.session_state.current_activity
                    
                    # Add back button at the top
                    if st.button("← Back to Activities", key="back_to_activity_list"):
                        st.session_state.current_activity = None
                        # Clear evaluation results when navigating away
                        if "evaluation_results" in st.session_state:
                            st.session_state.evaluation_results = {}
                        st.rerun()
                    
                    st.subheader(f"📝 {activity.get('title', 'Untitled Activity')}")
                    
                    # Activity info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"**Type:** {activity.get('activity_type', 'Unknown')}")
                    with col2:
                        st.markdown(f"**Complexity:** {activity.get('l_d_complexity', 'L1-D1')}")
                    with col3:
                        target_skill = activity.get('target_skill', {})
                        if isinstance(target_skill, dict):
                            skill_name = target_skill.get('skill_name', str(target_skill.get('id', 'Unknown Skill')))
                        else:
                            skill_name = str(target_skill)
                        st.markdown(f"**Target Skill:** {skill_name}")
                    with col4:
                        st.markdown(f"**Time Estimate:** {activity.get('estimated_time_minutes', 30)} min")
                    
                    st.divider()
                    
                    # Activity instructions
                    with st.expander("📋 Activity Instructions", expanded=True):
                        instructions = activity.get('instructions', 'No instructions provided.')
                        st.markdown(instructions)
                    
                    # Response input based on activity type
                    activity_type = activity.get('activity_type', 'CR')
                    activity_id = activity.get('activity_id')
                    response_key = f"response_{activity_id}"
                    combined_response = ""
                    
                    if activity_type in ['CR', 'COD']:
                        st.subheader("📝 Your Response")
                        if activity_type == 'COD':
                            st.markdown("**Code Solution:**")
                            code_response = st.text_area(
                                "Enter your code here:",
                                height=200,
                                key=f"code_{response_key}",
                                help="Write your code solution"
                            )
                            st.markdown("**Code Explanation:**")
                            explanation_response = st.text_area(
                                "Explain your approach:",
                                height=100,
                                key=f"explanation_{response_key}",
                                help="Explain your code solution"
                            )
                            combined_response = f"Code:\n{code_response}\n\nExplanation:\n{explanation_response}"
                        else:
                            # CR activity
                            combined_response = st.text_area(
                                "Enter your response here:",
                                height=300,
                                key=response_key,
                                help="Write your detailed response"
                            )
                    
                    elif activity_type == 'RP':
                        st.subheader("💬 Role Play Conversation")
                        conv_key = f"conversation_{activity_id}"
                        if conv_key not in st.session_state:
                            st.session_state[conv_key] = []
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
                            
                            st.session_state[conv_key].append({
                                'speaker': 'ai_character',
                                'message': initial_message,
                                'timestamp': datetime.now().isoformat()
                            })
                        
                        # Display conversation history
                        for message in st.session_state[conv_key]:
                            if message['speaker'] == 'ai_character':
                                st.chat_message("assistant").write(message['message'])
                            else:
                                st.chat_message("user").write(message['message'])
                        
                        # Handle user input
                        processing_key = f"processing_{activity_id}"
                        is_processing = st.session_state.get(processing_key, False)
                        if not is_processing:
                            user_message = st.chat_input("Type your message...")
                        else:
                            st.info("Processing your message...")
                            user_message = None
                        
                        if user_message:
                            last_message_key = f"last_processed_message_{activity_id}"
                            last_processed = st.session_state.get(last_message_key, "")
                            if user_message != last_processed:
                                st.session_state[last_message_key] = user_message
                                st.session_state[processing_key] = True
                                st.session_state[conv_key].append({
                                    'speaker': 'learner',
                                    'message': user_message,
                                    'timestamp': datetime.now().isoformat()
                                })
                                
                                # Generate AI response
                                try:
                                    content = activity.get('content', {})
                                    scenario_context = content.get('scenario_context', 'General conversation')
                                    character_profile = content.get('character_profile', {})
                                    objectives = content.get('objectives', [])
                                    conversation_history = "\n".join([
                                        f"{msg['speaker']}: {msg['message']}"
                                        for msg in st.session_state[conv_key][-5:]
                                    ])
                                    rp_prompt = f"""You are an AI character in a role-playing educational scenario. 

SCENARIO: {scenario_context}

CHARACTER PROFILE: {json.dumps(character_profile, indent=2) if character_profile else 'Helpful AI assistant'}

OBJECTIVES: {objectives}

RECENT CONVERSATION:
{conversation_history}

USER'S LATEST MESSAGE: {user_message}

Respond as the character would, staying in role and helping advance the educational objectives. Keep responses conversational and appropriate for the scenario. Respond with only the character's message, no extra formatting."""
                                    
                                    with st.spinner("AI is thinking..."):
                                        llm_response = backend['llm_client'].call_llm_with_fallback(
                                            system_prompt="You are a helpful AI character in an educational role-playing scenario.",
                                            user_prompt=rp_prompt,
                                            phase='role_play'
                                        )
                                    
                                    if llm_response and hasattr(llm_response, 'success') and llm_response.success:
                                        ai_response = llm_response.content
                                    else:
                                        ai_response = f"I'm having trouble responding right now. Could you please rephrase that? (Error: {getattr(llm_response, 'error', 'No response') if llm_response else 'No response'})"
                                    
                                    st.session_state[conv_key].append({
                                        'speaker': 'ai_character', 
                                        'message': ai_response,
                                        'timestamp': datetime.now().isoformat()
                                    })
                                except Exception as e:
                                    st.error(f"Error generating AI response: {e}")
                                    ai_response = f"I understand you said: '{user_message}'. Let me think about how to respond to that in this scenario."
                                    st.session_state[conv_key].append({
                                        'speaker': 'ai_character', 
                                        'message': ai_response,
                                        'timestamp': datetime.now().isoformat()
                                    })
                                
                                st.session_state[processing_key] = False
                                st.rerun()
                        
                        combined_response = json.dumps(st.session_state[conv_key])
                    
                    elif activity_type == 'SR':
                        st.subheader("🔘 Multiple Choice Questions")
                        components = activity.get('components', [])
                        
                        responses = []
                        if components:
                            for i, component in enumerate(components):
                                st.markdown(f"**Question {i + 1}:**")
                                question_text = component.get('stem', 'Question text not available')
                                st.markdown(question_text)
                                options = component.get('options', ['Option A', 'Option B', 'Option C', 'Option D'])
                                selected = st.radio(
                                    "Choose your answer:",
                                    options,
                                    key=f"sr_{activity_id}_{i}",
                                    help=f"Select one option for question {i + 1}",
                                    index=None
                                )
                                responses.append(selected)
                                st.divider()
                        else:
                            st.warning("No multiple choice questions found in this activity.")
                        combined_response = json.dumps({
                            'component_responses': responses,
                            'total_questions': len(components)
                        })
                    
                    elif activity_type == 'BR':
                        st.subheader("🌳 Interactive Scenario")
                        scenario_key = f"scenario_{activity_id}"
                        if scenario_key not in st.session_state:
                            st.session_state[scenario_key] = {
                                'current_node': 'start',
                                'score': 0,
                                'decisions': [],
                                'completed': False
                            }
                        scenario_state = st.session_state[scenario_key]
                        st.markdown("**Current Situation:**")
                        st.info(activity.get('scenario_description', 'Scenario description not available'))
                        st.markdown(f"**Current Score:** {scenario_state['score']}")
                        if not scenario_state['completed']:
                            st.markdown("**What do you choose to do?**")
                            options = [
                                "Option A - Conservative approach",
                                "Option B - Balanced approach", 
                                "Option C - Aggressive approach"
                            ]
                            selected_option = st.radio("Select your decision:", options, key=f"br_decision_{activity_id}", index=None)
                            if st.button("Make Decision", key=f"br_submit_{activity_id}"):
                                decision_score = 1.0 if "Balanced" in selected_option else 0.5
                                scenario_state['score'] += decision_score
                                scenario_state['decisions'].append({
                                    'decision': selected_option,
                                    'score': decision_score,
                                    'timestamp': datetime.now().isoformat()
                                })
                                if len(scenario_state['decisions']) >= 3:
                                    scenario_state['completed'] = True
                                st.rerun()
                        else:
                            st.success("Scenario completed!")
                            st.markdown(f"**Final Score:** {scenario_state['score']}")
                        combined_response = json.dumps(scenario_state)
                    
                    # Submit button
                    if combined_response.strip():
                        submit_key = f"submit_{activity_id}"
                        if st.button("📤 Submit Activity", type="primary", key=submit_key):
                            # Create activity transcript
                            transcript = {
                                'activity_id': activity_id,
                                'learner_id': learner.learner_id,
                                'activity_transcript': {
                                    'activity_generation_output': activity,
                                    'student_engagement': {
                                        'start_timestamp': datetime.now(timezone.utc).isoformat(),
                                        'submit_timestamp': datetime.now(timezone.utc).isoformat(),
                                        'completion_status': 'completed',
                                        'component_responses': [
                                            {
                                                'component_id': 'main_response',
                                                'response_content': combined_response,
                                                'response_type': 'text',
                                                'metadata': {
                                                    'activity_type': activity_type,
                                                    'target_skill': activity.get('target_skill', 'Unknown')
                                                }
                                            }
                                        ],
                                        'assistance_log': []
                                    }
                                }
                            }
                            
                            # Store in session state
                            st.session_state.submitted_activity = transcript
                            
                            # Add to evaluation queue
                            if 'evaluation_queue' not in st.session_state:
                                st.session_state.evaluation_queue = []
                            st.session_state.evaluation_queue.append(transcript)
                            
                            # Debug information
                            if st.session_state.get('debug_mode', False):
                                st.write("🔍 **Submission Debug:**")
                                st.write(f"Transcript created: {transcript.get('activity_id', 'Unknown')}")
                                st.write(f"Queue length after append: {len(st.session_state.evaluation_queue)}")
                                st.write(f"Queue items: {[item.get('activity_id', 'Unknown') for item in st.session_state.evaluation_queue]}")
                            
                            # Clear current activity
                            st.session_state.current_activity = None
                            
                            st.success("✅ Activity submitted successfully!")
                            st.rerun()
                    else:
                        st.warning("Please provide a response before submitting.")

    # RIGHT COLUMN - EVALUATION MANAGEMENT
    with right_col:
        st.markdown("""
        <div style="text-align: center; padding: 0.3rem; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); border-radius: 6px; color: #68d391; margin-bottom: 1rem; border: 1px solid #4a5568;">
            <h2 style="margin: 0; font-size: 1.1rem; font-family: 'Menlo', 'Monaco', 'Courier New', monospace;">Evaluation and Scoring Backend</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Debug: Always show current state
        if st.session_state.get('debug_mode', False):
            st.write("🔍 **Current State Debug:**")
            st.write(f"Has submitted_activity: {hasattr(st.session_state, 'submitted_activity')}")
            st.write(f"Submitted activity: {st.session_state.submitted_activity if hasattr(st.session_state, 'submitted_activity') else 'None'}")
            st.write(f"Evaluation queue: {st.session_state.evaluation_queue}")
            st.write(f"Queue length: {len(st.session_state.evaluation_queue) if st.session_state.evaluation_queue else 0}")
            st.write(f"Pipeline status: {st.session_state.pipeline_status}")
            st.write("---")
        
        # Check for pipeline running first (highest priority)
        if st.session_state.pipeline_status:
            status = st.session_state.pipeline_status
            item = status.get('item', {})
            
            # Header with current status
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader("⚙️ Pipeline Monitor")
                st.markdown(f"**Evaluating:** {item.get('activity_id', 'Unknown')}")
                st.markdown(f"**Learner:** {item.get('learner_id', 'Unknown')}")
            with col2:
                if status.get('status') == 'running':
                    st.info("🔄 **Running**")
                elif status.get('status') == 'completed':
                    st.success("✅ **Completed**")
                elif status.get('status') == 'failed':
                    st.error("❌ **Failed**")
                
                # Real-time pipeline execution
                if status.get('status') == 'running':
                    try:
                        activity_id = item.get('activity_id', 'unknown')
                        learner_id = item.get('learner_id', 'unknown')
                        activity_transcript = item.get('activity_transcript', {})
                        
                        # Run evaluation in real-time with progress updates
                        evaluation_result = None
                        try:
                            with st.spinner("Running evaluation pipeline..."):
                                # Update status to show we're starting
                                st.session_state.pipeline_status['current_phase'] = 'rubric_evaluation'
                                
                                evaluation_result = backend['pipeline'].evaluate_activity(
                                    activity_id=activity_id,
                                    learner_id=learner_id,
                                    activity_transcript=activity_transcript,
                                    evaluation_mode='full'
                                )
                        except Exception as pipeline_error:
                            st.error(f"❌ Pipeline execution failed: {str(pipeline_error)}")
                            st.error(f"Error details: {traceback.format_exc()}")
                            st.session_state.pipeline_status.update({
                                'status': 'failed',
                                'error': str(pipeline_error)
                            })
                            st.rerun()
                        
                        # Process results OUTSIDE of spinner context to ensure session state persistence
                        if evaluation_result is not None:
                            # Update pipeline status with results
                            phases = []
                            
                            # Extract phase information from evaluation result
                            if hasattr(evaluation_result, 'pipeline_phases'):
                                for phase_result in evaluation_result.pipeline_phases:
                                    if hasattr(phase_result, 'phase'):
                                        phases.append({
                                            'phase': phase_result.phase,
                                            'status': 'completed' if phase_result.success else 'failed',
                                            'execution_time': phase_result.execution_time_ms / 1000 if phase_result.execution_time_ms else 0,
                                            'tokens_used': phase_result.tokens_used or 0,
                                            'cost_estimate': phase_result.cost_estimate or 0,
                                            'result': phase_result.result or {},
                                            'error': phase_result.error
                                        })
                            
                            # Update session state
                            st.session_state.pipeline_status.update({
                                'status': 'completed',
                                'phases': phases,
                                'evaluation_result': evaluation_result
                            })
                            
                            # Store results in session state for display in learner view
                            if not hasattr(st.session_state, 'evaluation_results'):
                                st.session_state.evaluation_results = {}
                            
                            # Convert evaluation result to dict for storage
                            if hasattr(evaluation_result, '__dict__'):
                                result_dict = evaluation_result.__dict__.copy()
                                # Convert pipeline_phases to a more displayable format
                                if 'pipeline_phases' in result_dict:
                                    phases_dict = {}
                                    for phase in result_dict['pipeline_phases']:
                                        if hasattr(phase, 'phase'):
                                            phases_dict[phase.phase] = {
                                                'status': 'completed' if phase.success else 'failed',
                                                'execution_time': phase.execution_time_ms / 1000 if phase.execution_time_ms else 0,
                                                'tokens_used': phase.tokens_used or 0,
                                                'cost_estimate': phase.cost_estimate or 0,
                                                'result': phase.result or {},
                                                'error': phase.error
                                            }
                                    result_dict['pipeline_phases'] = phases_dict
                            else:
                                result_dict = evaluation_result
                            
                            # Add timestamp for file recovery
                            result_dict['timestamp'] = time.time()
                            
                            # Store in session state
                            st.session_state.evaluation_results[activity_id] = result_dict
                            
                            # Also save to temporary file for recovery
                            try:
                                temp_file = f"temp_eval_results_{activity_id}.json"
                                with open(temp_file, 'w') as f:
                                    json.dump(result_dict, f, indent=2, default=str)
                            except Exception as e:
                                if st.session_state.get('debug_mode', False):
                                    st.write(f"⚠️ **Could not save to temp file:** {e}")
                            
                            # Set flags for UI updates
                            st.session_state.evaluation_complete = True
                            st.session_state.evaluation_results_updated = True
                            
                            # Clear pipeline status
                            st.session_state.pipeline_status = {}
                            
                            st.success("✅ Evaluation completed successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Evaluation failed - no result returned")
                            st.session_state.pipeline_status.update({
                                'status': 'failed',
                                'error': 'No evaluation result returned'
                            })
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Evaluation failed: {str(e)}")
                        st.error(f"Error details: {traceback.format_exc()}")
                        st.session_state.pipeline_status.update({
                            'status': 'failed',
                            'error': str(e)
                        })
                        st.rerun()
                
                # Show pipeline phase details if available
                if status.get('phases'):
                    st.subheader("📊 Pipeline Phase Details")
                    for phase in status['phases']:
                        phase_name = phase['phase'].replace('_', ' ').title()
                        if phase['status'] == 'completed':
                            st.success(f"✅ {phase_name}")
                            if 'result' in phase and phase['result']:
                                display_phase_results(phase['phase'], phase['result'], backend)
                        elif phase['status'] == 'failed':
                            st.error(f"❌ {phase_name}")
                            if 'error' in phase:
                                st.error(f"Error: {phase['error']}")
                        else:
                            st.info(f"⏳ {phase_name} - {phase['status']}")
                
                # Show execution metrics
                if status.get('phases'):
                    st.subheader("📈 Execution Metrics")
                    total_time = sum(phase.get('execution_time', 0) for phase in status['phases'])
                    total_tokens = sum(phase.get('tokens_used', 0) for phase in status['phases'])
                    total_cost = sum(phase.get('cost_estimate', 0) for phase in status['phases'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Time", f"{total_time:.2f}s")
                    with col2:
                        st.metric("Total Tokens", f"{total_tokens:,}")
                    with col3:
                        st.metric("Estimated Cost", f"${total_cost:.4f}")
                
                # Add clear button for pipeline status
                if st.button("🗑️ Clear Pipeline Status"):
                    st.session_state.pipeline_status = {}
                    st.rerun()
        
        # Check for completed evaluation results second
        elif hasattr(st.session_state, 'submitted_activity') and st.session_state.submitted_activity:
            submitted = st.session_state.submitted_activity
            activity_id = submitted.get('activity_id', 'Unknown')
            
            # Only show results if we actually have evaluation results
            if activity_id in st.session_state.evaluation_results:
                result = st.session_state.evaluation_results[activity_id]
                
                st.subheader("📊 Evaluation Results")
                
                # Display summary card at the top
                create_evaluation_summary_card(result)
                
                # Show overall success/failure
                if result.get('overall_success', False):
                    st.success("✅ **Evaluation Successful!**")
                else:
                    st.error("❌ **Evaluation Failed**")
                    if 'error_summary' in result:
                        st.error(f"Error: {result['error_summary']}")
                
                # Show evaluation details
                with st.expander("📊 Evaluation Details", expanded=True):
                    # Display pipeline phases if available
                    if 'pipeline_phases' in result and result['pipeline_phases']:
                        if isinstance(result['pipeline_phases'], list):
                            # Handle list format (original PhaseResult objects)
                            for phase in result['pipeline_phases']:
                                if hasattr(phase, 'phase'):
                                    phase_name = phase.phase.replace('_', ' ').title()
                                    if phase.success:
                                        st.success(f"✅ {phase_name}")
                                        if phase.result:
                                            display_phase_results(phase.phase, phase.result, backend)
                                    else:
                                        st.error(f"❌ {phase_name}")
                                        if phase.error:
                                            st.error(f"Error: {phase.error}")
                        elif isinstance(result['pipeline_phases'], dict):
                            # Handle dictionary format (converted for display)
                            try:
                                for phase_name, phase_result in result['pipeline_phases'].items():
                                    if phase_result['status'] == 'completed':
                                        st.success(f"✅ {phase_name.replace('_', ' ').title()}")
                                        if 'result' in phase_result:
                                            display_phase_results(phase_name, phase_result['result'], backend)
                                    elif phase_result['status'] == 'failed':
                                        st.error(f"❌ {phase_name.replace('_', ' ').title()}")
                                        if 'error' in phase_result:
                                            st.error(f"Error: {phase_result['error']}")
                                    else:
                                        st.info(f"⏳ {phase_name.replace('_', ' ').title()} - {phase_result['status']}")
                            except AttributeError:
                                # Fallback if items() fails - treat as list
                                st.warning("⚠️ Pipeline phases format error - displaying as list")
                                for phase in result['pipeline_phases']:
                                    if hasattr(phase, 'phase'):
                                        phase_name = phase.phase.replace('_', ' ').title()
                                        if phase.success:
                                            st.success(f"✅ {phase_name}")
                                            if phase.result:
                                                display_phase_results(phase.phase, phase.result, backend)
                                        else:
                                            st.error(f"❌ {phase_name}")
                                            if phase.error:
                                                st.error(f"Error: {phase.error}")
                    else:
                        # Fallback to old format
                        for phase_name, phase_result in result.items():
                            if phase_name in ['overall_success', 'error_summary', 'timestamp', 'pipeline_phases']:
                                continue
                            
                            if isinstance(phase_result, dict) and 'status' in phase_result:
                                if phase_result['status'] == 'completed':
                                    st.success(f"✅ {phase_name.title()}")
                                    if 'result' in phase_result:
                                        display_phase_results(phase_name, phase_result['result'], backend)
                                elif phase_result['status'] == 'failed':
                                    st.error(f"❌ {phase_name.title()}")
                                    if 'error' in phase_result:
                                        st.error(f"Error: {phase_result['error']}")
                                else:
                                    st.info(f"⏳ {phase_name.title()} - {phase_result['status']}")
                            else:
                                st.write(f"**{phase_name.title()}:**")
                                display_phase_results(phase_name, phase_result, backend)
                
                # Add clear button
                if st.button("🗑️ Clear Results"):
                    if activity_id in st.session_state.evaluation_results:
                        del st.session_state.evaluation_results[activity_id]
                    st.session_state.submitted_activity = None
                    st.rerun()
            else:
                # We have a submitted activity but no evaluation results yet
                st.info(f"📋 Activity '{activity_id}' submitted and waiting for evaluation.")
                st.info("💡 Click 'Start Evaluation' below to begin processing.")
                
                # Show the submitted activity details
                with st.expander("📄 Submitted Activity Details", expanded=True):
                    st.markdown(f"**Activity ID:** {activity_id}")
                    st.markdown(f"**Learner:** {submitted.get('learner_id', 'Unknown')}")
                    submit_time = submitted.get('activity_transcript', {}).get('student_engagement', {}).get('submit_timestamp', 'Unknown')
                    st.markdown(f"**Submitted:** {format_timestamp(submit_time)}")
                    
                    # Show response preview
                    responses = submitted.get('activity_transcript', {}).get('student_engagement', {}).get('component_responses', [])
                    if responses:
                        st.markdown("**Response:**")
                        for resp in responses:
                            st.text_area("Student Response", resp.get('response_content', ''), height=100, disabled=True)
                
                # Start evaluation button
                if st.button("🚀 Start Evaluation", type="primary", key="start_eval_submitted"):
                    try:
                        # Initialize pipeline status for real-time monitoring
                        st.session_state.pipeline_status = {
                            'item': submitted,
                            'status': 'running',
                            'current_phase': 'starting',
                            'phases': [],
                            'start_time': time.time(),
                            'evaluation_result': None
                        }
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to start evaluation: {e}")
                        st.rerun()
        
        # Show evaluation queue if there are items waiting
        elif st.session_state.evaluation_queue:
            st.subheader(f"📋 Evaluation Queue ({len(st.session_state.evaluation_queue)} items)")
            
            # Debug information
            if st.session_state.get('debug_mode', False):
                st.write("🔍 **Debug Info:**")
                st.write(f"Queue length: {len(st.session_state.evaluation_queue)}")
                st.write(f"Queue items: {[item.get('activity_id', 'Unknown') for item in st.session_state.evaluation_queue]}")
                st.write(f"Submitted activity: {st.session_state.submitted_activity.get('activity_id', 'None') if hasattr(st.session_state, 'submitted_activity') and st.session_state.submitted_activity else 'None'}")
                st.write(f"Pipeline status: {st.session_state.pipeline_status}")
            
            for i, item in enumerate(st.session_state.evaluation_queue):
                with st.expander(f"Item {i + 1}: {item.get('activity_id', 'Unknown Activity')}", expanded=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(f"**Learner:** {item.get('learner_id', 'Unknown')}")
                        st.markdown(f"**Activity:** {item.get('activity_id', 'Unknown')}")
                    with col2:
                        submit_time = item.get('activity_transcript', {}).get('student_engagement', {}).get('submit_timestamp', 'Unknown')
                        st.markdown(f"**Submitted:** {format_timestamp(submit_time)}")
                        st.markdown(f"**Status:** {'Pending Evaluation' if not item.get('scored', False) else 'Evaluated'}")
                    with col3:
                        if st.button("🚀 Start Evaluation", key=f"eval_{i}"):
                            eval_item = st.session_state.evaluation_queue.pop(i)
                            try:
                                # Initialize pipeline status for real-time monitoring
                                st.session_state.pipeline_status = {
                                    'item': eval_item,
                                    'status': 'running',
                                    'current_phase': 'starting',
                                    'phases': [],
                                    'start_time': time.time(),
                                    'evaluation_result': None
                                }
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to start evaluation: {e}")
                                st.rerun()
        

        
        # No activities in queue and no pipeline running
        else:
            st.info("No activities in the evaluation queue.")
            st.info("💡 **How to evaluate:** Submit an activity from the learner view on the left, then it will appear here for evaluation.")
            
            # Debug information
            if st.session_state.get('debug_mode', False):
                st.write("🔍 **Debug Info:**")
                st.write(f"Evaluation queue: {st.session_state.evaluation_queue}")
                st.write(f"Queue length: {len(st.session_state.evaluation_queue) if st.session_state.evaluation_queue else 0}")
                st.write(f"Submitted activity: {st.session_state.submitted_activity if hasattr(st.session_state, 'submitted_activity') else 'Not set'}")
                st.write(f"Pipeline status: {st.session_state.pipeline_status}")
                st.write(f"Current activity: {st.session_state.current_activity.get('activity_id', 'None') if st.session_state.current_activity else 'None'}")

else:
    # New Student Progress split-screen view
    
    # Check if learner is selected
    if not st.session_state.current_learner:
        st.warning("Please select a learner from the sidebar to view progress.")
        st.stop()
    
    # Add CSS class for Student Progress View alignment
    st.markdown('<div class="student-progress-view">', unsafe_allow_html=True)
    
    # Create the split columns
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.markdown("""
        <div style='text-align: center; padding: 0.3rem; background: linear-gradient(135deg, #38b2ac 0%, #4299e1 100%); border-radius: 6px; color: white; margin-bottom: 1rem;'>
            <h2 style='margin: 0; font-size: 1.1rem;'>Program Progress</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Show active learner name
        learner = st.session_state.current_learner
        st.success(f"👤 **Active Learner:** {getattr(learner, 'name', 'Unknown')}")
        
        try:
            display_competency_progress_view(st.session_state.current_learner.learner_id, backend)
        except Exception as e:
            st.error(f"Error displaying competency progress: {str(e)}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
    
    with right_col:
        st.markdown("""
        <div style='text-align: center; padding: 0.3rem; background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); border-radius: 6px; color: #68d391; margin-bottom: 1rem; border: 1px solid #4a5568;'>
            <h2 style='margin: 0; font-size: 1.1rem; font-family: 'Menlo', 'Monaco', 'Courier New', monospace;'>Backend Scoring Tables</h2>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            display_activity_history_tables(st.session_state.current_learner.learner_id, backend)
        except Exception as e:
            st.error(f"Error displaying activity history tables: {str(e)}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
    
    # Close the Student Progress View div
    st.markdown('</div>', unsafe_allow_html=True)

# Always show divider and version at the end
st.divider()
st.markdown("**Evaluator v16** - Educational Assessment Pipeline | Version 1.0.0")