"""
Reference implementation of the Evaluator v16 scoring algorithm.
This shows the exact Bayesian model with position-based decay.
"""
import math
from typing import List, Dict, Tuple

def calculate_cumulative_score(activities: List[Dict], decay_factor: float = 0.9) -> Tuple[float, float]:
    """
    Calculate cumulative score and SEM using position-based decay.
    
    Args:
        activities: List of activity records with keys:
            - score: float (0-1) 
            - target_evidence: float (from activity design)
            - validity_modifier: float (0-1, from evaluation)
        decay_factor: float (default 0.9)
    
    Returns:
        (cumulative_score, sem): Tuple of final score and standard error
    """
    if not activities:
        return 0.0, 0.0
    
    # Initialize running sums
    cumulative_weight = 0.0  # Σ (vae_i × decay_i)  
    weighted_sum = 0.0       # Σ ((vae_i × decay_i) × score_i)
    
    # Process each activity (most recent = position 1)
    total_activities = len(activities)
    
    for i, activity in enumerate(activities):
        # Calculate position from most recent (1, 2, 3, ...)
        position_from_recent = i + 1
        
        # Evidence adjustment: target_evidence * validity_modifier
        adjusted_evidence = activity['target_evidence'] * activity['validity_modifier']
        
        # Position-based decay: 0.9 ^ position_from_most_recent  
        decay = decay_factor ** position_from_recent
        
        # Weight for this activity: adjusted_evidence * decay_factor
        weight = adjusted_evidence * decay
        
        # Update running sums
        cumulative_weight += weight
        weighted_sum += weight * activity['score']
    
    # Calculate cumulative score
    if cumulative_weight == 0:
        return 0.0, 0.0
        
    cumulative_score = weighted_sum / cumulative_weight
    
    # Calculate Standard Error of Measurement
    sem = math.sqrt(cumulative_score * (1 - cumulative_score) / cumulative_weight)
    
    return cumulative_score, sem

def evaluate_gates(cumulative_score: float, total_evidence: float, 
                  gate_1_threshold: float = 0.75, gate_2_threshold: float = 30.0) -> Dict:
    """
    Evaluate dual-gate status.
    
    Args:
        cumulative_score: Current performance score (0-1)
        total_evidence: Sum of all validity-adjusted evidence  
        gate_1_threshold: Performance threshold (default 0.75)
        gate_2_threshold: Evidence volume threshold (default 30.0)
    
    Returns:
        Dict with gate statuses and overall assessment
    """
    # Gate 1: Performance threshold
    if cumulative_score >= gate_1_threshold:
        gate_1_status = "passed"
    elif cumulative_score >= gate_1_threshold - 0.10:
        gate_1_status = "approaching"  
    elif cumulative_score >= gate_1_threshold - 0.25:
        gate_1_status = "developing"
    else:
        gate_1_status = "needs_improvement"
    
    # Gate 2: Evidence volume threshold  
    if total_evidence >= gate_2_threshold:
        gate_2_status = "passed"
    elif total_evidence >= gate_2_threshold * 0.67:  # ~20 if threshold is 30
        gate_2_status = "approaching"
    elif total_evidence >= gate_2_threshold * 0.33:  # ~10 if threshold is 30  
        gate_2_status = "developing"
    else:
        gate_2_status = "needs_improvement"
    
    # Overall status
    if gate_1_status == "passed" and gate_2_status == "passed":
        overall_status = "mastered"
    elif gate_1_status in ["passed", "approaching"] and gate_2_status in ["passed", "approaching"]:
        overall_status = "progressing"
    elif gate_1_status in ["developing"] or gate_2_status in ["developing"]:
        overall_status = "developing"  
    else:
        overall_status = "not_started"
    
    return {
        "gate_1_status": gate_1_status,
        "gate_2_status": gate_2_status, 
        "overall_status": overall_status,
        "cumulative_score": cumulative_score,
        "total_evidence": total_evidence
    }

# Example usage:
if __name__ == "__main__":
    # Example with 3 activities (most recent first)
    activities = [
        {
            "score": 0.82,
            "target_evidence": 4.0,  # From activity design
            "validity_modifier": 1.0  # From evaluation pipeline
        },
        {
            "score": 0.71, 
            "target_evidence": 3.5,
            "validity_modifier": 0.9  # Some assistance provided
        },
        {
            "score": 0.65,
            "target_evidence": 5.0,
            "validity_modifier": 1.0
        }
    ]
    
    score, sem = calculate_cumulative_score(activities)
    print(f"Cumulative Score: {score:.3f}")
    print(f"Standard Error: {sem:.3f}")
    
    # Calculate total evidence for gate 2
    total_evidence = sum(a['target_evidence'] * a['validity_modifier'] for a in activities)
    
    gates = evaluate_gates(score, total_evidence)
    print(f"Gate Assessment: {gates}")