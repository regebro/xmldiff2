import os
import unittest

from io import open
from lxml import etree
from xmldiff2 import match, utils

class TestAPI(unittest.TestCase):
    left = u"<document><p>Text</p><p>More</p></document>"
    right = u"<document><p>Tokst</p><p>More</p></document>"
    lefttree = etree.fromstring(left)
    righttree = etree.fromstring(right)
    matcher = match.Matcher()

    def test_set_trees(self):
        # Passing in just one parameter causes an error:
        with self.assertRaises(TypeError):
            self.matcher.set_trees(self.lefttree, None)

        # Passing in something that isn't iterable also cause errors...
        with self.assertRaises(TypeError):
            self.matcher.set_trees(object(), self.righttree)

        # This is the way:
        self.matcher.set_trees(self.lefttree, self.righttree)

    def test_match(self):
        # Passing in just one parameter causes an error:
        with self.assertRaises(TypeError):
            self.matcher.match(self.lefttree, None)

        # Passing in something that isn't iterable also cause errors...
        with self.assertRaises(TypeError):
            self.matcher.match(object(), self.righttree)

        # This is the way:
        res1 = self.matcher.match(self.lefttree, self.righttree)

        # Or, you can use set_trees:
        self.matcher.set_trees(self.lefttree, self.righttree)
        res2 = self.matcher.match()

        # The match sequences should be the same, of course:
        self.assertEqual(res1, res2)
        # But importantly, they are not the same object, meaning the
        # matching was redone.
        self.assertIsNot(res1, res2)
        # However, if we call match() a second time without setting
        # new sequences, we'll get a cached result:
        self.assertIs(self.matcher.match(), res2)

    def test_diff(self):
        # Passing in just one parameter causes an error:
        with self.assertRaises(TypeError):
            list(self.matcher.diff(self.lefttree, None))

        # Passing in something that isn't iterable also cause errors...
        with self.assertRaises(TypeError):
            list(self.matcher.diff(object(), self.righttree))

        # This is the way:
        res1 = list(self.matcher.diff(self.lefttree, self.righttree))

        # Or, you can use set_trees() or match()
        # We need to reparse self.lefttree, since after the diffing they
        # are equal.
        self.lefttree = etree.fromstring(self.left)
        self.matcher.set_trees(self.lefttree, self.righttree)
        res2 = list(self.matcher.diff())

        # The match sequences should be the same, of course:
        self.assertEqual(res1, res2)
        # But importantly, they are not the same object, meaning the
        # matching was redone.
        self.assertIsNot(res1, res2)
        # There is no caching of diff(), so running it again means another
        # diffing.
        self.assertIsNot(list(self.matcher.diff()), res2)

