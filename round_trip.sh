#!/bin/bash

# This script automates the 4 major steps in
# database extraction / cleanup performed by the tools provided.

if [ -f .venv/bin/activate ]; then
    echo "Activating python virtual environment"
    source .venv/bin/activate
fi

echo "################# Starting up db extraction tool #################"
python -m Sources.dbextractor false true true

echo -e "\n################# Starting up db patching tool #################"
python -m Sources.ScriptingTools.patcher Patches Sources/.cache/deployed/recipes

echo -e "\n################# Starting up db cleanup tool #################"
python -m Sources.dbsanitizer References Sources/.cache/deployed Sources/.cache/dbsanitizer

echo -e "\n################# Copying database #################"
cp Sources/.cache/dbsanitizer/*.json Sources/.cache/deployed/recipes
echo "-> Ok !"

echo -e "\n################# Starting up db analysis tool #################"
python -m Sources.dbanalyser Sources/.cache/deployed/recipes/all_recipes.json Sources/.cache/deployed/dbanalysis

echo -e "\n################# Copying References to deployed #################"
mkdir Sources/.cache/deployed/references
cp References/* Sources/.cache/deployed/references/
echo "-> Ok !"


echo -e "\n################# All steps done ! #################"