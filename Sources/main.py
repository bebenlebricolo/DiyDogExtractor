#!/usr/bin/python

import os
import re
import sys
import math
import json
from pathlib import Path
import argparse
from enum import Enum


from copy import copy
import traceback
from typing import Optional

from pypdf import PageObject, PdfWriter, PdfReader
import fitz
from fitz.utils import get_page_pixmap

# Local imports

from .Utils.parsing import parse_line
from .Utils.logger import Logger
from .Utils.downloader import download_pdf
from .Models.blocks import PageBlocks, Coordinates, TextBlock, TextElement
from .Models import recipe as rcp
from .Utils import image as utim
from .Utils.filesystem import ensure_folder_exist, list_pages, list_files

C_DIYDOG_URL = "https://brewdogmedia.s3.eu-west-2.amazonaws.com/docs/2019+DIY+DOG+-+V8.pdf"

GRAMS_PATTERN = re.compile(r"([0-9]+\.?[0-9]*) *([k]?[g])")
NUMERICS_PATTERN = re.compile(r"([0-9]+\.?[0-9]*)")
DEGREES_PATTERN = re.compile(r"([0-9]+\.?[0-9]*)[ ]?°[CF]")
DEGREES_C_PATTERN = re.compile(r"([0-9]+\.?[0-9]*)[ ]?°C")
DEGREES_F_PATTERN = re.compile(r"([0-9]+\.?[0-9]*)[ ]?°F")

# This one is simpler as sometimes lb data is missing
LBS_PATTERN = re.compile(r"([0-9]+\.[0-9]+)")

THIS_DIR = Path(__file__).parent
CACHE_DIRECTORY = THIS_DIR.joinpath(".cache")
logger = Logger(CACHE_DIRECTORY.joinpath("logs.txt"))


def custom_assert_equal(val1, val2) :
    if val1 != val2 :
        print("Caught 2 different values, but they should be equal")
        raise Exception("val1 = {}, val2 = {}".format(val1, val2))


def celsius_to_fahrenheit(value : float) -> float :
    return (value* 1.8) + 32

def fahrenheit_to_celsius(value : float) -> float :
    return (value - 32)/1.8

# Useful doc : https://pypdf.readthedocs.io/en/latest/user/extract-text.html


def cache_raw_blocks(filepath : Path, blocks : list[list[str]] ) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    with open(filepath, "wb") as file :
        for block in blocks :
            for line in block :
                data = (line + "\n").encode("utf-8")
                file.write(data)
            file.write("\n".encode("utf-8"))


def cache_single_pdf_page(filepath : Path, page : PageObject ) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    pdf_writer = PdfWriter()
    pdf_writer.add_page(page)
    with open(filepath, "wb") as file :
        pdf_writer.write(file)

def cache_pdf_contents(filepath : Path, page : PageObject) :
    if not filepath.parent.exists() :
        filepath.parent.mkdir(parents=True)

    contents = page.get_contents()
    if contents :
        raw_data : bytes = contents.get_data()
        str_contents = raw_data.decode()
        with open(filepath, "w") as file :
            file.writelines(str_contents)
    else :
        raise Exception("Content is missing from page document")


def cache_images(directory : Path, page_file : Path, beer_number = 0) :
    if not directory.exists() :
        directory.mkdir(parents=True)

    try :
        document = fitz.Document(page_file) # type: ignore

        full_page_rendered = get_page_pixmap(document, 0)
        full_page_rendered.pil_save(directory.joinpath("full.png"))

        # Cropping area : left, right, top, bottom
        #                  x0    x1     y0    y1
        cropping_zone = [0.64, 0.92, 0.26, 0.69]
        cropped_image = utim.extract_zone_from_image(full_page_rendered, cropping_zone )

        cropped_image_path = directory.joinpath("cropped.png")
        cropped_image.save(cropped_image_path)

        extracted_shape = directory.joinpath("extracted_silhouette.png")
        most_probable_packaging = utim.extract_biggest_silhouette(cropped_image_path, extracted_shape, logger, fit_crop_image=True, beer_number=beer_number)
        logger.log("Extracted image {} with potential packaging : {}".format(beer_number, most_probable_packaging))

    # Sometimes we can't even list the images because of some weird errors earlier in the pdf parsing methods
    except Exception as e :
        logger.log("Caught error while caching images for page {}".format(directory.name))
        logger.log(e.__repr__())


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
        content = page.to_json()
        json.dump(content, file, indent=4)

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

        # Case where we stumble upon our reference, that's not the one we're aiming for !
        if distance == 0 and element == reference:
            continue

        if distance < min_distance :
            closest = element
            min_distance = distance

    return closest