class TestNodeRatios(unittest.TestCase):

    def test_compare_equal(self):
        xml = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section xml:id="oldfirst" ref="3" single-ref="3">
            <para>First paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        lefttree = etree.fromstring(xml)
        righttree = etree.fromstring(xml)
        matcher = match.Matcher()
        matcher.set_trees(lefttree, righttree)
        matcher.match()

        # Every node in these trees should get a 1.0 comparison from
        # both comparisons.
        for left, right in zip(utils.post_order_traverse(lefttree),
                               utils.post_order_traverse(righttree)):
            self.assertEqual(matcher.leaf_ratio(left, right), 1.0)
            self.assertEqual(matcher.child_ratio(left, right), 1.0)


    def test_compare_different_leafs(self):
        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="2" single-ref="2">
            <para>This doesn't match at all</para>
        </section>
        <section xml:id="oldfirst" ref="3" single-ref="3">
            <para>First paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>It's completely different</para>
        </section>
        <section xml:id="oldfirst" ref="4" single-ref="4">
            <para>Another paragraph</para>
        </section>
        <section ref="5" single-ref="5">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        lefttree = etree.fromstring(left)
        righttree = etree.fromstring(right)
        matcher = match.Matcher()

        # Make some choice comparisons here
        # These node are exactly the same
        left = lefttree.xpath('/document/story/section[3]/para')[0]
        right = righttree.xpath('/document/story/section[3]/para')[0]

        self.assertEqual(matcher.leaf_ratio(left, right), 1.0)

        # These nodes have slightly different text, but no children
        left = lefttree.xpath('/document/story/section[2]/para')[0]
        right = righttree.xpath('/document/story/section[2]/para')[0]

        self.assertAlmostEqual(matcher.leaf_ratio(left, right),
                               0.7058823529411765)

        # These nodes should not be very similar
        left = lefttree.xpath('/document/story/section[1]/para')[0]
        right = righttree.xpath('/document/story/section[1]/para')[0]
        self.assertAlmostEqual(matcher.leaf_ratio(left, right),
                               0.2692307692307692)


    def test_compare_different_nodes(self):
        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="2" single-ref="2">
            <para>First paragraph</para>
            <para>Second paragraph</para>
        </section>
        <section ref="3" single-ref="3">
            <para>Third paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="2" single-ref="2">
            <para>First paragraph</para>
        </section>
        <section single-ref="3" ref="3">
            <para>Second paragraph</para>
            <para>Third paragraph</para>
        </section>
        <section single-ref="4" ref="4" >
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        lefttree = etree.fromstring(left)
        righttree = etree.fromstring(right)
        matcher = match.Matcher()
        matcher.set_trees(lefttree, righttree)
        matcher.match()

        # Make some choice comparisons here. leaf_ratio will always be 1.0,
        # as these leafs have the same attributes and no text, even though
        # attributes may be in different order.
        left = lefttree.xpath('/document/story/section[1]')[0]
        right = righttree.xpath('/document/story/section[1]')[0]

        self.assertEqual(matcher.leaf_ratio(left, right), 1.0)
        # Only one of two matches:
        self.assertEqual(matcher.child_ratio(left, right), 0.5)

        left = lefttree.xpath('/document/story/section[2]')[0]
        right = righttree.xpath('/document/story/section[2]')[0]

        self.assertEqual(matcher.leaf_ratio(left, right), 1.0)
        # Only one of two matches:
        self.assertEqual(matcher.child_ratio(left, right), 0.5)

        # These nodes should not be very similar
        left = lefttree.xpath('/document/story/section[3]')[0]
        right = righttree.xpath('/document/story/section[3]')[0]
        self.assertEqual(matcher.leaf_ratio(left, right), 1.0)
        self.assertEqual(matcher.child_ratio(left, right), 1.0)


    def test_compare_with_xmlid(self):
        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section xml:id="oldfirst" ref="1" single-ref="1">
            <para>First paragraph</para>
            <para>This is the second paragraph</para>
        </section>
        <section ref="3" single-ref="3" xml:id="tobedeleted">
            <para>Det tredje stycket</para>
        </section>
        <section xml:id="last" ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section xml:id="newfirst" ref="1" single-ref="1">
            <para>First paragraph</para>
        </section>
        <section xml:id="oldfirst" single-ref="2" ref="2">
            <para>This is the second</para>
            <para>Det tredje stycket</para>
        </section>
        <section single-ref="4" ref="4" >
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        lefttree = etree.fromstring(left)
        righttree = etree.fromstring(right)
        matcher = match.Matcher()
        matcher.set_trees(lefttree, righttree)
        matcher.match()

        # Make some choice comparisons here.

        left = lefttree.xpath('/document/story/section[1]')[0]
        right = righttree.xpath('/document/story/section[1]')[0]

        # These have different id's
        self.assertEqual(matcher.leaf_ratio(left, right), 0)
        # And one out of two children in common
        self.assertEqual(matcher.child_ratio(left, right), 0.5)

        # Here's the ones with the same id:
        left = lefttree.xpath('/document/story/section[1]')[0]
        right = righttree.xpath('/document/story/section[2]')[0]

        self.assertEqual(matcher.leaf_ratio(left, right), 1.0)
        # And one out of two children in common
        self.assertEqual(matcher.child_ratio(left, right), 0.5)

        # The last ones are completely similar, but only one
        # has an xml:id, so they do not match.
        left = lefttree.xpath('/document/story/section[3]')[0]
        right = righttree.xpath('/document/story/section[3]')[0]
        self.assertEqual(matcher.leaf_ratio(left, right), 0)
        self.assertEqual(matcher.child_ratio(left, right), 1.0)


