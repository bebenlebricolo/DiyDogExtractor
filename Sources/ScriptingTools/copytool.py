from pathlib import Path
import shutil
import sys
import argparse
from ..Utils.filesystem import list_files_pattern, ensure_folder_exist

# Simple tool to move data around, useful when developing.

def copy_extracted_silhouettes_to_folder(root_cache_dir : Path, output_dir : Path) :
    file_list = list_files_pattern(root_cache_dir, "extracted_silhouette", extension=".png")

    ensure_folder_exist(output_dir)
    for file in file_list :
        page_name = file.parent.stem
        outfile = output_dir.joinpath(page_name + ".png")
        shutil.copyfile(file, outfile)


def main(args) :
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["silextract"], help="Choose a service to use")
    parser.add_argument("input_folder", help="Input folder for the targeted service")
    parser.add_argument("output_folder", help="Output folder for the targeted service")
    content = parser.parse_args(args)

    command = content.command

    if command == "silextract" :
        copy_extracted_silhouettes_to_folder(Path(content.input_folder), Path(content.output_folder))


if __name__ == "__main__" :
    exit(main(sys.argv[1:]))