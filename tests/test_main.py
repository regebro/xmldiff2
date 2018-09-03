import os
import unittest

from lxml import etree
from xmldiff2 import main, formatting

CURDIR = os.path.split(__file__)[0]
LEFT_FILE = os.path.join(CURDIR, 'test_data', 'rmldoc.left.xml')
RIGHT_FILE = os.path.join(CURDIR, 'test_data', 'rmldoc.right.xml')
EXPECTED_FILE = os.path.join(CURDIR, 'test_data', 'rmldoc.expected.xml')


class MainAPITests(unittest.TestCase):

    def test_api_diff_files(self):
        # diff_files can take filenames
        result1 = main.diff_files(LEFT_FILE, RIGHT_FILE)

        # Or open file streams:
        with open(LEFT_FILE, 'rb') as l:
            with open(RIGHT_FILE, 'rb') as r:
                result2 = main.diff_files(l, r)

        self.assertEqual(result1, result2)

        # Give something else, and it fails:
        with self.assertRaises(IOError):
            main.diff_files('<xml1/>', '<xml2/>')

    def test_api_diff_texts(self):
        # diff_text can take bytes
        with open(LEFT_FILE, 'rb') as l:
            with open(RIGHT_FILE, 'rb') as r:
                left = l.read()
                right = r.read()
                result1 = main.diff_texts(left, right)

                # And unicode
                result2 = main.diff_texts(left.decode('utf8'),
                                          right.decode('utf8'))

                self.assertEqual(result1, result2)

        with open(LEFT_FILE, 'rb') as l:
            with open(RIGHT_FILE, 'rb') as r:
                # Give something else, and it fails:
                with self.assertRaises(ValueError):
                    main.diff_texts(l, r)

    def test_api_diff_trees(self):
        # diff_tree can take ElementEtrees
        left = etree.parse(LEFT_FILE)
        right = etree.parse(RIGHT_FILE)
        result1 = main.diff_trees(left, right)

        # And Elements
        result2 = main.diff_trees(left.getroot(), right.getroot())
        self.assertEqual(result1, result2)

        # Give something else, and it fails:
        with self.assertRaises(TypeError):
            main.diff_trees(LEFT_FILE, RIGHT_FILE)

    def test_api_diff_files_with_formatter(self):
        formatter = formatting.XMLFormatter()
        # diff_files can take filenames
        result = main.diff_files(LEFT_FILE, RIGHT_FILE, formatter=formatter)
        # This formatter will insert a diff namespace:
        self.assertIn('xmlns:diff="http://namespaces.shoobx.com/diff"', result)