class TestMatcherMatch(unittest.TestCase):

    def _match(self, left, right):
        left_tree = etree.fromstring(left)
        right_tree = etree.fromstring(right)
        matcher = match.Matcher()
        matcher.set_trees(left_tree, right_tree)
        matches = matcher.match()
        lpath = left_tree.getroottree().getpath
        rpath = right_tree.getroottree().getpath
        return [(lpath(item[0]), rpath(item[1])) for item in matches]

    def test_same_tree(self):
        xml = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section xml:id="oldfirst" ref="3" single-ref="3">
            <para>First paragraph</para>
        </section>
        <section xml:id="oldlast" ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""
        result = self._match(xml, xml)
        nodes = list(utils.post_order_traverse(etree.fromstring(xml)))
        # Everything matches
        self.assertEqual(len(result), len(nodes))

    def test_no_xml_id_match(self):
        # Here we insert a section first, but because they contain numbering
        # it's easy to match section 1 in left with section 2 in right,
        # though it should be detected as an insert.

        # If the number of similar attributes are few it works fine, the
        # differing content of the ref="3" section means it's detected to
        # be an insert.
        left = u"""<document>
            <story firstPageTemplate="FirstPage">
            <section ref="3" single-ref="3">
            <para>First paragraph</para>
            </section>
            <section ref="4" single-ref="4">
            <para>Last paragraph</para>
            </section>
            </story>
    </document>
    """

        # We even detect that the first section is an insert without
        # xmlid, but that's less reliable.
        right = u"""<document>
            <story firstPageTemplate="FirstPage">
            <section ref="3" single-ref="3">
            <para>New paragraph</para>
            </section>
            <section ref="4" single-ref="4">
            <para>First paragraph</para>
            </section>
            <section ref="5" single-ref="5">
            <para>Last paragraph</para>
            </section>
            </story>
    </document>
    """

        result = self._match(left, right)
        self.assertEqual(result, [
            ('/document/story/section[1]/para',
             '/document/story/section[2]/para'),
            ('/document/story/section[1]',
             '/document/story/section[2]'),
            ('/document/story/section[2]/para',
             '/document/story/section[3]/para'),
            ('/document/story/section[2]',
             '/document/story/section[3]'),
            ('/document/story',
             '/document/story'),
            ('/document',
             '/document')
        ])

    def test_no_xmlid_miss(self):
        # Here we insert a section first, but because they contain numbering
        # it's easy to match section 1 in left with section 2 in right,
        # though it should be detected as an insert.

        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3"
                 description="This is to trick the differ">
            <para>First paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Second paragraph</para>
        </section>
        <section ref="5" single-ref="5">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        # This first section contains attributes that are similar and longer
        # than the content text. This tricks the matcher so we don't get a
        # match between old section 1 and new section 2.
        # We also do not get a match between old section 1 and new section 1,
        # as they have no matching children. So this will generate a lot
        # of updates and inserts, and not look good.
        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3"
                 description="This is to trick the differ">
            <para>New paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>First paragraph</para>
        </section>
        <section ref="5" single-ref="5">
            <para>Second paragraph</para>
        </section>
        <section ref="6" single-ref="6">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        result = self._match(left, right)
        self.assertEqual(result, [
            ('/document/story/section[1]/para',
             '/document/story/section[2]/para'),
            ('/document/story/section[2]/para',
             '/document/story/section[3]/para'),
            ('/document/story/section[2]',
             '/document/story/section[3]'),
            ('/document/story/section[3]/para',
             '/document/story/section[4]/para'),
            ('/document/story/section[3]',
             '/document/story/section[4]'),
            ('/document/story',
             '/document/story'),
            ('/document',
             '/document'),
        ])

    def test_with_xmlid(self):
        # This first section contains attributes that are similar (and longer
        # than the content text. That would trick the matcher into matching
        # the oldfirst and the newfirst section to match, except that we
        # this time also have xml:id's, and they trump everything else!
        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3" xml:id="oldfirst"
                 description="This is to trick the differ">
            <para>First paragraph</para>
        </section>
        <section ref="4" single-ref="4" xml:id="oldsecond">
            <para>Second paragraph</para>
        </section>
        <section ref="5" single-ref="5" xml:id="oldlast">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        # We even detect that the first section is an insert without
        # xmlid, but that's less reliable.
        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3" xml:id="newfirst"
                 description="This is to trick the differ">
            <para>New paragraph</para>
        </section>
        <section ref="4" single-ref="4" xml:id="oldfirst">
            <para>First paragraph</para>
        </section>
        <section ref="5" single-ref="5" xml:id="oldsecond">
            <para>Second paragraph</para>
        </section>
        <section ref="6" single-ref="6" xml:id="oldlast">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        result = self._match(left, right)
        self.assertEqual(result, [
            ('/document/story/section[1]/para',
             '/document/story/section[2]/para'),
            ('/document/story/section[1]',
             '/document/story/section[2]'),
            ('/document/story/section[2]/para',
             '/document/story/section[3]/para'),
            ('/document/story/section[2]',
             '/document/story/section[3]'),
            ('/document/story/section[3]/para',
             '/document/story/section[4]/para'),
            ('/document/story/section[3]',
             '/document/story/section[4]'),
            ('/document/story',
             '/document/story'),
            ('/document',
             '/document')
        ])

    def test_change_attribs(self):

        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section xml:id="oldfirst" ref="3" single-ref="3">
            <para>First</para>
        </section>
        <section xml:id="oldlast" ref="4" single-ref="4">
            <para>Last</para>
        </section>
    </story>
