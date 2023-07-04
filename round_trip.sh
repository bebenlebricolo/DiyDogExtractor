#!/bin/bash

# This script automates the 4 major steps in
# database extraction / cleanup performed by the tools provided.

source .venv/bin/activate

echo "################# Starting up db extraction tool #################"
python -m Sources.dbextractor false true true

echo -e "\n################# Starting up db patching tool #################"
python -m Sources.ScriptingTools.patcher Patches Sources/.cache/deployed/recipes

echo -e "\n################# Starting up db cleanup tool #################"
python -m Sources.dbsanitizer References Sources/.cache/deployed Sources/.cache/dbsanitizer

echo -e "\n################# Cleaning up deployed database #################"
cp Sources/.cache/dbsanitizer/all_recipes.json Sources/.cache/deployed/recipes/all_recipes.json
echo "-> Ok !"

echo -e "\n################# Starting up db analysis tool #################"
python -m Sources.dbanalyser Sources/.cache/deployed/recipes/all_recipes.json Sources/.cache/deployed/dbanalysis
echo -e "\n################# All steps done ! #################"
