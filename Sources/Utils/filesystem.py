import os
from pathlib import Path
from typing import Callable

def ensure_folder_exist(folder_path : Path) :
    if not folder_path.exists():
        folder_path.mkdir(parents=True)

def list_files_with_predicate(directory : Path, predicate, *args) :
    file_list : list[Path] = []
    for (dirpath, _, filenames) in os.walk(directory) :
        for file in filenames :
            filepath = Path(dirpath).joinpath(file)
            if predicate(filepath, *args):
                file_list.append(filepath)
    return file_list

def list_all_files(directory : Path) -> list[Path] :
    file_list : list[Path] = list_files_with_predicate(directory, lambda filepath , args : True, None )
    return file_list

def list_files_by_extension(directory : Path, extension : str ) -> list[Path] :
    def predicate(filepath : Path, extension : str) -> bool :
        return filepath.name.endswith(extension.lstrip('.'))
    file_list : list[Path] = list_files_with_predicate(directory, predicate, extension )
    return file_list

def list_files_pattern(directory : Path, pattern : str = "", extension : str = ".png") -> list[Path] :
    def predicate(filepath : Path, extension : str, pattern : str) -> bool :
        fname = filepath.name
        return pattern in fname and fname.endswith(extension.lstrip('.'))
    file_list : list[Path] = list_files_with_predicate(directory, predicate, extension, pattern)
    return file_list

def list_pages_with_number(directory : Path, extension = ".pdf") -> list[tuple[int, Path]] :
    """List all pages under a directory that match the {radical}{index}{extension} pattern."""
    # All files matching the targeted extension
    radical = "page_"

    file_list = list_files_pattern(directory, pattern=radical, extension=extension)
    page_list : list[tuple[int, Path]] = []

    for file in file_list :
        filename = file.stem
        str_index = filename.lstrip(radical).rstrip(extension)
        index = 0
        try :
            index = int(str_index)
        except :
            continue
        page_list.append((index, file))

    # Sort by indices
    page_list.sort(key=lambda x : x[0])
    return page_list