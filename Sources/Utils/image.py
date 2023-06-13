from array import array
import math
import sys
import cv2
import numpy as np
from matplotlib import pyplot as plt
from pathlib import Path

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

def _compute_aspect_ratio(contour : array) -> float :
    x_boundaries = [0.0, 0.0]
    y_boundaries = [0.0, 0.0]

    for point in contour :
        x_boundaries = _find_min_max(point[0], x_boundaries)
        y_boundaries = _find_min_max(point[1], y_boundaries)

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

    biggest_contour = perimeter_contour_map[0][1]

    # Save figure to disk
    perimeter = perimeter_contour_map[0][0]
    aspect_ratio = _compute_aspect_ratio(biggest_contour)
    return (perimeter, aspect_ratio, biggest_contour)

def _extract_image(img : cv2.Mat, contour : np.ndarray, output_filepath : Path, background_color=(0,0,0,0)) :

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
    output_image.save(output_filepath)

def _ensure_folder_exist(folder_path : Path) :
    if not folder_path.exists():
        folder_path.mkdir(parents=True)




def extract_biggest_silhouette(source : Path, destination : Path, background_color = (0,0,0,0)) -> tuple[float, float]:
    """Extracts the biggest contiguous/opaque element from a source image and produces a .png output image with transparency
       @param :
            source           : source image file path
            destination      : output image file path
            background_color : output image will have this background color (rgba format). Default is transparent.
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
    [perimeter, aspect_ratio,contour] = _scikit_find_biggest_contour(gray)

    print("Extracted contour for image \"{}\" with perimeter : {} and aspect ratio : {}".format(source.name, perimeter, aspect_ratio))

    # Force encode output as .png, in order to be sure file format supports transparency
    output_image = destination.parent.joinpath(destination.stem + ".png")
    _extract_image(img, contour, output_image, background_color)

    return (perimeter, aspect_ratio)
