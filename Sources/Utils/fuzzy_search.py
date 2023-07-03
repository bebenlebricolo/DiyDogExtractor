from dataclasses import dataclass, field
from enum import Enum

from typing import cast, Optional, Generic, TypeVar
from thefuzz import fuzz
from statistics import geometric_mean

from ..Models.DBSanizer.known_good_props import *


T = TypeVar("T", YeastProp, HopProp, MaltProp, StylesProp)
@dataclass
class MostProbablePropertyHit(Generic[T]) :
    score : float = 0
    hit : Optional[T] = None

def fuzzy_search_prop(ref_list: list[T], specimen_str : str) -> tuple[str, MostProbablePropertyHit[T]]:
    most_probable_hit = fuzzy_search_in_ref(specimen_str, ref_list)
    pair = (specimen_str, most_probable_hit)
    return pair


def compute_string_ratios(tag : str, token : str) -> int :
    distance = fuzz.ratio(tag, token)
    return distance

def fuzzy_search_in_ref(tag : str, ref_list : list[T]) -> MostProbablePropertyHit[T] :
    # Trying to minimize the hamming distance
    max_ratio = 0
    most_probable_hit = MostProbablePropertyHit(0, ref_list[0])

    for prop in ref_list :
        ratios = []
        ratios.append(compute_string_ratios(tag, prop.name.value))

        if hasattr(prop, "aliases") and prop.aliases is not None : #type:ignore
            for alias in prop.aliases.value : #type:ignore
                result = compute_string_ratios(tag, alias)

                # Required because geometric mean is sensitive to zeros and non positive values, so artificially set the score to 1 to prevent
                # a numeric failure -> clamp result to 1
                if result <= 0:
                    result = 1
                ratios.append(result)

        computed_ratio = geometric_mean(ratios)

        if computed_ratio > max_ratio :
            max_ratio = computed_ratio
            most_probable_hit = MostProbablePropertyHit(computed_ratio, prop)

        # Stop in case we've found the perfect hit one
        if computed_ratio == 100 :
            break

    return most_probable_hit