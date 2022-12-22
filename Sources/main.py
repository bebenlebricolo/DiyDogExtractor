#!/usr/bin/python

import sys
import os
import requests
import json
from pathlib import Path
import PyPDF2
from PyPDF2 import PageObject, PdfFileWriter

from dataclasses import dataclass, field
from copy import copy
import struct
import pickle
from io import BufferedReader
from typing import Optional

C_DIYDOG_URL = "https://brewdogmedia.s3.eu-west-2.amazonaws.com/docs/2019+DIY+DOG+-+V8.pdf"

def download_pdf(url : str, output_file : Path) -> None:
    response = requests.get(url)
    match(response.status_code) :
        case 200 :
            pass
        case _ :
            print("Could not download pdf file, error code was : {}".format(response.status_code))
            return

    # Create output directory if it does not exist yet
    if not output_file.parent.exists() :
        output_file.parent.mkdir(parents=True)

    # Dump pdf to file
    with open(output_file, "wb") as file :
        file.write(response.content)


# Useful doc : https://pypdf2.readthedocs.io/en/latest/user/extract-text.html

class Jsonable :
    def _read_prop(self, key : str, content : dict, default) :
        if key in content :
            return content[key]
        return default

    def to_json(self) -> dict :
        pass

    def from_json(self, content) -> None :
        pass


@dataclass
class TextBlock(Jsonable) :
    text : str = ""
    transformation_matrix = None
    current_matrix = None
    x : float = 0.0
    y : float = 0.0

    def to_bytes(self) -> bytes :
        struct.pack()
        return pickle.dumps(self)

    def to_json(self) -> dict :
        return {
            "text" : self.text,
            "tm" : self.transformation_matrix,
            "cm" : self.current_matrix,
            "x" : self.x,
            "y" : self.y
        }

    def from_json(self, content : dict) -> None :
        self.text = self._read_prop("text", content, "")
        self.transformation_matrix = self._read_prop("tm", content, [0,0,0,0,0,0])
        self.current_matrix = self._read_prop("cm", content, [0,0,0,0,0,0])
        self.x = self._read_prop("x", content, 0.0)
        self.y = self._read_prop("y", content, 0.0)

    def from_buffer(self, buffer : BufferedReader) :
        self = pickle.load(buffers=buffer)

@dataclass
class PageBlocks(Jsonable) :
    blocks : list[TextBlock] = field(default_factory=list)
    index : int = 0

    def reset(self) :
        self.__init__()

    def to_json(self) -> dict:
        blocks_list = []
        for block  in self.blocks :
            blocks_list.append(block.to_json())
        return {
            "index" : self.index,
            "blocks" : blocks_list
        }

    def from_json(self, content) -> None:
        self.blocks.clear()
        self.index = self._read_prop("index", content, 0)
        if "blocks" in content :
            for block in content["blocks"] :
                new_block = TextBlock()
                new_block.from_json(block)
                self.blocks.append(new_block)


    def get_last_block(self) -> Optional[TextBlock] :
        if len(self.blocks) != 0 :
            return self.blocks[len(self.blocks) - 1]
        return None

all_blocks : list[PageBlocks] = []
page_blocks : PageBlocks = PageBlocks()

def text_block_from_page(text : str, cm, tm, font_dict, font_size) :
    text = text.strip().rstrip("\n")
    if text == "" or text == " " :
        return
    block = TextBlock()
    block.text = text
    block.current_matrix = cm
    block.transformation_matrix = tm
    block.x = tm[4]
    block.y = tm[5]
    page_blocks.blocks.append(block)


def cache_all_blocks(directory : Path, block_list : list[PageBlocks]) :
    if not directory.exists() :
        directory.mkdir(parents=True)

    for blocks in block_list :
        filepath = directory.joinpath("block_{}.bin".format(blocks.index))
        cache_page_blocks(filepath, blocks)



def cache_page_blocks(filepath : Path, page : PageBlocks ) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    # with open(filepath, "wb") as file :
    #     for block in page.blocks :
    #         pickle.dump(block, file)

    with open(filepath, "w") as file :
        json.dump(page.to_json(), file, indent=4)


