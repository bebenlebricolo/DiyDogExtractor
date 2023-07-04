from dataclasses import dataclass, field
from enum import Enum

from typing import cast, Optional, Generic, TypeVar
from thefuzz import fuzz
from statistics import geometric_mean

from ..Models.DBSanizer.known_good_props import *

class FuzzMode(Enum) :
    """Used to control fuzzy search algorithm"""
    Ratio = 0
    PartialRatio = 1
    PartialTokenSetRatio = 2
    PartialTokenSortRatio = 3
    TokenSetRatio = 4
    TokenSortRatio = 5

T = TypeVar("T", YeastProp, HopProp, MaltProp, StylesProp)
@dataclass
class MostProbablePropertyHit(Generic[T]) :
    score : float = 0
    hit : Optional[T] = None

def fuzzy_search_prop(ref_list: list[T], specimen_str : str, fuzz_mode : FuzzMode = FuzzMode.Ratio) -> tuple[str, MostProbablePropertyHit[T]]:
    most_probable_hit = fuzzy_search_in_ref(specimen_str, ref_list, fuzz_mode)
    pair = (specimen_str, most_probable_hit)
    return pair


def compute_string_ratios(tag : str, token : str, fuzz_mode : FuzzMode = FuzzMode.Ratio) -> int :
    ratio = 0
    match fuzz_mode:
        case FuzzMode.Ratio :
            ratio = fuzz.ratio(tag, token)

        case FuzzMode.PartialRatio :
            ratio = fuzz.partial_ratio(tag, token)

        case FuzzMode.PartialTokenSetRatio :
            ratio = fuzz.partial_token_set_ratio(tag, token)

        case FuzzMode.PartialTokenSortRatio :
            ratio = fuzz.partial_token_sort_ratio(tag, token)

        case FuzzMode.TokenSetRatio :
            ratio = fuzz.token_set_ratio(tag, token)

        case FuzzMode.TokenSortRatio :
            ratio = fuzz.token_sort_ratio(tag, token)

        case _:
            # Not supported !
            raise Exception("Not supported fuzz mode !")
    return ratio

def normalise_ratio_result(ratio : int) -> int :
    out = ratio
    if ratio <= 0:
        out = 1
    return out

def fuzzy_search_in_ref(tag : str, ref_list : list[T], fuzz_mode : FuzzMode = FuzzMode.Ratio) -> MostProbablePropertyHit[T] :
    # Trying to minimize the hamming distance
    max_ratio = 0
    most_probable_hit = MostProbablePropertyHit(0, ref_list[0])

    for prop in ref_list :
        ratios = []
        result = compute_string_ratios(tag, prop.name.value, fuzz_mode)
        ratios.append(normalise_ratio_result(result))

        if hasattr(prop, "aliases") and prop.aliases.value is not None : #type:ignore
            for alias in prop.aliases.value : #type:ignore
                result = compute_string_ratios(tag.lower(), alias.lower(), fuzz_mode)

                # If any alias has a 100 match score (the whole alias exactly match the whole input sequence)
                # Then we're sure that we've found the right item, so skip next ones.
                # This is to ensure that the geometric mean does not tear down our results in case a really good match is found, as it often happens when a target prop has multiple
                # matching aliases versus another item that has no aliases.
                # It happens because out of 3 aliases, maybe one will have a very good match while the other ones not that much (20 * 100 * 35)^1/3 = 41 whereas we have an exact match in there !
                if result >= 98 :
                    most_probable_hit = MostProbablePropertyHit(result, prop)
                    return most_probable_hit

                # Required because geometric mean is sensitive to zeros and non positive values, so artificially set the score to 1 to prevent
                # a numeric failure -> clamp result to 1
                ratios.append(normalise_ratio_result(result))

        computed_ratio = geometric_mean(ratios)

        if computed_ratio > max_ratio :
            max_ratio = computed_ratio
            most_probable_hit = MostProbablePropertyHit(computed_ratio, prop)

        # Stop in case we've found the perfect hit one
        if computed_ratio == 100 :
            break

    return most_probable_hit