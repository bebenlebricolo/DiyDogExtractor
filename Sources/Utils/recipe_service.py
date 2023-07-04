
import json
from pathlib import Path

# Local utils imports
from ..Models.recipe import Recipe

def dump_all_recipes_to_disk(output_file : Path, all_recipes:  list[Recipe]) :
    json_data = []
    for recipe in all_recipes :
        json_data.append(recipe.to_json())
    with open(output_file, "w") as file :
        json.dump({"recipes" : json_data}, file, indent=4)

def read_all_recipes(input_file : Path) -> list[Recipe] :
    all_recipes : list[Recipe] = []
    with open(input_file, 'r') as file :
        content = json.load(file)
        for recipe in content["recipes"] :
            new_recipe = Recipe()
            new_recipe.from_json(recipe)
            all_recipes.append(new_recipe)

    return all_recipes