def cache_single_pdf_page(filepath : Path, page : PageObject ) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    pdf_writer = PdfFileWriter()
    pdf_writer.add_page(page)
    with open(filepath, "wb") as file :
        pdf_writer.write(file)

def retrieve_single_page_from_cache(filepath : Path) -> list[TextBlock] :
    blocks : list[TextBlock] = []
    with open(filepath, "rb") as file :
        length = file.read(sys.getsizeof(int))
        for i in range(length) :
            block = TextBlock()
            block.from_buffer(buffer=file)
            blocks.append(block)

def list_pages(directory : Path, radical : str, extension : str = ".pdf") -> list :
    pages_list : list[tuple[int, Path]] = []
    for (dirpath, _, filenames) in os.walk(directory) :
        for file in filenames :
            if file.endswith(extension) :
                filepath = Path(dirpath).joinpath(file)
                index = int(file.lstrip(radical).rstrip(extension))
                pages_list.append((index, filepath))
    # Sort by indices
    pages_list.sort(key=lambda x : x[0])
    return pages_list



def main() :
    force_caching = False

    this_dir = Path(__file__).parent
    cache_directory = this_dir.joinpath(".cache")
    cached_pages_dir = cache_directory.joinpath("pages")
    cached_blocks_dir = cache_directory.joinpath("blocks")

    pdf_file = cache_directory.joinpath("diydog-2022.pdf")
    if not pdf_file.exists() :
        print("Downloading brewdog's Diydog pdf booklet ...")
        download_pdf(C_DIYDOG_URL, pdf_file)
        print("-> OK : Downloading succeeded ! Pdf file was downloaded at : {}".format(pdf_file))
        # Triggers force caching because we need to regenerate everything
        force_caching = True

    # Extract pages for caching purposes
    if force_caching :
        print("Extracting all beer pages to {}".format(cached_pages_dir))
        with open(pdf_file, "rb") as file :
            reader = PyPDF2.PdfFileReader(file)
            # Page 22 is the first beer
            start_page = 21

            # Page 436 is the very last beer
            end_page = 436

            for i in range(start_page, end_page) :
                print("Extracting page : {}".format(i))
                page = reader.getPage(i)
                print("Caching page to disk")
                cache_single_pdf_page(cached_pages_dir.joinpath("page_{}.pdf".format(i)), page=page)
        print("-> OK : Pages extracted successfully in {}".format(cached_pages_dir))

    # List already cached pages
    print("Listing available pdf pages ...")
    pages_list = list_pages(cached_pages_dir, "page_", ".pdf")
    print("-> OK : Found {} pages in {}".format(len(pages_list), cached_pages_dir))

    blocks_list : list[tuple[int, Path]] = []
    if cached_blocks_dir.exists() :
        blocks_list = list_pages(cached_blocks_dir, "blocks_", ".json")
    else :
        cached_blocks_dir.mkdir(parents=True)

    # Recache pages in case length differ
    if len(blocks_list) != len(pages_list) :
        # Skip caching pages
        for page in pages_list :
            print("Analysing page {}".format(page[0]))
            with open(page[1], "rb") as file :
                reader = PyPDF2.PdfFileReader(file)
                parsed = reader.getPage(0)
                page_blocks.index = page[0]

                text = parsed.extract_text(visitor_text=text_block_from_page)
                last_block = page_blocks.get_last_block()
                all_blocks.append(copy(page_blocks))

                print("Caching page and contents ...")
                cache_page_blocks(cached_blocks_dir.joinpath("blocks_{}.json".format(page_blocks.index)), page_blocks)
                print("-> OK : Successfully cached page text blocks.")

                page_blocks.reset()


            print("Done parsing content")
    else :
        # Read back pages
        print("Loading back cached data from disk")
        all_blocks.clear()
        for block in blocks_list :
            blocks = PageBlocks()
            print("Loading {} from disk ...".format(block[1].name))
            with open(block[1], "r") as file :
                blocks.from_json(json.load(file))
            all_blocks.append(blocks)

    print("Done !")

if __name__ == "__main__" :
    try :
        main()
    except Exception as e :
        print("-> ERROR : Caught exception while running script, error was  : {}".format(e))