</document>
"""

        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section xml:id="oldfirst" ref="4" single-ref="4">
            <para>First</para>
        </section>
        <section xml:id="oldlast" ref="5" single-ref="5">
            <para>Last</para>
        </section>
    </story>
</document>
"""
        # It matches everything straight, which means the attrib changes
        # should become updates, which makes sense.
        result = self._match(left, right)
        self.assertEqual(result, [
            ('/document/story/section[1]/para',
             '/document/story/section[1]/para'),
            ('/document/story/section[1]',
             '/document/story/section[1]'),
            ('/document/story/section[2]/para',
             '/document/story/section[2]/para'),
            ('/document/story/section[2]',
             '/document/story/section[2]'),
            ('/document/story',
             '/document/story'),
            ('/document',
             '/document')
        ])

    def test_move_paragraph(self):
        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>First paragraph</para>
            <para>Second paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>First paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Second paragraph</para>
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""
        result = self._match(left, right)
        self.assertEqual(result, [
            ('/document/story/section[1]/para[1]',
             '/document/story/section[1]/para'),
            ('/document/story/section[1]/para[2]',
             '/document/story/section[2]/para[1]'),
            ('/document/story/section[1]', '/document/story/section[1]'),
            ('/document/story/section[2]/para',
             '/document/story/section[2]/para[2]'),
            ('/document/story/section[2]', '/document/story/section[2]'),
            ('/document/story', '/document/story'),
            ('/document', '/document')
        ])


class TestMatcherUpdateNode(unittest.TestCase):
    """Testing only the update phase of the diffing"""

    def _match(self, left, right):
        left_tree = etree.fromstring(left)
        right_tree = etree.fromstring(right)
        matcher = match.Matcher()
        matcher.set_trees(left_tree, right_tree)
        matches = matcher.match()
        steps = []
        for left, right, m in matches:
            steps.extend(matcher.update_node(left, right))

        return steps

    def test_same_tree(self):
        xml = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section xml:id="oldfirst" ref="3" single-ref="3">
            <para>First paragraph</para>
        </section>
        <section xml:id="oldlast" ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""
        result = self._match(xml, xml)
        nodes = list(utils.post_order_traverse(etree.fromstring(xml)))
        # Everything matches
        self.assertEqual(result, [])

    def test_attribute_changes(self):
        left = u"""<root><node attr1="ohyeah" attr2="ohno" attr3="maybe" """\
               u"""attr0="del">The contained text</node>And a tail!</root>"""

        right = u"""<root><node attr4="ohyeah" attr2="uhhuh" attr3="maybe" """\
                u"""attr5="new">The new text</node>Also a tail!</root>"""

        result = self._match(left, right)

        self.assertEqual(
            result,
            [
                ('update', '/root/node/text()', 'The new text'),
                ('update', '/root/text()', 'Also a tail!'),
                ('update', '/root/node/@attr2', 'uhhuh'),
                ('move', '/root/node/@attr1', '/root/node/@attr4', -1),
                ('insert', '/root/node/@attr5', 'new'),
                ('delete', '/root/node/@attr0'),
            ]
        )


