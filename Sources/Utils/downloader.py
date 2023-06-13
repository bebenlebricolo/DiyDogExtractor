import requests
from pathlib import Path
from .logger import Logger

def download_pdf(url : str, output_file : Path, logger : Logger) -> None:
    response = requests.get(url)
    match(response.status_code) :
        case 200 :
            pass
        case _ :
            logger.log("Could not download pdf file, error code was : {}".format(response.status_code))
            return

    # Create output directory if it does not exist yet
    if not output_file.parent.exists() :
        output_file.parent.mkdir(parents=True)

    # Dump pdf to file
    with open(output_file, "wb") as file :
        file.write(response.content)