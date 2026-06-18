# Operational Package for AIFS v1.1 and v2.0 — India

A complete operational package to run **ECMWF AIFS (Artificial Intelligence Forecasting System) version 1.1 and version 2.0** simultaneously for India. The package automates the full pipeline: downloading initial conditions from the ECMWF Open Data server, preprocessing them, running inference with both AIFS models, and postprocessing the outputs for the India domain.

---

## Table of Contents

1. [Description](#description)
2. [Repository Structure](#repository-structure)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [Scripts](#scripts)
   - [run_pipeline.sh](#run_pipelinesh)
   - [download_ic.py](#download_icpy)
   - [preprocess_ic.py](#preprocess_icpy)
   - [run_aifsv1p1.py](#run_aifsv1p1py)
   - [run_aifsv2.py](#run_aifsv2py)
   - [slurm_submit_job_aifsv1p1.sh](#slurm_submit_job_aifsv1p1sh)
   - [pbs_submit_job_aifsv1p1.sh](#pbs_submit_job_aifsv1p1sh)
   - [slurm_submit_job_aifsv2.sh](#slurm_submit_job_aifsv2sh)
   - [pbs_submit_job_aifsv2.sh](#pbs_submit_job_aifsv2sh)
8. [Outputs](#outputs)
9. [Weights](#weights)
10. [Logs](#logs)

---

## Description

This repository downloads **ECMWF IFS cycle 50 analysis data at T+00hrs UTC** as initial conditions (ICs) for running both AIFS models. The GRIB2 files are fetched directly and programmatically from the ECMWF Open Data portal, preprocessed, and then fed into the respective models. Outputs are postprocessed and cropped to the India domain.

---

## Repository Structure

```
.
├── data/
│   ├── lsm.grib              # Land-sea mask, used during preprocessing
│   └── india_mask.nc         # India domain mask, used during postprocessing
│
├── EKR/                      # Grid conversion matrices and tools required by AIFS
│   └── mir_16_linear/
│       ├── 9533e9...npz      # LATLON → N320 transformation matrix (used in preprocessing)
│       └── 7f0be5...npz      # N320 → LATLON transformation matrix (used in inference)
│
├── environments/
│   ├── AIFS.yml              # Conda environment for AIFSv1.1
│   └── AIFSv2.yml            # Conda environment for AIFSv2.0
│
├── IC_data/                  # Downloaded initial conditions (auto-created at runtime)
│   └── YYYYMMDD/
│       ├── YYYYMMDD000000-0h-oper-fc.grib2
│       ├── YYYYMMDD000000-0h-wave-fc.grib2
│       ├── YYYYMMDD180000-0h-oper-fc.grib2
│       ├── YYYYMMDD180000-0h-wave-fc.grib2
│       ├── input_state_YYYYMMDDThh_v1p1.pkl   # Preprocessed IC for v1.1
│       └── input_state_YYYYMMDDThh_v2.pkl     # Preprocessed IC for v2.0
│
├── logs/
│   └── AIFS.log              # Unified log file for all pipeline steps
│
├── outputs/                  # Inference outputs (auto-created at runtime)
│   └── YYYYMMDDTHH/
│       ├── init_v1p1_YYYYMMDDThh.nc
│       └── init_v2_YYYYMMDDThh.nc
│
├── utils/                    # All scripts for running both versions of AIFS
│   ├── run_pipeline.sh
│   ├── download_ic.py
│   ├── preprocess_ic.py
│   ├── run_aifsv1p1.py
│   ├── run_aifsv2.py
│   ├── slurm_submit_job_aifsv1p1.sh
│   ├── pbs_submit_job_aifsv1p1.sh
│   ├── slurm_submit_job_aifsv2.sh
│   └── pbs_submit_job_aifsv2.sh
│
└── weights/                  # AIFS model weights (download separately — see below)
    ├── aifs-single-mse-1.1.ckpt
    └── aifs-single-mse-2.0.ckpt
```

---

## Requirements

- Linux system with a CUDA-compatible GPU (A100 recommended)
- CUDA 12.8
- Conda / Miniconda
- Access to the ECMWF Open Data portal
- SLURM or PBS job scheduler

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Create the conda environments

For **AIFSv1.1**:
```bash
conda env create -f environments/AIFS.yml
```

For **AIFSv2.0**:
```bash
conda env create -f environments/AIFSv2.yml
```

> **Note:** The `environments/` yml files contain system-dependent packages (CUDA libraries, PyTorch builds, `flash-attn`, etc.). If your system has a different CUDA version, update the `+cu128` torch packages and all `nvidia-*` packages accordingly before creating the environment. See comments inside the yml files for guidance.

### 3. Download model weights

Download the weights and place them in the `weights/` directory:

- **AIFSv1.1** → [aifs-single-mse-1.1.ckpt](https://huggingface.co/ecmwf/aifs-single-1.1/blob/main/aifs-single-mse-1.1.ckpt)
- **AIFSv2.0** → [aifs-single-mse-2.0.ckpt](https://huggingface.co/ecmwf/aifs-single-2.0/blob/main/aifs-single-mse-2.0.ckpt)

```
weights/
├── aifs-single-mse-1.1.ckpt
└── aifs-single-mse-2.0.ckpt
```

### 4. Make shell scripts executable

```bash
chmod +x utils/*.sh
```

---

## Configuration

Every script has a clearly marked configuration block at the top. Before running, update the paths in each script for your system. The specific lines to change are listed in each script's section below.

---

## Usage

### Running the full pipeline (recommended)

The easiest way to run both models end-to-end:

```bash
conda activate AIFSv2        # the pipeline script uses the AIFSv2 Python for steps 1 and 2
./utils/run_pipeline.sh
```

This runs all 8 steps automatically: download → preprocess → submit AIFSv1.1 job → wait → submit AIFSv2 job → wait.

### Running individual steps manually

```bash
# Step 1 — Download initial conditions
conda activate AIFSv2
python utils/download_ic.py

# Step 2 — Preprocess
python utils/preprocess_ic.py 20260618T00

# Step 3 — Run AIFSv1.1 inference (SLURM)
sbatch --export=DATE_F=20260618T00 utils/slurm_submit_job_aifsv1p1.sh

# Step 4 — Run AIFSv2 inference (SLURM)
sbatch --export=DATE_F=20260618T00 utils/slurm_submit_job_aifsv2.sh
```

For PBS clusters, replace `sbatch` with `qsub`:
```bash
qsub -v DATE_F=20260618T00 utils/pbs_submit_job_aifsv1p1.sh
qsub -v DATE_F=20260618T00 utils/pbs_submit_job_aifsv2.sh
```

---

## Scripts

### `run_pipeline.sh`

The master orchestration script that runs the entire pipeline end-to-end. It sequentially handles downloading, preprocessing, and submitting both inference jobs to the scheduler, waiting for each to finish before proceeding.

**Pipeline steps:**

| Step | Action |
|---|---|
| 1 | Download initial conditions (`download_ic.py`) |
| 2 | Preprocess initial conditions (`preprocess_ic.py`) |
| 3 | Submit AIFSv1.1 inference job to scheduler |
| 4 | Wait for AIFSv1.1 job to complete |
| 5 | Check AIFSv1.1 exit code |
| 6 | Submit AIFSv2 inference job to scheduler |
| 7 | Wait for AIFSv2 job to complete |
| 8 | Check AIFSv2 exit code |

The script polls job status every 60 seconds and exits with an error if any step fails, with a pointer to `logs/AIFS.log`.

**Scheduler support:** The script supports both SLURM (active by default) and PBS (commented out). To switch to PBS, comment out the SLURM lines and uncomment the PBS lines — these are clearly marked throughout the script.

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 3 | `PYTHON` — path to the Python executable in your AIFSv2 environment, e.g. `/path/to/conda-envs/AIFSv2/bin/python` |
| Line 4 | `SCRIPT_DIR` — full path to the `utils/` directory |

---

### `download_ic.py`

Downloads the **initial condition GRIB2 files** required to run AIFS inference from the ECMWF Open Data server.

**What it does:**

1. Queries the ECMWF Open Data server for the latest available forecast date using the `ecmwf-opendata` client.
2. Checks whether all 4 expected GRIB2 files already exist locally — skips download if they do.
3. Constructs download URLs and streams the files in 1 MB chunks from `data.ecmwf.int`.
4. Saves files to `IC_data/YYYYMMDD/`.
5. Prints the date string (`YYYYMMDDThh`) to stdout so the calling shell script can capture it.
6. Exits with code `0` on success, `1` on failure.

**Files downloaded:**

| File | Description |
|---|---|
| `YYYYMMDD000000-0h-oper-fc.grib2` | Atmospheric analysis at T+00h |
| `YYYYMMDD000000-0h-wave-fc.grib2` | Wave analysis at T+00h |
| `YYYYMMDD180000-0h-oper-fc.grib2` | Atmospheric analysis at T-06h |
| `YYYYMMDD180000-0h-wave-fc.grib2` | Wave analysis at T-06h |

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 13 | `root` — if your directory layout differs from the default, update the `parent.parent` chain |
| Line 14 | `log_dir` — path to the log directory |
| Line 15 | `IC_dir` — path to where IC files should be saved |

---

### `preprocess_ic.py`

Reads the downloaded GRIB2 files, extracts the required meteorological fields, applies grid transformations, and saves the result as a `.pkl` file ready for AIFS inference. Produces **separate output files for v1.1 and v2.0** since the two models require different sets of parameters.

**What it does:**

1. Reads atmospheric (`oper-fc`) and wave (`wave-fc`) GRIB2 files for both T+00h and T-06h.
2. Extracts surface, soil, wave, and pressure level fields for each model version.
3. Rolls the global grid from a 0°–360° longitude convention to a -180°–180° convention.
4. Applies the **LATLON → N320 sparse matrix transformation** (`TFM_LATLON_N320`) to regrid fields onto the AIFS native grid.
5. Applies unit and variable transformations:
   - `gh` (geopotential height) → `z` (geopotential) by multiplying by 9.80665
   - `mwd` (mean wave direction) → `cos_mwd` and `sin_mwd` to avoid angular discontinuity
   - Soil variable names are remapped: `sot_1` → `stl1`, `sot_2` → `stl2`, `vsw_1` → `swvl1`, `vsw_2` → `swvl2`
6. For v2.0 only: applies the **land-sea mask** (`lsm.grib`) to set `sd`, `swvl1`, and `swvl2` to `NaN` over ocean points.
7. Saves the result as a pickle file.

**Parameter differences between v1.1 and v2.0:**

| Category | v1.1 | v2.0 |
|---|---|---|
| Surface | 12 params (no `sd`) | 13 params (includes `sd`) |
| Pressure levels | 13 levels, includes `w` | 14 levels, no `w` |
| Wave parameters | Not used | 11 wave parameters |
| Land-sea mask | Not applied | Applied to `sd`, `swvl1`, `swvl2` |

**Output files:**

```
IC_data/YYYYMMDD/
├── input_state_YYYYMMDDThh_v1p1.pkl
└── input_state_YYYYMMDDThh_v2.pkl
```

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 14 | `root` — project root path |
| Line 15 | `log_dir` — log directory path |
| Line 17 | `IC_dir` — initial conditions directory |
| Line 18 | `EKR_path` — path to the EKR directory containing the grid transformation matrices |
| Line 19 | `TFM_LATLON_N320` — path to the `.npz` sparse matrix file for LATLON → N320 |
| Line 20 | `LSM_GRIB_PATH` — path to the `lsm.grib` land-sea mask file |

---

### `run_aifsv1p1.py`

Runs **AIFS v1.1 inference** for a given date and saves the output as a NetCDF file cropped to the India domain.

**What it does:**

1. Loads the preprocessed v1.1 initial condition pickle file from `IC_data/YYYYMMDD/`.
2. Loads the AIFS v1.1 model checkpoint from `weights/`.
3. Runs inference for a **50-day lead time** (1200 hours) using the `anemoi-inference` `SimpleRunner`, stepping forward in 6-hourly increments.
4. After each 6-hourly step, transforms the output fields from the AIFS native N320 grid back to a regular 0.25° lat-lon grid using the **N320 → LATLON sparse matrix** (`TFM_N320_LATLON`).
5. Only saves the `tp` (total precipitation) field at each step.
6. Concatenates all timesteps into a single `xarray` Dataset with a `step` dimension.
7. Clips the output to the India bounding box (lat: 6.5°N–38.5°N, lon: 66.5°E–100.0°E).
8. Applies the India mask — sets all points outside India to `NaN`.
9. Saves the final output as a NetCDF file.

**Output:**

```
outputs/YYYYMMDDTHH/
└── init_v1p1_YYYYMMDDThh.nc    # tp field, 50-day forecast, India domain
```

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 19 | `root` — project root path (currently set to `parent`, adjust if needed) |
| Line 20 | `log_dir` — log directory |
| Line 23 | `output_dir` — where NetCDF outputs are saved |
| Line 26 | `weights_dir` — path to weights directory |
| Line 27 | `EKR_path` — path to EKR directory |
| Line 28 | `checkpoint` — **replace `name_of_cpkt_file.cpkt` with the actual filename**, e.g. `aifs-single-mse-1.1.ckpt` |
| Line 29 | `TFM_N320_LATLON` — path to the N320 → LATLON `.npz` matrix |
| Line 72 | `mask_path` — full path to `india_mask.nc` |

---

### `run_aifsv2.py`

Runs **AIFS v2.0 inference** for a given date. Functionally identical to `run_aifsv1p1.py` with two differences: it loads the v2.0 preprocessed IC file and runs for a **5-day lead time** instead of 50 days.

**What it does:**

1. Loads the preprocessed v2.0 initial condition pickle file from `IC_data/YYYYMMDD/`.
2. Loads the AIFS v2.0 model checkpoint from `weights/`.
3. Runs inference for a **5-day lead time** (120 hours) in 6-hourly steps.
4. Transforms outputs from N320 to 0.25° lat-lon grid.
5. Saves only the `tp` field at each timestep.
6. Clips to India domain and applies India mask.
7. Saves output as NetCDF.

**Output:**

```
outputs/YYYYMMDDTHH/
└── init_v2_YYYYMMDDThh.nc    # tp field, 5-day forecast, India domain
```

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 19 | `root` — project root path |
| Line 20 | `log_dir` — log directory |
| Line 23 | `output_dir` — where NetCDF outputs are saved |
| Line 26 | `weights_dir` — path to weights directory |
| Line 27 | `EKR_path` — path to EKR directory |
| Line 28 | `checkpoint` — **replace `name_of_cpkt_file.cpkt` with the actual filename**, e.g. `aifs-single-mse-2.0.ckpt` |
| Line 29 | `TFM_N320_LATLON` — path to the N320 → LATLON `.npz` matrix |
| Line 72 | `mask_path` — full path to `india_mask.nc` |

---

### `slurm_submit_job_aifsv1p1.sh`

SLURM job submission script for AIFSv1.1 inference. Requests 1 A100 GPU, 4 CPU cores, and 64 GB RAM with a 2-hour wall time.

The date is passed in via the `DATE_F` environment variable, either exported by `run_pipeline.sh` or set manually with `--export`.

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 8 | `#SBATCH -o` — full path to the log file for stdout, e.g. `/path/to/logs/AIFS.log` |
| Line 9 | `#SBATCH -e` — full path to the log file for stderr (can be the same as stdout) |
| Line 14 | `PYTHON` — full path to Python in your AIFSv1.1 conda environment, e.g. `/path/to/conda-envs/AIFS_ENS/bin/python` |
| Line 15 | `SCRIPT_DIR` — full path to the `utils/` directory |

---

### `pbs_submit_job_aifsv1p1.sh`

PBS equivalent of `slurm_submit_job_aifsv1p1.sh`. Use this if your cluster runs PBS/Torque instead of SLURM. Requests the same resources: 1 GPU, 4 CPUs, 64 GB RAM, 2-hour wall time.

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 7 | `#PBS -o` — full path to the log file for stdout |
| Line 8 | `#PBS -e` — full path to the log file for stderr |
| Line 14 | `PYTHON` — full path to Python in your AIFSv1.1 conda environment |
| Line 15 | `SCRIPT_DIR` — full path to the `utils/` directory |

---

### `slurm_submit_job_aifsv2.sh`

SLURM job submission script for AIFSv2.0 inference. Same resource requests as the v1.1 SLURM script.

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 8 | `#SBATCH -o` — full path to the log file for stdout |
| Line 9 | `#SBATCH -e` — full path to the log file for stderr |
| Line 15 | `PYTHON` — full path to Python in your AIFSv2.0 conda environment, e.g. `/path/to/conda-envs/AIFSv2/bin/python` |
| Line 16 | `SCRIPT_DIR` — full path to the `utils/` directory |

---

### `pbs_submit_job_aifsv2.sh`

PBS equivalent of `slurm_submit_job_aifsv2.sh`.

**Lines to modify before running:**

| Line | What to change |
|---|---|
| Line 7 | `#PBS -o` — full path to the log file for stdout |
| Line 8 | `#PBS -e` — full path to the log file for stderr |
| Line 14 | `PYTHON` — full path to Python in your AIFSv2.0 conda environment |
| Line 15 | `SCRIPT_DIR` — full path to the `utils/` directory |

---

## Outputs

Both inference scripts produce NetCDF files in the `outputs/` directory:

```
outputs/
└── YYYYMMDDTHH/
    ├── init_v1p1_YYYYMMDDThh.nc    # AIFSv1.1 — 50-day tp forecast over India
    └── init_v2_YYYYMMDDThh.nc      # AIFSv2.0 — 5-day tp forecast over India
```

**Output file structure:**

| Dimension | Values |
|---|---|
| `time` | Forecast initialisation time |
| `step` | Forecast step in hours (6, 12, 18, ...) |
| `lat` | 6.5°N to 38.5°N at 0.25° resolution |
| `lon` | 66.5°E to 100.0°E at 0.25° resolution |

Variable saved: `tp` (total precipitation), masked to India using `india_mask.nc`.

---

## Weights

Model weights are **not included** in this repository and must be downloaded separately from HuggingFace:

| Model | Download Link |
|---|---|
| AIFSv1.1 | https://huggingface.co/ecmwf/aifs-single-1.1/blob/main/aifs-single-mse-1.1.ckpt |
| AIFSv2.0 | https://huggingface.co/ecmwf/aifs-single-2.0/blob/main/aifs-single-mse-2.0.ckpt |

Place the downloaded `.ckpt` files in the `weights/` directory and update the `checkpoint` variable in `run_aifsv1p1.py` (line 28) and `run_aifsv2.py` (line 28) with the correct filenames.

---

## Logs

All pipeline activity — downloads, preprocessing, inference steps, and errors — is logged to a single unified file:

```
logs/AIFS.log
```

Each log entry includes a timestamp, the name of the script that generated it, the log level, and the message. Check this file first whenever any step fails.

---

## Authors

Anustup Biswas