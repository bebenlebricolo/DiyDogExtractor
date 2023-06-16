from enum import Enum
from typing import Optional
from dataclasses import dataclass, field

# Local utils imports
from .jsonable import JsonProps_custom_equal, Jsonable, JsonProperty, JsonOptionalProperty
from .record import Record, RecordBuilder, RecordKind, FileRecord, CloudRecord

@dataclass
class Description(Jsonable) :
    text : str = ""

    def from_json(self, content) -> None:
        self.text = self._read_prop("text", content, "")

    def to_json(self) -> dict:
        return {
            "text" : self.text
        }

@dataclass
class Volume(Jsonable) :
    litres : float = 0.0
    galons : float = 0.0

    def to_json(self) -> dict:
        return self.__dict__

    def from_json(self, content) -> None:
        self.__dict__ = content

@dataclass
class Basics(Jsonable) :
    volume : Volume = field(default_factory=Volume)
    boil_volume : Volume = field(default_factory=Volume)
    abv : float = 0.0
    target_og : float = 1000.0
    target_fg : float = 1000.0
    ebc : float = 0.0
    ibu : float = 0.0
    srm : float = 0.0
    ph : float = 7.0
    attenuation_level : float = 80.0

    def to_json(self) -> dict:
        return {
            "volume" : self.volume.to_json(),
            "boilVolume" : self.boil_volume.to_json(),
            "abv" : self.abv,
            "targetOg" : self.target_og,
            "targetFg" : self.target_fg,
            "ebc" : self.ebc,
            "ibu" : self.ibu,
            "srm" : self.srm,
            "ph" : self.ph,
            "attenuationLevel" : self.attenuation_level
        }

    def from_json(self, content: dict) -> None:
        if "volume" in content :
            self.volume.from_json(content["volume"])
        if "boilVolume" in content :
            self.boil_volume.from_json(content["boilVolume"])
        self.abv = self._read_prop("abv", content, 0.0)
        self.target_fg = self._read_prop("targetFg", content, 1000)
        self.target_og = self._read_prop("targetOg", content, 1000)
        self.ebc = self._read_prop("ebc", content, 0)
        self.ibu = self._read_prop("ibu", content, 0)
        self.srm = self._read_prop("srm", content, 0.0)
        self.ph = self._read_prop("ph", content, 7.0)
        self.attenuation_level = self._read_prop("attenuationLevel", content, 80.0)

@dataclass
class FoodPairing(Jsonable):
    pairings : list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return self.__dict__

    def from_json(self, content: dict) -> None:
        if "pairings" in content :
            self.pairings = []
            for item in content["pairings"] :
                self.pairings.append(item)

@dataclass
class Malt(Jsonable) :
    name : str = ""
    kgs : float = 0.0
    lbs : float = 0.0

    def to_json(self) -> dict:
        return self.__dict__

    def from_json(self, content: dict) -> None:
        self.name = self._read_prop("name", content, "")
        self.kgs = self._read_prop("kgs", content, 0.0)
        self.lbs = self._read_prop("lbs", content, 0.0)

@dataclass
class Hop(Jsonable) :
    name : str  = ""
    amount : float = 0.0
    when : str = ""
    attribute : str = ""

    def to_json(self) -> dict:
        return {
            "name" : self.name,
            "amount" : self.amount,
            "when" : self.when,
            "attribute" : self.attribute
        }

    def from_json(self, content: dict) -> None:
        self.name = self._read_prop("name", content, "")
        self.amount = self._read_prop("amount", content, 0.0)
        self.when = self._read_prop("when", content, "")
        self.attribute = self._read_prop("attribute", content, "")

@dataclass
class Yeast(Jsonable) :
    name : str = ""

    def from_json(self, content: dict) -> None:
        self.name = self._read_prop("name", content, "")

    def to_json(self) -> dict:
        return self.__dict__

@dataclass
class Ingredients(Jsonable) :
    MALTS_KEY = "malts"
    HOPS_KEY = "hops"
    YEASTS_KEY = "yeasts"
    DESCRIPTION_KEY = "alternativeDescription"

    malts : list[Malt] = field(default_factory=list)
    hops : list[Hop] = field(default_factory=list)
    yeasts : list[Yeast] = field(default_factory=list)
    alternative_description : Optional[str] = None

    def to_json(self) -> dict:
        malts_list = [x.to_json() for x in self.malts]
        hops_list = [x.to_json() for x in self.hops]
        yeast_list = [x.to_json() for x in self.yeasts]

        return {
            self.MALTS_KEY : malts_list,
            self.HOPS_KEY : hops_list,
            self.YEASTS_KEY : yeast_list,
            self.DESCRIPTION_KEY : self.alternative_description
        }

    def from_json(self, content: dict) -> None:
        if self.MALTS_KEY in content :
            self.malts = []
            for malt in content[self.MALTS_KEY] :
                new_malt = Malt()
                new_malt.from_json(malt)
                self.malts.append(new_malt)

        if self.HOPS_KEY in content :
            self.hops = []
            for hop in content[self.HOPS_KEY] :
                new_hop = Hop()
                new_hop.from_json(hop)
                self.hops.append(new_hop)

        if self.YEASTS_KEY in content :
            self.yeasts = []
            for yeast in content[self.YEASTS_KEY] :
                new_yeast = Yeast()
                new_yeast.from_json(yeast)
                self.yeasts.append(new_yeast)

        if self.DESCRIPTION_KEY in content :
            self.alternative_description = content[self.DESCRIPTION_KEY]


