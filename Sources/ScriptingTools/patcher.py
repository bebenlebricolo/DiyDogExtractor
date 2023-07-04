from pathlib import Path
import shutil
import sys
import argparse
import json

from ..Models import recipe as rcp
from ..Utils.filesystem import list_files_pattern, ensure_folder_exist
from ..Utils.recipe_service import dump_all_recipes_to_disk


def patch_all_recipes(dep_recipes_folder : Path, patch_folder : Path) -> bool:
    ALL_RECIPES_FILENAME = "all_recipes.json"

    # list available patches
    patches = list_files_pattern(patch_folder, "recipe", ".json")

    # Overwrite single recipe.json files and parse them
    if len(patches) == 0 :
        print(f"No patches found in folder {patch_folder}.")
        return False

    print(f"Reading patches from folder : {patch_folder} ...")
    patched_recipes : list[rcp.Recipe] = []
    patched_recipes_indexes : list[int] = []
    for patch in patches :
        patched_recipe = rcp.Recipe()
        with open(patch, 'r') as file :
            patched_recipe.from_json(json.load(file))
            print(f"Deserialized patch #{patched_recipe.number.value} : {patched_recipe.name.value}")
        patched_recipes.append(patched_recipe)
        patched_recipes_indexes.append(patched_recipe.number.value)
    print("Patch deserialization ok")

    all_recipes_file = dep_recipes_folder.joinpath(ALL_RECIPES_FILENAME)
    if not all_recipes_file.exists() :
        print(f"No {ALL_RECIPES_FILENAME} was found in folder {dep_recipes_folder}")
        return True

    print("Reading back previous all_recipes.json file before patching ...")
    all_recipes_parsed : list[rcp.Recipe] = []
    with open(all_recipes_file, 'r') as file :
        json_content = json.load(file)
        for elem in json_content["recipes"] :
            parsed_recipe = rcp.Recipe()
            parsed_recipe.from_json(elem)

            # While parsing, if we happen to have the patched version at hands then
            # use it instead of the parsed version
            if parsed_recipe.number.value in patched_recipes_indexes :
                matching_recipe = next(filter(lambda x : x.number.value == parsed_recipe.number.value, patched_recipes))
                all_recipes_parsed.append(matching_recipe)
            else :
                all_recipes_parsed.append(parsed_recipe)
    print("Parsing ok.")


    # Overwrite all_recipes.json with the newer version
    print("Rewriting all_recipes.json with updated dataset ...")
    dump_all_recipes_to_disk(all_recipes_file, all_recipes_parsed)
    print("Patching done !")

    return True






def main(args) :
    parser = argparse.ArgumentParser()
    parser.add_argument("patch_folder", help="Input patch folder where recipes patch reside.")
    parser.add_argument("dep_recipes_folder", help="Deployed recipes folder where recipes will be patched")
    content = parser.parse_args(args)

    dep_recipes_folder = Path(content.dep_recipes_folder)
    patch_folder = Path(content.patch_folder)
    result = patch_all_recipes(dep_recipes_folder, patch_folder)

    return 0 if result else 1

if __name__ == "__main__" :
    exit(main(sys.argv[1:]))