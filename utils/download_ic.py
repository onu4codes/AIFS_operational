import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import requests
from ecmwf.opendata import Client as OpendataClient

########################################################################################################
# Modify this part according to your needs:
root = Path(__file__).resolve().parent.parent
log_dir = root / 'logs'
IC_dir = root / 'IC_data'

########################################################################################################

os.makedirs(log_dir, exist_ok=True)
os.makedirs(IC_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_dir / 'AIFS.log')]
)
logger = logging.getLogger("download_ic")


def check_latest_ic_date():
    SOURCE = "ecmwf"
    DATE = OpendataClient(SOURCE).latest()
    return DATE


def download_ic(date):
    date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    IC_loc = IC_dir / f"{date.strftime('%Y%m%d')}"
    os.makedirs(IC_loc, exist_ok=True)

    dates = [date - timedelta(hours=6), date]

    models = {
        'oper': 'oper-fc',
        'wave': 'wave-fc',
    }

    for d in dates:
        for folder, suffix in models.items():
            date_str = d.strftime('%Y%m%d')
            hour_str = d.strftime('%Hz')
            filename = f"{d.strftime('%Y%m%d%H%M%S')}-0h-{suffix}.grib2"
            file_path = IC_loc / filename

            # check if file already exists before downloading
            if file_path.exists():
                logger.info(f"File already exists, skipping: {filename}")
                continue

            url = f"https://data.ecmwf.int/forecasts/{date_str}/{hour_str}/ifs/0p25/{folder}/{filename}"
            logger.info(f"Constructed URL: {url}")

            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                logger.info(f"Successfully downloaded {filename}")
            else:
                logger.error(f"Failed to download {filename}. Status code: {response.status_code}")
                logger.error(f"Response content: {response.content}")
                raise Exception(f"Failed to download {filename}. Status code: {response.status_code}")


def main():
    logger.info("Starting the download process...")
    try:
        latest_ic_date = check_latest_ic_date()
        # latest_ic_date = datetime.strptime(2024-06-01T00:00:00Z, '%Y-%m-%dT%H:%M:%SZ')  # ← hardcoded for testing; replace with above line for production
        logger.info(f"Latest IC date found: {latest_ic_date}")

        # check if all expected files exist
        IC_loc = IC_dir / latest_ic_date.strftime('%Y%m%d')
        date_midnight = latest_ic_date.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_files = [
            f"{date_midnight.strftime('%Y%m%d%H%M%S')}-0h-oper-fc.grib2",
            f"{date_midnight.strftime('%Y%m%d%H%M%S')}-0h-wave-fc.grib2",
            f"{(date_midnight - timedelta(hours=6)).strftime('%Y%m%d%H%M%S')}-0h-oper-fc.grib2",
            f"{(date_midnight - timedelta(hours=6)).strftime('%Y%m%d%H%M%S')}-0h-wave-fc.grib2",
        ]
        all_files_exist = all((IC_loc / f).exists() for f in expected_files)

        if not all_files_exist:
            logger.info(f"Downloading data for date: {latest_ic_date}")
            download_ic(latest_ic_date)
            logger.info("Data downloaded successfully.")
        else:
            logger.info(f"All files for {latest_ic_date} already exist. Skipping download.")

        # print for shell to capture
        print(latest_ic_date.strftime('%Y%m%dT%H'))
        sys.exit(0)

    except Exception as e:
        logger.error(f"An error occurred during download: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()