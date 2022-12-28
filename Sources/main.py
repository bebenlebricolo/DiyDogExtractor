#!/usr/bin/python

import sys
import os
import math
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

from .Utils.parsing import parse_line
from .Models.jsonable import Jsonable
from .Models import recipe as rcp


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


def cache_raw_blocks(filepath : Path, blocks : list[list[str]] ) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    with open(filepath, "w") as file :
        for block in blocks :
            for line in block :
                file.write(line + "\n")
            file.write("\n")


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
    for blocks in raw_blocks :
        current_coords = Coordinates()
        new_element : Optional[TextElement] = None
        for line in blocks :
            if line.find("TJ") != -1 or line.find("Tj") != -1 :
                if not new_element :
                    new_element = TextElement()
                    new_element.x = current_coords.x
                    new_element.y = current_coords.y

                parsed_line = parse_line(line)
                # This is required as sometimes PDF can chain multiple "Tj" instructions with different formatting (like color)
                # Without resetting the transformation matrix, so they need to be read as a single line instead
                new_element.text += parsed_line
                continue

            elif line.find("Tm") != -1:
                tokens = line.split()
                tm_index = tokens.index("Tm")
                current_coords.x = float(tokens[tm_index - 2])
                current_coords.y = float(tokens[tm_index - 1])

                # New transformation matrix means a new PDF write somewhere else in the page, so we can bump the element if any
                if new_element :
                    out.append(new_element)
                    new_element = None

            elif line.find("Td") != -1 or line.find("TD") != -1:
                tokens = line.split()
                td_index = tokens.index("Td")
                if td_index == -1 :
                    td_index = tokens.index("TD")

                current_coords.x += float(tokens[td_index - 2])
                current_coords.y += float(tokens[td_index - 1])

                # Td/TD mean a new line, with an updated transformation matrix, so we can bump the element if any
                if new_element :
                    out.append(new_element)
                    new_element = None

        # Consume new element at the end of the parsing if needed
        if new_element :
            out.append(new_element)
            new_element = None

    return out


def cache_contents(filepath : Path, page : PageBlocks) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    with open(filepath, "w") as file :
        data = page.to_json()
        json.dump(data, file, indent=4)

def cache_pdf_raw_contents(filepath : Path, content : str) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    with open(filepath, "w") as file :
        file.write(content)

def find_closest_x_element(elements : list[TextElement], reference : TextElement) -> TextElement :
    min_distance = 1000
    closest : TextElement = elements[0]
    for element in elements :
        distance = abs(reference.x - element.x)
        if distance < min_distance :
            closest = element
            min_distance = distance

    return closest

def find_closest_y_element(elements : list[TextElement], reference : TextElement) -> TextElement :
    min_distance = 1000
    closest : TextElement = elements[0]
    for element in elements :
        distance = abs(reference.y - element.y)
        if distance < min_distance :
            closest = element
            min_distance = distance

    return closest

def find_closest_element(elements : list[TextElement], reference : TextElement) -> TextElement :
    min_distance = 1000
    closest : TextElement = elements[0]
    for element in elements :
        distance = math.sqrt(math.pow(reference.x - element.x, 2) + math.pow(reference.y - element.y, 2))
        if distance < min_distance :
            closest = element
            min_distance = distance

    return closest

