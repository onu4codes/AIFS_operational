import logging
import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import earthkit.data as ekd
from scipy.sparse import load_npz
import pickle
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

###########################################################################################################
# modify this part according to your needs:
root = Path(__file__).resolve().parent.parent
log_dir = root / 'logs'
os.makedirs(log_dir, exist_ok=True)
IC_dir = root / 'IC_data'
EKR_path = root / "EKR"
TFM_LATLON_N320 = load_npz(EKR_path / "mir_16_linear" / "9533e90f8433424400ab53c7fafc87ba1a04453093311c0b5bd0b35fedc1fb83.npz")
LSM_GRIB_PATH = Path(root / "data" / "lsm.grib")
###########################################################################################################

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_dir / 'AIFS.log')]
)
logger = logging.getLogger("preprocess_ic")

# ── v2 parameters ────────────────────────────────────────────────────────────
PARAM_SFC_V2   = ["10u", "10v", "2d", "2t", "msl", "skt", "sp", "tcw", "lsm", "z", "slor", "sdor", "sd"]
PARAM_SOIL_V2  = ["vsw", "sot"]
PARAM_WAVE_V2  = ["wmb", "h1012", "h1214", "h1417", "h1721", "h2125", "h2530", "mwd", "cdww", "mwp", "swh"]
PARAM_PL_V2    = ["gh", "t", "u", "v", "q"]
LEVELS_V2      = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50, 10]
SOIL_LEVELS    = [1, 2]

# ── v1.1 parameters ──────────────────────────────────────────────────────────
PARAM_SFC_V1P1  = ["10u", "10v", "2d", "2t", "msl", "skt", "sp", "tcw", "lsm", "z", "slor", "sdor"]
PARAM_SOIL_V1P1 = ["vsw", "sot"]
PARAM_PL_V1P1   = ["gh", "t", "u", "v", "w", "q"]
LEVELS_V1P1     = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50]
SOIL_LEVELS_V1P1 = [1, 2]

