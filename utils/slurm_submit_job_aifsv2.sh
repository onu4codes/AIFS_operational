#!/bin/bash -l
#SBATCH -p general
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=64G
#SBATCH -t 02:00:00
#SBATCH -J run_aifsv2
#SBATCH -o path to log file
#SBATCH -e path to log file
#SBATCH --open-mode=append

# DATE_F=$1
#################################################################################################################
# modify this part according to your needs:
# - make sure to set the correct path to your Python environment and the script directory

PYTHON="path of environment AIFS2/bin/python"           #modify according to the environment that you have created for AIFS 2
SCRIPT_DIR="put the path of the script"             #modify according to the environment that you have created for AIFS 2
#################################################################################################################


echo "======================================================================="
echo "Starting AIFS v2 inference"
echo "Job ID: $SLURM_JOB_ID"
echo "Date: $DATE_F"
echo "======================================================================="

$PYTHON $SCRIPT_DIR/run_aifsv2.py $DATE_F

if [ $? -eq 0 ]; then
    echo "Inference completed successfully for date: $DATE_F"
else
    echo "Inference failed for date: $DATE_F"
    echo "Please check logs/AIFS.log for more details."
    exit 1
fi

echo "======================================================================="
echo "AIFS v2 inference completed"
echo "======================================================================="