@dataclass
class BrewersTip(Jsonable) :
    text : str = ""

    def from_json(self, content: dict) -> None:
        self.text = self._read_prop("text", content, "")

    def to_json(self) -> dict:
        return self.__dict__

@dataclass
class Temperature(Jsonable) :
    celsius : float = 0.0       # celsius degrees
    fahrenheit : float = 0.0     # fahrenheit degrees

    def from_json(self, content: dict) -> None:
        self.celsius = self._read_prop("celsius", content, 0.0)
        self.fahrenheit = self._read_prop("fahrenheit", content, 0.0)

    def to_json(self) -> dict:
        return self.__dict__

@dataclass
class MashTemp(Temperature) :
    time : float = 0.0          # in minutes

    def from_json(self, content: dict) -> None:
        self.__init__()
        super().from_json(content)
        self.time = self._read_prop("time", content, 0.0)

    def to_json(self) -> dict:
        return self.__dict__

@dataclass
class Fermentation(Temperature) :
    tips : list[str] = field(default_factory=list)

    def from_json(self, content: dict) -> None:
        self.__init__()
        super().from_json(content)
        if "tips" in content:
            for tip in content["tips"] :
                self.tips.append(tip)

    def to_json(self) -> dict:
        return self.__dict__

@dataclass
class Twist(Jsonable) :
    name : str = ""
    amount : Optional[float] = None # This is optional as some twists are simply text hints/techniques
                                    # If set, this field stands for an amount in grams
    when : Optional[str] = None # used when the amount is provided

    def to_json(self) -> dict:
        return self.__dict__

    def from_json(self, content: dict) -> None:
        # Reset class
        self.__init__()
        self.name = self._read_prop("name", content, "")
        if "amount" in content and content["amount"]:
            self.amount = content["amount"]
        if "when" in content and content["when"] :
            self.when = content["when"]


@dataclass
class MethodTimings(Jsonable) :
    mash_temps : list[MashTemp] = field(default_factory=list)
    mash_tips : list[str] = field(default_factory=list)
    fermentation : Fermentation = field(default_factory=Fermentation)
    twists : Optional[list[Twist]] = None

    def to_json(self) -> dict:
        out = {
            "mashTemps" : [x.to_json() for x in self.mash_temps],
            "mashTips" : [x for x in self.mash_tips],
            "fermentation" : self.fermentation.to_json(),
            "twists" : None
        }
        if self.twists :
            twists = [x.to_json() for x in self.twists]
            out["twists"] = twists
        return out

    def from_json(self, content: dict) -> None:
        self.__init__()

        if "mashTemps" in content :
            self.mash_temps = []
            for temp in content["mashTemps"] :
                new_temp = MashTemp()
                new_temp.from_json(temp)
                self.mash_temps.append(new_temp)

        if "mashTips" in content :
            for tip in content["mashTips"] :
                self.mash_tips.append(tip)

        if "fermentation" in content :
            self.fermentation.from_json(content["fermentation"])

        if "twists" in content :
            self.twists = None
            if content["twists"] :
                self.twists = []
                for twist in content["twists"] :
                    new_twist = Twist()
                    new_twist.from_json(twist)
                    self.twists.append(new_twist)

class PackagingType(Enum) :
    Bottle = "Bottle"
    BigBottle = "BigBottle"
    Squirrel = "Squirrel" # Yes ... there is a squirrel in their bottles... number 63 - "The end of history" !
    Keg = "Keg"
    Barrel = "Barrel"
    Can = "Can"

@dataclass
class Packaging(Jsonable) :
    # Enums are not considered as mutable dataclasses, so plain initialization like this one works out of the box
    # Otherwise we can't get this to work with regular @dataclass and field(default_factory=...) for `PackagingType` object.
    type : PackagingType = PackagingType.Bottle

