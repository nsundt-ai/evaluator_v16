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
            cursor.execute('''
                SELECT DISTINCT skill_id 
                FROM activity_history 
                WHERE learner_id = ?
                ORDER BY skill_id
            ''', (learner_id,))
            skills_with_history = [row['skill_id'] for row in cursor.fetchall()]
        
        # If we have a current activity result, make sure its skill is included
        current_skill_id = None
        if current_activity_result:
            current_skill_id = current_activity_result.get('target_skill') or current_activity_result.get('skill_id', 'S001')
            if current_skill_id not in skills_with_history:
                skills_with_history.append(current_skill_id)
                skills_with_history.sort()  # Keep them ordered
        
        if not skills_with_history:
            st.info("No activity history found for any skills yet.")
            return
        
        # Display a table for each skill
        for skill_id in skills_with_history:
            display_single_skill_table(learner_id, skill_id, backend)
            
    except Exception as e:
        st.error(f"Error displaying activity history tables: {str(e)}")

def display_single_skill_table(learner_id: str, skill_id: str, backend: Dict):
    """Display activity history table for a single skill"""
    try:
        # Get activity history from database
        history_records = backend['learner_manager'].get_activity_history_for_learner_skill(learner_id, skill_id)
        
        if not history_records:
            return
        
        # Create DataFrame for display
        import pandas as pd
        from datetime import datetime
        
        # Prepare data for display
        display_data = []
        for i, record in enumerate(history_records):
            # Format scores as percentages
            performance_score = f"{record['performance_score']:.1%}"
            cumulative_performance = f"{record['cumulative_performance']:.1%}"
            
            # Format evidence volumes - ensure these are correct
            target_evidence = f"{record['target_evidence_volume']:.1f}"
            adjusted_evidence = f"{record['adjusted_evidence_volume']:.1f}"
            cumulative_evidence = f"{record['cumulative_evidence']:.1f}"
            
            # Format validity modifier
            validity_modifier = f"{record['validity_modifier']:.2f}"
            
            # Format decay factor
            decay_factor = f"{record['decay_factor']:.3f}"
            
            # Make cumulative values bold for the most recent row (i == 0)
            if i == 0:  # Most recent row
                cumulative_performance = f"**{cumulative_performance}**"
                cumulative_evidence = f"**{cumulative_evidence}**"
            
            display_data.append({
                'Activity': record['activity_title'] or record['activity_id'],
                'Score': performance_score,
                'Adjusted Evidence': adjusted_evidence,
                'Cumulative Performance': cumulative_performance,
                'Cumulative Evidence': cumulative_evidence,
                'Target Evidence': target_evidence,
                'Validity Modifier': validity_modifier,
                'Decay Factor': decay_factor,
                'Position': record['position_from_most_recent']
            })
        
        # Create DataFrame
        df = pd.DataFrame(display_data)
        
        # Display table with custom styling
        st.subheader(f"📊 Activity History - Skill {skill_id}")
        
        # Add custom CSS for highlighting the newest activity
        st.markdown("""
        <style>
        .new-activity {
            background-color: #d4edda !important;
            font-weight: bold;
        }
        .new-activity td {
            background-color: #d4edda !important;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display the table with highlighting for the newest activity
        if len(df) > 0:
            # Highlight the first row (most recent) with green background and "NEW" label
            st.markdown("""
            <div style="background-color: #d4edda; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>🆕 NEW</strong> - Most recent activity (highlighted in green)
            </div>
            """, unsafe_allow_html=True)
            
            # Display the table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Activity": st.column_config.TextColumn("Activity", width="medium"),
                    "Score": st.column_config.TextColumn("Score", width="small"),
                    "Adjusted Evidence": st.column_config.TextColumn("Adjusted Evidence", width="small"),
                    "Cumulative Performance": st.column_config.TextColumn("Cumulative Performance", width="small"),
                    "Cumulative Evidence": st.column_config.TextColumn("Cumulative Evidence", width="small"),
                    "Target Evidence": st.column_config.TextColumn("Target Evidence", width="small"),
                    "Validity Modifier": st.column_config.TextColumn("Validity Modifier", width="small"),
                    "Decay Factor": st.column_config.TextColumn("Decay Factor", width="small"),
                    "Position": st.column_config.NumberColumn("Position", width="small")
                }
            )
            
            # Add a divider between skill tables
            st.divider()
            
    except Exception as e:
        st.error(f"Error displaying activity history for skill {skill_id}: {str(e)}")

def display_activity_history_table(learner_id: str, skill_id: str, backend: Dict):
    """Legacy function - now calls the new single skill table function"""
    display_single_skill_table(learner_id, skill_id, backend)

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
                st.subheader("📈 Activity History st.subheader("📈 Activity History st.subheader("📊 Your Activity History         st.subheader("📈 Activity History & Scoring Results") Scores") Scoring Results") Scoring Results")
        
        # Get current learner and activity info
        if hasattr(st.session_state, "current_learner") and st.session_state.current_learner:
            learner_id = st.session_state.current_learner.learner_id
        else:
            learner_id = "unknown"
        
        # Display activity history tables for all skills that have history
                display_activity_history_tables(learner_id, backend)
    
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
        # Display intelligent feedback results (combined diagnostic + feedback)
        st.subheader("🧠💬 Intelligent Feedback Results")
        
        # Handle the intelligent_feedback structure
        intelligent_data = result.get('intelligent_feedback', result)
        
        # Display diagnostic analysis section
        if 'diagnostic_analysis' in intelligent_data:
            diagnostic = intelligent_data['diagnostic_analysis']
            
            # Show subskill performance if available
            if 'subskill_performance' in diagnostic:
                st.subheader("📊 Subskill Performance Analysis")
                subskills = diagnostic['subskill_performance']
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
            
            # Show strength and improvement areas
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Strength Areas")
                strengths = diagnostic.get('strength_areas', [])
                if isinstance(strengths, list) and strengths:
                    for strength in strengths:
                        st.write(f"• {strength}")
                else:
                    st.write("No strengths identified")
            
            with col2:
                st.subheader("📈 Improvement Areas")
                improvement_areas = diagnostic.get('improvement_areas', [])
                if isinstance(improvement_areas, list) and improvement_areas:
                    for area in improvement_areas:
                        st.write(f"• {area}")
                else:
                    st.write("No improvement areas identified")
        
        # Display student feedback section
        if 'student_feedback' in intelligent_data:
            feedback = intelligent_data['student_feedback']
            
            # Show performance summary
            if 'performance_summary' in feedback:
                performance = feedback['performance_summary']
                if isinstance(performance, dict):
                    if 'overall_assessment' in performance:
                        st.subheader("📋 Overall Assessment")
                        st.info(performance['overall_assessment'])
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'key_strengths' in performance:
                            st.subheader("🏆 Key Strengths")
                            strengths = performance['key_strengths']
                            if isinstance(strengths, list) and strengths:
                                for strength in strengths:
                                    st.write(f"• {strength}")
                            else:
                                st.write("Strengths being analyzed...")
                    
                    with col2:
                        if 'primary_opportunities' in performance:
                            st.subheader("🚀 Growth Opportunities")
                            opportunities = performance['primary_opportunities']
                            if isinstance(opportunities, list) and opportunities:
                                for opportunity in opportunities:
                                    st.write(f"• {opportunity}")
                            else:
                                st.write("Opportunities being analyzed...")
                    
                    if 'achievement_highlights' in performance:
                        st.subheader("🌟 Achievement Highlights")
                        highlights = performance['achievement_highlights']
                        if isinstance(highlights, list) and highlights:
                            for highlight in highlights:
                                st.write(f"• {highlight}")
            
            # Show actionable guidance
            if 'actionable_guidance' in feedback:
                guidance = feedback['actionable_guidance']
                if isinstance(guidance, dict):
                    st.subheader("🎯 Actionable Guidance")
                    
                    if 'immediate_next_steps' in guidance:
                        st.markdown("#### 📝 Immediate Next Steps")
                        steps = guidance['immediate_next_steps']
                        if isinstance(steps, list) and steps:
                            for i, step in enumerate(steps, 1):
                                if isinstance(step, dict):
                                    action = step.get('action', '')
                                    rationale = step.get('rationale', '')
                                    st.write(f"**{i}. {action}**")
                                    if rationale:
                                        st.write(f"   *{rationale}*")
                                else:
                                    st.write(f"**{i}. {step}**")
                    
                    if 'recommendations' in guidance:
                        st.markdown("#### 💡 Recommendations")
                        recommendations = guidance['recommendations']
                        if isinstance(recommendations, list) and recommendations:
                            for i, rec in enumerate(recommendations, 1):
                                st.write(f"**{i}. {rec}**")
    
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
        
        # Show actionable guidance if available
        if 'actionable_guidance' in feedback_data:
            guidance = feedback_data['actionable_guidance']
            if isinstance(guidance, dict):
                st.subheader("Actionable Guidance")
                
                if 'immediate_next_steps' in guidance:
                    st.write("**Immediate Next Steps:**")
                    steps = guidance['immediate_next_steps']
                    if isinstance(steps, list):
                        for i, step in enumerate(steps, 1):
                            if isinstance(step, dict):
                                action = step.get('action', '')
                                rationale = step.get('rationale', '')
                                st.write(f"{i}. **{action}**")
                                if rationale:
                                    st.write(f"   *{rationale}*")
                            else:
                                st.write(f"{i}. {step}")
                
                if 'recommendations' in guidance:
                    st.write("**Recommendations:**")
                    recommendations = guidance['recommendations']
                    if isinstance(recommendations, list):
                        for i, rec in enumerate(recommendations, 1):
                            st.write(f"{i}. {rec}")
        
        # Handle legacy format or fallback
        if not any(key in result for key in ['feedback', 'feedback_generation']):
            # Display as formatted text if it's a simple structure
            if isinstance(result, dict):
                for key, value in result.items():
                    if key not in ['phase', 'success', 'error', 'execution_time_ms', 'tokens_used', 'cost_estimate']:
                        st.subheader(key.replace('_', ' ').title())
                        if isinstance(value, list):
                            for item in value:
                                st.write(f"• {item}")
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                st.write(f"**{subkey.replace('_', ' ').title()}:** {subvalue}")
                        else:
                            st.write(value)
    
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

# Add custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
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
    .dataframe {
        border: 1px solid #ddd;
        border-radius: 6px;
        overflow: hidden;
    }
    .stDataFrame {
        border: 1px solid #ddd;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'debug_mode' not in st.session_state:
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
            'estimated_time_minutes': a.get('estimated_time_minutes', 30),
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
                if not isinstance(activity, dict):
                    st.error(f"Invalid activity format: {type(activity)}")
                    return
                
                st.markdown(f"### {activity.get('title', 'Untitled Activity')}")
                activity_type = activity.get('activity_type', 'Unknown')
                st.markdown(f":{get_activity_type_badge_color(activity_type)}[{activity_type}] **{activity.get('l_d_complexity', 'L1-D1')}**")
                
                target_skill = activity.get('target_skill', {})
                if isinstance(target_skill, dict):
                    skill_name = target_skill.get('skill_name', 'Unknown')
                else:
                    skill_name = str(target_skill)
                st.markdown(f"**Target Skill:** {skill_name}")
                
                st.markdown(f"**Time:** {activity.get('estimated_time_minutes', 30)} min")
                description = activity.get('description', 'No description available.')
                if len(description) > 100:
                    description = description[:100] + "..."
                st.markdown(description)
                
                if st.button("🎯 Start Activity", key=f"start_{activity.get('activity_id')}"):
                    # Store the formatted activity (which has extracted components and instructions)
                    st.session_state.current_activity = activity
                    # Clear any previous evaluation results when starting a new activity
                    if "evaluation_results" in st.session_state:
                        st.session_state.evaluation_results = {}
                    if "submitted_activity" in st.session_state:
                        st.session_state.submitted_activity = None
                    st.rerun()
            except Exception as e:
                st.error(f"Error creating activity card: {e}")
                st.error(f"Activity: {activity}")

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

# Learner Selection in Sidebar
with st.sidebar:
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
            
            # Find current index
            current_index = default_index
            if st.session_state.current_learner:
                for i, l in enumerate(learners):
                    if getattr(st.session_state.current_learner, 'learner_id', None) == getattr(l, 'learner_id', None):
                        current_index = i
                        break

            selected_learner = st.selectbox(
                "Select Active Learner:",
                options=learner_options,
                index=current_index,
                help="Choose a learner to work with"
            )

            selected_index = learner_options.index(selected_learner)
            if 0 <= selected_index < len(learners):
                st.session_state.current_learner = learners[selected_index]
                backend['logger'].log_system_event('streamlit_ui', 'learner_selected', f"Selected learner: {learners[selected_index].name}")
                st.success(f"✅ Active: {learners[selected_index].name}")
            else:
                st.session_state.current_learner = None
        else:
            st.warning("No learners found in database")
            st.session_state.current_learner = None
    except Exception as e:
        st.error(f"Error loading learners: {e}")
        st.error(f"Traceback: {traceback.format_exc()}")
        st.session_state.current_learner = None
    
    # Debug mode toggle
    st.header("🔧 Debug Options")
    debug_mode = st.checkbox("Debug Mode", value=st.session_state.get('debug_mode', False))
    st.session_state.debug_mode = debug_mode
    
    # Learner Management Section
    st.header("👤 Learner Management")
    
    if st.session_state.current_learner:
        current_learner = st.session_state.current_learner
        st.info(f"Managing: {current_learner.name}")
        
        # Learner History Management
                st.subheader("📊 Your Activity History         st.subheader("📊 Activity History") Scores")
        
        # Show current activity count and data summary
        try:
            # Get detailed data summary with fallback
            try:
                data_summary = backend['learner_manager'].get_learner_data_summary(current_learner.learner_id)
            except AttributeError:
                # Fallback if method doesn't exist yet
                with backend['learner_manager']._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) as count FROM activity_history WHERE learner_id = ?', (current_learner.learner_id,))
                    activity_history_count = cursor.fetchone()['count']
                    cursor.execute('SELECT COUNT(*) as count FROM skill_progress WHERE learner_id = ?', (current_learner.learner_id,))
                    skill_progress_count = cursor.fetchone()['count']
                    cursor.execute('SELECT COUNT(*) as count FROM activity_records WHERE learner_id = ?', (current_learner.learner_id,))
                    activity_records_count = cursor.fetchone()['count']
                
                data_summary = {
                    'activity_history': activity_history_count,
                    'skill_progress': skill_progress_count,
                    'activity_records': activity_records_count,
                    'total': activity_history_count + skill_progress_count + activity_records_count
                }
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Activity History", data_summary['activity_history'])
            with col2:
                st.metric("Skill Progress", data_summary['skill_progress'])
            with col3:
                st.metric("Activity Records", data_summary['activity_records'])
            with col4:
                st.metric("Total Records", data_summary['total'])
            
            if data_summary['total'] > 0:
                # Reset history button
                if st.button("🗑️ Reset All Learner History", type="secondary"):
                    if st.checkbox("I understand this will permanently delete ALL learner data including activity history, skill progress, and activity records"):
                        try:
                            # Use the comprehensive reset method
                            success = backend['learner_manager'].reset_learner_history(current_learner.learner_id)
                            
                            if success:
                                st.success(f"✅ All learner history reset for {current_learner.name}")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to reset learner history")
                        except Exception as e:
                            st.error(f"❌ Failed to reset history: {str(e)}")
            else:
                st.write("No activity history to reset")
                
        except Exception as e:
            st.error(f"Error checking activity history: {str(e)}")
    else:
        st.warning("No learner selected")
    
    # Add backend health check
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
                        st.markdown(f"**{component}:**")
                        for key, value in status.items():
                            st.text(f"  {key}: {value}")
                    else:
                        st.text(f"{component}: {status}")
                    
            except Exception as e:
                st.error(f"Health check failed: {str(e)}")
                st.error(f"Traceback: {traceback.format_exc()}")

# Main 50/50 Layout
left_col, right_col = st.columns(2)

# LEFT COLUMN - LEARNER VIEW
with left_col:
    st.header("🎯 Learner Activity View")
    
    if not st.session_state.current_learner:
        st.warning("Please select a learner from the dropdown above to start.")
        st.info("💡 **How to get started:** Select a learner from the dropdown, then choose an activity to begin.")
    else:
        learner = st.session_state.current_learner
        st.success(f"👤 **Active Learner:** {getattr(learner, 'name', 'Unknown')}")
                            # Removed learner level display as requested
        
        # Show submitted activity if available
        if hasattr(st.session_state, 'submitted_activity') and st.session_state.submitted_activity:
            st.subheader("📝 Submitted Activity")
            submitted = st.session_state.submitted_activity
            activity_id = submitted.get('activity_id', 'Unknown')
            
            # Check if evaluation is complete
            if activity_id in st.session_state.evaluation_results:
                result = st.session_state.evaluation_results[activity_id]
                if result.get('overall_success'):
                    # Show completed evaluation
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        # Calculate overall score from scoring phase
                        overall_score = 0
                        if 'pipeline_phases' in result:
                            for phase in result['pipeline_phases']:
                                if phase.get('phase') == 'scoring':
                                    scoring_result = phase.get('result', {})
                                    if 'final_score' in scoring_result:
                                        overall_score = scoring_result['final_score']
                                    elif 'score' in scoring_result:
                                        overall_score = scoring_result['score']
                                    break
                        
                        st.metric("Overall Score", f"{overall_score:.0f}%")
                    
                    with col2:
                        st.success("✅ Evaluation Complete")
                    
                    # Show prominent score display
                    st.markdown("---")
                    st.markdown(f"## 🎯 **Your Activity Score: {overall_score:.1f}%**")
                    
                    # Add score interpretation
                    if overall_score >= 90:
                        st.success("🌟 **Excellent Work!** You've demonstrated mastery of this activity.")
                    elif overall_score >= 80:
                        st.info("👍 **Great Job!** You've shown strong understanding of the concepts.")
                    elif overall_score >= 70:
                        st.warning("📚 **Good Progress!** You're on the right track with some areas for improvement.")
                    elif overall_score >= 60:
                        st.warning("📖 **Keep Learning!** Review the feedback below to strengthen your understanding.")
                    else:
                        st.error("📝 **More Practice Needed** - Check the feedback for guidance on improvement.")
                    
                    # Show scoring details
                    if 'pipeline_phases' in result:
                        for phase in result['pipeline_phases']:
                            if phase.get('phase') == 'scoring':
                                scoring_result = phase.get('result', {})
                                if scoring_result:
                                    st.markdown("### 📊 Scoring Details")
                                    
                                    # Display scoring algorithm outputs
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if 'score' in scoring_result:
                                            st.metric("Raw Score", f"{scoring_result['score']:.2f}")
                                        if 'target_evidence_volume' in scoring_result:
                                            st.metric("Target Evidence Volume", f"{scoring_result['target_evidence_volume']:.2f}")
                                    with col2:
                                        if 'validity_modifier' in scoring_result:
                                            st.metric("Validity Modifier", f"{scoring_result['validity_modifier']:.2f}")
                                        if 'adjusted_evidence_volume' in scoring_result:
                                            st.metric("Adjusted Evidence Volume", f"{scoring_result['adjusted_evidence_volume']:.2f}")
                                    
                                    # Show final score prominently
                                    if 'final_score' in scoring_result:
                                        st.markdown("---")
                                        st.markdown(f"### 🎯 **Final Activity Score: {scoring_result['final_score']:.1f}%**")
                                    
                                    # Show scoring rationale if available
                                    if 'scoring_rationale' in scoring_result:
                                        with st.expander("📋 Scoring Rationale"):
                                            st.info(scoring_result['scoring_rationale'])
                    
                    # Show student-facing feedback
                    if 'pipeline_phases' in result:
                        st.markdown("### 📋 Your Evaluation Results")
                        st.info("Evaluation completed successfully!")
                        
                        # Find and display feedback
                        for phase in result['pipeline_phases']:
                            if phase.get('phase') == 'feedback_generation':
                                feedback_result = phase.get('result', {})
                                if feedback_result:
                                    st.markdown("#### 💬 Your Feedback")
                                    
                                    # Display feedback in a user-friendly format
                                    feedback_data = feedback_result.get('feedback_generation', feedback_result)
                                    
                                    # Show performance summary
                                    if 'performance_summary' in feedback_data:
                                        performance = feedback_data['performance_summary']
                                        if isinstance(performance, dict):
                                            if 'overall_assessment' in performance:
                                                st.write("**Overall Assessment:**")
                                                st.info(performance['overall_assessment'])
                                            
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                if 'key_strengths' in performance:
                                                    st.write("**🎯 Your Strengths:**")
                                                    strengths = performance['key_strengths']
                                                    if isinstance(strengths, list) and strengths:
                                                        for strength in strengths:
                                                            st.write(f"• {strength}")
                                                    else:
                                                        st.write("Strengths being analyzed...")
                                            
                                            with col2:
                                                if 'primary_opportunities' in performance:
                                                    st.write("**📈 Growth Opportunities:**")
                                                    opportunities = performance['primary_opportunities']
                                                    if isinstance(opportunities, list) and opportunities:
                                                        for opportunity in opportunities:
                                                            st.write(f"• {opportunity}")
                                                    else:
                                                        st.write("Opportunities being analyzed...")
                                    
                                    # Show actionable guidance
                                    if 'actionable_guidance' in feedback_data:
                                        guidance = feedback_data['actionable_guidance']
                                        if isinstance(guidance, dict):
                                            st.markdown("#### 🚀 Next Steps")
                                            
                                            if 'immediate_next_steps' in guidance:
                                                steps = guidance['immediate_next_steps']
                                                if isinstance(steps, list) and steps:
                                                    for i, step in enumerate(steps, 1):
                                                        if isinstance(step, dict):
                                                            action = step.get('action', '')
                                                            rationale = step.get('rationale', '')
                                                            st.write(f"**{i}. {action}**")
                                                            if rationale:
                                                                st.write(f"   *{rationale}*")
                                                        else:
                                                            st.write(f"**{i}. {step}**")
                                            
                                            if 'recommendations' in guidance:
                                                st.write("**💡 Recommendations:**")
                                                recommendations = guidance['recommendations']
                                                if isinstance(recommendations, list) and recommendations:
                                                    for rec in recommendations:
                                                        st.write(f"• {rec}")
                                    
                                    break
                else:
                    st.error("❌ Evaluation Failed")
                    if 'error_summary' in result:
                        st.error(f"Error: {result['error_summary']}")
            else:
                # Show pending status
                st.info("⏳ **Evaluation Pending** - Your activity has been submitted and is being evaluated.")
                st.info("Check the Evaluation Queue on the right to see the progress.")
            
            # Back button to return to activities
            if st.button("← Back to Activities", key="back_to_activities"):
                st.session_state.submitted_activity = None
                st.session_state.current_activity = None
                # Clear evaluation results when navigating away
                if "evaluation_results" in st.session_state:
                    st.session_state.evaluation_results = {}
                # Reset all submission states
                for key in list(st.session_state.keys()):
                    if key.startswith('submit_'):
                        st.session_state[key] = False
                st.rerun()
            
            # Display scoring table for current learner
        if hasattr(st.session_state, "current_learner") and st.session_state.current_learner:
            learner_id = st.session_state.current_learner.learner_id
            st.subheader('📊 Your Activity History & Scores')
            display_activity_history_tables(learner_id, backend)
            st.divider()
        
        st.divider()
        
        # Activity Selection (only show if no submitted activity)
        if not hasattr(st.session_state, 'submitted_activity') or not st.session_state.submitted_activity:
            if not st.session_state.current_activity:
                st.subheader("📚 Available Activities")
                try:
                    activities_dict = backend['activity_manager'].load_activities()
                    if activities_dict:
                        st.info(f"Loaded {len(activities_dict)} activities from activity manager")
                        activities = []
                        for activity_id, activity in activities_dict.items():
                            try:
                                formatted_activity = format_activity_for_ui(activity)
                                activities.append(formatted_activity)
                            except Exception as e:
                                st.error(f"Error formatting activity {activity_id}: {e}")
                                st.error(f"Activity type: {type(activity)}")
                                st.error(f"Activity content: {activity}")
                                continue
                        
                        if activities:
                            cols_per_row = 2
                            for i in range(0, len(activities), cols_per_row):
                                cols = st.columns(cols_per_row)
                                for j, activity in enumerate(activities[i:i + cols_per_row]):
                                    create_activity_card(activity, cols[j])
                        else:
                            st.warning("No activities found matching the selected filters.")
                    else:
                        st.warning("No activities found in the activities directory.")
                except Exception as e:
                    st.error(f"Error loading activities: {e}")
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
                    st.markdown(f"**Type:** :{get_activity_type_badge_color(activity.get('activity_type', 'Unknown'))}[{activity.get('activity_type', 'Unknown')}]")
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
                            "Explain your approach and reasoning:",
                            height=150,
                            key=f"explanation_{response_key}",
                            help="Describe your solution approach"
                        )
                        combined_response = f"CODE:\n{code_response}\n\nEXPLANATION:\n{explanation_response}"
                    else:
                        combined_response = st.text_area(
                            "Enter your response:",
                            height=300,
                            key=response_key,
                            help="Write your detailed response here"
                        )
                    if combined_response:
                        word_count = len(combined_response.split())
                        char_count = len(combined_response)
                        st.markdown(f"**Word count:** {word_count} | **Character count:** {char_count}")
                
                elif activity_type == 'RP':
                    st.subheader("💬 Role Play Conversation")
                    conv_key = f"conversation_{activity_id}"
                    if conv_key not in st.session_state:
                        st.session_state[conv_key] = []
                        character_name = activity.get('character_name', 'AI Character')
                        initial_message = activity.get('initial_message', 'Hello! How can I help you today?')
                        st.session_state[conv_key].append({
                            'speaker': 'ai_character',
                            'message': initial_message,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    for message in st.session_state[conv_key]:
                        if message['speaker'] == 'ai_character':
                            st.chat_message("assistant").write(message['message'])
                        else:
                            st.chat_message("user").write(message['message'])
                    
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
                                help=f"Select one option for question {i + 1}"
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
                        selected_option = st.radio("Select your decision:", options, key=f"br_decision_{activity_id}")
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
                
                st.divider()
                
                # Submit button with stable key pattern
                submit_key = f"submit_{activity_id}"
                if st.session_state.get(submit_key, False):
                    st.success("✅ Activity submitted!")
                    st.info("Check the Evaluation Queue on the right.")
                else:
                    submitted = st.button("📤 Submit Activity", type="primary", key=f"submit_btn_{activity_id}")
                    if submitted:
                        if not combined_response or combined_response.strip() == "":
                            st.error("Please provide a response before submitting.")
                        else:
                            try:
                                learner_id = getattr(learner, 'learner_id', 'unknown')
                                transcript = {
                                    'learner_id': learner_id,
                                    'activity_id': activity_id,
                                    'activity_transcript': {
                                        'activity_generation_output': activity,
                                        'student_engagement': {
                                            'start_timestamp': datetime.now().isoformat(),
                                            'submit_timestamp': datetime.now().isoformat(),
                                            'completion_status': 'completed',
                                            'component_responses': [
                                                {
                                                    'component_id': 'main_response',
                                                    'response_content': combined_response,
                                                    'response_timestamp': datetime.now().isoformat(),
                                                    'component_completion_status': 'completed'
                                                }
                                            ],
                                            'timing_data': {
                                                'total_duration_minutes': 30
                                            },
                                            'assistance_log': []
                                        }
                                    },
                                    'scored': False
                                }
                                st.session_state[submit_key] = True
                                st.session_state.evaluation_queue.append(transcript)
                                st.session_state.current_activity = None
                                st.session_state.submitted_activity = transcript
                                try:
                                    st.experimental_rerun()
                                except Exception:
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Submission failed: {str(e)}")
                
                # Show evaluation results if available (for debugging - hidden from student view)
                if activity_id in st.session_state.evaluation_results and st.session_state.get('debug_mode', False):
                    st.divider()
                    st.subheader("🔧 Debug: Evaluation Results")
                    result = st.session_state.evaluation_results[activity_id]
                    
                    if result.get('overall_success'):
                        st.success("🎉 Evaluation completed successfully!")
                        
                        # Display scores
                        if 'final_skill_scores' in result:
                            st.markdown("**Skill Scores:**")
                            for skill_id, skill_score in result['final_skill_scores'].items():
                                score_value = getattr(skill_score, 'cumulative_score', 0)
                                status = getattr(skill_score, 'overall_status', 'unknown')
                                st.metric(f"Skill {skill_id}", f"{score_value:.2f}", status)
                        
                        # Display comprehensive results
                        if 'pipeline_phases' in result:
                            st.markdown("**📋 Detailed Results:**")
                            
                            # Find and display each phase result
                            for phase in result['pipeline_phases']:
                                phase_key = phase.get('phase', 'Unknown')
                                phase_name = phase_key.title().replace('_', ' ')
                                phase_result = phase.get('result', {})
                                
                                if phase_result and isinstance(phase_result, dict):
                                    with st.expander(f"📊 {phase_name}", expanded=True):
                                        display_phase_results(phase_key, phase_result, backend)
                    else:
                        st.error("❌ Evaluation failed")
                        if 'error_summary' in result:
                            st.error(f"Error: {result['error_summary']}")
                
                # Student view - show only score and feedback
                elif activity_id in st.session_state.evaluation_results:
                    result = st.session_state.evaluation_results[activity_id]
                    if result.get('overall_success'):
                        st.success("🎉 Evaluation completed successfully!")
                        
                        # Show only activity score and feedback
                        if 'pipeline_phases' in result:
                            # Find scoring phase for score
                            for phase in result['pipeline_phases']:
                                if phase.get('phase') == 'scoring':
                                    scoring_result = phase.get('result', {})
                                    if 'final_score' in scoring_result:
                                        st.metric("Overall Score", f"{scoring_result['final_score']:.1%}")
                                    elif 'activity_score' in scoring_result:
                                        st.metric("Activity Score", f"{scoring_result['activity_score']:.1%}")
                                    break
                            
                            # Find feedback phase for student feedback
                            for phase in result['pipeline_phases']:
                                if phase.get('phase') == 'feedback_generation':
                                    feedback_result = phase.get('result', {})
                                    if feedback_result:
                                        st.markdown("### 📋 Your Feedback")
                                        
                                        # Show overall summary
                                        if 'feedback' in feedback_result:
                                            feedback = feedback_result['feedback']
                                            if 'overall_summary' in feedback:
                                                st.info(feedback['overall_summary'])
                                            
                                            # Show motivational message
                                            if 'motivational_message' in feedback:
                                                st.markdown("**💪 Encouragement:**")
                                                st.write(feedback['motivational_message'])
                                            
                                            # Show actionable recommendations
                                            if 'actionable_recommendations' in feedback:
                                                st.markdown("**📝 Actionable Steps:**")
                                                recommendations = feedback['actionable_recommendations']
                                                if isinstance(recommendations, list):
                                                    for i, rec in enumerate(recommendations, 1):
                                                        st.markdown(f"{i}. {rec}")
                                            
                                            # Show next steps
                                            if 'next_steps' in feedback:
                                                st.markdown("**➡️ Next Steps:**")
                                                st.write(feedback['next_steps'])
                                    break
                    else:
                        st.error("❌ Evaluation failed")
                        if 'error_summary' in result:
                            st.error(f"Error: {result['error_summary']}")

# RIGHT COLUMN - EVALUATION MANAGEMENT
with right_col:
    st.header("⚙️ Evaluation Management")
    
    # Evaluation Queue and Monitor combined
    if not st.session_state.evaluation_queue and not st.session_state.pipeline_status:
        st.info("No activities in the evaluation queue.")
        st.info("💡 **How to evaluate:** Submit an activity from the learner view on the left, then it will appear here for evaluation.")
    
    else:
        # Show evaluation queue
        if st.session_state.evaluation_queue:
            st.subheader(f"📋 Evaluation Queue ({len(st.session_state.evaluation_queue)} items)")
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
        
        # Show pipeline monitor
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
                    with st.spinner("Running evaluation pipeline..."):
                        try:
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
                        
                        # Update pipeline status with results
                        phases = []
                        if hasattr(evaluation_result, 'pipeline_phases'):
                            if st.session_state.get('debug_mode', False):
                                st.write("Debug - Raw pipeline phases:", evaluation_result.pipeline_phases)
                            for phase in evaluation_result.pipeline_phases:
                                phase_dict = {
                                    'phase': getattr(phase, 'phase', 'unknown'),
                                    'status': 'completed' if getattr(phase, 'success', False) else 'failed',
                                    'execution_time': (getattr(phase, 'execution_time_ms', 0) / 1000) if hasattr(phase, 'execution_time_ms') else 0,
                                    'tokens_used': getattr(phase, 'tokens_used', 0) or 0,
                                    'cost_estimate': getattr(phase, 'cost_estimate', 0) or 0.0,
                                    'result': getattr(phase, 'result', None),
                                    'error': getattr(phase, 'error', None) if not getattr(phase, 'success', False) else None
                                }
                                phases.append(phase_dict)
                                if st.session_state.get('debug_mode', False):
                                    st.write(f"Debug - Processed phase {phase_dict['phase']}:", phase_dict)
                        
                        # Results will be displayed in the pipeline progress section below
                        
                        # Determine overall success
                        overall_success = getattr(evaluation_result, 'overall_success', False)
                        error_summary = getattr(evaluation_result, 'error_summary', 'Unknown error')
                        
                        st.session_state.pipeline_status.update({
                            'status': 'completed' if overall_success else 'failed',
                            'phases': phases,
                            'evaluation_result': evaluation_result
                        })
                        
                        # Store results for display in learner view
                        if overall_success:
                            st.session_state.evaluation_results[activity_id] = {
                                'overall_success': True,
                                'final_skill_scores': getattr(evaluation_result, 'final_skill_scores', {}),
                                'pipeline_phases': phases
                            }
                            st.success("✅ Evaluation completed successfully!")
                        else:
                            st.session_state.evaluation_results[activity_id] = {
                                'overall_success': False,
                                'error_summary': error_summary
                            }
                            st.error(f"❌ Evaluation failed: {error_summary}")
                        
                        
                except Exception as e:
                    st.error(f"❌ Evaluation failed: {e}")
                    st.session_state.pipeline_status.update({
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Display pipeline progress and results as they complete
            st.subheader("Pipeline Progress")
            
            # Define all possible phases in order
            all_phases = [
                ('combined_evaluation', 'Summative Evaluation'),
                ('scoring', 'Scoring'),
                ('intelligent_feedback', 'Intelligent Feedback'),
                ('trend_analysis', 'Trend Analysis')
            ]
            
            phases = status.get('phases', [])
            current_phase = status.get('current_phase', 'starting')
            completed_phases = [p.get('phase') for p in phases if p.get('status') == 'completed']
            failed_phases = [p.get('phase') for p in phases if p.get('status') == 'failed']
            
            # Debug: Show what's actually in the status
            if st.session_state.get('debug_mode', False):
                st.write("Debug - Status content:", status)
                st.write("Debug - Phases:", phases)
                st.write("Debug - Completed phases:", completed_phases)
                st.write("Debug - Failed phases:", failed_phases)
            
            progress = 0
            progress_bar = st.progress(0, text="Initializing...")
            
            for idx, (phase_id, phase_name) in enumerate(all_phases):
                if phase_id in completed_phases:
                    progress += 1
                    phase_data = next((p for p in phases if p.get('phase') == phase_id), {})
                    
                    # Special handling for trend analysis when disabled
                    if phase_id == 'trend_analysis':
                        result = phase_data.get('result', {})
                        # Check if this is the disabled case (has specific structure)
                        if (isinstance(result, dict) and 
                            'trend_analysis' in result and 
                            isinstance(result['trend_analysis'], dict) and
                            'status' in result['trend_analysis'] and
                            result['trend_analysis']['status'] == 'disabled'):
                            st.success(f"✅ {phase_name} - Feature Disabled ({phase_data.get('execution_time', 0):.1f}s) | Tokens: 0 | Cost: $0.0000")
                            st.info("💡 Trend analysis has been disabled to reduce costs and processing time.")
                        else:
                            st.success(f"✅ {phase_name} - Complete ({phase_data.get('execution_time', 0):.1f}s) | Tokens: {phase_data.get('tokens_used', 0)} | Cost: ${phase_data.get('cost_estimate', 0):.4f}")
                            
                            # Display results immediately as they complete
                            if result and isinstance(result, dict):
                                with st.expander(f"📊 {phase_name} Results", expanded=True):
                                    display_phase_results(phase_id, result, backend)
                    else:
                        st.success(f"✅ {phase_name} - Complete ({phase_data.get('execution_time', 0):.1f}s) | Tokens: {phase_data.get('tokens_used', 0)} | Cost: ${phase_data.get('cost_estimate', 0):.4f}")
                        
                        # Display results immediately as they complete
                        result = phase_data.get('result')
                        if result and isinstance(result, dict):
                            with st.expander(f"📊 {phase_name} Results", expanded=True):
                                display_phase_results(phase_id, result, backend)
                        
                elif phase_id in failed_phases:
                    phase_data = next((p for p in phases if p.get('phase') == phase_id), {})
                    
                    # Special handling for trend analysis when disabled
                    if phase_id == 'trend_analysis':
                        result = phase_data.get('result', {})
                        # Check if this is the disabled case (has specific structure)
                        if (isinstance(result, dict) and 
                            'trend_analysis' in result and 
                            isinstance(result['trend_analysis'], dict) and
                            'status' in result['trend_analysis'] and
                            result['trend_analysis']['status'] == 'disabled'):
                            st.success(f"✅ {phase_name} - Feature Disabled")
                            st.info("💡 Trend analysis has been disabled to reduce costs and processing time.")
                        else:
                            st.error(f"❌ {phase_name} - Failed")
                            if phase_data.get('error'):
                                st.error(f"Error: {phase_data.get('error')}")
                    else:
                        st.error(f"❌ {phase_name} - Failed")
                        if phase_data.get('error'):
                            st.error(f"Error: {phase_data.get('error')}")
                elif phase_id == current_phase:
                    progress_bar.progress(progress / len(all_phases), text=f"🔄 {phase_name} - In Progress...")
                    st.info(f"🔄 {phase_name} - In Progress...")
                else:
                    st.info(f"⏳ {phase_name} - Waiting")
                    
            progress_bar.progress(progress / len(all_phases), text=f"{progress} of {len(all_phases)} phases complete")
            
            if not phases and not current_phase:
                st.info("No pipeline phases started yet.")
            
            # Final results and actions
            if status.get('status') == 'completed':
                evaluation_result = status.get('evaluation_result')
                if evaluation_result:
                    st.success("🎉 Evaluation completed successfully!")
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Overall Success", "✅" if getattr(evaluation_result, 'overall_success', False) else "❌")
                    with col2:
                        total_time = sum(p.get('execution_time', 0) for p in status.get('phases', []))
                        st.metric("Total Time", f"{total_time:.1f}s")
                    with col3:
                        total_tokens = sum(p.get('tokens_used', 0) for p in status.get('phases', []))
                        st.metric("Total Tokens", f"{total_tokens:,}")
                    with col4:
                        total_cost = sum(p.get('cost_estimate', 0) for p in status.get('phases', []))
                        st.metric("Total Cost", f"${total_cost:.4f}")
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Clear Pipeline"):
                            st.session_state.pipeline_status = {}
                            st.rerun()
                    with col2:
                        if st.button("📊 View Raw JSON"):
                            if evaluation_result:
                                st.subheader("Complete Evaluation Results (JSON)")
                                st.json(evaluation_result.__dict__ if hasattr(evaluation_result, '__dict__') else evaluation_result)
            
            elif status.get('status') == 'failed':
                st.error("❌ Evaluation failed!")
                if st.button("🗑️ Clear Pipeline"):
                    st.session_state.pipeline_status = {}
                    st.rerun()

st.divider()
st.markdown("**Evaluator v16** - Educational Assessment Pipeline | Version 1.0.0")