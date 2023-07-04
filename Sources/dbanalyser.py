import sys
from pathlib import Path
import argparse
import json
from dataclasses import dataclass, field

from typing import Optional, cast, TypeVar, Generic
from enum import Enum

from .Utils.logger import Logger
from .Utils import filesystem as fs
from .Utils.recipe_service import read_all_recipes
from .Models import recipe as rcp
from .Models.jsonable import Jsonable

class PropKind(Enum):
    Yeast = "yeasts"
    Hop = "hops"
    FoodPairing = "foodPairings"
    Malt = "malts"
    Tag = "tags"
    Style = "styles"

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
            case PropKind.Style :
                return StyleMapping()
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

@dataclass
class StyleMapping(BaseMapping) :
    pass


T = TypeVar("T", HopMapping, YeastMapping, TagMapping, MaltMapping, StyleMapping, FoodPairingMapping)

# Tag is a list of str, so it needs to be there as well.
RP = TypeVar("RP", rcp.Hop, rcp.Malt, rcp.Yeast, str)
def get_targeted_prop_list_from_recipe(recipe : rcp.Recipe, prop_kind : PropKind) -> Optional[list[RP]] :
    target_list : list[RP]
    match prop_kind :
        case PropKind.Hop :
            target_list = recipe.ingredients.value.hops #type:ignore
        case PropKind.Malt :
            target_list = recipe.ingredients.value.malts #type:ignore
        case PropKind.Yeast :
            target_list = recipe.ingredients.value.yeasts #type:ignore
        case PropKind.Tag :
            target_list = recipe.tags.value #type:ignore
        case PropKind.FoodPairing :
            target_list = recipe.food_pairing.value #type:ignore
        case PropKind.Style :
            # Making up a fake list of a single style string to be used in the more general list algorithm
            target_list = [recipe.style.value] #type:ignore
        case _:
            raise Exception("Invalid property !")
    return target_list

def extract_properties(all_recipes : list[rcp.Recipe], prop_kind : PropKind) -> tuple[list[str] , list[T]] :
    props_mapping_list : list[T] = []

    for recipe in all_recipes :
        target_list = get_targeted_prop_list_from_recipe(recipe, prop_kind)

        # Sometimes some elements are None (such as the tags list), skip them
        if target_list is None :
            continue

        for elem in target_list :
            name = ""
            if prop_kind in [PropKind.Style, PropKind.Tag, PropKind.FoodPairing] :
                # Those are single string elements, so they can be appended directly
                name = elem
            elif hasattr(elem, "name") :
                name = elem.name
            else:
                # Don't know how to treat this one
                continue

            # Sometimes getting None properties (like missing styles)
            if not name and prop_kind == PropKind.Style:
                name = "Unknown"

            prop_mapping = [x for x in props_mapping_list if x.name == name]
            if len(prop_mapping) == 0 :
                prop_mapping = BaseMapping.build_derived(prop_kind)
                prop_mapping.name = name
                props_mapping_list.append(prop_mapping) #type:ignore
            else :
                prop_mapping = prop_mapping[0]

            # Add new element in list
            if recipe.number.value not in prop_mapping.found_in_beers :
                prop_mapping.found_in_beers.append(recipe.number.value)

    prop_list = [x.name for x in props_mapping_list]
    prop_list = sorted(prop_list)
    props_mapping_list = sorted(props_mapping_list, key=lambda x : x.name)

    return (prop_list, props_mapping_list)


def dump_dbs(name_list : list[str], content_mapping : list[T], db_basename : str, output_directory : Path) :
    output_names_db_filepath = output_directory.joinpath(f"{db_basename}_db.json")
    output_content_mapping_filepath = output_directory.joinpath(f"{db_basename}_rv_db.json")

    names_db_json = {db_basename : name_list}
    with open(output_names_db_filepath, 'w') as file :
        json.dump(names_db_json, file, indent=4)

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
    (hops_list, hops_mappings) = extract_properties(all_recipes, PropKind.Hop)
    logger.log("-> Ok")

    logger.log("Extracting malts data ...")
    (malts_list, malts_mappings) = extract_properties(all_recipes, PropKind.Malt)
    #(malts_list, malts_mappings) = extract_malts(all_recipes)
    logger.log("-> Ok")

    logger.log("Extracting yeasts data ...")
    (yeasts_list, yeasts_mappings) = extract_properties(all_recipes, PropKind.Yeast)
    #(yeasts_list, yeasts_mappings) = extract_yeasts(all_recipes)
    logger.log("-> Ok")

    logger.log("Extracting tags data ...")
    (tags_list, tags_mappings) = extract_properties(all_recipes, PropKind.Tag)
    #(tags_list, tags_mappings) = extract_tags(all_recipes)
    logger.log("-> Ok")

    logger.log("Extracting food pairing data ...")
    (fps_list, fps_mappings) = extract_properties(all_recipes, PropKind.FoodPairing)
    #(fps_list, fps_mappings) = extract_food_pairing(all_recipes)
    logger.log("-> Ok")

    logger.log("Extracting styles data ...")
    (styles_list, styles_mappings) = extract_properties(all_recipes, PropKind.Style)
    logger.log("-> Ok")

    logger.log("Dumping databases (hops)")
    dump_dbs(hops_list, hops_mappings, "hops", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (malts)")
    dump_dbs(malts_list, malts_mappings, "malts", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (yeasts)")
    dump_dbs(yeasts_list, yeasts_mappings, "yeasts", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (tags)")
    dump_dbs(tags_list, tags_mappings, "tags", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (food pairings)")
    dump_dbs(fps_list, fps_mappings, "foodPairing", output_directory)
    logger.log("-> Ok")

    logger.log("Dumping databases (styles)")
    dump_dbs(styles_list, styles_mappings, "styles", output_directory)
    logger.log("-> Ok")


    return 0



if __name__ == "__main__":
    exit(main(sys.argv[1:]))