import unittest
from pathlib import Path

from ..fuzzy_search import *
from ...dbsanitizer import read_known_good_yeasts_from_file

class TestFuzzySearch(unittest.TestCase) :
    def test_yeast_fuzzy_search(self) :
        yeast_1056 = YeastProp(name="Wyeast 1056 - American Ale\u0099",
                           aliases=[ "1056","American Ale"],
                           manufacturer="WYeast",
                           url="https://beermaverick.com/yeast/wy1056-american-ale-wyeast")

        yeast_1272 = YeastProp(name="Wyeast 1272 - American Ale II\u0099",
                               aliases=["1272","American Ale II"],
                               manufacturer="WYeast",
                               url="https://beermaverick.com/yeast/wy1272-american-ale-ii-wyeast/")

        # Specimen string vs expected result of fuzzy search
        test_data :list[tuple[str, YeastProp]] = [
            ("Wyeast 1056 - American Ale", yeast_1056),
            ("Wyeast 1272 - American Ale II", yeast_1272),
            ("Wyeast 1056- American Ale", yeast_1056),
            ("Wyeast 1056 -American Ale", yeast_1056),
            ("1056 -American Ale", yeast_1056),
            ("Wyeast 1272- American Ale II", yeast_1272),
            ("Wyeast 1272 -American Ale II", yeast_1272),
            ("1272 -American Ale II", yeast_1272),
        ]

        success = True
        for data in test_data :
            result = fuzzy_search_prop([yeast_1056, yeast_1272], data[0])
            self.assertIsNotNone(result)
            if result[1].hit.name.value != data[1].name.value : #type:ignore
                print(f"{result[1].hit.name.value} should be equal to {data[1].name.value } !") #type:ignore
                success = False

        self.assertTrue(success)

    def _get_yeast_with_name(self, name : str, yeast_ref : list[YeastProp]) -> YeastProp :
        """We assume we will find the targeted yeast anyways, otherwise it'll raise and make the test fail (which is good!) """
        found = [x for x in yeast_ref if x.name.value == name]
        return found[0]

    def test_yeast_fuzzy_search_extended(self) :
        # This test essentially serves as a non-regression test
        # and basically locks down yeast values found in recipes and known good yeasts relationships.
        # For now it really looks like a "hard coded" lookup table, but actually it's more like a way to secure the way for
        # now and have a more stable base on which we can build for later (like assuming DiyDog book will be reedited with more beers)
        # -> The more stable we are with yeast search the more robust the algorithm will be with later revisions of the book.


        this_dir = Path(__file__).parent
        yeast_ref_file = this_dir.parent.parent.parent.joinpath("References/known_good_yeasts.json")
        yeast_ref = read_known_good_yeasts_from_file(yeast_ref_file)


        # Building yeast catalogue ...
        safale_be134 = self._get_yeast_with_name("Safale - BE-134", yeast_ref)
        lalvin_ec1118 = self._get_yeast_with_name("Lalvin - EC-1118", yeast_ref)
        saflager_s189 = self._get_yeast_with_name("Saflager - S-189", yeast_ref)
        saflager_w3470 = self._get_yeast_with_name("Saflager - W-34/70", yeast_ref)
        safale_us05 = self._get_yeast_with_name("Safale - US-05", yeast_ref)
        safale_wb06 = self._get_yeast_with_name("SafAle - WB-06", yeast_ref)

        wlp4000 = self._get_yeast_with_name("WLP4000 - Vermont Ale", yeast_ref)
        wlp351 = self._get_yeast_with_name("WLP351 - Bavarian Weizen", yeast_ref)
        wlp013 = self._get_yeast_with_name("WLP013 - London Ale", yeast_ref)
        wlp099 = self._get_yeast_with_name("WLP099 - Super High Gravity Ale", yeast_ref)
        wlp500 = self._get_yeast_with_name("WLP500 - Monastery Ale", yeast_ref)

        wyeast_1010 = self._get_yeast_with_name("Wyeast 1010 - American Wheat\u0099", yeast_ref)
        wyeast_1056 = self._get_yeast_with_name("Wyeast 1056 - American Ale\u0099", yeast_ref)
        wyeast_1272 = self._get_yeast_with_name("Wyeast 1272 - American Ale II\u0099", yeast_ref)
        wyeast_1388 = self._get_yeast_with_name("Wyeast 1388 - Belgian Strong Ale \u0099", yeast_ref)
        wyeast_2007 = self._get_yeast_with_name("Wyeast 2007 - Pilsen Lager\u0099", yeast_ref)
        wyeast_3333 = self._get_yeast_with_name("Wyeast 3333 - German Wheat\u0099", yeast_ref)
        wyeast_3522 = self._get_yeast_with_name("Wyeast 3522 - Belgian Ardennes\u0099", yeast_ref)
        wyeast_3638 = self._get_yeast_with_name("Wyeast 3638 - Bavarian Wheat\u0099", yeast_ref)
        wyeast_3711 = self._get_yeast_with_name("Wyeast 3711 - French Saison\u0099", yeast_ref)
        wyeast_3724 = self._get_yeast_with_name("Wyeast 3724 - Belgian Saison\u0099", yeast_ref)
        wyeast_3787 = self._get_yeast_with_name("Wyeast 3787 - Belgian High Gravity\u0099", yeast_ref)
        wyeast_3944 = self._get_yeast_with_name("Wyeast 3944 - Belgian Witbier\u0099", yeast_ref)
        wyeast_3031pc = self._get_yeast_with_name("Wyeast 3031-PC - Saison-Brett Blend\u0099", yeast_ref)

        westvleteren = self._get_yeast_with_name("Westvleteren 12 (recovered from a bottle)", yeast_ref)

        # Specimen string vs expected result of fuzzy search
        test_data :list[tuple[str, YeastProp]] = [
            ("Bavarian Weizen WLP351", wlp351 ),
            ("WLP 351 Bavarian Weizen", wlp351 ),
            ("WLP013 London Ale", wlp013 ),
            ("WLP099 Super High Gravity Ale", wlp099 ),
            ("WLP500 Monastery Ale", wlp500 ),
            ("Be-134", safale_be134 ),
            ("Champagne", lalvin_ec1118 ),
            ("House Brett Blend", wyeast_3031pc ),
            ("S189 Yeast", saflager_s189 ),
            ("Sa\u001eager W-34/70", saflager_w3470 ),
            ("W34/70", saflager_w3470 ),
            ("Safale US-05", safale_us05 ),
            ("US-05", safale_us05 ),
            ("Vermont Ale (WLP4000)", wlp4000 ),
            ("WB-06", safale_wb06 ),
            ("Westvleteren 12 (recovered from a bottle)", westvleteren ),
            ("Wyeast 1010 American Wheat\u0099", wyeast_1010 ),
            ("Wyeast 1056 -American Ale \u0099", wyeast_1056 ),
            ("Wyeast 1056 -American Ale \u0099", wyeast_1056 ),
            ("Wyeast 1272", wyeast_1272 ),
            ("Wyeast 1388 \u0096 Belgian Strong Ale\u0099", wyeast_1388 ),
            ("Wyeast 2007 \u0096 Pilsen Lager\u0099", wyeast_2007 ),
            ("Yeast: Wyeast 2007 - Pilsen Lager\u0099", wyeast_2007 ),
            ("Wyeast 3333 German Wheat\u0099", wyeast_3333 ),
            ("Wyeast 3522 - Ardennes\u0099", wyeast_3522 ),
            ("Wyeast 3638 Bavarian Wheat", wyeast_3638 ),
            ("Wyeast 3711 French Saison", wyeast_3711 ),
            ("Wyeast 3724 - Belgian Saison\u0099", wyeast_3724 ),
            ("Wyeast 3787 - Trappist High Gravity\u0099", wyeast_3787 ),
            ("Wyeast 3944 - Belgian Witbier\u0099", wyeast_3944 )
        ]

        success = True
        for data in test_data :
            result = fuzzy_search_prop(yeast_ref, data[0])
            self.assertIsNotNone(result)
            if result[1].hit.name.value != data[1].name.value : #type:ignore
                print(f"{result[1].hit.name.value} should be equal to {data[1].name.value } !") #type:ignore
                success = False

        self.assertTrue(success)


if __name__ == "__main__" :
    unittest.main()