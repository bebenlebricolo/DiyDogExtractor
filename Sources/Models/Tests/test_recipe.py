import unittest
from ..recipe import *
import json

class TestRecipeModels(unittest.TestCase) :

    def test_Description_json_symmetry(self) :
        description = Description(text="This is a test description")
        data = description.to_json()
        parsed = Description()
        parsed.from_json(data)
        self.assertEqual(description, parsed)

    def test_Volume_json_symmetry(self) :
        volume = Volume(20.0, 5.0)
        data = volume.to_json()
        parsed = Volume()
        parsed.from_json(data)
        self.assertEqual(volume, parsed)

    def test_Basics_json_symmetry(self) :
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

        data = basics.to_json()
        parsed = Basics()
        parsed.from_json(data)
        self.assertEqual(basics, parsed)

if __name__ == "__main__" :
    unittest.main()