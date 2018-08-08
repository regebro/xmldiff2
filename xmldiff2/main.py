"""All major API points and command line tools"""
from lxml import etree
from xmldiff2 import diff


def diff_trees(left, right, F=0.5, uniqueattrs=None, formatter=None):
    """Takes two lxml root elements or element trees"""
    if isinstance(left, etree._ElementTree):
        left = left.getroot()
    if isinstance(right, etree._ElementTree):
        right = right.getroot()
    diffs = diff.Differ(F=F, uniqueattrs=uniqueattrs).diff(left, right)
    if formatter is None:
        return list(diffs)
    return formatter.format(left, diffs)


def diff_texts(left, right, F=0.5, uniqueattrs=None, formatter=None):
    """Takes two Unicode strings containing XML"""
    left_tree = etree.fromstring(left)
    right_tree = etree.fromstring(right)
    return diff_trees(left_tree, right_tree, F=F, uniqueattrs=uniqueattrs,
                      formatter=formatter)


def diff_files(left, right, F=0.5, uniqueattrs=None, formatter=None):
    """Takes two filenames or streams, and diffs the XML in those files"""
    left_tree = etree.parse(left)
    right_tree = etree.parse(right)
    return diff_trees(left_tree, right_tree, F=F, uniqueattrs=uniqueattrs,
                      formatter=formatter)
