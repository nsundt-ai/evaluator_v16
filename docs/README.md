# Evaluator v16 - Scoring Algorithm Documentation

## Overview

This directory contains reference documentation for the Evaluator v16 scoring algorithm, which uses a **position-based decay Bayesian model** to calculate cumulative skill scores from multiple activity evaluations.

## Core Algorithm

### Mathematical Model

The scoring algorithm combines three key components:

1. **Evidence Adjustment**: `adjusted_evidence = target_evidence × validity_modifier`
2. **Position-Based Decay**: `decay_factor = 0.9^position_from_most_recent` 
3. **Weighted Cumulative Score**: `cumulative_score = Σ(score × weight) / Σ(weight)`

### Key Principles

- **No Prior Mean**: The algorithm starts from the first activity (no assumed starting score)
- **Recency Weighting**: More recent activities have higher influence on the final score
- **Evidence-Based**: Each activity contributes evidence volume based on its design and validity
- **Dual-Gate System**: Separate thresholds for performance (Gate 1) and evidence volume (Gate 2)

## Algorithm Flow

### Step 1: Evidence Adjustment
```
For each activity:
  adjusted_evidence = target_evidence × validity_modifier
```
- `target_evidence`: Set during activity design (e.g., 4.0, 5.5, 3.0)
- `validity_modifier`: Calculated during evaluation (0.0 to 1.0, based on assistance)

### Step 2: Position-Based Decay
```
For activity at position i from most recent:
  decay = 0.9^i
  weight = adjusted_evidence × decay
```
- Position 1 (most recent): `decay = 0.9^1 = 0.9`
- Position 2: `decay = 0.9^2 = 0.81` 
- Position 3: `decay = 0.9^3 = 0.729`
- And so on...

### Step 3: Cumulative Score Calculation
```
weighted_sum = Σ(score × weight)
cumulative_weight = Σ(weight)
cumulative_score = weighted_sum / cumulative_weight
```

### Step 4: Standard Error of Measurement
```
sem = √(cumulative_score × (1 - cumulative_score) / cumulative_weight)
```

## Dual-Gate Evaluation

### Gate 1: Performance Threshold
- **Passed**: `cumulative_score ≥ 0.75`
- **Approaching**: `cumulative_score ≥ 0.65`
- **Developing**: `cumulative_score ≥ 0.50`
- **Needs Improvement**: `cumulative_score < 0.50`

### Gate 2: Evidence Volume Threshold  
- **Passed**: `total_evidence ≥ 30.0`
- **Approaching**: `total_evidence ≥ 20.0`
- **Developing**: `total_evidence ≥ 10.0`
- **Needs Improvement**: `total_evidence < 10.0`

### Overall Status
- **Mastered**: Both gates passed
- **Progressing**: Both gates passed or approaching
- **Developing**: At least one gate developing
- **Not Started**: Both gates need improvement

## Example Calculation

Given 3 activities (most recent first):

| Activity | Score | Target Evidence | Validity Modifier | Position | Decay | Adjusted Evidence | Weight |
|----------|-------|-----------------|-------------------|----------|-------|-------------------|--------|
| 1 (most recent) | 0.82 | 4.0 | 1.0 | 1 | 0.9 | 4.0 | 3.6 |
| 2 | 0.71 | 3.5 | 0.9 | 2 | 0.81 | 3.15 | 2.55 |
| 3 (oldest) | 0.65 | 5.0 | 1.0 | 3 | 0.729 | 5.0 | 3.645 |

**Calculation:**
- `weighted_sum = (0.82 × 3.6) + (0.71 × 2.55) + (0.65 × 3.645) = 6.738`
- `cumulative_weight = 3.6 + 2.55 + 3.645 = 9.795`
- `cumulative_score = 6.738 / 9.795 = 0.688`
- `total_evidence = 4.0 + 3.15 + 5.0 = 12.15`

**Gate Status:**
- Gate 1: 0.688 → Approaching (≥ 0.65)
- Gate 2: 12.15 → Developing (≥ 10.0)
- Overall: Developing

## Configurable Parameters

The following parameters can be adjusted via the application UI:

- **Gate 1 Threshold** (0.5 - 0.95): Performance competency threshold
- **Gate 2 Threshold** (10.0 - 100.0): Evidence volume requirement  
- **Decay Factor** (0.7 - 1.0): Rate of decay for older activities
- **Max Activities** (5 - 50): Number of recent activities to include

## Files in This Directory

- **`scoring_algorithm_reference.py`**: Complete Python implementation of the algorithm
- **`examples/`**: Future directory for worked examples and test cases
- **`README.md`**: This documentation file

## Implementation Notes

- The actual scoring engine is implemented in `src/scoring_engine.py`
- Configuration parameters are stored in `config/scoring_config.json`
- Gate thresholds and decay factors are adjustable via the Streamlit UI
- All calculations maintain 4 decimal precision for accuracy
- The algorithm gracefully handles edge cases (no activities, zero evidence, etc.)

## Validation

To validate the scoring implementation:

1. Run the reference implementation with known inputs
2. Compare results with the main application scoring
3. Verify edge cases are handled correctly
4. Test parameter adjustments produce expected results

## References

- Position-based decay ensures recent performance has more influence
- Bayesian approach provides uncertainty measurement via SEM
- Evidence adjustment accounts for assistance and validity concerns
- Dual-gate system separates performance from evidence accumulation requirements