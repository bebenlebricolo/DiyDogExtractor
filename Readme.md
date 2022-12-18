# DiyDog Extractor toolset

The idea behind this repository is to provide some tooling which will be able to parse DiyDog recipes from their online PDF file.
This file can be retrieved at : [DiyDog 2019 - V8 (2022 release)]("https://brewdogmedia.s3.eu-west-2.amazonaws.com/docs/2019+DIY+DOG+-+V8.pdf").

I'm trying this to programmatically scrap data out of the pdf file, and generate a mixed database (json data objects + images) which may serve as the working database for a web service api for instance.
Pretty much like the [PunkApi](https://punkapi.com/) website, however the database is not manually filled and relies on a programmatic approach.

If this approach works fine, then we'll be able to parse further revisions of the DiyDog book without having to manually do the job (and potentially miss one or two things, copy-pasting errors, etc..).

# Try it for yourself : get the required tools
For this toolset to work, you'll need to install the requirements as per depicted in the [requirements.txt](Sources/requirements.txt) file.

Be sure you are running a **recent python** version (>= python 3.10) and have a **pypi** installation up and running.

Then, run the following commands in a shell :

```bash
pip install -r requirements.txt
# or alternatively
python -m pip install -r requirements.txt
```

## Run the script
Simply call the script as-is : `python main.py`.
It will first download the pdf file locally and cache it in the [.cache](Sources/.cache/) directory, so that we don't need ti download it anymore after that.
Note that the downloading process will occur *next* to the script file, which was easier for development purposes. As such, the ***.cache** directory is ignored by git.