def preprocess_surface_parameters(date, PARAM_SFC):
    logger.info(f"Preprocessing surface parameters for date: {date.strftime('%Y-%m-%d %H:%M:%S')}")
    dates = [date - timedelta(hours=6), date]
    surface_fields = {}

    for d in dates:
        filename = f"{d.strftime('%Y%m%d%H%M%S')}-0h-oper-fc.grib2"
        file_path = IC_dir / date.strftime('%Y%m%d') / filename

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Reading GRIB file: {file_path}")
        source = ekd.from_source("file", str(file_path))
        data = source.sel(param=PARAM_SFC, levtype="sfc")

        for f in data:
            assert f.to_numpy().shape == (721, 1440), f"Unexpected shape {f.to_numpy().shape}"
            values = np.roll(f.to_numpy(), -f.shape[1] // 2, axis=1)
            values = TFM_LATLON_N320 * values.flatten()
            name = f.metadata("param")
            if name not in surface_fields:
                surface_fields[name] = []
            surface_fields[name].append(values)
            logger.info(f"Extracted '{name}' from {d.strftime('%Y%m%d%H%M%S')}, shape: {values.shape}")

    for key in surface_fields:
        surface_fields[key] = np.stack(surface_fields[key])

    missing = [p for p in PARAM_SFC if p not in surface_fields]
    if missing:
        logger.error(f"Missing parameters: {missing}")
        raise ValueError(f"Missing parameters: {missing}")

    logger.info(f"Successfully preprocessed {len(surface_fields)}/{len(PARAM_SFC)} surface parameters")
    return surface_fields


def preprocess_soil_parameters(date, PARAM_SOIL, SOIL_LEVELS):
    logger.info(f"Preprocessing soil parameters for date: {date.strftime('%Y-%m-%d %H:%M:%S')}")
    dates = [date - timedelta(hours=6), date]
    soil_fields = {}

    for d in dates:
        filename = f"{d.strftime('%Y%m%d%H%M%S')}-0h-oper-fc.grib2"
        file_path = IC_dir / date.strftime('%Y%m%d') / filename

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Reading GRIB file: {file_path}")
        source = ekd.from_source("file", str(file_path))
        data = source.sel(param=PARAM_SOIL, level=SOIL_LEVELS)

        for f in data:
            assert f.to_numpy().shape == (721, 1440), f"Unexpected shape {f.to_numpy().shape}"
            values = np.roll(f.to_numpy(), -f.shape[1] // 2, axis=1)
            values = TFM_LATLON_N320 * values.flatten()
            name = f"{f.metadata('param')}_{f.metadata('level')}"
            if name not in soil_fields:
                soil_fields[name] = []
            soil_fields[name].append(values)
            logger.info(f"Extracted '{name}' from {d.strftime('%Y%m%d%H%M%S')}, shape: {values.shape}")

    for key in soil_fields:
        soil_fields[key] = np.stack(soil_fields[key])

    SOIL_MAPPING = {
        'sot_1': 'stl1',
        'sot_2': 'stl2',
        'vsw_1': 'swvl1',
        'vsw_2': 'swvl2'
    }

    renamed_fields = {}
    for k, v in soil_fields.items():
        if k in SOIL_MAPPING:
            renamed_fields[SOIL_MAPPING[k]] = v
            logger.info(f"Renamed '{k}' → '{SOIL_MAPPING[k]}'")
        else:
            renamed_fields[k] = v

    expected = list(SOIL_MAPPING.values())
    missing = [p for p in expected if p not in renamed_fields]
    if missing:
        logger.error(f"Missing soil parameters: {missing}")
        raise ValueError(f"Missing soil parameters: {missing}")

    logger.info(f"Successfully preprocessed {len(renamed_fields)} soil parameters")
    return renamed_fields


def preprocess_wave_parameters(date):
    logger.info(f"Preprocessing wave parameters for date: {date.strftime('%Y-%m-%d %H:%M:%S')}")
    dates = [date - timedelta(hours=6), date]
    wave_fields = {}

    for d in dates:
        filename = f"{d.strftime('%Y%m%d%H%M%S')}-0h-wave-fc.grib2"
        file_path = IC_dir / date.strftime('%Y%m%d') / filename

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Reading GRIB file: {file_path}")
        source = ekd.from_source("file", str(file_path))
        data = source.sel(param=PARAM_WAVE_V2)

        for f in data:
            assert f.to_numpy().shape == (721, 1440), f"Unexpected shape {f.to_numpy().shape}"
            values = np.roll(f.to_numpy(), -f.shape[1] // 2, axis=1)
            values = TFM_LATLON_N320 * values.flatten()
            name = f.metadata("param")
            if name not in wave_fields:
                wave_fields[name] = []
            wave_fields[name].append(values)
            logger.info(f"Extracted '{name}' from {d.strftime('%Y%m%d%H%M%S')}, shape: {values.shape}")

    for key in wave_fields:
        wave_fields[key] = np.stack(wave_fields[key])

    if "mwd" in wave_fields:
        mwd = wave_fields.pop("mwd")
        mwd_rad = np.deg2rad(mwd)
        wave_fields["cos_mwd"] = np.cos(mwd_rad)
        wave_fields["sin_mwd"] = np.sin(mwd_rad)
        logger.info("Transformed 'mwd' → 'cos_mwd' and 'sin_mwd'")

    expected = [p for p in PARAM_WAVE_V2 if p != "mwd"] + ["cos_mwd", "sin_mwd"]
    missing = [p for p in expected if p not in wave_fields]
    if missing:
        logger.error(f"Missing wave parameters: {missing}")
        raise ValueError(f"Missing wave parameters: {missing}")

    logger.info(f"Successfully preprocessed {len(wave_fields)} wave parameters")
    return wave_fields


def preprocess_pressure_level_parameters(date, PARAM_PL, LEVELS):
    logger.info(f"Preprocessing pressure level parameters for date: {date.strftime('%Y-%m-%d %H:%M:%S')}")
    dates = [date - timedelta(hours=6), date]
    pl_fields = {}

    for d in dates:
        filename = f"{d.strftime('%Y%m%d%H%M%S')}-0h-oper-fc.grib2"
        file_path = IC_dir / date.strftime('%Y%m%d') / filename

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Reading GRIB file: {file_path}")
        source = ekd.from_source("file", str(file_path))
        data = source.sel(param=PARAM_PL, level=LEVELS)

        for f in data:
            assert f.to_numpy().shape == (721, 1440), f"Unexpected shape {f.to_numpy().shape}"
            values = np.roll(f.to_numpy(), -f.shape[1] // 2, axis=1)
            values = TFM_LATLON_N320 * values.flatten()
            name = f"{f.metadata('param')}_{f.metadata('level')}"
            if name not in pl_fields:
                pl_fields[name] = []
            pl_fields[name].append(values)
            logger.info(f"Extracted '{name}' from {d.strftime('%Y%m%d%H%M%S')}, shape: {values.shape}")

    for key in pl_fields:
        pl_fields[key] = np.stack(pl_fields[key])

    for level in LEVELS:
        key = f"gh_{level}"
        if key in pl_fields:
            gh = pl_fields.pop(key)
            pl_fields[f"z_{level}"] = gh * 9.80665
            logger.info(f"Transformed 'gh_{level}' → 'z_{level}'")

    expected = []
    for p in PARAM_PL:
        for level in LEVELS:
            if p == "gh":
                expected.append(f"z_{level}")
            else:
                expected.append(f"{p}_{level}")

    missing = [p for p in expected if p not in pl_fields]
    if missing:
        logger.error(f"Missing pressure level parameters: {missing}")
        raise ValueError(f"Missing pressure level parameters: {missing}")

    logger.info(f"Successfully preprocessed {len(pl_fields)} pressure level parameters")
    return pl_fields


def apply_land_sea_mask(fields):
    logger.info("Applying land-sea mask...")

    if not LSM_GRIB_PATH.exists():
        raise FileNotFoundError(f"LSM file not found: {LSM_GRIB_PATH}")

    mask = np.equal(
        ekd.from_source("file", str(LSM_GRIB_PATH))[0].to_numpy(flatten=True), 0
    )

    fields["sd"][:, mask] = np.nan
    fields["swvl1"][:, mask] = np.nan
    fields["swvl2"][:, mask] = np.nan

    logger.info("Land-sea mask applied to 'sd', 'swvl1', 'swvl2'")
    return fields


def preprocess_v2(date, output_file):
    logger.info("Starting v2 preprocessing...")
    fields = {}

    logger.info("Preprocessing Surface Parameters (v2)...")
    fields.update(preprocess_surface_parameters(date, PARAM_SFC_V2))

    logger.info("Preprocessing Soil Parameters (v2)...")
    fields.update(preprocess_soil_parameters(date, PARAM_SOIL_V2, SOIL_LEVELS))

    logger.info("Preprocessing Wave Parameters (v2)...")
    fields.update(preprocess_wave_parameters(date))

    logger.info("Preprocessing Pressure Level Parameters (v2)...")
    fields.update(preprocess_pressure_level_parameters(date, PARAM_PL_V2, LEVELS_V2))

    # remove unused variables
    for var in ["q_10", "q_50"]:
        if var in fields:
            fields.pop(var)
            logger.info(f"Removed '{var}' from fields")

    logger.info(f"Total v2 fields: {len(fields)}")

    # apply land sea mask
    fields = apply_land_sea_mask(fields)

    # save to pkl
    input_state = dict(date=date, fields=fields)
    with open(output_file, 'wb') as f:
        pickle.dump(input_state, f)

    logger.info(f"v2 input state saved to: {output_file}")


def preprocess_v1p1(date, output_file):
    logger.info("Starting v1.1 preprocessing...")
    fields = {}

    logger.info("Preprocessing Surface Parameters (v1.1)...")
    fields.update(preprocess_surface_parameters(date, PARAM_SFC_V1P1))

    logger.info("Preprocessing Soil Parameters (v1.1)...")
    fields.update(preprocess_soil_parameters(date, PARAM_SOIL_V1P1, SOIL_LEVELS_V1P1))

    # no wave parameters for v1.1
    logger.info("Skipping wave parameters for v1.1...")

    logger.info("Preprocessing Pressure Level Parameters (v1.1)...")
    fields.update(preprocess_pressure_level_parameters(date, PARAM_PL_V1P1, LEVELS_V1P1))

    # no q removal for v1.1 — 10 hPa level doesn't exist
    # no land sea mask for v1.1 — no sd field

    logger.info(f"Total v1.1 fields: {len(fields)}")

    # save to pkl
    input_state = dict(date=date, fields=fields)
    with open(output_file, 'wb') as f:
        pickle.dump(input_state, f)

    logger.info(f"v1.1 input state saved to: {output_file}")


def main():
    logger.info("Starting the preprocessing of initial conditions...")

    parser = argparse.ArgumentParser(description="Preprocess initial conditions for AIFS")
    parser.add_argument("date", type=str, help="Date in yyyymmddThh format e.g. 20260527T00")
    args = parser.parse_args()
    date = datetime.strptime(args.date, "%Y%m%dT%H")

    # output file paths
    output_file_v2   = IC_dir / date.strftime('%Y%m%d') / f"input_state_{date.strftime('%Y%m%dT%H')}_v2.pkl"
    output_file_v1p1 = IC_dir / date.strftime('%Y%m%d') / f"input_state_{date.strftime('%Y%m%dT%H')}_v1p1.pkl"

    # check if both already exist
    if output_file_v2.exists() and output_file_v1p1.exists():
        logger.info("Both input states already exist. Skipping preprocessing.")
        print(date.strftime('%Y%m%dT%H'))
        sys.exit(0)

    try:
        # preprocess v2 if not already done
        if not output_file_v2.exists():
            preprocess_v2(date, output_file_v2)
        else:
            logger.info(f"v2 input state already exists. Skipping v2 preprocessing.")

        # preprocess v1.1 if not already done
        if not output_file_v1p1.exists():
            preprocess_v1p1(date, output_file_v1p1)
        else:
            logger.info(f"v1.1 input state already exists. Skipping v1.1 preprocessing.")

        logger.info("All input states preprocessed successfully.")
        print(date.strftime('%Y%m%dT%H'))
        sys.exit(0)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()