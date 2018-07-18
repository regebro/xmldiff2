from __future__ import division

from difflib import SequenceMatcher
from lxml import etree

from xmldiff2 import utils


class Matcher(object):

    def __init__(self, T=0.5, F=0.5, uniqueattrs=None):
        # The minimum similarity between two leaf nodes to consider them equal
        self.F = F
        # The minimum similarity between two trees to consider them equal
        self.T = T
        # uniquattrs is a list of attributes that uniquely identifies a node
        # inside a document. Deafults to 'xml:id'.
        if uniqueattrs is None:
            uniqueattrs = ['{http://www.w3.org/XML/1998/namespace}id']
        self.uniqueattrs = uniqueattrs
        self.clear()
        # Avoid recreating this for every node
        self._sequencematcher = SequenceMatcher()

    def clear(self):
        # Use None for all values, as markings that they aren't done yet.
        self.left = None
        self.right = None
        self._matches = None
        self._l2rmap = None
        self._r2lmap = None
        self._inorder = None

    def set_seqs(self, left, right):
        self.clear()
        self.left = left
        self.right = right

    def append_match(self, lnode, rnode, max_match):
        self._matches.append((lnode, rnode, max_match))
        self._l2rmap[id(lnode)] = rnode
        self._r2lmap[id(rnode)] = lnode

    def match(self):
        if self.left is None or self.right is None:
            raise RuntimeError("You must set the sequences to compare with "
                               ".set_seqs(left, right) before matching.")

        if self._matches is not None:
            # We already matched these sequences, use the cache
            return self._matches

        # Make sure the caches are cleared:
        self._matches = []
        self._l2rmap = {}
        self._r2lmap = {}
        self._inorder = set()

        # Let's first just do the naive slow matchings
        lroot = self.left.getroottree()
        lnodes = utils.post_order_traverse(self.left)

        rroot = self.right.getroottree()
        rnodes = list(utils.post_order_traverse(self.right))

        for lnode in lnodes:
            max_match = 0
            match_node = None
            for rnode in rnodes:
                match = (self.leaf_ratio(lnode, rnode) *
                         self.child_ratio(lnode, rnode))
                if match > max_match:
                    match_node = rnode
                    max_match = match
                elif match == max_match and match >= self.F:
                    # We got two (or more) equal matches. In that case
                    # pick the one with the same xpath, if any.
                    if lroot.getpath(lnode) == rroot.getpath(rnode):
                        match_node = rnode

                # Try to shortcut for nodes that are not only equal but also
                # in the same place in the tree
                if (match == 1.0 and
                    lroot.getpath(lnode) == rroot.getpath(rnode)):
                    # This is a complete match, break here
                    break

            if max_match >= self.F:
                self.append_match(lnode, match_node, max_match)

            # We don't want to check nodes that already are matched
            if match_node is not None:
                rnodes.remove(match_node)

        # TODO: If the roots do not match, we should create new roots, and
        # have the old roots be children of the new roots, but let's skip
        # that for now, we don't need it. That's strictly a part of the
        # insert phase, but hey, even the paper defining the phases
        # ignores the phases, so...

        return self._matches

    def node_text(self, node):
        texts = []

        for each in sorted(node.attrib.items()):
            texts.append(':'.join(each))
        if node.text:
            texts.append(node.text.strip())
        if node.tail:
            texts.append(node.tail.strip())

        return ' '.join(texts)

    def leaf_ratio(self, left, right):
        # How similar two nodes are, with no consideration of their children
        if (left.prefix, left.tag) != (right.prefix, right.tag):
            # Different tags == not the same node at all
            return 0

        for attr in self.uniqueattrs:
            if attr in left.attrib or attr in right.attrib:
                # One of the nodes have a unique attribute, we check only that.
                # If only one node has it, it means they are not the same.
                return int(left.attrib.get(attr) == right.attrib.get(attr))

        # We use a simple ratio here, I tried Levenshtein distances
        # but that took a 100 times longer.
        self._sequencematcher.set_seqs(self.node_text(left),
                                      self.node_text(right))
        return self._sequencematcher.ratio()

    def child_ratio(self, left, right):
        # How similar the children of two nodes are
        left_children = left.getchildren()
        right_children = right.getchildren()
        if not left_children and not right_children:
            return 1
        count = 0
        child_count = max((len(left_children), len(right_children)))
        for lchild in left_children:
            for rchild in right_children:
                if self._l2rmap.get(id(lchild)) is rchild:
                    count += 1
                    right_children.remove(rchild)
                    break

        return count/child_count

    def update_node(self, left, right):

        left_xpath = left.getroottree().getpath(left)
        right_xpath = right.getroottree().getpath(right)

        if left.text != right.text:
            yield ('update',
                   '%s/text()' % left_xpath,
                   right.text)
            left.text = right.text

        if left.tail != right.tail:
            xpath = left.getroottree().getpath(left.getparent())
            yield ('update',
                   '%s/text()' % xpath,
                   right.tail)
            left.tail = right.tail

        # Update: Look for differences in common attributes
        left_keys = set(left.attrib.keys())
        right_keys = set(right.attrib.keys())
        newattrs = right_keys.difference(left_keys)
        removedattrs = left_keys.difference(right_keys)
        commonattrs = left_keys.intersection(right_keys)

        # We sort the attributes to get a consistent order in the edit script.
        # That's only so we can do testing in a reasonable way...
        for key in sorted(commonattrs):
            if left.attrib[key] != right.attrib[key]:
                yield ('update',
                       '%s/@%s' % (left_xpath, key),
                       right.attrib[key])
                left.attrib[key] = right.attrib[key]

        # Align: Not needed here, we don't care about the order of
        # attributes.

        # Move: Check if any of the new attributes have the same value
        # as the removed attributes. If they do, it's actually
        # a renaming, and a move is one action instead of remove + insert
        newattrmap = {v:k for (k, v) in right.attrib.items()
                      if k in newattrs}
        for lk in sorted(removedattrs):
            value = left.attrib[lk]
            if value in newattrmap:
                rk = newattrmap[value]
                yield ('move',
                       '%s/@%s' % (left_xpath, lk),
                       '%s/@%s' % (right_xpath, rk),
                       -1)  # Order is irrelevant, -1 is last
                # Remove from list of new attributes
                newattrs.remove(rk)
                # Update left node
                left.attrib[rk] = value
                del left.attrib[lk]

        # Insert: Find new attributes
        for key in sorted(newattrs):
            yield ('insert',
                   '%s/@%s' % (right_xpath, key),
                    right.attrib[key])
            left.attrib[key] = right.attrib[key]

        # Delete: remove removed attributes
        for key in sorted(removedattrs):
            if not key in left.attrib:
                # This was already moved
                continue
            yield ('delete',
                   '%s/@%s' % (left_xpath, key))
            del left.attrib[key]

    def find_pos(self, child):
        parent = child.getparent()
        # Is child is the leftmost child of it's parents that are in order?
        for sibling in parent.getchildren():
            if sibling in self._inorder:
                if sibling is child:
                    # Yup, it's first inorder
                    return 0
                first_inorder = sibling
                break

        # Find the last sibling before the child that is in order
        i = parent.index(child) - 1
        while i >= 0:
            sibling = parent[i]
            if sibling in self._inorder:
                # That's it
                last_inorder = sibling
                break
            i -= 1
        else:
            # No previous sibling in order, this may be a new tree being
            # inserted, and this would be the first child, then.
            return 0

        # Now find the partner of this in the left tree
        u = self._r2lmap[id(sibling)]
        if u is not None:
            return u.getparent().index(u) + 1

    def align_children(self, left, right):
        # Move this definition out
        eqfn = lambda x, y: self._l2rmap[id(x)] is y

        lchildren = [c for c in left.getchildren()
                     if (id(c) in self._l2rmap and
                         self._l2rmap[id(c)].getparent() is right)]
        rchildren = [c for c in right.getchildren()
                     if (id(c) in self._r2lmap and
                         self._r2lmap[id(c)].getparent() is left)]
        if not lchildren or not rchildren:
            # Nothing to align
            return

        lcs = utils.longest_common_subsequence(lchildren, rchildren, eqfn)
        for x, y in lcs:
            # Mark these as in order
            self._inorder.add(lchildren[x])
            self._inorder.add(rchildren[y])

        # Go over those children that are not in order:
        for unaligned_left in set(lchildren) - self._inorder:
            unaligned_right = self._l2rmap.get(id(unaligned_left))
            right_pos = self.find_pos(unaligned_right)
            yield ('move',
                   unaligned_left.getroottree().getpath(unaligned_left),
                   right.getroottree().getpath(right),
                   right_pos)

    def diff(self):
        # Make sure the matching is done first:
        self.match()

        # The paper talks about the five phases, and then does four of them
        # in one phase, in a different order that described. Ah well.
        ltree = self.left.getroottree()
        rtree = self.right.getroottree()

        for rnode in utils.breadth_first_traverse(self.right):

            # (a)
            rparent = rnode.getparent()
            ltarget = self._r2lmap.get(id(rparent))

            # (b) Insert
            if id(rnode) not in self._r2lmap:
                # (i)
                pos = self.find_pos(rnode)
                # (ii)
                yield ('insert',
                       rnode.tag,
                       ltree.getpath(ltarget),
                       pos)
                # (iii)
                lnode = ltarget.makeelement(rnode.tag)
                self.append_match(lnode, rnode, 1.0)
                ltarget.insert(pos, lnode)
                # And then we add attributes and contents with an update.
                # This is different from the paper, because the paper
                # assumes nodes only has labels and values
                for action in self.update_node(lnode, rnode):
                    yield action

            # (c)
            else:
                # Normally there is a check that rnode isn't a root,
                # but that's perhaps only because comparing valueless
                # roots is pointless, but in an elementtree we have no such
                # thing as a valueless root anyway.
                # (i)
                lnode = self._r2lmap[id(rnode)]

                # (ii) Update
                # XXX If they are exactly equal, we can skip this,
                # maybe store match results in a cache?
                for action in self.update_node(lnode, rnode):
                    yield action

                # (iii) Move
                lparent = lnode.getparent()
                if ltarget is not lparent:
                    pos = self.find_pos(rnode)
                    yield ('move',
                           rtree.getpath(rnode),
                           ltree.getpath(ltarget),
                           pos)
                    # Move the node from current parent to target
                    lparent.remove(lnode)
                    ltarget.insert(pos, lnode)

            # (d) Align
            for action in self.align_children(lnode, rnode):
                yield action


        for lnode in utils.post_order_traverse(self.left):
            if id(lnode) not in self._l2rmap:
                # No match
                yield ('delete', ltree.getpath(lnode))
                lnode.getparent().remove(lnode)
