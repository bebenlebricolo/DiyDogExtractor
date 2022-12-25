#!/usr/bin/python

import sys
import os
import re
import requests
import json
from pathlib import Path
import PyPDF2
from PyPDF2 import PageObject, PdfFileWriter
from dataclasses import dataclass, field
from copy import copy
import struct
import pickle
from typing import Optional


import io
from io import BufferedReader

from PIL import Image

from parsing import parse_line

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
class Coordinates(Jsonable) :
    x : float = 0.0
    y : float = 0.0

    def to_json(self) -> dict:
        return {
            "x" : self.x,
            "y" : self.y
        }

    def from_json(self, content) -> None:
        self.x = self._read_prop("x", content, 0.0)
        self.y = self._read_prop("y", content, 0.0)

@dataclass
class TextBlock(Coordinates) :
    text : str = ""
    transformation_matrix = None
    current_matrix = None

    def to_bytes(self) -> bytes :
        struct.pack()
        return pickle.dumps(self)

    def to_json(self) -> dict :
        parent_dict = super().to_json()
        parent_dict.update({
            "text" : self.text,
            "tm" : self.transformation_matrix,
            "cm" : self.current_matrix,
            }
        )
        return parent_dict

    def from_json(self, content : dict) -> None :
        super().from_json(content)
        self.text = self._read_prop("text", content, "")
        self.transformation_matrix = self._read_prop("tm", content, [0,0,0,0,0,0])
        self.current_matrix = self._read_prop("cm", content, [0,0,0,0,0,0])

    def from_buffer(self, buffer : BufferedReader) :
        self = pickle.load(buffers=buffer)

@dataclass
class TextElement(Coordinates) :
    text : str = ""

    def to_json(self) -> dict:
        parent_dict = super().to_json()
        parent_dict.update({
            "text" : self.text
        })
        return parent_dict

    def from_json(self, content) -> None:
        super().from_json(content)
        self.text = self._read_prop("text", content, "")

@dataclass
class PageBlocks(Jsonable) :
    blocks : list[TextElement] = field(default_factory=list)
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

def cache_pdf_contents(filepath : Path, page : PageObject) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    contents = page.get_contents()
    raw_data : bytes = contents.get_data()
    str_contents = raw_data.decode()
    with open(filepath, "w") as file :
        file.writelines(str_contents)


def cache_images(directory : Path, page : PageObject) :
    if not directory.exists() :
        directory.mkdir(parents=True)

    try :
        for image in page.images:
            image_name = Path(image.name).stem
            image_path = directory.joinpath(image_name + ".png")
            try :
                decoded = Image.open(io.BytesIO(image.data)).convert(mode="RGBA")
                decoded.save(image_path, format="PNG")

            except Exception as e :
                print("Caught error while caching images for page {}".format(directory.name))
                print(e)
                continue

    # Sometimes we can't even list the images because of some weird errors ealier in the pdf parsing methods
    except Exception as e :
        print("Caught error while caching images for page {}".format(directory.name))
        print(e)

def retrieve_single_page_from_cache(filepath : Path) -> list[TextBlock] :
    blocks : list[TextBlock] = []
    with open(filepath, "rb") as file :
        length = file.read(sys.getsizeof(int))
        for i in range(length) :
            block = TextBlock()
            block.from_buffer(buffer=file)
            blocks.append(block)

def list_pages(directory : Path, radical : str, extension : str = ".pdf") -> list[tuple[int, Path]] :
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


def extract_raw_text_blocks_from_content(contents : str) -> list[list[str]] :
    """Extracts text blocks (raw) from input text contents. This essentially uses the BT ET parts and splits blocks based on this"""
    text_block_parsing = False
    out : list[list[str]] = []
    current : list[str] = []
    for line in contents.split("\n") :
        if text_block_parsing :
            if line == "ET" :
                # Finishing parsing this block
                text_block_parsing = False
                out.append(current)
                current = []
            else :
                current.append(line)

        # Look for starting patterns
        else :
            if line == "BT" :
                text_block_parsing = True

    return out

