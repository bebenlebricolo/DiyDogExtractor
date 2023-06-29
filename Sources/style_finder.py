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

def read_styles_from_file(styles_ref_file : Path) -> list[RefStyle]:
    ref_styles : list[RefStyle] = []
    with open(styles_ref_file, 'r') as file :
        content = json.load(file)
        for elem in content["styles"] :
            new_style = RefStyle()
            new_style.from_json(elem)
            ref_styles.append(new_style)

    return ref_styles


def fuzzy_search_on_real_styles(styles_ref_file : Path, tags_list_file : Path, output_directory : Path, logger: Logger):
    logger.log("Reading styles from reference file")
    ref_styles = read_styles_from_file(styles_ref_file)

    logger.log("Reading tags from file")
    tags_list : list[str] = []
    with open(tags_list_file, 'r') as file :
        content = json.load(file)
        for elem in content["tags"] :
            tags_list.append(elem)

    # Perform fuzzy search
    tags_inferred_style_map : list[tuple[str, MostProbableHit]] = []
    rejected_tags : list[tuple[str, MostProbableHit]] = []
    for tag in tags_list :
        if len(tag) <= 10 :
            # Skip small tags and numbers-only
            continue
        most_probable_hit = fuzzy_search_in_ref(tag, ref_styles)
        pair = (tag, most_probable_hit)
        if most_probable_hit.distance >= (len(tag) / 2) :
            tags_inferred_style_map.append(pair)
        else :
            rejected_tags.append(pair)

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
    # fuzzy_search_on_real_styles(styles_ref_file , tags_list_file , output_directory , logger)

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