class Recipe(Jsonable) :
    image : JsonProperty[Record]                    # Ref to file with image
    original_pdf_page : JsonProperty[Record]        # Ref to original pdf page extracted from DiyDog book

    name : str          # Beer title
    subtitle : str      # Beer subtitle, contains tags and other information
    number : int        # Refers to the "#1" tag
    page_number : int   # page number as parsed from pdf page
    tags : list[str]    # tag line
    first_brewed : str  # Date of first brew

    # ibu -> Ibus are stored within the "Basics" object, despite not 100% matching the recipe it makes sense to have it there instead
    description : Description
    basics : Basics
    ingredients : Ingredients
    brewers_tip : BrewersTip
    method_timings : MethodTimings
    packaging : Packaging

    # Some beers have parsing errors along the way, so list some potential issues here and let the end user check the pdf instead
    parsing_errors : Optional[list[str]]
    # Some beers don't have food pairing associated (happens for beer #79 and #156)
    food_pairing : Optional[FoodPairing]


    def __init__( self, name : str = "",
                  subtitle : str = "",
                  number : int = 0,
                  page_number : int = 0,
                  tags : list[str] = [],
                  first_brewed : str = "",
                  description : Description = Description(),
                  basics : Basics = Basics(),
                  ingredients : Ingredients = Ingredients(),
                  brewers_tip : BrewersTip = BrewersTip(),
                  method_timing : MethodTimings = MethodTimings(),
                  packaging : Packaging = Packaging()) :
        self.image = JsonProperty('image', FileRecord())
        self.original_pdf_page = JsonProperty('originalPdfPage', FileRecord())
        self.name = name
        self.subtitle = subtitle
        self.number = number
        self.page_number = page_number
        self.tags = tags
        self.first_brewed = first_brewed
        self.description = description
        self.basics = basics
        self.ingredients = ingredients
        self.brewers_tip = brewers_tip
        self.method_timings = method_timing
        self.packaging = packaging
        self.parsing_errors = None
        self.food_pairing = None


    def to_json(self) -> dict:
        return {
            "name" : self.name,
            "subtitle" : self.subtitle,
            "number" : self.number,
            "pageNumber" : self.page_number,
            "tags" : self.tags,
            "firstBrewed" : self.first_brewed,
            self.image._prop_key : self.image.value.to_json(),
            self.original_pdf_page._prop_key : self.original_pdf_page.value.to_json(),
            "description" : self.description.to_json(),
            "basics" : self.basics.to_json(),
            "foodPairing" : self.food_pairing.to_json() if self.food_pairing else None,
            "ingredients" : self.ingredients.to_json(),
            "brewersTip" : self.brewers_tip.to_json(),
            "methodTimings" : self.method_timings.to_json(),
            "packaging" : self.packaging.to_json(),
            "parsingErrors" : self.parsing_errors
        }

    def from_json(self, content: dict) -> None:
        self.name = self._read_prop("name", content, "")
        self.subtitle = self._read_prop("subtitle", content, "")
        self.number = self._read_prop("number", content, 0)
        self.page_number = self._read_prop("pageNumber", content, 0)
        self.tags = []
        if "tags" in content :
            for tag in content["tags"] :
                self.tags.append(tag)
        self.first_brewed = self._read_prop("firstBrewed", content, "")

        # Image and Original PDF page deserve special handling, as they can be both a FileRecord or Cloud Record
        image_node = self.image.get_node(content)
        if image_node :
            parsed_record = RecordBuilder.from_json(image_node)
            self.image.value = parsed_record or self.image.value

        orig_pdf_node = self.original_pdf_page.get_node(content)
        if orig_pdf_node :
            parsed_record = RecordBuilder.from_json(orig_pdf_node)
            self.original_pdf_page.value = parsed_record or self.original_pdf_page.value

        if "description" in content :
            self.description.from_json(content["description"])
        if "basics" in content :
            self.basics.from_json(content["basics"])
        if "foodPairing" in content and content["foodPairing"] :
            self.food_pairing = FoodPairing()
            self.food_pairing.from_json(content["foodPairing"])
        if "ingredients" in content :
            self.ingredients.from_json(content["ingredients"])
        if "brewersTip" in content :
            self.brewers_tip.from_json(content["brewersTip"])
        if "methodTimings" in content :
            self.method_timings.from_json(content["methodTimings"])
        if "packaging" in content :
            self.packaging.from_json(content["packaging"])

        if "parsingErrors" in content and content["parsingErrors"] is not None:
            self.parsing_errors = []
            for elem in content["parsingErrors"] :
                self.parsing_errors.append(elem)

    def add_parsing_error(self, error_string : str) :
        if not self.parsing_errors :
            self.parsing_errors = []
        self.parsing_errors.append(error_string)

    def __eq__(self, other: object) -> bool:
        """Custom comparison tool as it seems the regular == one is not explicit (when using asserts)
        about what's the issue, so this comparison tool will help pinpoint what's the issue more easily"""
        if type(self) != type(other) :
            return False
        identical = True
        identical &= self.image ==  other.image                         #type: ignore
        identical &= self.original_pdf_page == other.original_pdf_page  #type: ignore
        identical &= self.name == other.name                            #type: ignore
        identical &= self.subtitle == other.subtitle                    #type: ignore
        identical &= self.number == other.number                        #type: ignore
        identical &= self.page_number == other.page_number              #type: ignore
        identical &= self.tags == other.tags                            #type: ignore
        identical &= self.first_brewed == other.first_brewed            #type: ignore
        identical &= self.description == other.description              #type: ignore
        identical &= self.basics == other.basics                        #type: ignore
        identical &= self.ingredients == other.ingredients              #type: ignore
        identical &= self.brewers_tip == other.brewers_tip              #type: ignore
        identical &= self.method_timings == other.method_timings        #type: ignore
        identical &= self.packaging == other.packaging                  #type: ignore
        identical &= self.parsing_errors == other.parsing_errors        #type: ignore
        identical &= self.food_pairing == other.food_pairing            #type: ignore
        return identical
