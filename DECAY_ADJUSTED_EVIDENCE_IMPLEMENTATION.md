# Decay-Adjusted Evidence Implementation

## Overview
This document summarizes the implementation of the "Decay Adjusted Evidence" column in the activity history tables, which shows the effective evidence contribution of each activity after the decay factor is applied.

## Changes Made

### 1. Database Schema Updates (`src/learner_manager.py`)

**Added new column to activity_history table:**
- `decay_adjusted_evidence_volume REAL NOT NULL` - Stores the decay-adjusted evidence volume
- Added ALTER TABLE statement to handle existing databases

**Updated add_activity_history_record method:**
- Added `decay_adjusted_evidence_volume` parameter
- Updated SQL INSERT statement to include the new column

**Added chronological activity history method:**
- `get_activity_history_chronological()` - Gets activities in chronological order for cumulative calculations

### 2. Scoring Engine Updates (`src/scoring_engine.py`)

**Enhanced _add_activity_history_record method:**
- **FIXED**: Now stores the actual decay factor from settings (not the calculated decay)
- **FIXED**: Calculates decay-adjusted evidence correctly: `adjusted_evidence * evidence_based_decay`
- **FIXED**: Uses `current_decay_factor` (from settings) instead of storing the calculated decay value
- **FIXED**: Evidence-based decay calculation: `decay_factor ** cumulative_evidence_weight`
- **FIXED**: Cumulative values now calculated at the time each activity was completed
- **FIXED**: Current activity has no decay (decay = 1.0) since no evidence has accumulated since it was completed
- **FIXED**: Evidence weight now stores decay-adjusted evidence volume (the actual weight that affects progress)

**Fixed cumulative calculations:**
- **FIXED**: Cumulative evidence weight calculated from previous activities only
- **FIXED**: Cumulative performance calculated using chronological activity order
- **FIXED**: Each activity stores its own cumulative values at completion time

**Fixed decay calculation logic:**
- **FIXED**: Most recent activity has LEAST decay (decay = 1.0)
- **FIXED**: Older activities have MORE decay based on evidence accumulated since they were completed
- **FIXED**: Decay calculated as: `base_decay_factor ** evidence_accumulated_since_activity_completed`

**Added update_configuration method:**
- Allows dynamic updates to scoring engine configuration
- Updates decay factor when settings change

### 3. UI Improvements (`app.py`)

**Enhanced display_single_skill_table function:**
- **FIXED**: Shows both base decay factor and applied decay factor: `"Base→Applied"`
- **FIXED**: Calculates actual decay factor for each activity based on evidence accumulated since completion
- **FIXED**: Updated column header to "Decay Factor (Base→Applied)"
- **FIXED**: Evidence weight column now shows decay-adjusted evidence volume
- **FIXED**: Updated column header to "Decay-Adjusted Evidence Weight"
- **FIXED**: Summary statistics show meaningful metrics
- **FIXED**: Decay-adjusted evidence calculated dynamically in UI instead of using stored value
- **FIXED**: Evidence weight calculated dynamically as `adjusted_evidence * actual_decay_factor`
- **CLEANUP**: Removed redundant "Decay Adjusted Evidence" column (kept only "Evidence Weight")
- **CLEANUP**: Removed "Cumulative Evidence" column (no longer needed)
- **CLEANUP**: Updated summary statistics to show meaningful metrics instead of total decay-adjusted evidence

**Key Display Features:**
- Shows decay factor progression: `0.900 → 1.000` (most recent), `0.900 → 0.590` (older)
- Evidence weight column shows the actual weight that affects student progress (calculated dynamically)
- Summary statistics show: Current Performance, Total Adjusted Evidence, Total Evidence Weight, Avg Applied Decay
- Clean, focused table with essential columns only

**Sidebar Improvements:**
- **PRECISION**: Changed from sliders to numeric inputs for precise control
- **Evidence Threshold**: Numeric input with 0.1 step precision (1.0-200.0 range)
- **Score Threshold**: Numeric input with 0.01 step precision (0.1-1.0 range)
- **Decay Factor**: Numeric input with 0.001 step precision (0.1-1.0 range)

## How the Decay Factor Works

### 1. **Base Decay Factor** (from settings)
- This is the decay factor set in the sidebar (default: 0.9)
- Applied to each new activity based on current settings

### 2. **Applied Decay Factor** (calculated per activity)
- **Most Recent Activity**: No decay (decay = 1.0) since no evidence has accumulated since it was completed
- **Older Activities**: Decay increases based on evidence accumulated since they were completed
- Formula: `base_decay_factor ** evidence_accumulated_since_activity_completed`

### 3. **Decay-Adjusted Evidence Volume**
- Formula: `adjusted_evidence_volume * applied_decay_factor`
- Shows the effective contribution of each activity after decay
- Demonstrates how evidence contribution decreases over time

### 4. **Evidence Weight**
- **FIXED**: Now represents the decay-adjusted evidence volume
- This is the actual weight that affects the student's progress
- Formula: `adjusted_evidence_volume * applied_decay_factor`
- Shows how much each activity actually contributes to the cumulative score

## Key Insights

1. **Most Recent Activity**: Has the LEAST decay (decay = 1.0)
2. **Older Activities**: Have MORE decay based on evidence accumulated since completion
3. **Decay-Adjusted Evidence**: Shows the effective contribution after decay is applied
4. **Exponential Decay**: Decay factor decreases exponentially with evidence accumulated since completion
5. **Cumulative Values**: Each activity stores its own cumulative values at completion time
6. **Evidence Weight**: Represents the actual weight that affects student progress

## Example Calculation

For a decay factor of 0.9 with 3 activities (most recent first):
- **Activity 3 (Most Recent)**: Evidence accumulated since = 0, Applied decay = 0.9^0 = 1.0, Evidence Weight = 5.0
- **Activity 2 (Middle)**: Evidence accumulated since = 5, Applied decay = 0.9^5 = 0.590, Evidence Weight = 2.95
- **Activity 1 (Oldest)**: Evidence accumulated since = 10, Applied decay = 0.9^10 = 0.349, Evidence Weight = 1.74
- **Total Evidence Weight**: 9.69

This shows how the most recent activity has the least decay and highest evidence weight, and older activities have progressively more decay and lower evidence weights.

## Testing

The implementation has been tested with:
- ✅ Correct decay factor calculations (most recent = least decay)
- ✅ Proper storage of base vs applied decay factors
- ✅ Accurate decay-adjusted evidence volume calculations
- ✅ Dynamic decay factor updates from settings
- ✅ Correct cumulative value calculations at each point in time
- ✅ Chronological activity ordering for cumulative calculations
- ✅ Evidence weight now represents decay-adjusted evidence volume 