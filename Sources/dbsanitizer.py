import sys
from pathlib import Path
import argparse
import json
from dataclasses import dataclass, field
from enum import Enum

from typing import cast, Optional, Generic, TypeVar
from thefuzz import fuzz

from .Utils.logger import Logger
from .Utils import filesystem as fs
from .Utils.recipe_service import dump_all_recipes_to_disk, dump_individual_recipes_files_to_disk
from .Models import recipe as rcp
from .Models.jsonable import Jsonable, JsonOptionalProperty, JsonProperty
from .style_finder import read_keywords_file, find_style_with_keywords, read_styles_from_file
from .dbanalyser import read_all_recipes
from .Models.DBSanizer.known_good_props import *
from .Utils.fuzzy_search import fuzzy_search_prop, MostProbablePropertyHit, FuzzMode

def infer_style_from_name(recipe : rcp.Recipe, styles_reflist : list[StylesProp]) -> None :
    most_probable_hit = fuzzy_search_prop(styles_reflist, recipe.name.value, FuzzMode.PartialRatio)
    if most_probable_hit and most_probable_hit[1].hit and most_probable_hit[1].score >= 80:
        recipe.style.value = most_probable_hit[1].hit.name.value
    else :
        recipe.style.value = None

def infer_style_from_tags_fuzzy_search(recipe : rcp.Recipe, styles_reflist : list[StylesProp]) -> None :
    if recipe.tags.value is None :
        return

    # Try with the fuzzy search approach
    tags_hits_map : list[tuple[str, MostProbablePropertyHit]] = []
    for tag in recipe.tags.value :
        most_probable_hit_pair  = fuzzy_search_prop(styles_reflist, tag, FuzzMode.Ratio)
        if not most_probable_hit_pair :
            continue
        tags_hits_map.append(most_probable_hit_pair)

    # We are really out of luck !
    if len(tags_hits_map) == 0 :
        return

    sorted_map = sorted(tags_hits_map, key=lambda x: x[1].score)
    most_probable_hit : MostProbablePropertyHit[StylesProp] = sorted_map[-1][1]

    # Assign max style now
    if most_probable_hit.score >= 60 and most_probable_hit.hit:
        recipe.style.value = most_probable_hit.hit.name.value
    else :
        recipe.style.value = None


def infer_style_for_recipe(recipes_list : list[rcp.Recipe], keywords_list : list[str], styles_reflist : list[StylesProp], logger : Logger) -> None :
    for recipe in recipes_list :
        # Handling styles inferring from tags
        if recipe.tags.value is not None :
            # Adding beer's name and its subtitle, sometimes names carry more data than tags themselves, regarding beer style (...)
            styles = find_style_with_keywords(keywords_list, recipe.tags.value)
            if len(styles) != 0 :
                recipe.style.value = styles[0] if styles[0] else "Unknown"

        # Fall back on name validation, fuzzy search mode
        if recipe.style.value is None or recipe.style.value == "Unknown" :
            logger.log("   /!\\ Could not retrieve style from tags with keywords only : Fuzzy searching style with recipe's name ...")
            infer_style_from_name(recipe, styles_reflist)

        # Then if the style is still not found, try to go for the tags fuzzy search as a last chance fallback mode
        if recipe.style.value is None or recipe.style.value == "Unknown" :
            logger.log("   /!\\ Could not retrieve style from name nor keyworded tags : Fuzzy searching style with recipe's tags as a last chance test ...")
            infer_style_from_tags_fuzzy_search(recipe, styles_reflist)

        if recipe.style.value is None or recipe.style.value == "Unknown":
            logger.log(f"   /!\\ Could not retrieve style for recipe #{recipe.number.value} : {recipe.name.value}")
            recipe.style.value = "Unknown"

        logger.log(f"Extracted style \"{recipe.style.value}\" for recipe #{recipe.number.value} : {recipe.name.value}")

def merge_yeasts(recipes_list : list[rcp.Recipe], yeasts_ref : list[YeastProp], logger : Logger) -> None :
    for recipe in recipes_list :
        for rcp_yeast in recipe.ingredients.value.yeasts :
            returned_pair = fuzzy_search_prop(yeasts_ref, rcp_yeast.name)
            if not returned_pair :
                continue

            most_probable_hit = returned_pair[1]
            # Swap yeast name by the one we've found
            if most_probable_hit  is not None and most_probable_hit.score >= 23 and most_probable_hit.hit:
                rcp_yeast.name = most_probable_hit.hit.name.value
                logger.log(f"Yeast swap : recipe #{recipe.number.value} : {recipe.name.value}")
                logger.log(f"   -> Swapping original yeast name \"{returned_pair[0]}\" for known good \"{rcp_yeast.name}\"")

