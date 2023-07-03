import sys
from pathlib import Path
import argparse
import json
from dataclasses import dataclass, field

from typing import cast
from enum import Enum

from .Utils.logger import Logger
from .Utils import filesystem as fs
from .Models import recipe as rcp
from .Models.jsonable import Jsonable

class PropKind(Enum):
    Yeast = "yeasts"
    Hop = "hops"
    FoodPairing = "foodPairings"
    Malt = "malts"
    Tag = "tags"

@dataclass
class BaseMapping(Jsonable):
    name : str = ""
    found_in_beers : list[int] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "name" : self.name,
            "foundInBeers" : self.found_in_beers
        }

    def from_json(self, content: dict) -> None:
        self.name = content["name"]
        self.found_in_beers = []
        for elem in content["foundInBeers"] :
            self.found_in_beers.append(elem)

    @staticmethod
    def build_derived(kind : PropKind) :
        match kind :
            case PropKind.Yeast :
                return YeastMapping()
            case PropKind.Hop :
                return HopMapping()
            case PropKind.Malt :
                return MaltMapping()
            case PropKind.FoodPairing :
                return FoodPairingMapping()
            case PropKind.Tag :
                return TagMapping()
            case _:
                raise Exception("Whoops ! Wrong type !")

@dataclass
class HopMapping(BaseMapping) :
    pass

@dataclass
class MaltMapping(BaseMapping) :
    pass

@dataclass
class YeastMapping(BaseMapping) :
    pass

@dataclass
class TagMapping(BaseMapping) :
    pass

@dataclass
class FoodPairingMapping(BaseMapping) :
    pass

def read_all_recipes(input_file : Path) -> list[rcp.Recipe] :
    all_recipes : list[rcp.Recipe] = []
    with open(input_file, 'r') as file :
        content = json.load(file)
        for recipe in content["recipes"] :
            new_recipe = rcp.Recipe()
            new_recipe.from_json(recipe)
            all_recipes.append(new_recipe)

    return all_recipes

def extract_hops(all_recipes : list[rcp.Recipe]) -> tuple[list[str], list[HopMapping]] :
    hops_list : list[str] = [] # List of hops, ordered by name
    hops_mapping_list : list[HopMapping] = []
    for recipe in all_recipes :
        for hop in recipe.ingredients.value.hops :
            if not hop.name in hops_list :
                hops_list.append(hop.name)
                hops_mapping_list.append(HopMapping(hop.name, [recipe.number.value]))
            else:
                # Find the mapped hop
                hop_mapping = [x for x in hops_mapping_list if x.name == hop.name][0]
                if recipe.number.value not in hop_mapping.found_in_beers :
                    hop_mapping.found_in_beers.append(recipe.number.value)

    return (hops_list, hops_mapping_list)

def extract_malts(all_recipes : list[rcp.Recipe]) -> tuple[list[str], list[MaltMapping]] :
    malts_list : list[str] = [] # List of malts, ordered by name
    malts_mapping_list : list[MaltMapping] = []
    for recipe in all_recipes :
        for malt in recipe.ingredients.value.malts :
            if not malt.name in malts_list :
                malts_list.append(malt.name)
                malts_mapping_list.append(MaltMapping(malt.name, [recipe.number.value]))
            else:
                # Find the mapped hop
                malt_mapping = [x for x in malts_mapping_list if x.name == malt.name][0]
                if recipe.number.value not in malt_mapping.found_in_beers :
                    malt_mapping.found_in_beers.append(recipe.number.value)

    return (malts_list, malts_mapping_list)

def extract_yeasts(all_recipes : list[rcp.Recipe]) -> tuple[list[str], list[YeastMapping]] :
    yeasts_list : list[str] = [] # List of yeasts, ordered by name
    yeasts_mapping_list : list[YeastMapping] = []
    for recipe in all_recipes :
        for yeast in recipe.ingredients.value.yeasts :
            if not yeast.name in yeasts_list :
                yeasts_list.append(yeast.name)
                yeasts_mapping_list.append(YeastMapping(yeast.name, [recipe.number.value]))
            else:
                # Find the mapped yeast
                yeast_mapping = [x for x in yeasts_mapping_list if x.name == yeast.name][0]
                if recipe.number.value not in yeast_mapping.found_in_beers :
                    yeast_mapping.found_in_beers.append(recipe.number.value)

    return (yeasts_list, yeasts_mapping_list)

