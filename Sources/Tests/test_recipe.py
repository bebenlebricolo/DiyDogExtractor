import re
import unittest
from ..main import pre_process_malts, TextElement, TextElement, group_in_distinct_columns

class TestRecipe(unittest.TestCase) :
    def test_pre_process_malts_simple_case(self) :
        elements : list[TextElement] = [
            TextElement(x=216.1984, y=595.9623, text='Extra Pale'),
            TextElement(x=282.1039, y=595.9623, text='5.3kg'),
            TextElement(x=330.0016, y=595.9623, text='11.7lb')
        ]

        processed = pre_process_malts(elements)
        self.assertEqual(processed, elements)

    def test_pre_process_malts_complex_case(self) :
        elements : list[TextElement] = [
            TextElement(x=217.02, y=615.73, text='Extra Pale -'),
            TextElement(x=225.56, y=615.11, text='5.36kg'),
            TextElement(x=231.45, y=615.11, text='11.8lb'),
            TextElement(x=217.02, y=614.48, text='Maris Otter'),

            TextElement(x=217.02, y=612.89, text='Dark Crystal'),
            TextElement(x=225.66, y=612.27, text='0.71kg'),
            TextElement(x=231.80, y=612.27, text='1.6lb'),
            TextElement(x=217.02, y=611.64, text='350-400'),

            TextElement(x=217.02, y=610.06, text='Carafa Special'),
            TextElement(x=225.88, y=609.43, text='0.18g'),
            TextElement(x=231.48, y=609.43, text='0.4lb'),
            TextElement(x=217.02, y=608.81, text='Malt Type 3'),

            TextElement(x=217.02, y=607.02, text='Caramalt'),
            TextElement(x=225.50, y=607.02, text='0.54kg'),
            TextElement(x=231.80, y=607.02, text='1.2lb'),

            TextElement(x=217.02, y=605.04, text='Chocolate'),
            TextElement(x=225.53, y=605.04, text='0.25kg'),
            TextElement(x=231.53, y=605.04, text='0.6lb'),

            TextElement(x=217.02, y=603.06, text='Wheat'),
            TextElement(x=225.53, y=603.06, text='0.36kg'),
            TextElement(x=231.53, y=603.06, text='0.8lb'),

            TextElement(x=217.02, y=601.07, text='Flaked Oats'),
            TextElement(x=225.50, y=601.07, text='0.54kg'),
            TextElement(x=231.80, y=601.07, text='1.2lb')
            ]

        processed = pre_process_malts(elements)
        self.assertTrue((len(processed) % 3) == 0)
        grams_pattern = re.compile(r"([0-9]+\.?[0-9]*) *([k]?[g])")
        lbs_pattern = re.compile(r"([0-9]+\.?[0-9]*) *(lb)")

        # Verify that data is ordered as expected : malt name, weight in grams, weight in lbs
        for i in range(0, int(len(processed) / 3)) :
            self.assertIsNone(grams_pattern.match(processed[i * 3].text))
            self.assertIsNone(lbs_pattern.match(processed[i * 3].text))
            self.assertIsNotNone(lbs_pattern.match(processed[i * 3 + 2].text))

    def test_pre_process_malts_complex_case_2(self) :
        elements : list[TextElement] = [
                TextElement(x=239.704, y=615.539, text='Extra Pale'),
                TextElement(x=248.505, y=615.539, text='6.5kg'),
                TextElement(x=253.897, y=615.539, text='14.3lb'),
                TextElement(x=239.704, y=613.547, text='Caramalt'),
                TextElement(x=248.194, y=613.547, text='0.86kg'),
                TextElement(x=254.477, y=613.547, text='1.9lb'),
                TextElement(x=239.704, y=611.563, text='Munich'),
                TextElement(x=248.485, y=611.563, text='0.5kg'),
                TextElement(x=254.697, y=611.563, text='1.1lb'),
                TextElement(x=239.705, y=609.579, text='Flaked Oats'),
                TextElement(x=248.899, y=609.579, text='2kg'),
                TextElement(x=253.813, y=609.579, text='4.41lb'),
                TextElement(x=239.706, y=607.595, text='Dark Crystal'),
                TextElement(x=248.196, y=607.595, text='0.86kg'),
                TextElement(x=254.479, y=607.595, text='1.9lb'),
                TextElement(x=239.706, y=605.811, text='Carafa Special'),
                TextElement(x=248.212, y=605.186, text='0.25kg'),
                TextElement(x=254.215, y=605.186, text='0.6lb'),
                TextElement(x=239.706, y=604.561, text='Malt Type 1'),
                TextElement(x=239.706, y=602.976, text='Carafa Special'),
                TextElement(x=248.487, y=602.351, text='0.5kg'),
                TextElement(x=254.699, y=602.351, text='1.1lb'),
                TextElement(x=239.706, y=601.726, text='Malt Type 3')
            ]

        processed = pre_process_malts(elements)
        self.assertTrue((len(processed) % 3) == 0)
        grams_pattern = re.compile(r"([0-9]+\.?[0-9]*) *([k]?[g])")
        lbs_pattern = re.compile(r"([0-9]+\.?[0-9]*) *(lb)")

        # Verify that data is ordered as expected : malt name, weight in grams, weight in lbs
        for i in range(0, int(len(processed) / 3)) :
            self.assertIsNone(grams_pattern.match(processed[i * 3].text))
            self.assertIsNone(lbs_pattern.match(processed[i * 3].text))
            self.assertIsNotNone(lbs_pattern.match(processed[i * 3 + 2].text))


    def test_group_in_columns(self) :
        elements : list[TextElement] = [
            TextElement(x=217.02, y=615.73, text='Extra Pale -'),
            TextElement(x=225.56, y=615.11, text='5.36kg'),
            TextElement(x=231.45, y=615.11, text='11.8lb'),
            TextElement(x=217.02, y=614.48, text='Maris Otter')
        ]

        columns = group_in_distinct_columns(elements)
        self.assertEqual(len(columns), 3)

if __name__ == "__main__" :
    unittest.main()