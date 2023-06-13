from array import array
import math
import sys
import cv2
import numpy as np
from pathlib import Path
from fitz import Pixmap

from skimage import measure
from skimage.draw import polygon

from PIL import Image


def _compute_perimeter(data : array) -> float:
    perimeter = 0.0
    for i in range(0,len(data)):
        if i == len(data) - 1 :
            pass
        # Should wrap back to 0 when i == len(data), so that we also compute the distance between the first and last item
        next = (i + 1) % (len(data))
        distance = math.sqrt(math.pow(data[i][0] - data[next][0], 2) + math.pow(data[i][1] - data[next][1], 2))
        perimeter += distance

    return perimeter

def _find_min_max(value : float, boundaries : list[float]) -> list[float] :
    if value < boundaries[0] :
        boundaries[0] = value
    if value > boundaries[1] :
        boundaries[1] = value
    return boundaries

def _compute_bounding_box(contour : np.ndarray) -> tuple[list[float], list[float]] :
    x_boundaries = [sys.float_info.max, 0.0]
    y_boundaries = [sys.float_info.max, 0.0]

    for point in contour :
        # Contours are given with the (row, column) nomenclature, so point[0] is the row (y) and point[1] the column (x) ... haha ...
        y_boundaries = _find_min_max(point[0], y_boundaries)
        x_boundaries = _find_min_max(point[1], x_boundaries)

    return (x_boundaries, y_boundaries)

def _compute_aspect_ratio(contour : np.ndarray) -> float :
    (x_boundaries, y_boundaries) = _compute_bounding_box(contour)
    aspect_ratio = (x_boundaries[1] - x_boundaries[0]) / (y_boundaries[1] - y_boundaries[0])
    return aspect_ratio

def _scikit_find_biggest_contour(gray : cv2.Mat) -> tuple[float, float, np.ndarray]:
     # Find contours at a constant value of 0.8
    contours : array = measure.find_contours(gray, 190)

    # Contours shaping / datastructure :
    # unique contour = list[2D arrays] -> list of x,y points in image space where [x, y] are stored in a 2d array
    # array of contours : list[contour] -> list[list[2D array]]
    # -> Points are very probably listed in direct order (order in which their linking constructs a non-crossing contour)
    # Api reference : https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.find_contours
    perimeter_contour_map = []
    for contour in contours:
        #ax.plot(contour[:, 1], contour[:, 0], linewidth=2)
        perimeter = _compute_perimeter(contour)
        perimeter_contour_map.append([perimeter, contour])

    # Sort decreasing, biggest perimeter first
    perimeter_contour_map.sort(key = lambda x : x[0], reverse=True)

    biggest_contour  : np.ndarray = perimeter_contour_map[0][1]

    # Save figure to disk
    perimeter = perimeter_contour_map[0][0]
    aspect_ratio = _compute_aspect_ratio(biggest_contour)
    return (perimeter, aspect_ratio, biggest_contour)

def _extract_image(img : cv2.Mat, contour : np.ndarray, output_filepath : Path, background_color=(0,0,0,0), fit_crop_image = True) :

    # Fill in the hole created by the contour boundary
    height = len(img)
    width = len(img[0])

    # Heavily inspired from http://tonysyu.github.io/scikit-image/auto_examples/plot_shapes.html
    extracted_image = np.full((height, width, 4), fill_value=background_color, dtype=np.uint8)
    rr, cc = polygon(contour[:,0], contour[:,1], img.shape )
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    extracted_image[rr, cc, 0:3] = rgb_img[rr, cc, 0:3]
    extracted_image[rr,cc,3] = 255

    output_image = Image.fromarray(extracted_image, mode="RGBA")
    if fit_crop_image :
        (x_boundaries, y_boundaries) = _compute_bounding_box(contour)
        left = x_boundaries[0]
        right = x_boundaries[1]
        top = y_boundaries[0]
        bottom = y_boundaries[1]
        output_image = output_image.crop((left, top, right, bottom))  # type: ignore

    output_image.save(output_filepath)

def _ensure_folder_exist(folder_path : Path) :
    if not folder_path.exists():
        folder_path.mkdir(parents=True)

def extract_biggest_silhouette(source : Path, destination : Path, background_color = (0,0,0,0), fit_crop_image = True) -> tuple[float, float]:
    """Extracts the biggest contiguous/opaque element from a source image and produces a .png output image with transparency
       @param :
            source           : source image file path
            destination      : output image file path
            background_color : output image will have this background color (rgba format). Default is transparent.
            fit_crop_image   : if set to True, will crop the image to the bounding box of the resulting object
       @returns :
            biggest contour perimeter (float) value
            aspect ratio of the image (float) value
    """

    output_folder = destination.parent
    _ensure_folder_exist(output_folder)

    if not source.exists() :
        print("Could not find input image at pointed disk node : {}".format(source))
        raise IOError("Could not read input image")

    img = cv2.imread(source.as_posix())
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Try with basic pixel thre
    [perimeter, aspect_ratio, contour] = _scikit_find_biggest_contour(gray)
    print("Extracted contour for image \"{}\" with perimeter : {} and aspect ratio : {}".format(source.name, perimeter, aspect_ratio))

    # Force encode output as .png, in order to be sure file format supports transparency
    output_image = destination.parent.joinpath(destination.stem + ".png")
    _extract_image(img, contour, output_image, background_color, fit_crop_image)

    return (perimeter, aspect_ratio)


def extract_zone_from_image(pixmap : Pixmap, box : list[float]) -> Image.Image :
    image_data = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

    left = int(round(box[0] * pixmap.width))
    right = int(box[1] *  pixmap.width)
    top = int(box[2] * pixmap.height)
    bottom = int(box[3] * pixmap.height)
    cropped_image = image_data.crop(box=(left, top, right, bottom)) # type: ignore

    return cropped_image