class TestMatcherAlignChildren(unittest.TestCase):
    """Testing only the align phase of the diffing"""

    def _align(self, left, right):
        left_tree = etree.fromstring(left)
        right_tree = etree.fromstring(right)
        matcher = match.Matcher()
        matcher.set_trees(left_tree, right_tree)
        matches = matcher.match()
        steps = []
        for left, right, m in matches:
            steps.extend(matcher.align_children(left, right))
        return steps

    def test_same_tree(self):
        xml = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section xml:id="oldfirst" ref="3" single-ref="3">
            <para>First paragraph</para>
        </section>
        <section xml:id="oldlast" ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""
        result = self._align(xml, xml)
        # Everything matches
        self.assertEqual(result, [])

    def test_move_paragraph(self):
        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>First paragraph</para>
            <para>Second paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>First paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Second paragraph</para>
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""
        result = self._align(left, right)
        # Everything matches
        self.assertEqual(result, [])

    def test_move_children(self):
        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>First paragraph</para>
            <para>Second paragraph</para>
            <para>Last paragraph</para>
        </section>
    </story>
</document>
"""

        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>Second paragraph</para>
            <para>Last paragraph</para>
            <para>First paragraph</para>
        </section>
    </story>
</document>
"""
        result = self._align(left, right)
        self.assertEqual(result,
                         [('move', '/document/story/section/para[1]',
                           '/document/story/section', 2)])


class TestMatcherDiff(unittest.TestCase):
    """Testing only the align phase of the diffing"""

    def _diff(self, left, right):
        parser = etree.XMLParser(remove_blank_text=True)
        left_tree = etree.XML(left, parser)
        right_tree = etree.XML(right, parser)
        matcher = match.Matcher()
        matcher.set_trees(left_tree, right_tree)
        matches = list(matcher.diff())
        return matches

    def test_process_1(self):
        left = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>First paragraph</para>
            <para>Second paragraph</para>
            <para>Third paragraph</para>
        </section>
        <deleteme>
            <para>Delete it</para>
        </deleteme>
    </story>
</document>
"""

        right = u"""<document>
    <story firstPageTemplate="FirstPage">
        <section ref="3" single-ref="3">
            <para>First paragraph</para>
            <para>Second paragraph</para>
        </section>
        <section ref="4" single-ref="4">
            <para>Third paragraph</para>
            <para>Fourth paragraph</para>
        </section>
    </story>
