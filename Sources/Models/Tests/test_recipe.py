import unittest
import json
from tempfile import gettempdir
from pathlib import Path
import shutil

from ..recipe import *
from ...Utils.filesystem import ensure_folder_exist

class TestRecipeModels(unittest.TestCase) :

    def get_fake_description(self) -> str :
        return "This is a test description"

    def get_fake_Volume(self) -> Volume :
        return Volume(20.0, 5.0)

    def get_fake_Basics(self) -> Basics :
        basics = Basics()
        basics.volume.litres = 20
        basics.volume.galons = 5
        basics.boil_volume.litres = 25
        basics.boil_volume.galons = 6.6
        basics.abv = 6
        basics.target_og = 1056
        basics.target_fg = 1010
        basics.ebc = 17
        basics.srm = 8.5
        basics.ph = 4.4
        basics.attenuation_level = 82.144

        return basics

    def get_fake_FoodPairing(self) -> list[str] :
        return [
            "pairing 1",
            "pairing 2",
            "pairing 3"
        ]

    def get_fake_Malt(self) -> Malt :
        return Malt(name="test malt", kgs=1.2, lbs= 2.3)

    def get_fake_Hop(self) -> Hop :
        return Hop(name="test hop", amount=1.2, when="dry hop", attribute="flavour")

    def get_fake_Yeast(self) -> Yeast :
        return Yeast(name="Lallemand BRY-97")

    def get_fake_Ingredients(self) -> Ingredients :
        ingredients = Ingredients()
        ingredients.malts = [
            Malt("test malt 1", 1.2, 2.3),
            Malt("test malt 2", 2.2, 3.3),
            Malt("test malt 3", 3.2, 4.3),
        ]
        ingredients.hops = [
            Hop("test hop 1", 1.1, "when 1", "attribute 1"),
            Hop("test hop 2", 2.1, "when 2", "attribute 2"),
            Hop("test hop 3", 3.1, "when 3", "attribute 3"),
        ]
        ingredients.yeasts = [
            Yeast("test yeast 1"),
            Yeast("test yeast 2")
        ]
        ingredients.extra_mash = [
            ExtraMash("Candy sugar", kgs=1.0, lbs=2.5),
            ExtraMash("Syrup", kgs=0.50, lbs=1.25)
        ]
        ingredients.extra_boil = [
            ExtraBoil("Coffee beans", 50, "End", "Flavour"),
            ExtraBoil("Chilli pepper", 25, "End", "Flavour"),
        ]

        # No description, this is voluntary
        ingredients.alternative_description = None

        return ingredients

    def get_fake_BrewersTip(self) -> str :
        return "fake brewer's tip"

    def get_fake_Temperature(self) -> Temperature :
        return Temperature(celsius=12.0, fahrenheit=33.2)

    def get_fake_MashTemp(self) -> MashTemp :
        return MashTemp(12,33,50)

    def get_fake_Fermentation(self) -> Fermentation :
        return Fermentation(12,33)

    def get_fake_Twist(self) -> Twist :
        return Twist("fake twist", 35)

    def get_fake_MethodTimings(self) -> MethodTimings :
        method_timings = MethodTimings()
        method_timings.fermentation = Fermentation(12, 33)
        method_timings.mash_temps = [
            MashTemp(12, 33, 20),
            MashTemp(22, 55, 20),
            MashTemp(35, 65, 20),
        ]
        method_timings.twists = None

        return method_timings

    def get_fake_Packaging(self) -> PackagingType :
        return PackagingType.Bottle

    def test_Volume_json_symmetry(self) :
        volume = self.get_fake_Volume()
        data = volume.to_json()
        parsed = Volume()
        parsed.from_json(data)
        self.assertEqual(volume, parsed)

    def test_Basics_json_symmetry(self) :
        basics = self.get_fake_Basics()

        data = basics.to_json()
        parsed = Basics()
        parsed.from_json(data)
        self.assertEqual(basics, parsed)

    def test_Malt_json_symmetry(self) :
        malt = self.get_fake_Malt()

        data = malt.to_json()
        parsed = Malt()
        parsed.from_json(data)
        self.assertEqual(malt, parsed)

    def test_Hop_json_symmetry(self) :
        hop = self.get_fake_Hop()

        data = hop.to_json()
        parsed = Hop()
        parsed.from_json(data)
        self.assertEqual(hop, parsed)

    def test_Yeast_json_symmetry(self) :
        yeast = self.get_fake_Yeast()

        data = yeast.to_json()
        parsed = Yeast()
        parsed.from_json(data)
        self.assertEqual(yeast, parsed)

    def test_Ingredients_json_symmetry(self) :
        ingredients = self.get_fake_Ingredients()

        data = ingredients.to_json()
        parsed = Ingredients()
        parsed.from_json(data)
        self.assertEqual(ingredients, parsed)

    def test_Temperature_json_symmetry(self) :
        temperature = self.get_fake_Temperature()

        data = temperature.to_json()
        parsed = Temperature()
        parsed.from_json(data)
        self.assertEqual(temperature, parsed)

    def test_MashTemp_json_symmetry(self) :
        mash_temp = self.get_fake_MashTemp()

        data = mash_temp.to_json()
        parsed = MashTemp()
        parsed.from_json(data)
        self.assertEqual(mash_temp, parsed)

    def test_Fermentation_json_symmetry(self) :
        fermentation = self.get_fake_Fermentation()

        data = fermentation.to_json()
        parsed = Fermentation()
        parsed.from_json(data)
        self.assertEqual(fermentation, parsed)

    def test_Twist_json_symmetry(self) :
        twist_1 = Twist("fake twist 1", 35)
        twist_2 = Twist("fake twist 2", None)

        data = twist_1.to_json()
        parsed = Twist()
        parsed.from_json(data)
        self.assertEqual(twist_1, parsed)

        data = twist_2.to_json()
        parsed.from_json(data)
        self.assertEqual(twist_2, parsed)

    def test_MethodTimings_json_symmetry(self) :
        method_timings = self.get_fake_MethodTimings()

        data = method_timings.to_json()
        parsed = MethodTimings()
        parsed.from_json(data)
        self.assertEqual(method_timings, parsed)

    def test_Recipe_json_symmetry(self) :
        tmp_dir = Path(gettempdir()).joinpath(f"DiyDogExtractor/{Path(__file__).stem}")
        ensure_folder_exist(tmp_dir)

        recipe = Recipe()
        recipe.basics.value = self.get_fake_Basics()
        recipe.brewers_tip.value = self.get_fake_BrewersTip()
        recipe.description.value = self.get_fake_description()
        recipe.first_brewed.value = "I don't know !"
        recipe.food_pairing.value = self.get_fake_FoodPairing()
        recipe.ingredients.value = self.get_fake_Ingredients()
        recipe.image.value = FileRecord("Somewhere on this computer")
        recipe.name.value = "Fake beer name"
        recipe.number.value = 123
        recipe.pdf_page.value = FileRecord("somewhere ELSE on this computer")
        recipe.packaging.value = self.get_fake_Packaging()
        recipe.tags.value = [
            "tag 1",
            "tag 2",
            "tag 3",
        ]


        test_json_filepath = tmp_dir.joinpath("recipe_test_dump.json")
        data = recipe.to_json()

        # Trying to dump the file to filesystem, it should be json compatible !
        with open(test_json_filepath, "w") as file :
            json.dump(data, file, indent=4)

        parsed = Recipe()

        # Should be able to read a Json representation as well
        with open(test_json_filepath, 'r') as file :
            parsed.from_json(json.load(file))
        self.assertEqual(recipe, parsed)


    def test_multiple_recipes_instantiation_and_isolation(self) :
        """This test tries to instantiate many recipes in a row, and none of them should be equal."""
        recipe_1 = Recipe()
        recipe_1.tags.value = []
        recipe_1.tags.value.append("1")
        recipe_1.tags.value.append("2")
        recipe_1.tags.value.append("3")

        recipe_2 = Recipe()
        self.assertNotEqual(recipe_1.tags, recipe_2.tags)

    def test_multiple_instantiations_and_isolation(self) :
        class TestClass :
            tags : list[str]
            def __init__(self, tags = []) -> None:
                self.tags = tags

        test_object_1 = TestClass()
        test_object_1.tags.append("1")
        test_object_1.tags.append("2")
        test_object_1.tags.append("3")

        test_object_2 = TestClass()
        test_object_2.tags = []
        self.assertNotEqual(test_object_1.tags, test_object_2.tags)

if __name__ == "__main__" :
    unittest.main()