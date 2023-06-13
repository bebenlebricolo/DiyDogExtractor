import os
from pathlib import Path

def ensure_folder_exist(folder_path : Path) :
    if not folder_path.exists():
        folder_path.mkdir(parents=True)


def list_pages(directory : Path, radical : str, extension : str = ".pdf") -> list[tuple[int, Path]] :
    """List all pages under a directory that match the {radical}{index}{extension} pattern."""
    # All files matching the targeted extension
    file_list = list_files(directory, pattern="page", extension=extension)
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


def list_files(directory : Path, pattern : str = "", extension : str = ".png") -> list[Path] :
    file_list : list[Path] = []
    for (dirpath, _, filenames) in os.walk(directory) :
        for file in filenames :
            if file.endswith(extension) and pattern in file :
                filepath = Path(dirpath).joinpath(file)
                file_list.append(filepath)
    return file_list