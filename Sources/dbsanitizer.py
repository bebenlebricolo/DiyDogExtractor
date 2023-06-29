import sys
from pathlib import Path
import argparse
import json
from dataclasses import dataclass, field

from typing import cast, Optional
from thefuzz import fuzz

from .Utils.logger import Logger
from .Utils import filesystem as fs
from .Models import recipe as rcp
from .Models.jsonable import Jsonable
from .style_finder import read_keywords_file, find_style_with_keywords
from .dbanalyser import read_all_recipes

@dataclass
class RefStyle(Jsonable):
    name : str = ""
    category : str = ""
    aliases : Optional[list[str]] = None
    url : str = ""

    def from_json(self, content: dict) -> None:
        self.name = content["name"]
        self.category = content["category"]
        self.url = content["url"]
        if "aliases" in content and content["aliases"] is not None :
            self.aliases = []
            for elem in content["aliases"] :
                self.aliases.append(elem)

    def to_json(self) -> dict:
        out_dict = {
            "name" : self.name,
            "category" : self.category,
            "url" : self.url,
            "aliases" : self.aliases
        }
        return out_dict

@dataclass
class MostProbableHit:
    distance : float = 0.0
    style : Optional[RefStyle] = None


def compute_string_ratios(tag : str, token : str) -> int :
    distance = fuzz.token_set_ratio(tag, token)
    return distance

def fuzzy_search_in_ref(tag : str, styles_ref_list : list[RefStyle]) -> MostProbableHit :
    # Trying to minimize the hamming distance
    max_ratio = 0
    most_probable_style = styles_ref_list[0]

    for style in styles_ref_list :
        local_ratio = compute_string_ratios(tag, style.name)
        if style.aliases is not None :
            for alias in style.aliases :
                alias_distance = compute_string_ratios(tag, alias)
                if alias_distance > local_ratio :
                    local_ratio = alias_distance

        if local_ratio > max_ratio :
            max_ratio = local_ratio
            most_probable_style = style


    return MostProbableHit(style=most_probable_style, distance=max_ratio)

def infer_style_from_tags(recipe : rcp.Recipe, keywords_list : list[str]):
    pass



def main(args : list[str]):
    parser = argparse.ArgumentParser("Database sanitizer script", description="Tries to match recipes properties against known-good datasets and tries to uniformize recipes")
    parser.add_argument("ref_dir", help="References directory, where known good dataset (known_good_<prop>.json) reside")
    parser.add_argument("deployed_recipes_dir", help="Directory where deployed recipes databases are located")
    parser.add_argument("output_directory", help="Output directory where results will be written")

    commands = parser.parse_args(args)
    ref_dir = Path(commands.ref_dir)
    deployed_recipes_dir = Path(commands.deployed_recipes_dir)
    output_directory = Path(commands.output_directory)
    fs.ensure_folder_exist(output_directory)

    logger = Logger(output_directory.joinpath("dbsanitizer.txt"))
    if not ref_dir.exists():
        logger.log("/!\\ Input file does not exist, cannot continue with db analysis.")
        return 1

    # Using this keywords contraption instead of the known good style list, because styles used by BrewDog in their recipes vary too widely
    # and even fuzzy search has a hard time finding actual "regular" styles to stick to.
    # So instead, rely on manually-prepared dataset that I know is part of DiyDog book (...)
    styles_file = ref_dir.joinpath("diydog_styles_keywords.json")
    hops_file = ref_dir.joinpath("known_good_hops.json")
    malts_file = ref_dir.joinpath("known_good_malts.json")
    yeasts_file = ref_dir.joinpath("known_good_yeasts.json")


    logger.log("Reading all recipes from disk")
    recipes_list : list[rcp.Recipe] = []
    all_recipes_file = deployed_recipes_dir.joinpath("recipes/all_recipes.json")
    recipes_list = read_all_recipes(all_recipes_file)

    keywords_list = read_keywords_file(styles_file)

    # Process each recipe
    for recipe in recipes_list :
        # Handling styles inferring from tags
        if recipe.tags.value is not None :
            styles = find_style_with_keywords(keywords_list, recipe.tags.value)
            recipe.style.value = styles[0] if len(styles) > 0 else "Unknown"
            logger.log(f"Extracted style \"{recipe.style.value}\" for recipe #{recipe.number.value}")


    return 0



if __name__ == "__main__":
    exit(main(sys.argv[1:]))