"""All major API points and command line tools"""
from argparse import ArgumentParser, FileType
from lxml import etree
from xmldiff import diff, formatting


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
    normalize = bool(getattr(formatter, 'normalize', 1) & formatting.WS_TAGS)
    parser = etree.XMLParser(remove_blank_text=normalize)
    left_tree = etree.fromstring(left, parser)
    right_tree = etree.fromstring(right, parser)
    return diff_trees(left_tree, right_tree, F=F, uniqueattrs=uniqueattrs,
                      formatter=formatter)


def diff_files(left, right, F=0.5, uniqueattrs=None, formatter=None):
    """Takes two filenames or streams, and diffs the XML in those files"""
    normalize = bool(getattr(formatter, 'normalize', 1) & formatting.WS_TAGS)
    parser = etree.XMLParser(remove_blank_text=normalize)
    left_tree = etree.parse(left, parser)
    right_tree = etree.parse(right, parser)
    return diff_trees(left_tree, right_tree, F=F, uniqueattrs=uniqueattrs,
                      formatter=formatter)


def run(args=None):

    parser = ArgumentParser(description='Diff two XML files')
    parser.add_argument('file1', type=FileType('r'),
                        help='The first input file')
    parser.add_argument('file2', type=FileType('r'),
                        help='The second input file')
    parser.add_argument('--formatter', default='diff',
                        choices=['diff', 'xml', 'rml'],
                        help='Formatter choice. The diff and xml formatters '
                        'are generic, rml may not makes sense with non-RML '
                        'files. Default: diff')
    parser.add_argument('--keep-whitespace', action='store_true',
                        help="Do not strip ignorable whitespace")
    parser.add_argument('--pretty-print', action='store_true',
                        help="Try to make XML output more readable")
    args = parser.parse_args(args=args)
    if args.keep_whitespace:
        normalize = formatting.WS_NONE
    else:
        normalize = formatting.WS_BOTH

    FORMATTERS = {
        'diff': formatting.DiffFormatter,
        'xml': formatting.XMLFormatter,
        'rml': formatting.RMLFormatter,
    }

    formatter = FORMATTERS[args.formatter](normalize=normalize,
                                           pretty_print=args.pretty_print)
    result = diff_files(args.file1, args.file2, formatter=formatter)
    print(result)
