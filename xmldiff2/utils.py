from __future__ import division

import re
from operator import eq


def post_order_traverse(node):
    for child in node.getchildren():
        # PY3: Man, I want yield from!
        for item in post_order_traverse(child):
            yield item
    yield node


def reverse_post_order_traverse(node):
    for child in reversed(node.getchildren()):
        # PY3: Man, I want yield from!
        for item in reverse_post_order_traverse(child):
            yield item
    yield node


def breadth_first_traverse(node):
    # First yield the root node
    yield node

    # Then go into the recursing part:
    for item in _breadth_first_recurse(node):
        yield item


def _breadth_first_recurse(node):
    for child in node.getchildren():
        yield child

    for child in node.getchildren():
        for item in _breadth_first_recurse(child):
            # PY3: Man, I want yield from!
            yield item


# LCS from Myers: An O(ND) Difference Algorithm and Its Variations. This
# implementation uses Chris Marchetti's technique of only keeping the history
# per dpath, and not per node, so it should be vastly less memory intensive.
# It also skips any items that are equal in the beginning and end, speeding
# up the search, and using even less memory.
def longest_common_subsequence(left_sequence, right_sequence, eqfn=eq):

    start = 0
    lend = lslen = len(left_sequence)
    rend = rslen = len(right_sequence)

    # Trim off the matching items at the beginning
    while (start < lend and start < rend and
           eqfn(left_sequence[start], right_sequence[start])):
        start += 1

    # trim off the matching items at the end
    while (start < lend and start < rend and
           eqfn(left_sequence[lend - 1], right_sequence[rend - 1])):
        lend -= 1
        rend -= 1

    left = left_sequence[start:lend]
    right = right_sequence[start:rend]

    lmax = len(left)
    rmax = len(right)
    furtherst = {1: (0, [])}

    if not lmax + rmax:
        # The sequences are equal
        r = range(lslen)
        return zip(r, r)

    for d in range(0, lmax + rmax + 1):
        for k in range(-d, d + 1, 2):
            if (k == -d or
               (k != d and furtherst[k - 1][0] < furtherst[k + 1][0])):
                # Go down
                old_x, history = furtherst[k + 1]
                x = old_x
            else:
                # Go left
                old_x, history = furtherst[k - 1]
                x = old_x + 1

            # Copy the history
            history = history[:]
            y = x - k

            while x < lmax and y < rmax and eqfn(left[x], right[y]):
                # We found a match
                history.append((x + start, y + start))
                x += 1
                y += 1

            if x >= lmax and y >= rmax:
                # This is the best match
                return [(e, e) for e in range(start)] + history + \
                    list(zip(range(lend, lslen), range(rend, rslen)))
            else:
                furtherst[k] = (x, history)


WHITESPACE = re.compile(u'\s+', flags=re.MULTILINE)


def cleanup_whitespace(text):
    return WHITESPACE.sub(' ', text)


def getpath(element, tree=None):
    if tree is None:
        tree = element.getroottree()
    xpath = tree.getpath(element)
    if xpath[-1] != ']':
        # The path is unique without specifying a count. However, we always
        # want that count, so we add [1].
        xpath = xpath + '[1]'
    return xpath
