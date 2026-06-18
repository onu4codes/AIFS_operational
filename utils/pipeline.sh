#!/bin/bash

PYTHON="give environment path for AIFSv2/bin/python"  # ← update this path to your Python executable if needed
SCRIPT_DIR="path to the script" # ← update this path to your script directory if needed

echo "======================================================================="
echo "Starting the AIFS pipeline (v1p1 → v2)"
echo "======================================================================="

# step 1 — download initial conditions
echo "Step 1: Downloading initial conditions..."
DATE=$($PYTHON $SCRIPT_DIR/download_ic.py)

if [ $? -eq 0 ]; then
    echo "Initial conditions downloaded successfully for date: $DATE"
else
    echo "Error downloading initial conditions. Exiting."
    echo "Please check logs/AIFS.log for more details."
    exit 1
fi

# step 2 — preprocess initial conditions
echo "Step 2: Preprocessing initial conditions..."
$PYTHON $SCRIPT_DIR/preprocess_ic.py $DATE

if [ $? -eq 0 ]; then
    echo "Preprocessing successful for date: $DATE"
else
    echo "Error preprocessing initial conditions. Exiting."
    echo "Please check logs/AIFS.log for more details."
    exit 1
fi

# =============================================================================
# AIFS v1p1
# =============================================================================

echo "======================================================================="
echo "Step 3: Submitting AIFS v1p1 inference job..."

# ── SLURM (active) ────────────────────────────────────────────────────────────
JOB_ID_V1P1=$(sbatch --export=DATE_F=$DATE $SCRIPT_DIR/slurm_submit_job_aifsv1p1.sh | awk '{print $4}')

# ── PBS (commented out — uncomment if using PBS) ─────────────────────────────
# JOB_ID_V1P1=$(qsub -v DATE_F=$DATE $SCRIPT_DIR/pbs_submit_job_aifsv1p1.sh)

if [ $? -eq 0 ]; then
    echo "AIFS v1p1 inference job submitted successfully! Job ID: $JOB_ID_V1P1"
else
    echo "Error submitting AIFS v1p1 inference job. Exiting."
    echo "Please check logs/AIFS.log for more details."
    exit 1
fi

echo "Step 4: Waiting for AIFS v1p1 job $JOB_ID_V1P1 to complete..."

while true; do
    # ── SLURM ─────────────────────────────────────────────────────────────────
    JOB_STATE=$(squeue -j $JOB_ID_V1P1 -h -o "%T" 2>/dev/null)
    # ── PBS (commented out) ───────────────────────────────────────────────────
    # JOB_STATE=$(qstat -j $JOB_ID_V1P1 2>/dev/null | grep "job_state" | awk '{print $3}')

    if [ -z "$JOB_STATE" ]; then
        break
    fi
    echo "Job $JOB_ID_V1P1 status: $JOB_STATE — waiting..."
    sleep 60
done

echo "Step 5: Checking AIFS v1p1 job completion status..."

# ── SLURM ─────────────────────────────────────────────────────────────────────
JOB_EXIT=$(sacct -j $JOB_ID_V1P1 --format=ExitCode --noheader | head -1 | awk '{print $1}' | cut -d: -f1)
# ── PBS (commented out) ───────────────────────────────────────────────────────
# JOB_EXIT=$(qstat -f $JOB_ID_V1P1 | grep "exit_status" | awk '{print $3}')

if [ "$JOB_EXIT" -eq 0 ]; then
    echo "AIFS v1p1 job $JOB_ID_V1P1 completed successfully!"
else
    echo "AIFS v1p1 job $JOB_ID_V1P1 failed with exit code $JOB_EXIT"
    echo "Please check logs/AIFS.log for more details."
    exit 1
fi

# =============================================================================
# AIFS v2
# =============================================================================

echo "======================================================================="
echo "Step 6: Submitting AIFS v2 inference job..."

# ── SLURM (active) ────────────────────────────────────────────────────────────
JOB_ID_V2=$(sbatch --export=DATE_F=$DATE $SCRIPT_DIR/submit_job_aifsv2.sh | awk '{print $4}')

# ── PBS (commented out — uncomment if using PBS) ─────────────────────────────
# JOB_ID_V2=$(qsub -v DATE_F=$DATE $SCRIPT_DIR/submit_job_aifsv2.sh)

if [ $? -eq 0 ]; then
    echo "AIFS v2 inference job submitted successfully! Job ID: $JOB_ID_V2"
else
    echo "Error submitting AIFS v2 inference job. Exiting."
    echo "Please check logs/AIFS.log for more details."
    exit 1
fi

echo "Step 7: Waiting for AIFS v2 job $JOB_ID_V2 to complete..."

while true; do
    # ── SLURM ─────────────────────────────────────────────────────────────────
    JOB_STATE=$(squeue -j $JOB_ID_V2 -h -o "%T" 2>/dev/null)
    # ── PBS (commented out) ───────────────────────────────────────────────────
    # JOB_STATE=$(qstat -j $JOB_ID_V2 2>/dev/null | grep "job_state" | awk '{print $3}')

    if [ -z "$JOB_STATE" ]; then
        break
    fi
    echo "Job $JOB_ID_V2 status: $JOB_STATE — waiting..."
    sleep 60
done

echo "Step 8: Checking AIFS v2 job completion status..."

# ── SLURM ─────────────────────────────────────────────────────────────────────
JOB_EXIT=$(sacct -j $JOB_ID_V2 --format=ExitCode --noheader | head -1 | awk '{print $1}' | cut -d: -f1)
# ── PBS (commented out) ───────────────────────────────────────────────────────
# JOB_EXIT=$(qstat -f $JOB_ID_V2 | grep "exit_status" | awk '{print $3}')

if [ "$JOB_EXIT" -eq 0 ]; then
    echo "AIFS v2 job $JOB_ID_V2 completed successfully!"
else
    echo "AIFS v2 job $JOB_ID_V2 failed with exit code $JOB_EXIT"
    echo "Please check logs/AIFS.log for more details."
    exit 1
fi

echo "======================================================================="
echo "Pipeline completed successfully for date: $DATE"
# ── SLURM ─────────────────────────────────────────────────────────────────────
echo "Monitor with: squeue -u anustupb"
# ── PBS (commented out) ───────────────────────────────────────────────────────
# echo "Monitor with: qstat -u anustupb"
echo "Logs at: $SCRIPT_DIR/logs/AIFS.log"
echo "======================================================================="