def value_in_list_case_insensitive(value : str, input_list : list[str]) -> bool :
    for elem in input_list :
        if elem.lower() == value.lower() :
            return True
    return False

def merge_malts(recipes_list : list[rcp.Recipe], malts_ref : list[MaltProp], known_malt_extras : list[str], logger : Logger) -> None :
    for recipe in recipes_list :
        malts_to_convert_in_extra : list[rcp.Malt] = []
        for malt in recipe.ingredients.value.malts :

            # Search for known in advance malt extras
            if value_in_list_case_insensitive(malt.name, known_malt_extras) :
                logger.log(f"Found probable \"Extra\" mash ingredient : {malt.name}")
                malts_to_convert_in_extra.append(malt)
                continue

            returned_pair = fuzzy_search_prop(malts_ref, malt.name)
            most_probable_hit = returned_pair[1]

            # Swap malt name
            if most_probable_hit  is not None and most_probable_hit.hit:
                if most_probable_hit.score >= 23 :
                    malt.name = most_probable_hit.hit.name.value
                    logger.log(f"Malt swap : recipe #{recipe.number.value} : {recipe.name.value}")
                    logger.log(f"   -> Swapping original malt name \"{returned_pair[0]}\" for known good \"{malt.name}\"")

                # Probably an extra ingredient added during the mash (sometimes they are mixed up in DiyDog's recipes)
                else :
                    logger.log(f"Found probable \"Extra\" mash ingredient : {malt.name}")
                    malts_to_convert_in_extra.append(malt)

        # Time to convert malts to extra mash ingredients
        if len(malts_to_convert_in_extra) != 0 :
            logger.log(f"Converting malts to extra mash ingredients for recipe #{recipe.number.value} : {recipe.name.value}")
            for malt in malts_to_convert_in_extra :
                logger.log(f"Converting {malt.name} into mash ingredient")
                new_mash = rcp.ExtraMash()
                new_mash.from_malt(malt)
                recipe.ingredients.value.add_extra_mash(new_mash)
                recipe.ingredients.value.remove_malt(malt)

def merge_hops(recipes_list : list[rcp.Recipe], hops_ref : list[HopProp], known_hop_extras : list[str], logger : Logger) -> None :
    for recipe in recipes_list :
        hops_to_convert_in_extra : list[rcp.Hop] = []
        for hop in recipe.ingredients.value.hops :

            # Search for known in advance malt extras
            if value_in_list_case_insensitive(hop.name, known_hop_extras) :
                logger.log(f"Found probable \"Extra\" boil ingredient : {hop.name}")
                hops_to_convert_in_extra.append(hop)
                continue

            returned_pair = fuzzy_search_prop(hops_ref, hop.name)
            most_probable_hit = returned_pair[1]

            # Swap hop name
            if most_probable_hit  is not None and most_probable_hit.hit:
                if most_probable_hit.score >= 23 :
                    hop.name = most_probable_hit.hit.name.value
                    logger.log(f"Hop swap : recipe #{recipe.number.value} : {recipe.name.value}")
                    logger.log(f"   -> Swapping original hop name \"{returned_pair[0]}\" for known good \"{hop.name}\"")

                # Probably an extra ingredient added during the boil (sometimes they are mixed up in DiyDog's recipes)
                else :
                    logger.log(f"Found probable \"Extra\" boil ingredient : {hop.name}")
                    hops_to_convert_in_extra.append(hop)

        # Time to convert malts to extra mash ingredients
        if len(hops_to_convert_in_extra) != 0 :
            logger.log(f"Converting hops to extra boil/fermentation ingredients for recipe #{recipe.number.value} : {recipe.name.value}")
            for hop in hops_to_convert_in_extra :
                logger.log(f"Converting {hop.name} into boil (hot side) / fermentation (cold side) ingredient")
                new_boil = rcp.ExtraBoil()
                new_boil.from_hop(hop)
                recipe.ingredients.value.add_extra_boil(new_boil)
                recipe.ingredients.value.remove_hop(hop)

def read_known_good_yeasts_from_file(yeast_filepath : Path) -> list[YeastProp]:
    built_list = read_known_good_prop_from_file(yeast_filepath, PropKind.Yeast)
    cast(list[YeastProp] , built_list)
    return built_list