def text_blocks_from_raw_blocks(raw_blocks : list[list[str]]) -> list[TextElement] :
    out : list[TextElement] = []
    #pattern = r"[\[]?\(([a-zA-Z 0-9#,%\.]*)\)[\]]?"

    # This regular expression is used to match constructs like these ones :
    #  (HOPS)Tj
    #  [( Ad)-18 (d)]TJ
    #  [(A)47 (ttribut)18 (e)]TJ
    #
    current_coords = Coordinates()
    for blocks in raw_blocks :
        for line in blocks :

            if line.find("TJ") != -1 or line.find("Tj") != -1 :
                new_element = TextElement()
                parsed_line = parse_line(line)
                new_element.text = parsed_line.rstrip()
                new_element.x = current_coords.x
                new_element.y = current_coords.y
                out.append(new_element)

            elif line.find("Tm") != -1:
                tokens = line.split()
                tm_index = tokens.index("Tm")
                current_coords.x = round(float(tokens[tm_index - 2]), 4)
                current_coords.y = round(float(tokens[tm_index - 1]), 4)

            elif line.find("Td") != -1 or line.find("TD") != -1:
                tokens = line.split()
                td_index = tokens.index("Td")
                if td_index == -1 :
                    td_index = tokens.index("TD")

                current_coords.x += round(float(tokens[td_index - 2]), 4)
                current_coords.y += round(float(tokens[td_index - 1]), 4)

    return out


def cache_custom_blocks(filepath : Path, text_blocks : list[TextElement]) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    with open(filepath, "w") as file :
        data = []
        for block in text_blocks :
            data.append(block.to_json())
        json.dump(data, file, indent=4)


def main() :
    force_caching = False

    this_dir = Path(__file__).parent
    cache_directory = this_dir.joinpath(".cache")
    cached_pages_dir = cache_directory.joinpath("pages")
    #cached_blocks_dir = cache_directory.joinpath("blocks")
    cached_images_dir = cache_directory.joinpath("images")
    # Pages decoded content with PyPDF2 library
    cached_content_dir = cache_directory.joinpath("contents")
    #cached_custom_blocks = cache_directory.joinpath("custom_blocks")

    pdf_file = cache_directory.joinpath("diydog-2022.pdf")
    if not pdf_file.exists() :
        print("Downloading brewdog's Diydog pdf booklet ...")
        download_pdf(C_DIYDOG_URL, pdf_file)
        print("-> OK : Downloading succeeded ! Pdf file was downloaded at : {}".format(pdf_file))
        # Triggers force caching because we need to regenerate everything
        force_caching = True

    pages_content : list[PageBlocks] = []

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
                beer_index = i - start_page + 1
                print("Extracting page : {}, beer index : {}".format(i, beer_index))
                encoded_name = "page_{}".format(beer_index)
                page = reader.getPage(i)
                print("Caching page to disk")
                cache_single_pdf_page(cached_pages_dir.joinpath(encoded_name + ".pdf"), page=page)
                page_images_dir = cached_images_dir.joinpath(encoded_name)
                cache_images(page_images_dir, page)
                # contents_filepath = cached_content_dir.joinpath(encoded_name + ".txt")
                # cache_pdf_contents(contents_filepath, page)
                custom_blocks_filepath = cached_content_dir.joinpath(encoded_name + ".json")


                # Fetch raw contents and manually parse it (works better than brute text extraction from pypdf2)
                print("Extracting textual content of page ...")
                str_contents = bytes(page.get_contents().get_data()).decode("utf-8")
                raw_blocks = extract_raw_text_blocks_from_content(str_contents)
                text_blocks = text_blocks_from_raw_blocks(raw_blocks)
                cache_custom_blocks(custom_blocks_filepath, text_blocks)

                # Adding page blocks now, so that we
                # don't have to parse them again
                page_blocks = PageBlocks()
                page_blocks.blocks = text_blocks
                page_blocks.index = beer_index
                pages_content.append(page_blocks)



        print("-> OK : Pages extracted successfully in {}".format(cached_pages_dir))

    # List already cached pages
    print("Listing available pdf pages ...")
    pages_list = list_pages(cached_pages_dir, "page_", ".pdf")
    print("-> OK : Found {} pages in {}".format(len(pages_list), cached_pages_dir))

    print("Listing available json content from pages ...")
    pages_content_list = list_pages(cached_content_dir, "page_", ".json")
    print("-> OK : Found {} pages in {}".format(len(pages_list), cached_pages_dir))
    for page in pages_content_list :
        page_index = page[0]
        found_elem = [x for x in pages_content if  x.index == page_index ]
        # Skip deserialization if it already exist in memory
        if len(found_elem) != 0 :
            continue

        print("Reading back cached text content from json file {}".format(page[1].name))
        page_blocks = PageBlocks()
        page_blocks.index = page_index
        with open(page[1], "r") as file :
            data = json.load(file)
            page_blocks.from_json(data)
        pages_content.append(page_blocks)

    print("Done !")

if __name__ == "__main__" :
    try :
        main()
    except Exception as e :
        print("-> ERROR : Caught exception while running script, error was  : {}".format(e))
        raise e