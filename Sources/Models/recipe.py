from enum import Enum
from typing import Optional
from dataclasses import dataclass, field

# Local utils imports
from .jsonable import Jsonable, JsonProperty, JsonOptionalProperty
from .record import Record, RecordBuilder, RecordKind, FileRecord, CloudRecord

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

    @staticmethod
    def can_convert(input : str) -> bool :
        return input in [PackagingType.Bottle.value,
                         PackagingType.BigBottle.value,
                         PackagingType.Squirrel.value,
                         PackagingType.Keg.value,
                         PackagingType.Barrel.value,
                         PackagingType.Can.value
                         ]

@dataclass
class Recipe(Jsonable) :
    name : JsonProperty[str]                            # Beer title
    subtitle : JsonProperty[str]                        # Beer subtitle, contains tags and other information
    description : JsonProperty[str]
    number : JsonProperty[int]                          # Refers to the "#1" tag
    tags : JsonOptionalProperty[list[str]]              # tag line
    first_brewed : JsonProperty[str]                    # Date of first brew
    brewers_tip : JsonOptionalProperty[str]

    basics : JsonProperty[Basics]                       # Basic properties of the beer recipe (like volume, ph, ebc, ibus, etc...)
    ingredients : JsonProperty[Ingredients]             # Ingredients list
    method_timings : JsonProperty[MethodTimings]        # Brewing procedures, mashing, temps, fermentation, etc..
    packaging : JsonProperty[PackagingType]             # Most probable main packaging for this recipe

    image : JsonProperty[Record]                        # Ref to file with image
    pdf_page : JsonProperty[Record]                     # Ref to original pdf page extracted from DiyDog book

    # Some beers don't have food pairing associated (happens for beer #79 and #156)
    food_pairing : JsonOptionalProperty[list[str]]
    # Some beers have parsing errors along the way, so list some potential issues here and let the end user check the pdf instead
    parsing_errors : JsonOptionalProperty[list[str]]


    # NOTE : I had to manually override everything, because Python won't let me assign default values in the constructor.
    # This is very weird; but upon two contiguous instantiation of the same object like this :
    # def test_multiple_instantiations_and_isolation(self) :
    #     class TestClass :
    #         tags : list[str]
    #         def __init__(self, tags = []) -> None:
    #             self.tags = tags

    #     test_object_1 = TestClass()
    #     test_object_1.tags.append("1")
    #     test_object_1.tags.append("2")
    #     test_object_1.tags.append("3")

    #     test_object_2 = TestClass()
    #     self.assertEqual(test_object_1.tags, test_object_2.tags)

    # This is super weird, it looks like the default object instances remain somewhere in local memory, and as Python uses references to pass
    # objects left and right, they happen to map the the same object, which is then linked to multiple class instances.
    # A solution is that the user must specify himself afterwards test_object_2.tags = [] to force python to allocate new memory, which won't be linked to the default elements anymore
    # NOTE 2 : this is referred to as mutating default argument and is found everywhere in internet :
    # https://stackoverflow.com/a/1321061


    def __init__( self, name : Optional[str] = None,
                        subtitle : Optional[str] = None,
                        number : Optional[int] = None,
                        tags : Optional[list[str]] = None,
                        first_brewed : Optional[str] = None,
                        description : Optional[str] = None,
                        basics : Optional[Basics] = None,
                        ingredients : Optional[Ingredients] = None,
                        brewers_tip : Optional[str] = None,
                        method_timings : Optional[MethodTimings] = None,
                        packaging : Optional[PackagingType] = None,
                        parsing_errors : Optional[list[str]]= None,
                        food_pairing : Optional[list[str]] = None) :
        self.image = JsonProperty('image', FileRecord())
        self.pdf_page = JsonProperty('pdfPage', FileRecord())
        self.description = JsonProperty("description", "")
        self.brewers_tip = JsonOptionalProperty("brewersTip", None)
        self.name = JsonProperty('name', "")
        self.subtitle =  JsonProperty('subtitle', "")
        self.number =  JsonProperty('number', 0)
        self.tags =  JsonOptionalProperty('tags', None)
        self.first_brewed = JsonProperty("firstBrewed", "")
        self.basics =  JsonProperty("basics", Basics())
        self.ingredients = JsonProperty("ingredients", Ingredients())
        self.method_timings = JsonProperty("methodTimings", MethodTimings())
        self.packaging =  JsonProperty("packaging", PackagingType.Bottle)
        self.parsing_errors = JsonOptionalProperty("parsingErrors", None)
        self.food_pairing =  JsonOptionalProperty("foodPairings", None)

        if name :
            self.name.value = name
        if description :
            self.description.value = description
        if subtitle :
            self.subtitle.value = subtitle
        if number :
            self.number.value = number
        if tags :
            self.tags.value = tags
        if first_brewed :
            self.first_brewed.value = first_brewed
        if basics :
            self.basics.value = basics
        if ingredients :
            self.ingredients.value = ingredients
        if brewers_tip :
            self.brewers_tip.value = brewers_tip
        if method_timings:
            self.method_timings.value = method_timings
        if packaging:
            self.packaging.value = packaging
        if parsing_errors :
            self.parsing_errors.value = parsing_errors
        if food_pairing :
            self.food_pairing.value = food_pairing




    def to_json(self) -> dict:
        return {
            self.name._prop_key : self.name.value,
            self.subtitle._prop_key : self.subtitle.value,
            self.number._prop_key : self.number.value,
            self.tags._prop_key : self.tags.value,
            self.first_brewed._prop_key : self.first_brewed.value,
            self.image._prop_key : self.image.value.to_json(),
            self.pdf_page._prop_key : self.pdf_page.value.to_json(),
            self.description._prop_key : self.description.value,
            self.brewers_tip._prop_key : self.brewers_tip.value,
            self.basics._prop_key : self.basics.value.to_json(),
            self.food_pairing._prop_key  : self.food_pairing.value if self.food_pairing.value else None,
            self.ingredients._prop_key  : self.ingredients.value.to_json(),
            self.method_timings._prop_key  : self.method_timings.value.to_json(),
            self.packaging._prop_key  : self.packaging.value,
            self.parsing_errors._prop_key  : self.parsing_errors.value
        }

    def from_json(self, content: dict) -> None:
        self.name.value = self.name.try_read(content, "")
        self.subtitle.value = self.subtitle.try_read(content, "")
        self.number.value = self.number.try_read(content, 0)
        self.tags.value = self.tags.read(content)
        self.first_brewed.value = self.first_brewed.try_read(content, "")

        # Image and Original PDF page deserve special handling, as they can be both a FileRecord or Cloud Record
        image_node = self.image.get_node(content)
        if image_node :
            parsed_record = RecordBuilder.from_json(image_node)
            self.image.value = parsed_record or self.image.value

        orig_pdf_node = self.pdf_page.get_node(content)
        if orig_pdf_node :
            parsed_record = RecordBuilder.from_json(orig_pdf_node)
            self.pdf_page.value = parsed_record or self.pdf_page.value

        self.description.value = self.description.try_read(content, "")
        self.brewers_tip.value = self.brewers_tip.read(content)

        basics_node = self.basics.get_node(content)
        if basics_node :
            self.basics.value.from_json(basics_node)

        self.food_pairing.value = self.food_pairing.read(content)
        ingredients_node = self.ingredients.get_node(content)
        if ingredients_node :
            self.ingredients.value.from_json(ingredients_node)

        method_timings_node = self.method_timings.get_node(content)
        if method_timings_node :
            self.method_timings.value.from_json(method_timings_node)

        packaging_node = self.packaging.get_node(content)
        if packaging_node and PackagingType.can_convert(packaging_node):
            self.packaging.value = PackagingType[packaging_node]

        self.parsing_errors.value = self.parsing_errors.read(content)

    def add_parsing_error(self, error_string : str) :
        if not self.parsing_errors.value :
            self.parsing_errors.value = []
        self.parsing_errors.value.append(error_string)

    def __eq__(self, other: object) -> bool:
        """Custom comparison tool as it seems the regular == one is not explicit (when using asserts)
        about what's the issue, so this comparison tool will help pinpoint what's the issue more easily"""
        if type(self) != type(other) :
            return False
        identical = True
        identical &= self.image ==  other.image                         #type: ignore
        identical &= self.pdf_page == other.pdf_page                    #type: ignore
        identical &= self.name == other.name                            #type: ignore
        identical &= self.subtitle == other.subtitle                    #type: ignore
        identical &= self.number == other.number                        #type: ignore
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