def read_known_good_malts_from_file(malts_filepath : Path) -> list[MaltProp]:
    built_list = read_known_good_prop_from_file(malts_filepath, PropKind.Malt)
    cast(list[MaltProp] , built_list)
    return built_list


def read_known_good_hops_from_file(hops_filepath : Path) -> list[HopProp]:
    built_list = read_known_good_prop_from_file(hops_filepath, PropKind.Hop)
    cast(list[HopProp] , built_list)
    return built_list

def read_known_good_styles_from_file(styles_filepath : Path) -> list[StylesProp]:
    built_list = read_known_good_prop_from_file(styles_filepath, PropKind.Styles)
    cast(list[StylesProp] , built_list)
    return built_list


T = TypeVar("T", YeastProp, HopProp, MaltProp, StylesProp)
def read_known_good_prop_from_file(filepath : Path, prop_kind : PropKind) -> list[T]:
    out_list : list[T] = []
    with open(filepath, 'r') as file :
        content = json.load(file)
        for prop in content[prop_kind.value] :
            new_prop = BaseProperty.build_derived(prop_kind)
            new_prop.from_json(prop)
            out_list.append(new_prop) #type:ignore
    return out_list


def read_extras_from_file(filepath : Path) -> tuple[list[str], list[str]] :
    """Extracts extra elements from json file. Returns a tuple (mash elements, boil elements)"""
    mash_extras : list[str] = []
    boil_extras : list[str] = []
    with open(filepath, 'r') as file :
        content = json.load(file)
        for elem in content["mash"] :
            mash_extras.append(elem)
        for elem in content["boil"] :
            boil_extras.append(elem)
    return (mash_extras, boil_extras)

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
    styles_ref_file = ref_dir.joinpath("known_good_styles.json")
    known_extras_file = ref_dir.joinpath("known_diydog_extras.json")
    hops_file = ref_dir.joinpath("known_good_hops.json")
    malts_file = ref_dir.joinpath("known_good_malts.json")
    yeasts_file = ref_dir.joinpath("known_good_yeasts.json")


    logger.log("Reading all recipes from disk")
    recipes_list : list[rcp.Recipe] = []
    all_recipes_file = deployed_recipes_dir.joinpath("recipes/all_recipes.json")
    recipes_list = read_all_recipes(all_recipes_file)

    keywords_list = read_keywords_file(styles_file)
    (mash_extras, boil_extras) = read_extras_from_file(known_extras_file)

    # Try to infer the right style for each beer
    logger.log("Inferring styles for all recipes ...")
    refstyle_list = read_known_good_styles_from_file(styles_ref_file)
    infer_style_for_recipe(recipes_list, keywords_list, refstyle_list, logger)
    logger.log("Styles inferring OK!\n\n")

    # Try to cleanup yeasts for each recipe
    logger.log("Merging yeasts to known-good yeasts...")
    yeasts_ref_list = read_known_good_yeasts_from_file(yeasts_file)
    merge_yeasts(recipes_list, yeasts_ref_list, logger)
    logger.log("Yeast merging OK!\n\n")

    # Try to cleanup malts
    logger.log("Merging malts to known good ones ...")
    malts_ref_list = read_known_good_malts_from_file(malts_file)
    merge_malts(recipes_list, malts_ref_list, mash_extras, logger)
    logger.log("Malt merging OK!\n\n")

    # Try to cleanup hops
    logger.log("Merging hops to known good ones ...")
    hops_ref_list = read_known_good_hops_from_file(hops_file)
    merge_hops(recipes_list, hops_ref_list, boil_extras, logger)
    logger.log("Hops merging OK!\n\n")

    logger.log("Dumping cleaned up all_recipes.json to disk !")
    all_recipes_filepath = output_directory.joinpath("all_recipes.json")
    dump_all_recipes_to_disk(all_recipes_filepath, recipes_list)
    logger.log("Done !\n\n")

    # Dumping individual files as well, as they are used to speed up IO accesses in
    # The backend later on. And they don't take that much space (1 more MB) compared to images/Pdf pages altogether (~290MB)
    logger.log("Dumping cleaned up recipes individual files to disk !")
    dump_individual_recipes_files_to_disk(output_directory, recipes_list)
    logger.log("Done !")


    logger.log("Database sanitation Done !")

    return 0




if __name__ == "__main__":
    exit(main(sys.argv[1:]))