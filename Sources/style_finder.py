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


from .Utils.fuzzy_search import fuzzy_search_in_ref, StylesProp, FuzzMode

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
    ratio : float = 0.0
    style : Optional[RefStyle] = None


def compute_string_ratios(tag : str, token : str) -> int :
    ratio = fuzz.token_set_ratio(tag, token)
    return ratio


def read_styles_from_file(styles_ref_file : Path) -> list[RefStyle]:
    ref_styles : list[RefStyle] = []
    with open(styles_ref_file, 'r') as file :
        content = json.load(file)
        for elem in content["styles"] :
            new_style = RefStyle()
            new_style.from_json(elem)
            ref_styles.append(new_style)

    return ref_styles


def read_tags_from_file(tags_file_path : Path) -> list[str] :
    tags_list : list[str] = []
    with open(tags_file_path, 'r') as file :
        content = json.load(file)
        for elem in content["tags"] :
            tags_list.append(elem)

    return tags_list

def fuzzy_search_on_real_styles(styles_ref: list[StylesProp], specimen_str : str, fuzz_mode : FuzzMode = FuzzMode.Ratio) -> Optional[tuple[str, MostProbableHit]]:
    # Perform fuzzy search
    if len(specimen_str) <= 10 :
        return None

    most_probable_hit = fuzzy_search_in_ref(specimen_str, styles_ref)
    pair = (specimen_str, most_probable_hit)
    return None

def read_keywords_file(keywords_file : Path) -> list[str] :
    # Lowercasing all elements from keywords
    keywords : list[str] = []
    with open(keywords_file, "r") as file :
        content = json.load(file)
        for elem in content :
            keywords.append(cast(str, elem).lower())

    return keywords

def find_style_with_keywords(keywords : list[str], tags : list[str]) -> list[str] :
    found_styles : list[str] = []
    for tag in tags :
        lowercased = tag.lower()

        # Check if substring in tag, should be enough
        for kw in keywords :
            if kw in lowercased :
                found_styles.append(tag)
                # First hit already indicates the parsed tag already contains style information
                # So that's enough
                break

    return found_styles

def main(args : list[str]):
    usage_str = "Usage : python -m Sources.style_finder [styles_ref_file] [tags_list_file] [output_directory]"
    parser = argparse.ArgumentParser("Style Finder script", usage=usage_str, description="Tries to infer and match tokens with a known list of reference beer styles.")
    parser.add_argument("styles_ref", help="Input file (known_good_styles.json) where db is stored as json text")
    parser.add_argument("tags_list_file", help="list of tags (string tokens) against which we'll search for existing styles")
    parser.add_argument("keywords_file", help="Diydog known keywords file that'll be used to discriminate styles from random tags.")
    parser.add_argument("output_directory", help="output directory where this script will post its results.")


    commands = parser.parse_args(args)
    styles_ref_file = Path(commands.styles_ref)
    tags_list_file = Path(commands.tags_list_file)
    keywords_file = Path(commands.keywords_file)
    output_directory = Path(commands.output_directory)
    fs.ensure_folder_exist(output_directory)

    logger = Logger(output_directory.joinpath("style_finder_logs.txt"))
    if not styles_ref_file.exists():
        logger.log("/!\\ Input file does not exist, cannot continue with db analysis.")
        return 1

    # This algorithm does not perform as well as expected (...)

    logger.log("Reading tags from file")
    tags_list : list[str] = []
    with open(tags_list_file, 'r') as file :
        content = json.load(file)
        for elem in content["tags"] :
            tags_list.append(elem)

    # Lowercasing all elements from keywords
    keywords = read_keywords_file(keywords_file)
    found_styles = find_style_with_keywords(keywords, tags_list)

    return 0



if __name__ == "__main__":
    exit(main(sys.argv[1:]))