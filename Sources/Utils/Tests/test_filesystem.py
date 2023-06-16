import shutil
import unittest
from tempfile import gettempdir

from ..filesystem import *

class TestFilesystemUtils(unittest.TestCase) :

    dumped_files : list[str]
    tmp_dir : Path

    def setUp(self) -> None:
        super().setUp()
        self.tmp_dir = Path(gettempdir()).joinpath("DiyDogExtractorTests/test_filesystem")
        self.dumped_files = self.generate_files_in_folder(self.tmp_dir)

    def tearDown(self) -> None:
        super().tearDown()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def generate_files_in_folder(self, tmp_dir : Path) -> list[str]:
        if not tmp_dir.exists():
            tmp_dir.mkdir(parents=True)
        # Dump fake files
        dumped_files = ["file1.txt", "file2.json", "file3.pdf"]
        for file in dumped_files :
            with open(tmp_dir.joinpath(file), 'w') as file:
                file.write("Test !")
        return dumped_files

    def generate_fake_pdf_pages_in_folder(self, tmp_dir : Path) -> list[str]:
        if not tmp_dir.exists():
            tmp_dir.mkdir(parents=True)
        # Dump fake files
        dumped_files = ["page_1.pdf", "page_2.txt", "page_3.pdf"]
        for file in dumped_files :
            with open(tmp_dir.joinpath(file), 'w') as file:
                file.write("Test !")
        return dumped_files


    def test_list_all_files(self) :
        files = list_all_files(self.tmp_dir)
        self.assertEqual(len(files), len(self.dumped_files))
        for file in files :
            self.assertTrue(file.name in self.dumped_files)

    def test_list_files_with_extension(self) :
        files = list_files_by_extension(self.tmp_dir, ".txt")
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name in self.dumped_files)

    def test_list_files_with_extension_subfolders(self) :
        subfolder = self.tmp_dir.joinpath("subfolder")
        subfiles = self.generate_files_in_folder(subfolder)

        files = list_files_by_extension(self.tmp_dir, ".txt")
        self.assertEqual(len(files), 2)
        self.assertTrue(files[0].name in self.dumped_files)
        self.assertTrue(files[1].name in self.dumped_files)

    def test_list_files_with_ext_and_pattern(self) :
        files = list_files_pattern(self.tmp_dir, "file", ".txt")
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name in self.dumped_files)

    def test_list_files_with_ext_and_pattern_subfolders(self) :
        subfolder = self.tmp_dir.joinpath("subfolder")
        subfiles = self.generate_files_in_folder(subfolder)

        files = list_files_pattern(self.tmp_dir, "file", ".txt")
        self.assertEqual(len(files), 2)
        self.assertTrue(files[0].name in self.dumped_files)
        self.assertTrue(files[1].name in self.dumped_files)

    def test_list_pdf_pages(self) :
        subfolder = self.tmp_dir.joinpath("subfolder")
        subfiles = self.generate_fake_pdf_pages_in_folder(subfolder)

        files = list_pages_with_number(self.tmp_dir)
        self.assertEqual(len(files), 2),
        self.assertTrue(files[0][1].name in subfiles)
        self.assertTrue(files[1][1].name in subfiles)


if __name__ == "__main__" :
    unittest.main()