def extract_header(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    # Sort list based on y indices, top to bottom
    consumed_elements : list[TextElement] = []
    elements.sort(key=lambda x : x.y, reverse=True )

    recipe.number = int(elements[0].text.lstrip("#")) if elements[0].text.startswith("#") else 0
    name_elem = find_closest_element(elements[1:], elements[0])
    recipe.name = name_elem.text

    consumed_elements.append(elements[0])
    consumed_elements.append(name_elem)

    abv_elem : Optional[TextElement] = None
    ibu_elem : Optional[TextElement] = None
    og_elem :  Optional[TextElement] = None

    # Extracting first brew date, ABV, IBU and OG elements
    for element in elements :
        if element.text.find("FIRST BREWED") != -1 :
            recipe.first_brewed = element.text[len("FIRST BREWED "):]
            consumed_elements.append(element)
            continue

        if element.text == "ABV":
            abv_elem = element
            consumed_elements.append(element)
            continue

        if element.text == "IBU" :
            ibu_elem = element
            consumed_elements.append(element)
            continue

        if element.text == "OG" :
            og_elem = element
            consumed_elements.append(element)
            continue

    below_abv_elems : list[TextElement] = []
    for element in elements :
        if element.y < abv_elem.y :
            below_abv_elems.append(element)

    # Extract abv, ibu and og which are closest to column
    abv_data_elem = find_closest_x_element(below_abv_elems, abv_elem)

    # Sometimes, IBU does not exist for some beers (such as the beer #33 Tactical Nuclear Penguin)
    if ibu_elem :
        ibu_data_elem = find_closest_x_element(below_abv_elems, ibu_elem)
        consumed_elements.append(ibu_data_elem)

    # Same remark, sometimes OG is not there neither
    if og_elem :
        og_data_elem = find_closest_x_element(below_abv_elems, og_elem)
        consumed_elements.append(og_data_elem)

    consumed_elements.append(abv_data_elem)


    # Fill in the recipe with the header's content
    float_parsing_pattern = re.compile(r"([0-9]*\.?[0-9])")
    recipe.basics.abv = float(re.match(float_parsing_pattern, abv_data_elem.text).groups()[0])

    # Same, skip if nothing was parsed
    if ibu_elem :
        recipe.basics.ibu = float(re.match(float_parsing_pattern, ibu_data_elem.text).groups()[0])

    # Same, skip if nothing was parsed
    if og_elem :
        recipe.basics.target_og = float(og_data_elem.text)

    remaining_elements : list[TextElement] = []
    for element in elements :
        if not element in consumed_elements :
            remaining_elements.append(element)

    # Extract all tags from remaining elements
    for element in remaining_elements :
        splitted = element.text.split(".")
        for part in splitted :
            if part != "" :
                recipe.tags.append(part.strip())


    return recipe

def extract_footer(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    # Only extract page number
    for element in elements :
        if element.text.isnumeric() :
            recipe.page_number = int(element.text)
    return recipe

def find_element(elements : list[TextElement], text : str) -> Optional[TextElement] :
    for element in elements :
        if element.text == text :
            return element
    return None

def get_elem_index(elements : list[TextElement], text : str) -> int :
    for i in range(0, len(elements)) :
        if elements[i].text == text :
            return i
    return -1

def filter_categories_and_content(reference_list : list[TextElement], elements : list[TextElement] ) -> list[list[TextElement]] :
    categorized_lists : list[list[TextElement]] = []
    current_category : list[TextElement] = []
    for element in elements :
        if element in reference_list :
            # Start new category candidates filling
            if len(current_category) != 0 :
                categorized_lists.append(current_category)
                current_category = []
            current_category.append(element)
        else :
            current_category.append(element)
    # Pop the last items
    if len(current_category) != 0 :
        categorized_lists.append(current_category)
    return categorized_lists

def parse_this_beer_is_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    description = ""
    # Pop the first element "THIS BEER IS", we don't want that in the description
    for elem in elements[1:] :
        description += elem.text + " "
    recipe.description.text = description.strip()
    return recipe

def parse_basics_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    return recipe

def parse_method_timings_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    return recipe


def pre_process_malts(elements : list[TextElement]) -> list[TextElement] :
    # Sometimes, malts names are longer than one line and span on multiple lines.
    # A strategy to reduce this is to calculate the average distance between each contiguous text
    # elements on the y axis. When a step becomes bigger, it means we are jumping from one malt to the following one
    # Example :
    #   malt 1 name -               5kg        11lb
    #   with a trailing part
    #   --------------------------------------------- -> this line does not exist in the listed TextElement, we cannot rely on it !
    #   malt 2 name -
    #   with another trailing part  1kg        some lb
    #
    # Usually components are listed like so :
    #   malt 1 name -                 -
    #   5kg                            |
    #   11lb                           |
    #   with a trailing part          -
    #   malt 2 name -                 -
    #   1kg                            |
    #   some lb                        |
    #   with another trailing part    -

    blocks : list[list[TextElement]] = []
    current_block : list[TextElement] = []
    avg_distance = 0
    # Current block will always start with the first element
    current_block.append(elements[0])
    for i in range(1, len(elements)) :
        distance = abs(elements[i - 1].y - elements[i].y)

        # Maybe we've reached a new data block ?
        if distance > (avg_distance * 1.2) :
            blocks.append(current_block)
            current_block = [elements[i]]
            avg_distance = 0
            continue

        current_block.append(elements[i])
        avg_distance = ((avg_distance * (i - 1)) + distance) / (i)

    # Pop the last element as well
    if len(current_block) != 0 :
        blocks.append(current_block)

    out : list[TextElement] = []
    # Sort the lists the that text elements are contiguous and ordered by y
    for block in blocks :
        weight_data_list : list[TextElement] = []
        temp_list :list[TextElement] = []
        for elem in block :
            if elem.text.find("kg") != -1 or elem.text.find("lb") != -1 :
                weight_data_list.append(elem)
            else :
                temp_list.append(elem)

        # Aggregate data into a single text element
        aggregated_text_elem = copy(temp_list[0])
        for elem in temp_list[1:] :
            aggregated_text_elem.text += " " + elem.text
        out.append(aggregated_text_elem)

        # Move weight data elements as well
        for elem in weight_data_list :
            out.append(elem)

    return out

def parse_ingredients_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    malt_elem = find_element(elements, "MALT")
    hops_elem = find_element(elements, "HOPS")
    yeast_elem = find_element(elements, "YEAST")

    # Beer without ingredients, the beer #89 is one of them
    if not malt_elem and not hops_elem and not yeast_elem :
        for elem in elements :
            recipe.ingredients.description += elem.text + " "
        recipe.ingredients.description = recipe.ingredients.description.strip()
        return recipe

    malt_data_list : list[TextElement] = []
    hops_data_list : list[TextElement] = []
    yeast_data_list : list[TextElement] = []

    # Subcategorizing data
    working_list : list[TextElement] = []
    for element in elements :
        if element == malt_elem :
            working_list = malt_data_list
            continue
        if element == hops_elem :
            working_list = hops_data_list
            continue
        if element == yeast_elem :
            working_list = yeast_data_list
            continue
        working_list.append(element)

    # Parse malts
    malt_data_per_row = 3
    recipe.ingredients.malts.clear()

    # Pre-process malts
    # Required because sometimes malts might have trailing parts
    malt_data_list = pre_process_malts(malt_data_list)


    for i in range(0, int(len(malt_data_list) / malt_data_per_row)) :
        index = i * malt_data_per_row
        dataset = [malt_data_list[index], malt_data_list[index + 1], malt_data_list[index + 2]]
        # Sort items using the x component, left to right
        dataset.sort(key=lambda x : x.x)
        new_malt = rcp.Malt()
        new_malt.name = dataset[0].text
        new_malt.kgs = float(dataset[1].text.replace("kg", ""))
        new_malt.lbs = float(dataset[2].text.replace("lb", ""))
        recipe.ingredients.malts.append(new_malt)


    # Parse hops
    for hops_data in hops_data_list :
        pass

    # Parse yeast
    for yeast_data in yeast_data_list :
        pass

    return recipe

def parse_food_pairing_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    return recipe

def parse_brewers_tip_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    return recipe

def parse_packaging_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    return recipe

def extract_body(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    this_beer_is_elem   : TextElement = find_element(elements, "THIS BEER IS")
    basics_elem         : TextElement = find_element(elements, "BASICS")
    ingredients_elem    : TextElement = find_element(elements, "INGREDIENTS")
    food_pairing_elem   : TextElement = find_element(elements, "FOOD PAIRING")
    method_timings_elem : TextElement = find_element(elements, "METHOD / TIMINGS")
    brewers_tip_elem    : TextElement = find_element(elements, "BREWER\x92S TIP")
    packaging_elem      : TextElement = find_element(elements, "PACKAGING")

    # List of known good references/categories
    # This will be used in order to filter embedded data
    # and to discriminate categories start from other content
    references_list = [
        this_beer_is_elem,
        basics_elem,
        ingredients_elem,
        food_pairing_elem,
        method_timings_elem,
        brewers_tip_elem,
        packaging_elem
    ]

    # Offsetting a little bit, because formatting of pdf
    # page sometimes align words differently because of character spacing being inconsistent
    # For instance, "THIS BEER IS" is located a little bit more right that "BASICS", despite
    # being perfectly aligned to the eye on the final rendered page
    column_0_x_start = this_beer_is_elem.x - 20
    column_1_x_start = ingredients_elem.x - 20
    column_2_x_start = packaging_elem.x

    # Find the misplaced "MALT" text element, which is written in a weird coordinate system
    # And put that one right below the ingredients category
    malt_elem = find_element(elements, "MALT")
    if malt_elem :
        malt_elem.x = ingredients_elem.x + 5
        malt_elem.y = ingredients_elem.y - 10
    # If there is no malt element, it means that the beer does not have detailed ingredients
    # The beer #89 AB:19 is one of them and does not contain any ingredients

    # Filter elements based on their x coordinates
    column_0_elements : list[TextElement] = []
    column_1_elements : list[TextElement] = []
    column_2_elements : list[TextElement] = []
    for element in elements :
        if element.x < column_1_x_start :
            column_0_elements.append(element)
            continue
        if element.x >= column_1_x_start and element.x < column_2_x_start :
            column_1_elements.append(element)
            continue
        if element.x >= column_2_x_start :
            column_2_elements.append(element)
            continue

    # Sort items by y position (Top to bottom)
    column_0_elements.sort(key=lambda x : x.y, reverse=True)
    column_1_elements.sort(key=lambda x : x.y, reverse=True)
    column_2_elements.sort(key=lambda x : x.y, reverse=True)

    # Extract categories and content for each column
    column_0_categories = filter_categories_and_content(references_list, column_0_elements)
    column_1_categories = filter_categories_and_content(references_list, column_1_elements)
    column_2_categories = filter_categories_and_content(references_list, column_2_elements)

    # Perform all data parsing
    for column_data in [column_0_categories, column_1_categories, column_2_categories] :
        for category in column_data :
            match category[0].text :
                case "THIS BEER IS" :
                    recipe = parse_this_beer_is_category(category, recipe)

                case "BASICS" :
                    recipe = parse_basics_category(category, recipe)

                case "METHOD / TIMINGS" :
                    recipe = parse_method_timings_category(category, recipe)

                case "FOOD PAIRING" :
                    recipe = parse_food_pairing_category(category, recipe)

                case "INGREDIENTS" :
                    recipe = parse_ingredients_category(category, recipe)

                case "BREWER\x92S TIP" :
                    recipe = parse_brewers_tip_category(category, recipe)

                case "PACKAGING" :
                    recipe = parse_packaging_category(category, recipe)

                case _ :
                    raise Exception("Caught unexpected category name : {}".format(category[0].text))




    return recipe

def extract_recipe(page : PageBlocks) -> rcp.Recipe :
    header_y_limit = 660
    footer_y_limit = 50

    header_elements : list[TextElement] = []
    footer_elements : list[TextElement] = []
    body_elements : list[TextElement] = []

    for block in page.blocks :
        if block.y >= header_y_limit :
            header_elements.append(block)
        elif block.y <= footer_y_limit :
            footer_elements.append(block)
        else :
            body_elements.append(block)

    out = rcp.Recipe()
    out = extract_header(header_elements, out)
    out = extract_footer(footer_elements, out)
    out = extract_body(body_elements, out)
    return rcp.Recipe()


def main(args) :
    force_caching = False
    if len(args) >= 1 :
        print("Force caching mode activated")
        force_caching = args[0] == "true"

    this_dir = Path(__file__).parent
    cache_directory = this_dir.joinpath(".cache")
    cached_pages_dir = cache_directory.joinpath("pages")
    cached_blocks_dir = cache_directory.joinpath("blocks")
    cached_pdf_raw_content = cache_directory.joinpath("pdf_raw_contents")
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

                print("Caching page to disk ...")
                cache_single_pdf_page(cached_pages_dir.joinpath(encoded_name + ".pdf"), page=page)
                page_images_dir = cached_images_dir.joinpath(encoded_name)

                print("Caching images to disk ...")
                cache_images(page_images_dir, page)
                content_filepath = cached_content_dir.joinpath(encoded_name + ".json")


                # Fetch raw contents and manually parse it (works better than brute text extraction from pypdf2)
                print("Extracting textual content of page ...")
                str_contents = bytes(page.get_contents().get_data()).decode("utf-8")
                cache_pdf_raw_contents(cached_pdf_raw_content.joinpath(encoded_name + ".txt"), str_contents )

                raw_blocks = extract_raw_text_blocks_from_content(str_contents)
                print("Caching raw text blocks ...")
                cache_raw_blocks(cached_blocks_dir.joinpath(encoded_name + ".txt"), raw_blocks )

                print("Parsing raw text blocks into pre-processed text blocks")
                text_blocks = text_blocks_from_raw_blocks(raw_blocks)

                # Post processing of text blocks :
                print("Post processing text blocks ...")
                temp_blocks = []
                for block in text_blocks :
                    # Strip whitespaces and removes empty items
                    block.text = block.text.strip()
                    if block.text != "" :
                        temp_blocks.append(block)

                text_blocks = temp_blocks

                print("Caching preprocessed contents ...")
                # Adding page blocks now, so that we
                # don't have to parse them again
                page_blocks = PageBlocks()
                page_blocks.blocks = text_blocks
                page_blocks.index = beer_index
                pages_content.append(page_blocks)
                cache_contents(content_filepath, page_blocks)



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

    print("Parsing actual recipe content from extracted text blocks")
    recipes_list : list[rcp.Recipe] = []
    for page in pages_content :
        print("Parsing recipe from page {}".format(page.index))
        new_recipe = extract_recipe(page)
        recipes_list.append(new_recipe)


    print("Done !")

if __name__ == "__main__" :
    try :
        main(sys.argv[1:])
    except Exception as e :
        print("-> ERROR : Caught exception while running script, error was  : {}".format(e))
        raise e