</document>
"""
        result = self._diff(left, right)
        self.assertEqual(
            result,
            [('insert', 'section', '/document/story', 1),
             ('insert', '/document/story/section[2]/@ref', '4'),
             ('insert', '/document/story/section[2]/@single-ref', '4'),
             ('move', '/document/story/section[1]/para[3]',
              '/document/story/section[2]', 0),
             ('insert', 'para', '/document/story/section[2]', 0),
             ('update', '/document/story/section[2]/para[1]/text()',
              'Fourth paragraph'),
             ('delete', '/document/story/deleteme/para'),
             ('delete', '/document/story/deleteme'),
             ]
        )

    def test_needs_align(self):
        left = "<root><n><p>1</p><p>2</p><p>3</p></n><n><p>4</p></n></root>"
        right = "<root><n><p>2</p><p>4</p></n><n><p>1</p><p>3</p></n></root>"
        result = self._diff(left, right)
        self.assertEqual(
            result,
            [('move', '/root/n[1]', '/root', 1),
             ('move', '/root/n[2]/p[2]', '/root/n[1]', 0),
            ]
        )

    def test_rmldoc(self):
        here = os.path.split(__file__)[0]
        lfile = os.path.join(here, 'data', 'rmldoc_left.xml')
        rfile = os.path.join(here, 'data', 'rmldoc_right.xml')
        with open(lfile, 'rt', encoding='utf8') as l:
            left = l.read()
        with open(rfile, 'rt', encoding='utf8') as r:
            right = r.read()

        result = self._diff(left, right)
        self.assertEqual(
            result,
            [('insert',
              '{http://namespaces.shoobx.com/application}section',
              '/document/story',
              4),
             ('insert', '/document/story/app:section[4]/@hidden', 'false'),
             ('insert', '/document/story/app:section[4]/@name', 'sign'),
             ('insert', '/document/story/app:section[4]/@ref', '3'),
             ('insert', '/document/story/app:section[4]/@removed', 'false'),
             ('insert', '/document/story/app:section[4]/@single-ref', '3'),
             ('insert',
              '/document/story/app:section[4]/@title',
              'Signing Bonus'),
             ('update', '/document/story/app:section[5]/@ref', '4'),
             ('update', '/document/story/app:section[5]/@single-ref', '4'),
             ('update', '/document/story/app:section[6]/@ref', '5'),
             ('update', '/document/story/app:section[6]/@single-ref', '5'),
             ('update', '/document/story/app:section[7]/@ref', '6'),
             ('update', '/document/story/app:section[7]/@single-ref', '6'),
             ('update', '/document/story/app:section[8]/@ref', '7'),
             ('update', '/document/story/app:section[8]/@single-ref', '7'),
             ('update', '/document/story/app:section[9]/@ref', '8'),
             ('update', '/document/story/app:section[9]/@single-ref', '8'),
             ('update', '/document/story/app:section[10]/@ref', '9'),
             ('update', '/document/story/app:section[10]/@single-ref', '9'),
             ('update', '/document/story/app:section[11]/@ref', '10'),
             ('update', '/document/story/app:section[11]/@single-ref', '10'),
             ('update', '/document/story/app:section[12]/@ref', '11'),
             ('update', '/document/story/app:section[12]/@single-ref', '11'),
             ('update', '/document/story/app:section[14]/@ref', '12'),
             ('update', '/document/story/app:section[14]/@single-ref', '12'),
             ('update',
              '/document/story/app:section[1]/para[2]/app:placeholder/text()',
              'Second Name'),
             ('insert',
              '{http://namespaces.shoobx.com/application}term',
              '/document/story/app:section[4]',
              0),
             ('insert',
              '/document/story/app:section[4]/app:term/@name',
              'sign_bonus'),
             ('insert', '/document/story/app:section[4]/app:term/@set', 'ol'),
             ('insert', 'para', '/document/story/app:section[4]', 0),
             ('insert',
              '{http://namespaces.shoobx.com/application}ref',
              '/document/story/app:section[4]/para',
              0),
             ('update',
              '/document/story/app:section[4]/para/app:ref/text()',
              '3'),
             ('update', '/document/story/app:section[4]/para/text()', '. '),
             ('insert',
              '/document/story/app:section[4]/para/app:ref/@name',
              'sign'),
             ('insert',
              ('/document/story/app:section[4]/para/app:ref/' +
               '@{http://namespaces.shoobx.com/preview}body'),
              '<Ref>'),
             ('insert', 'u', '/document/story/app:section[4]/para', 0),
             ('update',
              '/document/story/app:section[4]/para/text()',
              '.\n              You will also be paid a '),
             ('insert',
              '{http://namespaces.shoobx.com/application}placeholder',
              '/document/story/app:section[4]/para',
              0),
             ('update',
              '/document/story/app:section[4]/para/text()',
              (' signing\n              bonus, which will be paid on the ' +
               'next regularly scheduled pay date\n              after ' +
               'you start employment with the Company.\n              \n' +
               '            ')
              ),
             ('insert',
              '/document/story/app:section[4]/para/app:placeholder/@field',
              'ol.sign_bonus_include_amt'),
             ('insert',
              '/document/story/app:section[4]/para/app:placeholder/@missing',
              'Signing Bonus Amount'),
             ('insert', 'b', '/document/story/app:section[4]/para/u', 0),
             ('update',
              '/document/story/app:section[4]/para/u/b/text()',
              'Signing Bonus'),
             ('update',
              '/document/story/app:section[5]/para/app:ref/text()',
              '4'),
             ('update',
              '/document/story/app:section[6]/para/app:ref/text()',
              '5'),
             ('update',
              '/document/story/app:section[7]/para/app:ref/text()',
              '6'),
             ('update',
              '/document/story/app:section[8]/para/app:ref/text()',
              '7'),
             ('update',
              '/document/story/app:section[9]/para/app:ref/text()',
              '8'),
             ('update',
              '/document/story/app:section[10]/para/app:ref/text()',
              '9'),
             ('update',
              '/document/story/app:section[11]/para/app:ref/text()',
              '10'),
             ('update',
              '/document/story/app:section[12]/para/app:ref/text()',
              '11')
            ]
        )
