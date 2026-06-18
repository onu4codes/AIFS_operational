#!/bin/bash -l
#SBATCH -p general
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=64G
#SBATCH -t 02:00:00
#SBATCH -J run_aifsv1p1
#SBATCH -o path to log file
#SBATCH -e path to log file
#SBATCH --open-mode=append

# DATE_F=$1

PYTHON="path of environment AIFS1p1/bin/python"           #modify according to the environment that you have created for AIFS 1.1
SCRIPT_DIR="put the path of the script"             #modify according to the environment that you have created for AIFS 1.1


echo "======================================================================="
echo "Starting AIFS v1.1 inference"
echo "Job ID: $SLURM_JOB_ID"
echo "Date: $DATE_F"
echo "======================================================================="

$PYTHON $SCRIPT_DIR/run_aifsv1p1.py $DATE_F

if [ $? -eq 0 ]; then
    echo "Inference completed successfully for date: $DATE_F"
else
    echo "Inference failed for date: $DATE_F"
    echo "Please check logs/AIFS.log for more details."
    exit 1
fi

echo "======================================================================="
echo "AIFS v1.1 inference completed"
echo "======================================================================="