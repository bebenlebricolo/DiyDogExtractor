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

>Note : I'd recommend running this in a venv, as on some linux distributions installing custom python packages messes up with the system's dependencies.
```bash
python -m venv <your directory>
./<bin somewhere in the venv>/activate # <- Hurray, you're in!
```

```bash
pip install -r requirements.txt
# or alternatively
python -m pip install -r requirements.txt
```

## Run the script
The [main.py](Sources/main.py) is part of a larger python package and thus shall be called as a python module like this :
```bash
python -m Sources.main
```

It will first download the pdf file locally and cache it in the ***.cache*** directory (created upon first run), so that we don't need to download it anymore after that.
Note that the ***.cache*** directory will be created *next* to the script file, within the [Sources](Sources) directory, which was easier for development purposes.

## Output data
For now, the parsed recipes are stored in the form of json files within the ***.cache*** directory, in a subfolder called "***extracted_recipes***".
They are produced by serializing the **Recipe** class, found in the [recipe.py](Sources/Models/recipe.py) file and contain all parsed data (except images and pdf pages which are registered under the form of filepath in the json file ; they are indirect object references).
They can be used as-is, despite being quite low-level, or they can be used throughout more evolved services (such as a web service / Rest Api)

## Patch the output dataset
Almost 100% of the dataset is clean, but out the 415 recipes, 3 remain hard to automatically parse (especially the hop section and the mash temperatures).
Some minor issues might still remain, but 3 patches are provided under the folder [Patches](Patches).
Those patches need to be applied using a tool which is located within the [Sources/ScriptingTools](Sources/ScriptingTools/) folder, called [Sources/ScriptingTools/patcher.py](Sources/ScriptingTools/patcher.py)

Usage :
```bash
cd DiydogExtractor # Repo's root folder
python -m Sources.ScriptingTools.patcher Patches Sources/.cache/deployed/recipes
```

It automatically handles recipes patching for you and normally you end up with a 100% processed datasets with all values up-to-date !