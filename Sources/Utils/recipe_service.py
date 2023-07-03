
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