def extract_tags(all_recipes : list[rcp.Recipe]) -> tuple[list[str], list[TagMapping]] :
    tags_list : list[str] = [] # List of tags, ordered by name
    tags_mapping_list : list[TagMapping] = []
    for recipe in all_recipes :
        if recipe.tags.value is None :
            continue
        for tag in recipe.tags.value :
            if not tag in tags_list :
                tags_list.append(tag)
                tags_mapping_list.append(TagMapping(tag, [recipe.number.value]))
            else:
                # Find the mapped tag
                tag_mapping = [x for x in tags_mapping_list if x.name == tag][0]
                if recipe.number.value not in tag_mapping.found_in_beers :
                    tag_mapping.found_in_beers.append(recipe.number.value)

    return (tags_list, tags_mapping_list)

def extract_food_pairing(all_recipes : list[rcp.Recipe]) -> tuple[list[str], list[FoodPairingMapping]] :
    fps_list : list[str] = [] # List of food pairings, ordered by name
    fps_mapping_list : list[FoodPairingMapping] = []
    for recipe in all_recipes :
        if recipe.food_pairing.value is None :
            continue
        for fp in recipe.food_pairing.value :
            if not fp in fps_list :
                fps_list.append(fp)
                fps_mapping_list.append(FoodPairingMapping(fp, [recipe.number.value]))
            else:
                # Find the mapped fp
                fp_mapping = [x for x in fps_mapping_list if x.name == fp][0]
                if recipe.number.value not in fp_mapping.found_in_beers :
                    fp_mapping.found_in_beers.append(recipe.number.value)

    return (fps_list, fps_mapping_list)


def dump_dbs(name_list : list[str], content_mapping : list[BaseMapping], db_basename : str, output_directory : Path) :
    output_names_db_filepath = output_directory.joinpath(f"{db_basename}_db.json")
    output_content_mapping_filepath = output_directory.joinpath(f"{db_basename}_rv_db.json")

    names_db_json = {db_basename : name_list}
    with open(output_names_db_filepath, 'w') as file :
        json.dump(names_db_json, file, indent=4)

    # Sorted names db as well, for debugging purposes
    output_names_sorted_db_filepath = output_directory.joinpath(f"{db_basename}_sorted_db.json")
    sorted_names_db = {db_basename: sorted(name_list)}
    with open(output_names_sorted_db_filepath, 'w') as file :
        json.dump(sorted_names_db, file, indent=4)


    content_rv_db_json = {db_basename : [x.to_json() for x in content_mapping]}
    with open(output_content_mapping_filepath, 'w') as file :
        json.dump({db_basename : content_rv_db_json}, file, indent=4)

def main(args : list[str]):
    usage_str = "Usage : python -m Sources.dbanalyser [input_file] [output_file]"
    parser = argparse.ArgumentParser("DB Analyser", usage=usage_str, description="Analyses an existing extracted database and produces reversed indexed db by properties.")
    parser.add_argument("input_file", help="Input file (all_recipes.json) where db is stored as json text")
    parser.add_argument("output_directory", help="Output directory where analyzed reversed db will be written")


    commands = parser.parse_args(args)
    input_file = Path(commands.input_file)
    output_directory = Path(commands.output_directory)
    fs.ensure_folder_exist(output_directory)

    logger = Logger(output_directory.joinpath("dbanalyser_logs.txt"))
    if not input_file.exists():
        logger.log("/!\\ Input file does not exist, cannot continue with db analysis.")
        return 1

    logger.log("Reading all recipes from file ...")
    all_recipes = read_all_recipes(input_file)

    logger.log("Extracting hops data ...")
    (hops_list, hops_mappings) = extract_hops(all_recipes)
    logger.log("-> Ok")

    logger.log("Extracting malts data ...")
    (malts_list, malts_mappings) = extract_malts(all_recipes)
    logger.log("-> Ok")

    logger.log("Extracting yeasts data ...")
    (yeasts_list, yeasts_mappings) = extract_yeasts(all_recipes)
    logger.log("-> Ok")

    logger.log("Extracting tags data ...")
    (tags_list, tags_mappings) = extract_tags(all_recipes)
    logger.log("-> Ok")

    logger.log("Extracting food pairing data ...")
    (fps_list, fps_mappings) = extract_food_pairing(all_recipes)
    logger.log("-> Ok")

    logger.log("Dumping databases (hops)")
    dump_dbs(hops_list, cast(list[BaseMapping], hops_mappings), "hops", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (malts)")
    dump_dbs(malts_list, cast(list[BaseMapping], malts_mappings), "malts", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (yeasts)")
    dump_dbs(yeasts_list, cast(list[BaseMapping], yeasts_mappings), "yeasts", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (tags)")
    dump_dbs(tags_list, cast(list[BaseMapping], tags_mappings), "tags", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (food pairings)")
    dump_dbs(fps_list, cast(list[BaseMapping], fps_mappings), "foodPairing", output_directory)
    logger.log("-> Ok")

    return 0



if __name__ == "__main__":
    exit(main(sys.argv[1:]))