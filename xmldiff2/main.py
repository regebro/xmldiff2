"""All major API points and command line tools"""
from lxml import etree
from xmldiff2 import diff


def diff_trees(left_tree, right_tree, F=0.5, uniqueattrs=None, formatter=None):
    """Takes two lxml root elements or element trees"""
    if isinstance(left_tree, etree._ElementTree):
        left_tree = left_tree.getroot()
    if isinstance(right_tree, etree._ElementTree):
        right_tree = right_tree.getroot()
    if formatter is not None:
        formatter.prepare(left_tree, right_tree)
    differ = diff.Differ(F=F, uniqueattrs=uniqueattrs)
    diffs = differ.diff(left_tree, right_tree)
    if formatter is None:
        return list(diffs)
    return formatter.format(diffs, left_tree)


def diff_texts(left, right, F=0.5, uniqueattrs=None, formatter=None):
    """Takes two Unicode strings containing XML"""
    remove_blank_text = getattr(formatter, 'remove_blank_text', False)
    parser = etree.XMLParser(remove_blank_text=remove_blank_text)
    left_tree = etree.fromstring(left, parser)
    right_tree = etree.fromstring(right, parser)
    return diff_trees(left_tree, right_tree, F=F, uniqueattrs=uniqueattrs,
                      formatter=formatter)


def diff_files(left, right, F=0.5, uniqueattrs=None, formatter=None):
    """Takes two filenames or streams, and diffs the XML in those files"""
    remove_blank_text = getattr(formatter, 'remove_blank_text', False)
    parser = etree.XMLParser(remove_blank_text=remove_blank_text)
    left_tree = etree.parse(left, parser)
    right_tree = etree.parse(right, parser)
    return diff_trees(left_tree, right_tree, F=F, uniqueattrs=uniqueattrs,
                      formatter=formatter)