def extract_header(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    # Sort list based on y indices, top to bottom
    consumed_elements : list[TextElement] = []
    elements.sort(key=lambda x : x.y, reverse=True )

    number_element =  elements[0]

    # Sometimes the beer number element is not the first one (for some reason...)
    for elem in elements :
        # Some beers start with the infamous "#" and we just want to isolate the beer number (always formatted as "#123")
        if elem.text.startswith("#") and elem.text.lstrip("#").isnumeric() :
            recipe.number = int(elem.text.lstrip("#"))
            number_element = elem

    # The beer's name is always the closest item to the beer's number, in the formatting
    name_elem = find_closest_element(elements, number_element)

    if recipe.number == 15:
        pass

    # For some beers, name components are split (because of a special character that needed dedicated pdf drawing instructions (...))
    name_comps_aligned = [x for x in elements if x.y == name_elem.y]
    name_comps_aligned.sort(key=lambda x : x.x)

    recipe.name = name_elem.text

    # Special handling for close words
    if len(name_comps_aligned) > 1 :
        threshold_distance = 20
        for i in range(1, len(name_comps_aligned)):
            if name_comps_aligned[i].x - name_comps_aligned[i-1].x >= threshold_distance:
                # This section seems to represent subtitles for beers, like characteristics, etc...
                recipe.subtitle += name_comps_aligned[i].text + " "
            else :
                recipe.name += name_comps_aligned[i].text
            consumed_elements.append(name_comps_aligned[i])
    recipe.name = recipe.name.rstrip(" ")
    recipe.subtitle = recipe.subtitle.rstrip(" ")

    # We need to keep track of the consumed element so that they don't fall into the tag lines
    consumed_elements.append(number_element)
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
        if abv_elem and element.y < abv_elem.y :
            below_abv_elems.append(element)


    # Handle data elements one by one
    abv_data_elem : Optional[TextElement] = None
    ibu_data_elem : Optional[TextElement] = None
    og_data_elem : Optional[TextElement] = None

    # Extract abv, ibu and og which are closest to column
    if abv_elem :
        abv_data_elem = find_closest_x_element(below_abv_elems, abv_elem)
        consumed_elements.append(abv_data_elem)

    # Sometimes, IBU does not exist for some beers (such as the beer #33 Tactical Nuclear Penguin)
    if ibu_elem :
        ibu_data_elem = find_closest_x_element(below_abv_elems, ibu_elem)
        consumed_elements.append(ibu_data_elem)

    # Same remark, sometimes OG is not there neither
    if og_elem :
        og_data_elem = find_closest_x_element(below_abv_elems, og_elem)
        consumed_elements.append(og_data_elem)


    # Then extract data from them adequately
    if abv_data_elem :
        # Fill in the recipe with the header's content
        match = NUMERICS_PATTERN.match(abv_data_elem.text)
        if match :
            recipe.basics.abv = float(match.groups()[0])

    # Same, skip if nothing was parsed
    if ibu_data_elem :
        match = NUMERICS_PATTERN.match(ibu_data_elem.text)
        if match :
            recipe.basics.ibu = float(match.groups()[0])

    # Same, skip if nothing was parsed
    if og_data_elem :
        recipe.basics.target_og = float(og_data_elem.text)



    remaining_elements : list[TextElement] = []
    for element in elements :
        if not element in consumed_elements :
            remaining_elements.append(element)

    # Extract all tags from remaining elements
    remaining_elements.sort(key=lambda x : x.x)
    for i in range(0, len(remaining_elements)) :
        element = remaining_elements[i]
        splitted = remaining_elements[i].text.split(".")
        for part in splitted :
            if part != "" :
                # We have some tag lines that contain stuff like "12 th anniversary", but they are encoded by the PDF as two
                # separate items for some reasons
                if part == "TH" and i != 0 and remaining_elements[i - 1].text.isnumeric() :
                    recipe.tags[len(recipe.tags) - 1] += "th"

                else :
                    # Popping out all parasitic characters such as " (FANZINE) " -> "FANZINE"
                    recipe.tags.append(part.strip().lstrip("(").rstrip(")").strip())



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

def find_element_substring(elements : list[TextElement], text : str) -> Optional[TextElement] :
    """Returns the first element in the given collection whose text contains the probing text. Exact match is not required"""
    for element in elements :
        if text in element.text :
            return element
    return None

# Variant of the above one, but we enforce the object state
# used essentially to cover the use case where data *needs* to be there
def find_element_strict(elements : list[TextElement], text : str) -> TextElement :
    elem = find_element(elements, text)
    assert(elem)
    return elem

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

def concatenate_columns(columns : list[tuple[float,list[TextElement]]]) -> list[TextElement]:
    out : list[TextElement] = []
    for column in columns :
        first = column[1][0]

        # Aggregate elements along the way ...
        for element in column[1][1:] :
            first.text += " " + element.text.strip()
        first.text = first.text.strip()
        out.append(first)

    return out

def group_in_distinct_columns(elements : list[TextElement], tolerance : float = 0.01) -> list[tuple[float,list[TextElement]]] :
    known_x_columns : list[tuple[float, list[TextElement]]] = []

    # Discover potential columns first based on x value extracted from transformation matrix
    for elem in elements :
        found_column = False
        for column_x in known_x_columns :
            # Match if value is within the interval, with some placement tolerance
            distance = abs(elem.x - column_x[0])
            if  distance <= (column_x[0] * tolerance):
                column_x[1].append(elem)
                found_column = True

        # Append new data if we haven't found any previous datasets
        if not found_column :
            known_x_columns.append((elem.x, [elem]))

    return known_x_columns

def split_blocks_based_on_y_distance(elements:  list[TextElement], threshold : float = 1.5) -> list[list[TextElement]] :
    blocks : list[list[TextElement]] = []
    current_block : list[TextElement] = []
    # Current block will always start with the first element
    current_block.append(elements[0])
    for i in range(1, len(elements)) :
        distance = abs(elements[i - 1].y - elements[i].y)

        # Maybe we've reached a new data block ?
        if distance >= threshold :
            blocks.append(current_block)
            current_block = [elements[i]]
            continue

        current_block.append(elements[i])

    # Pop the last element as well
    if len(current_block) != 0 :
        blocks.append(current_block)

    return blocks

def remove_exact_doubles(elements: list[TextElement]) -> list[TextElement] :
    unique : list[TextElement] = []
    for elem in elements :
        # If the element exactly match the one we're targetting, we remove this from the original list
        if find_element(unique, elem.text) == elem :
            continue
        unique.append(elem)

    return unique

def parse_this_beer_is_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    description = ""
    # Pop the first element "THIS BEER IS", we don't want that in the description
    for elem in elements[1:] :
        description += elem.text + " "
    recipe.description.text = description.strip()
    return recipe

def line_from_text_elements(elements: list[TextElement]) -> str :
    out = ""
    for elem in elements :
        out += elem.text.strip() + " "
    out.strip()
    return out

def parse_basics_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    elements.sort(key=lambda x : x.y, reverse=True)
    rows = split_blocks_based_on_y_distance(elements)
    for row in rows :
        # Skipping this element, we don't need it now
        if find_element(row, "BASICS") :
            continue

        raw_columns = group_in_distinct_columns(row)

        # Remove doubles !!!
        # Some beers; such as #290 have doubles (why ...???) so we need to get rid of them firstr
        filtered_raw : list[tuple[float, list[TextElement]]] = []
        for raw_column in raw_columns :
            filtered_raw.append((raw_column[0], remove_exact_doubles(raw_column[1])))

        flattened_rows = concatenate_columns(filtered_raw)
        flattened_rows.sort(key=lambda x : x.x)

        match flattened_rows[0].text :
            case "VOLUME" | "BOIL VOLUME" :
                volume = rcp.Volume()

                # Extract litres
                match = NUMERICS_PATTERN.match(flattened_rows[1].text)
                if match :
                    volume.litres = float(match.groups()[0])

                # Extract galons
                match = NUMERICS_PATTERN.match(flattened_rows[2].text)
                if match :
                    volume.galons = float(match.groups()[0])

                # Dispatch the volume accordingly
                if flattened_rows[0].text == "VOLUME" :
                    recipe.basics.volume = volume
                else :
                    recipe.basics.boil_volume = volume

            case "ABV" :
                if recipe.basics.abv != 0.0 :
                    continue
                # Parsing ABV in case it was not extracted from header yet ; There should only be 2 columns here
                match = NUMERICS_PATTERN.match(flattened_rows[1].text)
                if match :
                    recipe.basics.abv = float(match.groups()[0])

            case "TARGET OG" :
                if recipe.basics.target_og != 0.0 :
                    continue
                value = flattened_rows[1].text
                recipe.basics.target_og = float(value)

                # Again, ugly stuff ... gravities were swapped, and OG in "Basics" section
                # was replaced with ABV !
                if recipe.number == 413 :
                        recipe.basics.target_fg = recipe.basics.target_og

            case "TARGET FG" :
                try :
                    matches = NUMERICS_PATTERN.findall(flattened_rows[1].text)
                    # We're only taking the first one, by convention
                    # Some beers have a range (such as the beer #192) which we can't reproduce with a single
                    # value without adding extra complexity to the data model, so taking the first value will do the job instead
                    recipe.basics.target_fg = float(matches[0])
                except Exception as e :
                    logger.log("/!\\ Caught weird stuff in Target FG for beer {}. Text was : {}".format(recipe.number, flattened_rows[1]))


            # Beers #207, #213; #214, #215 have a weird field named TARGET EBC WORT that needs to be handled as a regular ebc
            case "EBC" | "SRM" | "TARGET EBC WORT" :
                # Some beers (such as the #16th one) have N/A mention for EBC and SRM
                value = flattened_rows[1].text
                fval : float = 0.0
                if value == "N/A" :
                    fval = -1.0
                else :
                    try :
                        fval = float(NUMERICS_PATTERN.findall(flattened_rows[1].text)[0])
                    except Exception as e:
                        logger.log("/!\\ Could not convert value for {} because {}.".format(flattened_rows[0].text, e))
                        continue

                # Same treatment for both categories
                if "EBC" in flattened_rows[0].text :
                    recipe.basics.ebc = fval
                else :
                    recipe.basics.srm = fval

            case "PH" :
                # Ph is missing on some recipes, so we can try to infer it
                if len(flattened_rows) == 2 :
                    recipe.basics.ph = float(flattened_rows[1].text)
                else :
                    # 4.4 seems a pretty common value in BrewDog's beers
                    recipe.basics.ph = 4.4

            case "ATTENUATION LEVEL" :
                match = NUMERICS_PATTERN.match(flattened_rows[1].text)
                if match :
                    recipe.basics.attenuation_level = float(match.groups()[0])

            case _ :
                logger.log("/!\\ Unhandled element in beer number {}. Element was : {}".format(recipe.number, flattened_rows[0].text))

    return recipe

def parse_method_timings_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :

    elements.sort(key=lambda x : x.y, reverse=True)
    mash_temp_elem = find_element_strict(elements, "MASH TEMP")
    # Some bers are missing the "Fermentation" element as well, such as the #406 one
    fermentation_elem = find_element(elements, "FERMENTATION")

    # Not all beers have the "Twist" element
    twist_elem = find_element_substring(elements, "TWIST")
    # Pops here and there for beer #265 for instance, goes along with the Twist/Brewhouse one
    additions_elem : Optional[TextElement] = find_element(elements, "ADDITIONS")

    mash_temp_data_list : list[TextElement] = []
    fermentation_data_list : list[TextElement] = []
    twist_data_list : list[TextElement] = []

    # Subcategorizing data
    working_list : list[TextElement] = []
    for element in elements :
        if element == mash_temp_elem :
            working_list = mash_temp_data_list
            continue
        if fermentation_elem and element == fermentation_elem :
            working_list = fermentation_data_list
            continue
        if twist_elem and element == twist_elem :
            working_list = twist_data_list
            continue

        # Skip this one
        if element == additions_elem :
            continue

        # Consume element
        working_list.append(element)

    # Sort all three lists
    mash_temp_data_list.sort(key=lambda x : x.y, reverse=True)
    fermentation_data_list.sort(key=lambda x : x.y, reverse=True)
    twist_data_list.sort(key=lambda x : x.y, reverse=True)

    method_timings = rcp.MethodTimings()

    # Extract mash temps
    mash_temps_rows = split_blocks_based_on_y_distance(mash_temp_data_list)
    for row in mash_temps_rows :
        columns = group_in_distinct_columns(row)
        flattened_row = concatenate_columns(columns)
        flattened_row.sort(key=lambda x : x.x)

        if len(flattened_row) == 1 :
            method_timings.mash_tips.append(flattened_row[0].text)
        else :
            mash_temp = rcp.MashTemp()
            if len(flattened_row) == 2 :
                matches = DEGREES_PATTERN.findall(flattened_row[0].text)
                if len(matches) != 0 :
                    mash_temp.celsius = float(matches[0])
                    mash_temp.fahrenheit = celsius_to_fahrenheit(mash_temp.celsius)
                else :
                    logger.log("/!\\ Could not read temperature from mash instructions for beer {}. Line was {}".format(recipe.number, line_from_text_elements(flattened_row)))

                matches = NUMERICS_PATTERN.findall(flattened_row[1].text)
                if len(matches) != 0 :
                    mash_temp.time = float(matches[0])
                else :
                    logger.log("/!\\ Could not read timing from mash instructions for beer {}. Line was {}".format(recipe.number, line_from_text_elements(flattened_row)))
            else :
                # Extract Celsius degrees from mash temp
                matches = DEGREES_PATTERN.findall(flattened_row[0].text)
                if len(matches) != 0 :
                    mash_temp.celsius = float(matches[0])
                else :
                    logger.log("/!\\ Caught weird looking patterns for Celsius degrees for beer {} when parsing mash temps data : {}".format(recipe.number, flattened_row[0].text))

                if recipe.number == 220 :
                    pass

                # Repeat for Fahrenheit degrees from mash temp
                matches = DEGREES_PATTERN.findall(flattened_row[1].text)
                if len(matches) != 0 :
                    mash_temp.fahrenheit = float(matches[0])
                else :
                    logger.log("/!\\ Caught weird looking patterns for Fahrenheit degrees for beer {} when parsing mash temps data : {}".format(recipe.number, flattened_row[1].text))

                # Not all beers have timing data for mash temperatures
                if len(flattened_row) == 3 :
                    matches = NUMERICS_PATTERN.findall(flattened_row[2].text)
                    if len(matches) != 0 :
                        mash_temp.time = float(matches[0])
                    else :
                        logger.log("/!\\ Caught weird looking patterns for timing for beer {} when parsing mash temps data : {}".format(recipe.number, flattened_row[2].text))

            method_timings.mash_temps.append(mash_temp)

    # Extract fermentation steps
    if fermentation_elem :
        fermentation_rows = split_blocks_based_on_y_distance(fermentation_data_list)
        for row in fermentation_rows :
            columns = group_in_distinct_columns(row)
            flattened_row = concatenate_columns(columns)

            # Fermentation steps usually contain 2 elements
            # But the fermentation "tips" fit in a single row
            if len(flattened_row) > 1 :
                # Handle fermentation steps as well
                # Note that the protections below are there to protect against the infamous secret beer #89 which does not come with ingredients nor
                # Mashing/Fermentation data
                matches = DEGREES_PATTERN.findall(fermentation_data_list[0].text)
                if len(matches) != 0 :
                    method_timings.fermentation.celsius = float(matches[0])
                else :
                    logger.log("/!\\ Caught weird looking patterns for fermentation temperature for beer {} when parsing mash temps data : {}".format(recipe.number, fermentation_data_list[0].text))

                matches = DEGREES_PATTERN.findall(fermentation_data_list[0].text)
                if len(matches) != 0 :
                    method_timings.fermentation.fahrenheit = float(matches[0])
                else :
                    logger.log("/!\\ Caught weird looking patterns for fermentation temperature for beer {} when parsing mash temps data : {}".format(recipe.number, fermentation_data_list[0].text))
            else :
                method_timings.fermentation.tips.append(flattened_row[0].text)

    # Parse twists, if any
    if twist_elem and len(twist_data_list) != 0:
        method_timings.twists = []
        twist_rows = split_blocks_based_on_y_distance(twist_data_list)
        for row in twist_rows :
            columns = group_in_distinct_columns(row)
            flattened_row = concatenate_columns(columns)
            flattened_row.sort(key=lambda x : x.x)

            twist = rcp.Twist()
            twist.name = flattened_row[0].text

            # Some twists are decoupled with the amount (g) and Time columns
            if len(flattened_row) == 3 :
                matches = NUMERICS_PATTERN.findall(flattened_row[1].text)
                if len(matches) != 0 :
                    twist.amount = float(matches[0])
                else :
                    twist.amount = -1.0
                    logger.log("/!\\ Missing data for twist amount in beer {}. Parsed block was : {}".format(recipe.number, line_from_text_elements(flattened_row)))

                # Misformatting strikes again !
                if recipe.number == 103 :
                    twist.when = flattened_row[1].text

            method_timings.twists.append(twist)

    recipe.method_timings = method_timings
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

    blocks = split_blocks_based_on_y_distance(elements)
    out : list[TextElement] = []

    # Now we need to order blocks with malt name, weight (grams or kg), weight (lb)
    for block in blocks :
        # We need to sort out data based on x placement now so that we can isolate kgs and lbs data
        x_sorted = copy(block)
        x_sorted.sort(key=lambda x : x.x)
        x_groups = group_in_distinct_columns(x_sorted)

        kg_data = x_groups[len(x_groups) - 2][1][0] # Taking the first element, should be the only one
        lb_data = x_groups[len(x_groups) - 1][1][0] # Taking the first element, should be the only one
        malt_text_list : list[TextElement] = x_groups[0][1]
        malt_text_list.sort(key=lambda x : x.y, reverse=True)

        # Aggregate data if need be
        new_elem = copy(malt_text_list[0])
        for elem in malt_text_list[1:] :
            new_elem.text += " " + elem.text.strip()
        new_elem.text.strip()
        out.append(new_elem)
        out.append(kg_data)
        out.append(lb_data)

    return out


class HopParsingErrors(Enum):
    ERROR_INCORRECT_AMOUNT="Error, incorrect amount",
    ERROR_OK = "No error"


def parse_ingredients_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    malt_elem = find_element(elements, "MALT")
    hops_elem = find_element(elements, "HOPS")
    yeast_elem = find_element(elements, "YEAST")

    # Beer without ingredients, the beer #89 is one of them
    if not malt_elem and not hops_elem and not yeast_elem :
        recipe.ingredients.alternative_description = ""
        for elem in elements :
            if elem.text == "INGREDIENTS" :
                continue
            recipe.ingredients.alternative_description += elem.text + " "
        recipe.ingredients.alternative_description = recipe.ingredients.alternative_description.strip()
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
    preprocessed_malts = pre_process_malts(malt_data_list)


    for i in range(0, int(len(preprocessed_malts) / malt_data_per_row)) :
        index = i * malt_data_per_row
        dataset = [
            preprocessed_malts[index],      # Aggregated malt text (name)
            preprocessed_malts[index + 1],  # Kg data
            preprocessed_malts[index + 2]   # Lb data
        ]

        new_malt = rcp.Malt()
        new_malt.name = dataset[0].text

        # Assuming malt is always provided either as "kg" or "lb" (it happens that on some recipes, data is misformatted)
        # Sometimes, unit is missing (such as in the beer #185, missing "lb", sometimes it is misspelled (6.6gal1lb -> Typo))
        # And sometimes the "k" of "kg" disappeared, giving incorrect malt amounts such as
        # in the beer #4 whose Carafa special says "0.18 grams". Who will ever put 0.18 grams of malt in a recipe ??
        match = NUMERICS_PATTERN.match(dataset[1].text)
        if match :
            new_malt.kgs = float(match.groups()[0])
        match = NUMERICS_PATTERN.match(dataset[2].text)
        if match :
            new_malt.lbs = float(match.groups()[0])
        recipe.ingredients.malts.append(new_malt)


    # Parse hops
    hops_data_list.sort(key=lambda x : x.y, reverse=True)
    assert("(g" in hops_data_list[0].text)

    # The beer #68 encodes the "Add" as "min" so we need to handle that case as well
    assert(hops_data_list[1].text == "Add" or "(min" in hops_data_list[1].text)
    assert(hops_data_list[2].text == "Attribute")

    threshold = 1.5
    if recipe.number == 237 or recipe.number == 250 :
        threshold = 1.8

    hops_rows = split_blocks_based_on_y_distance(hops_data_list[3:], threshold = threshold)
    hops_parsing_error = HopParsingErrors.ERROR_OK
    for row in hops_rows :
        columns = group_in_distinct_columns(row, 0.005)
        dataset = concatenate_columns(columns)
        dataset.sort(key=lambda x : x.x)

        # Sometimes, attributes is missing (this can be the case for )
        attribute = "N/A"
        when = ""
        amount = -1.0
        name = ""

        columns_count = len(dataset)
        if columns_count == 4 :
            attribute = dataset[columns_count - 1].text
            columns_count -= 1

        when = dataset[columns_count - 1].text
        # We need the regex pattern because on some beers, the "g" is there as well !
        match = NUMERICS_PATTERN.match(dataset[columns_count - 2].text)
        if match :
            amount = float(match.groups()[0])
        else:
            logger.log("/!\\ Could not extract amount from beer {}. Original text was : {}".format(recipe.number, dataset[columns_count - 2].text))
            hops_parsing_error = HopParsingErrors.ERROR_INCORRECT_AMOUNT
        name = dataset[0].text

        new_hop = rcp.Hop(name=name, amount=amount, when=when, attribute=attribute)
        recipe.ingredients.hops.append(new_hop)
        if hops_parsing_error != HopParsingErrors.ERROR_OK:
            recipe.add_parsing_error("Had some issues when reading hop : guessed name : {} . Reason : '{}'. Use the pdf page for reference !".format(name, hops_parsing_error.value))


    # Parse yeast
    for yeast_data in yeast_data_list :
        new_yeast = rcp.Yeast(name=yeast_data.text)
        recipe.ingredients.yeasts.append(new_yeast)

    return recipe

def parse_food_pairing_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    elements.sort(key=lambda x : x.y, reverse=True)
    rows = split_blocks_based_on_y_distance(elements)
    food_pairing = rcp.FoodPairing()
    for row in rows :
        # Skipping this element, we don't need it now
        if find_element(row, "FOOD PAIRING") :
            continue

        raw_columns = group_in_distinct_columns(row)
        flattened_rows = concatenate_columns(raw_columns)
        flattened_rows.sort(key=lambda x : x.x)

        for dataset in flattened_rows :
            food_pairing.pairings.append(dataset.text)

    recipe.food_pairing = food_pairing
    return recipe

def parse_brewers_tip_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    description = ""

    # Pop the first element "BREWERS TIP", we don't want that in the description
    for elem in elements[1:] :
        description += elem.text + " "
    recipe.brewers_tip.text = description.strip()
    return recipe

def parse_packaging_category(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :
    # TODO : find packaging based on image aspect ratio and / or the sometimes mentioned 'keg only'
    packaging = rcp.Packaging()
    if find_element(elements, "KEG ONLY") :
        packaging.type = rcp.PackagingType.Keg

    recipe.packaging = packaging
    return recipe

def extract_body(elements : list[TextElement], recipe : rcp.Recipe) -> rcp.Recipe :

    this_beer_is_elem   : TextElement = find_element_strict(elements, "THIS BEER IS")
    basics_elem         : TextElement = find_element_strict(elements, "BASICS")
    ingredients_elem    : TextElement = find_element_strict(elements, "INGREDIENTS")
    method_timings_elem : TextElement = find_element_strict(elements, "METHOD / TIMINGS")
    brewers_tip_elem    : TextElement = find_element_strict(elements, "BREWER\x92S TIP")
    packaging_elem      : TextElement = find_element_strict(elements, "PACKAGING")

    # Food pairing is not always there for all recipes
    food_pairing_elem   : Optional[TextElement] = find_element(elements, "FOOD PAIRING")


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
    column_2_x_start = packaging_elem.x - 20

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

    # Sometimes, the Method / timings element is not placed correctly (pdf placing artifacts...?)
    # Custom code for beer # 307 ... such a shame to do that kind of stuff ...
    if recipe.number == 307 :
        found = find_element(column_1_elements, "METHOD / TIMINGS")
        if found :
            logger.log("Found Method/Timings element in wrong column, moving it to column 0")
            column_1_elements.remove(found)

            # Duplicate parts of the previous element
            mash_temp_elem = find_element(column_0_elements, "MASH TEMP")
            if mash_temp_elem :
                found.x = mash_temp_elem.x - 10
                found.y = mash_temp_elem.y + 10
                column_0_elements.append(found)
            else :
                raise Exception("Could not find Mashing temperature data in current page ; beer number is {}".format(recipe.number))

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

    for element in page.elements :
        # Convert that to a TextElement to get rid of unnecessary data
        if element.y >= header_y_limit :
            header_elements.append(element)
        elif element.y <= footer_y_limit :
            footer_elements.append(element)
        else :
            body_elements.append(element)

    out = rcp.Recipe()
    out = extract_header(header_elements, out)
    out = extract_footer(footer_elements, out)
    out = extract_body(body_elements, out)
    return out


def main(args) :
    arg_parser = argparse.ArgumentParser("Python DiyDogExtractor tool. This software downloads the published DiyDog pdf book and tries to reconstruct a complete database out of it/")
    arg_parser.add_argument("force_caching", default="false", help="Force the tool to regenerate its cache from scratch. Downloads only if .pdf file is not there")
    arg_parser.add_argument("skip_image_extraction", default="false", help="Skips the image extraction step, as it takes quite a long time to achieve")
    arg_parser.add_argument("aggregate_results", default="false", help="Aggregates single recipes in a single big recipe collection")
    commands = arg_parser.parse_args(args)

    force_caching = commands.force_caching == "true"
    skip_image_extraction = commands.skip_image_extraction == "true"
    aggregate_results = commands.aggregate_results == "true"


    if force_caching :
        logger.log("Force caching mode activated")

    if skip_image_extraction :
        logger.log("Image extraction step skipping activated")

    if aggregate_results :
        logger.log("json data will also be aggregated into a single file")

    cached_pages_dir = CACHE_DIRECTORY.joinpath("pages")
    cached_blocks_dir = CACHE_DIRECTORY.joinpath("blocks")
    cached_pdf_raw_content = CACHE_DIRECTORY.joinpath("pdf_raw_contents")
    cached_images_dir = CACHE_DIRECTORY.joinpath("images")
    cached_extracted_recipes = CACHE_DIRECTORY.joinpath("extracted_recipes")
    # Pages decoded content with pypdf library
    cached_content_dir = CACHE_DIRECTORY.joinpath("contents")
    #cached_custom_blocks = CACHE_DIRECTORY.joinpath("custom_blocks")

    pdf_file = CACHE_DIRECTORY.joinpath("diydog-2022.pdf")
    if not pdf_file.exists() :
        logger.log("Downloading brewdog's Diydog pdf booklet ...")
        download_pdf(C_DIYDOG_URL, pdf_file, logger)
        logger.log("-> OK : Downloading succeeded ! Pdf file was downloaded at : {}".format(pdf_file))
        # Triggers force caching because we need to regenerate everything
        force_caching = True

    pages_content : list[PageBlocks] = []
    # List already cached pages before going, if nothing is there then trigger the force cache flag
    logger.log("Listing available pdf pages before starting up ...")
    pages_list = list_pages(cached_pages_dir, "page_", ".pdf")
    if len(pages_list) < 100 :
        force_caching = True
        logger.log("Very few pages were found on disk (actually : {} pages), app will regenerate the cache now.".format(len(pages_list)))

    # Extract pages for caching purposes
    if force_caching :
        logger.log("Extracting all beer pages to {}".format(cached_pages_dir))
        with open(pdf_file, "rb") as file :
            reader = PdfReader(file)

            # Page 22 is the first beer
            start_page = 21

            # Page 436 is the very last beer
            end_page = 436

            for i in range(start_page, end_page) :
                beer_index = i - start_page + 1
                logger.log("Extracting page : {}, beer index : {}".format(i, beer_index))
                encoded_name = "page_{}".format(beer_index)
                page = reader.pages[i]


                logger.log("Caching page to disk ...")
                cache_single_pdf_page(cached_pages_dir.joinpath(encoded_name + ".pdf"), page=page)
                content_filepath = cached_content_dir.joinpath(encoded_name + ".json")

                # Fetch raw contents and manually parse it (works better than brute text extraction from pypdf)
                logger.log("Extracting textual content of page ...")
                raw_contents = page.get_contents()

                if raw_contents == None :
                    raise Exception("Cannot read page !")
                data = bytes(raw_contents.get_data())

                str_contents : str
                try :
                    # File is written with the iso-8859-1 encoding and does not play well with the rest of the parsing
                    str_contents = data.decode("iso-8859-1")
                except Exception as ex :
                    logger.log("/!\\ Caught exception while parsing")
                    logger.log("   Exception was : {}".format(ex))
                    continue
                cache_pdf_raw_contents(cached_pdf_raw_content.joinpath(encoded_name + ".txt"), str_contents )

                raw_blocks = extract_raw_text_blocks_from_content(str_contents)
                logger.log("Caching raw text blocks ...")
                cache_raw_blocks(cached_blocks_dir.joinpath(encoded_name + ".txt"), raw_blocks )

                logger.log("Parsing raw text blocks into pre-processed text blocks")
                text_blocks = text_blocks_from_raw_blocks(raw_blocks)

                # Post processing of text blocks :
                logger.log("Post processing text blocks ...")
                temp_blocks = []
                for block in text_blocks :
                    # Strip whitespaces and removes empty items
                    block.text = block.text.strip()
                    if block.text != "" :
                        temp_blocks.append(block)

                text_blocks = temp_blocks

                logger.log("Caching preprocessed contents ...")
                # Adding page blocks now, so that we
                # don't have to parse them again
                page_blocks = PageBlocks()
                page_blocks.elements = text_blocks
                page_blocks.index = beer_index
                pages_content.append(page_blocks)
                cache_contents(content_filepath, page_blocks)

        logger.log("-> OK : Pages extracted successfully in {}".format(cached_pages_dir))


    # List already cached pages
    logger.log("Listing available pdf pages ...")
    pages_list = list_pages(cached_pages_dir, "page_", ".pdf")
    logger.log("-> OK : Found {} pages in {}".format(len(pages_list), cached_pages_dir))

    # List already cached images
    logger.log("Listing available pages images and extracted images...")
    images_list = list_files(cached_images_dir, "extracted_silhouette", ".png")

    # Extracting pdf rendered images !
    if skip_image_extraction == False and len(images_list) < 100 :
        logger.log("Found few {} pages images in {}. Triggering image extraction again.".format(len(images_list), cached_pages_dir))
        logger.log("Caching images to disk ...")

        # DEBUG : used to only feed those pages to the image extraction process
        # Comment out to extract every page on regular list
        #candidates = [1, 8, 11, 16, 63, 172]

        for page in pages_list :

            # DEBUG : skip images that are not in this list (used to determine aspect ratios for known images)
            #if page[0] not in candidates :
            #    continue

            page_images_dir = cached_images_dir.joinpath(page[1].stem)
            logger.log("Caching images for page {}".format(page[1].stem))
            cache_images(page_images_dir, page[1], page[0])
    else :
        logger.log("-> OK : Found {} pages images in {}".format(len(images_list), cached_pages_dir))
        logger.log("Image extraction step skipped.")

    # List already cached images
    logger.log("Listing available pages images and extracted images...")
    images_list = list_files(cached_images_dir, "extracted_silhouette", ".png")
    logger.log("-> OK : Found {} pages images in {}".format(len(images_list), cached_pages_dir))

    logger.log("Listing available json content from pages ...")
    pages_content_list = list_pages(cached_content_dir, "page_", ".json")
    logger.log("-> OK : Found {} pages in {}".format(len(pages_list), cached_pages_dir))
    for page in pages_content_list :
        page_index = page[0]
        found_elem = [x for x in pages_content if  x.index == page_index ]
        # Skip deserialization if it already exist in memory
        if len(found_elem) != 0 :
            continue

        logger.log("Reading back cached text content from json file {}".format(page[1].name))
        page_blocks = PageBlocks()
        page_blocks.index = page_index
        with open(page[1], "r") as file :
            data = json.load(file)
            page_blocks.from_json(data)
        pages_content.append(page_blocks)

    logger.log("Parsing actual recipe content from extracted text blocks")
    recipes_list : list[rcp.Recipe] = []
    for page in pages_content :
        logger.log("Parsing recipe from page {}".format(page.index))
        try :
            new_recipe = extract_recipe(page)
            recipes_list.append(new_recipe)
        except Exception as e :
            logger.log("Could not extract recipe from beer {}".format(page.index))
            logger.log("Error was : {}".format(e))
            logger.log(traceback.format_exc())

    # Dump recipes on disk now !
    if not cached_extracted_recipes.exists() :
        cached_extracted_recipes.mkdir(parents=True)

    logger.log("Dumping extracted recipes on disk now !")
    for recipe in recipes_list :
        logger.log("Dumping recipe {}, number {}".format(recipe.name, recipe.number))
        filename = "recipe_{}.json".format(recipe.number)
        filepath = cached_extracted_recipes.joinpath(filename)
        with open(filepath, "w") as file :
            json.dump(recipe.to_json(), file, indent=4)

    if aggregate_results :
        logger.log("Dumping aggregated recipe json book as 'all_recipes.json'.")
        json_data = []
        for recipe in recipes_list :
            json_data.append(recipe.to_json())
        filepath = cached_extracted_recipes.joinpath("all_recipes.json")
        with open(filepath, "w") as file :
            json.dump({"recipes" : json_data}, file, indent=4)


    logger.log("Done !")

if __name__ == "__main__" :
    try :
        main(sys.argv[1:])
    except Exception as e :
        logger.log("-> ERROR : Caught exception while running script, error was  : {}".format(e))
        raise e