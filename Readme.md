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
The [dbextractor.py](Sources/dbextractor.py) is part of a larger python package and thus shall be called as a python module like this :
```bash
python -m Sources.dbextractor
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

## Run database reverse indexing
Once the whole database has been patched, we can run the db reverse indexing to ease further use of the database by pre-calculating reverse indices.
This can be achieved using this script : [dbanalyser.py](Sources/dbanalyser.py)

```bash
python -m Sources.dbanalyser Sources/.cache/deployed/recipes/all_recipes.json Sources/.cache/deployed/dbanalysis
```

It will create lots of new json files which contain reverse mappings, items list and sorted lists (used to find issues in the database itself, Patches folder saw a big increase in patches after I wrote the dbanalysis tools).

## Finally, perform some database normalisation/sanitization
The database, once patched, still has some potential issues such as plenty of mistakes in words orthography, mismatched names, reversed works sequences and more generally lots of inconsistencies across the whole database.
This comes from the original hand-writing process behind the DiyDog book edition, and because we are locating ourselves as end-consumer of this document, there is no mean for us to make some edits.

```bash
python -m Sources.dbsanitizer References Sources/.cache/deployed Sources/.cache/deployed/dbsanitizer
```


So we need to tackle these subjects in order to produce a database which is as clean as possible, so that other tools can build safely upon its features.
This is achieved using the [dbsanitizer.py](Sources/dbsanitizer.py) script, which essentially opens up the `all_recipes.json` file once more and compares its main properties against known-good properties databases I handcrafted while looking at all the issues in the database.
They can be found under the folder [References](References), such as :
* [diydog_styles_keywords.json](References/diydog_styles_keywords.json)  -> list of known "styles" keywords found in the **tags** section of each recipe. Used to discriminate beer's style (and that's very hard !)
* [known_good_hops.json](References/known_good_hops.json) -> List of known existing **Hops**, with their **names**, **manufacturer** and **url**. Used to pinpoint the right hop to be replaced in recipes while being sanitized.
* [known_good_yeasts.json](References/known_good_yeasts.json) -> List of existing **Yeasts**, with their **names**, **manufacturer** and **url**. Used to pinpoint the right yeast to be replaced in recipes while being sanitized.
* [known_good_styles.json](References/known_good_styles.json)-> List of existing **Styles**, with their **names** and **url**. Used to pinpoint the right beer style to be replaced in recipes while being sanitized.
* [known_good_malts.json](References/known_good_malts.json)-> List of existing **Malts**, with their **names**, **manufacturer** and **url**. Used to pinpoint the right malt to be replaced in recipes while being sanitized.
* [known_diydog_extras.json](References/known_diydog_extras.json)-> List **Mash** and **Boil** extras found in the recipes. This one is used mostly to discriminate between a real Hop or Malt and an actual extra ingredient that was wildly inserted in Malts or Hops columns, whereas they mostly correspond to "Extra" ingredients class.

> Note:  most of the files listed above were used in conjunction with fuzzy searches so that we can "find" and clamp the maximum of elements we can from the database.
> Note 2 : Why is this important after all (having a clean database) ?
> -> Not to mention other tools that might rely on this database, having a clean and consistent database will allow further mapping to be developed (like the reverse mapping/indexing). This is a mandatory part in order to propose a clean end-user experience, with all links working, and the ability to find more information about a particular item with a single click !


------------------------------------------------------------------------------------------

# [Details] : How it works
### Extracts the raw database using python and a bunch of PDF tools
This is done via the script [dbextractor.py](Sources/dbextractor.py).
This piece of code scraps the DiyDog PDF book from the internet and extracts content from pages automatically.

1. PDF downloading and caching
Very straight forward, we first download the pdf book locally and cache it for later reuse (and faster startup times).

2. Pages extraction and caching
Each page is read and its content gets extracted in the form of raw ascii text blocks. Raw ASCII Text blocks look like this :
```
/T1_2 1 Tf
0 Tw
-15.068 -2.5030000000000001 Td
[ (T) 72 (AR) 36 (GET\040F) 14 (G) ] TJ
0.503 0.51 0.52 scn
/GS0 gs
/T1_0 1 Tf
-0.025 Tw
```

This is a 2 step process : raw ascii content is first extracted, then the script looks for text instruction start and end markers and isolate them as "content blocks".
Essentially, it reads each page's content, dumps an ascii version of it (because reading the text with pypdf loses the indication of text's location within the page; and it's impossible to retrace columns this way)

3. Data extraction from text blocks
Then, based on the text blocks location found earlier, we recompose each section based on x,y proximity, and each section is parsed individually (like the header, footer, ingredients section, description, etc...)
Also, we now need to actually decode pdf drawing instructions (because we can't rely on automated tools to do that for use in a generic way, so back to basics and proper PDF decoding !).
This is why you may find weird stuff such as transformation matrices decoding, etc. in the codebase : this is required to rebuild text content as well as text block location in the drawing space !

4. Recipe parsing !
That's when good stuff happens. Based on text block locations and special text anchors, we can retrace columns, rows and other block of visual content that we can easily visually identify on the rendered PDF page.
It's the starting point of the parsing process, now we can start to assemble data and group it as Yeast, Malt, Hop, etc...

5. Image extraction
Once the recipe is parsed, we also need to extract the beer's image (because, why not ?).
This is done using a combination of custom contouring algorithm and a marvelous Machine Learning background removal algorithm ([**rembg**](https://pypi.org/project/rembg/)).
First the image is roughly extracted, then we try to extract the background using traditional contouring algorithms (custom marching squares).
Then, under some conditions we use the ML algorithms to perform this task, it's not a 100% go-to solution but it does marvels on beer bottle samples !

6. Packaging guessing
Yes, we guesstimate the packaging of a recipe using the extracted image !:smile:.
This is performed using images aspect ratios, and it proved to work well with the 415 images, which was a great satisfaction !

7. Now the whole database (json files, png images and pdf pages) are deployed in the cache folder
This is the end goal of this first script, at the end you'll get a nice .cache folder under the [Sources/](Sources/) directory (yes, it's ignored by git so no issues with that !)
However the database is still quite inconsistent and the parsing is not perfect, so it needs a little bit of manual patching before continuing the process.

### Patches the raw database with manual patches
This is done via the script [patcher.py](Sources/ScriptingTools/patcher.py).
The **all_recipes.json** file is read back and some recipes are replaced with their counterparts located in the [Patches](Patches/) folder.
They are a few of them, and it was little issues here and there, such as double prints (2 pdf text lines superimposed in the PDF, which does not show up in the rendered page but does mess up the parsing, because the text block share a very close location ...)


### Run the database normalisation/sanitization tool
This is done via the script [dbsanitizer.py](Sources/dbsanitizer.py).
Finally, the database is straightened out using the dbsanitizer script.
This one takes care about matching as much properties as it can with known-good ones, and tries to normalize names, casings and especially find the right Hop/Yeast/Malt which are located in one of the known-good elements databases.
This is a crucial part (as stated somewhere above) in order to get the most out of this database.


### Further analysis can be conducted using the dbanalysis tool
This is done via the script [dbanalyser.py](Sources/dbanalyser.py).
This Optional tool is used to create reverse indexed databases that will be helpful for later use (and proved to be very useful when debugging, to provide some insights about properties).
It can noticeably be used to perform quick searches like "find me a beer that uses the Hop Ahtanum".
And we can easily mix the first list this gives with another "now find me a beer that matches the style Amber beer" and so on and so forth, without having to scan the whole database for those properties.
Out of 415 elements, this searches are easy to deal with, but it might still be interesting to have that kind of information at hands.