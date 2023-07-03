import unittest
from ..fuzzy_search import *

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


if __name__ == "__main__" :
    unittest.main()