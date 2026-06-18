import logging
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import pickle
import copy
import xarray as xr
import numpy as np
from scipy.sparse import load_npz
from anemoi.inference.runners.simple import SimpleRunner
from anemoi.inference.outputs.printer import print_state

#########################################################################################################
# Modify this part according to your needs:
# - set the correct path to your model checkpoint


root = Path(__file__).resolve().parent
log_dir = root / "logs"
os.makedirs(log_dir, exist_ok=True)
output_dir = root / "outputs"
os.makedirs(output_dir, exist_ok=True)

weights_dir = root / "weights"
EKR_path = root / "EKR"
checkpoint = Path(weights_dir / "name_of_cpkt_file.cpkt")           #put the name of the weights file here
TFM_N320_LATLON = load_npz(EKR_path / "mir_16_linear" / "7f0be51c7c1f522592c7639e0d3f95bcbff8a044292aa281c1e73b842736d9bf.npz")
###########################################################################################################

latitudes = np.linspace(90, -90, 721)
longitudes = np.linspace(0, 359.75, 1440)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_dir / "AIFS.log")]
)
logger = logging.getLogger("run_aifsv1p1")


def get_ic(date: datetime):
    ic_filename = root / "IC_data" / f"{date.strftime('%Y%m%d')}" / f"input_state_{date.strftime('%Y%m%dT%H')}_v1p1.pkl"
    if not ic_filename.exists():
        logger.error(f"Initial condition file {ic_filename} does not exist.")
        raise FileNotFoundError(f"Initial condition file {ic_filename} does not exist.")
    logger.info(f"Loading initial condition from {ic_filename}")
    with open(ic_filename, "rb") as f:
        input_state = pickle.load(f)
    return input_state


def clip_to_india(ds):
    logger.info("Clipping to India box at native 0.25° resolution")
    ds = ds.sel(
        lat=slice(38.5, 6.5),
        lon=slice(66.5, 100.0)
    )
    logger.info(f"Clipped shape: {ds['tp'].shape}")
    logger.info(f"Lat range: {float(ds.lat.min()):.2f} to {float(ds.lat.max()):.2f}")
    logger.info(f"Lon range: {float(ds.lon.min()):.2f} to {float(ds.lon.max()):.2f}")
    return ds


def apply_india_mask(ds, mask_path):
    logger.info("Applying India mask at 0.25° resolution")
    logger.info("Mask convention: 1 = inside India, NaN = outside India")

    mask = xr.open_dataset(mask_path)
    mask_data = mask["lsm"]
    mask_data["lat"] = mask_data["lat"].astype(float)
    mask_data["lon"] = mask_data["lon"].astype(float)

    logger.info(f"Mask shape: {mask_data.shape}")
    logger.info(f"DS shape:   {ds['tp'].shape}")

    ds["tp"] = ds["tp"].where(mask_data == 1.0)

    mask.close()
    logger.info("India mask applied successfully")
    return ds


def process_state(state):
    output_state, runcount = state
    data_vars = {}
    logger.info(f"Processing step {runcount} for date: {output_state['date']}")
    for field in output_state["fields"]:
        values = (
            TFM_N320_LATLON * output_state["fields"][field].reshape(-1, 1)
        ).reshape(721, 1440)
        data_vars[field] = (["lat", "lon"], values.astype(np.float32))

    step_ds = xr.Dataset(
        data_vars,
        coords={"lat": latitudes, "lon": longitudes},
    )
    step_ds = step_ds.expand_dims("step")
    step_ds["step"] = [int(runcount)]
    return step_ds


def run(date: datetime, lead_time: int, save_fields: list):
    mask_path = Path("/net/monsoon/operational/monsoon-onset/AIFS/data/india_mask.nc")

    logger.info(f"Loading model from checkpoint: {checkpoint}")
    output_dir = output_dir / date.strftime('%Y%m%d%T')
    os.makedirs(output_dir, exist_ok=True)
    output_filename = output_dir / f"init_v1p1_{date.strftime('%Y%m%dT%H')}.nc"

    if output_filename.exists():
        logger.warning(f"Output file {output_filename} already exists. Skipping inference.")
        return

    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    month_str = str(month).zfill(2)
    day_str = str(day).zfill(2)
    hour_str = str(hour).zfill(2)

    input_state = get_ic(date)

    runner = SimpleRunner(checkpoint=checkpoint, device="cuda")

    runcount = 6
    datasets = []

    logger.info(f"Running inference for lead time: {lead_time} hours")

    for state in runner.run(input_state=input_state, lead_time=lead_time):
        print_state(state)
        saved_state = copy.deepcopy(state)

        if save_fields:
            selected_data = {
                "date": saved_state["date"],
                "fields": {
                    key: saved_state["fields"][key]
                    for key in save_fields
                    if key in saved_state["fields"]
                },
                "latitudes": saved_state["latitudes"],
                "longitudes": saved_state["longitudes"],
            }
            datasets.append((selected_data, runcount))
        else:
            datasets.append((saved_state, runcount))

        logger.info(f"Completed inference for step {runcount}, valid time: {state['date']}")
        runcount += 6

    ds = xr.concat(
        [process_state(output_state) for output_state in datasets], dim='step'
    )
    del datasets
    ds = ds.expand_dims("time")
    ds["time"] = [np.datetime64(f"{year}-{month_str}-{day_str}T{hour_str}:00:00")]
    ds = clip_to_india(ds)
    ds = apply_india_mask(ds, mask_path)
    ds.to_netcdf(output_filename)
    logger.info(f"Saved output to {output_filename}")


def main():
    parser = argparse.ArgumentParser(description="Run AIFS v1p1")
    parser.add_argument("date", type=str, help="Date in yyyymmddThh format e.g. 20260527T00")
    args = parser.parse_args()
    date = datetime.strptime(args.date, "%Y%m%dT%H")

    lead_time = 50 * 24
    save_fields = ['tp']

    logger.info(f"Running AIFS v1p1 for date: {date}")
    logger.info(f"Lead time: {lead_time // 24} days")

    try:
        run(date, lead_time, save_fields)
        logger.info("AIFS v1p1 run completed successfully.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()