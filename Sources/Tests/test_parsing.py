import unittest
from ..Utils.parsing import parse_line, escape_content

class TestParsing(unittest.TestCase) :
    def test_parse_line(self) :
        content_list = [
            (R"(BASICS)Tj"                                       , "BASICS"),
            (R"[(V)48 (OL)36 (UME)]TJ"                           , "VOLUME"),
            (R"[(5g)16 (al)]TJ"                                  , "5gal"),
            (R"[(BOIL V)48 (OL)36 (UME)]TJ"                      , "BOIL VOLUME"),
            (R"(6%)Tj"                                           , "6%"),
            (R"[(A)72 (TTENU)24 (A)72 (TION)25 ( )]TJ"           , "ATTENUATION "),
            (R"(2007 - 2010)Tj"                                  , "2007 - 2010"),
            (R"[(SPIKY)100 (. TROPICAL. HOPPY)100 (.)]"          , "SPIKY. TROPICAL. HOPPY."),
            (R"( )Tj"                                            , " "),
            (R"[(W)24 (y)14 (east 1056 - American Ale\231)]TJ"   , u"Wyeast 1056 - American Ale\u0099"),
            (R"[(BREWER)91 (\222S TIP)]TJ"                       , u"BREWER\u0092S TIP"), # Contains octal escape sequences
            (R"(METHOD / TIMINGS)Tj"                             , "METHOD / TIMINGS"),
            (R"(65\260C)"                                        , "65°C"),
            (R"(150\260F)"                                       , "150°F"),
            (R"[(6)-10 (% )]"                                    , "6% "),
            (R"(\(g\))"                                          , "(g)"),
        ]

        for line in content_list :
            # We need to take out the unicode escapes if it happens to have some
            parsed = parse_line(line[0])
            self.assertEqual(parsed, line[1], "(parsed vs expected)")

    def test_escape_string(self) :
        test_string = R"This is a string with \\ an \\\\ escape sequence"
        expected = R"This is a string with \ an \\ escape sequence"
        escaped = escape_content(test_string)
        self.assertEqual(escaped, expected)

    def test_escape_string_with_octal_unicode_escape_method(self) :
        test_string = R"Another string with brewer\047s tip \\ "
        expected = R"Another string with brewer's tip \ "
        escaped = test_string.encode().decode("unicode-escape")
        self.assertEqual(escaped, expected)

    def test_escape_string_with_octal_custom_method(self) :
        test_string = R"Another string with brewer\047s tip \\ \055 "
        expected = R"Another string with brewer's tip \ - "
        escaped = escape_content(test_string)
        print(escaped)
        self.assertEqual(escaped, expected)


if __name__ == "__main__" :
    unittest.main()