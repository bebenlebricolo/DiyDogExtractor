#!/usr/bin/python

import requests
from pathlib import Path
import PyPDF2

C_DIYDOG_URL = "https://brewdogmedia.s3.eu-west-2.amazonaws.com/docs/2019+DIY+DOG+-+V8.pdf"

def download_pdf(url : str, output_file : Path) -> None:
    response = requests.get(url)
    match(response.status_code) :
        case 200 :
            pass
        case _ :
            print("Could not download pdf file, error code was : {}".format(response.status_code))
            return

    # Create output directory if it does not exist yet
    if not output_file.parent.exists() :
        output_file.parent.mkdir(parents=True)

    # Dump pdf to file
    with open(output_file, "wb") as file :
        file.write(response.content)


# Useful doc : https://pypdf2.readthedocs.io/en/latest/user/extract-text.html


def main() :
    this_dir = Path(__file__).parent
    cache_directory = this_dir.joinpath(".cache")
    pdf_file = cache_directory.joinpath("diydog-2022.pdf")
    if not pdf_file.exists() :
        download_pdf(C_DIYDOG_URL, pdf_file)

    with open(pdf_file, "rb") as file :
        reader = PyPDF2.PdfFileReader(file)
        # Page 22 is the first beer
        start_page = 21

        # Page 436 is the very last beer
        end_page = 435

        for i in range(start_page, end_page) :
            page = reader.getPage(i)
            text = page.extract_text()
            content = page.get_contents()
            data = content.get_data()
            print(text + "\n")


if __name__ == "__main__" :
    main()