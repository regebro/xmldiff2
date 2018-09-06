import os
import unittest

from io import open
from lxml import etree
from xmldiff import utils
from xmldiff.diff import (Differ, UpdateTextIn, InsertNode, MoveNode,
                          DeleteNode, UpdateAttrib, InsertAttrib, RenameAttrib,
                          DeleteAttrib, UpdateTextAfter)


class APITests(unittest.TestCase):
    left = u"<document><p>Text</p><p>More</p></document>"
    right = u"<document><p>Tokst</p><p>More</p></document>"
    lefttree = etree.fromstring(left)
    righttree = etree.fromstring(right)
    differ = Differ()

    def test_set_trees(self):
        # Passing in just one parameter causes an error:
        with self.assertRaises(TypeError):
            self.differ.set_trees(self.lefttree, None)

        # Passing in something that isn't iterable also cause errors...
        with self.assertRaises(TypeError):
            self.differ.set_trees(object(), self.righttree)

        # This is the way:
        self.differ.set_trees(self.lefttree, self.righttree)

    def test_match(self):
        # Passing in just one parameter causes an error:
        with self.assertRaises(TypeError):
            self.differ.match(self.lefttree, None)

        # Passing in something that isn't iterable also cause errors...
        with self.assertRaises(TypeError):
            self.differ.match(object(), self.righttree)

        # This is the way:
        res1 = self.differ.match(self.lefttree, self.righttree)
        lpath = self.differ.left.getroottree().getpath
        rpath = self.differ.right.getroottree().getpath
        res1x = [(lpath(x[0]), rpath(x[1]), x[2]) for x in res1]

        # Or, you can use set_trees:
        self.differ.set_trees(self.lefttree, self.righttree)
        res2 = self.differ.match()
        lpath = self.differ.left.getroottree().getpath
        rpath = self.differ.right.getroottree().getpath
        res2x = [(lpath(x[0]), rpath(x[1]), x[2]) for x in res2]

        # The match sequences should be the same, of course:
        self.assertEqual(res1x, res2x)
        # But importantly, they are not the same object, meaning the
        # matching was redone.
        self.assertIsNot(res1, res2)
        # However, if we call match() a second time without setting
        # new sequences, we'll get a cached result:
        self.assertIs(self.differ.match(), res2)

    def test_diff(self):
        # Passing in just one parameter causes an error:
        with self.assertRaises(TypeError):
            list(self.differ.diff(self.lefttree, None))

        # Passing in something that isn't iterable also cause errors...
        with self.assertRaises(TypeError):
            list(self.differ.diff(object(), self.righttree))

        # This is the way:
        res1 = list(self.differ.diff(self.lefttree, self.righttree))

        # Or, you can use set_trees() or match()
        # We need to reparse self.lefttree, since after the diffing they
        # are equal.
        self.lefttree = etree.fromstring(self.left)
        self.differ.set_trees(self.lefttree, self.righttree)
        res2 = list(self.differ.diff())

        # The match sequences should be the same, of course:
        self.assertEqual(res1, res2)
        # But importantly, they are not the same object, meaning the
        # matching was redone.
        self.assertIsNot(res1, res2)
        # There is no caching of diff(), so running it again means another
        # diffing.
        self.assertIsNot(list(self.differ.diff()), res2)


class NodeRatioTests(unittest.TestCase):

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
        tree = etree.fromstring(xml)
        differ = Differ()
        differ.set_trees(tree, tree)
        differ.match()

        # Every node in these trees should get a 1.0 leaf_ratio,
        # and if it has children, 1.0 child_ration, else None
        for left, right in zip(utils.post_order_traverse(differ.left),
                               utils.post_order_traverse(differ.right)):
            self.assertEqual(differ.leaf_ratio(left, right), 1.0)
            if left.getchildren():
                self.assertEqual(differ.child_ratio(left, right), 1.0)
            else:
                self.assertIsNone(differ.child_ratio(left, right))

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
        differ = Differ()

        # Make some choice comparisons here
        # These node are exactly the same
        left = lefttree.xpath('/document/story/section[3]/para')[0]
        right = righttree.xpath('/document/story/section[3]/para')[0]

        self.assertEqual(differ.leaf_ratio(left, right), 1.0)

        # These nodes have slightly different text, but no children
        left = lefttree.xpath('/document/story/section[2]/para')[0]
        right = righttree.xpath('/document/story/section[2]/para')[0]

        self.assertAlmostEqual(differ.leaf_ratio(left, right),
                               0.6875)

        # These nodes should not be very similar
        left = lefttree.xpath('/document/story/section[1]/para')[0]
        right = righttree.xpath('/document/story/section[1]/para')[0]
        self.assertAlmostEqual(differ.leaf_ratio(left, right),
                               0.24)

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

        differ = Differ()
        differ.set_trees(etree.fromstring(left), etree.fromstring(right))
        differ.match()

        # Make some choice comparisons here. leaf_ratio will always be 1.0,
        # as these leafs have the same attributes and no text, even though
        # attributes may be in different order.
        left = differ.left.xpath('/document/story/section[1]')[0]
        right = differ.right.xpath('/document/story/section[1]')[0]

        self.assertEqual(differ.leaf_ratio(left, right), 1.0)
        # Only one of two matches:
        self.assertEqual(differ.child_ratio(left, right), 0.5)

        left = differ.left.xpath('/document/story/section[2]')[0]
        right = differ.right.xpath('/document/story/section[2]')[0]

        self.assertEqual(differ.leaf_ratio(left, right), 1.0)
        # Only one of two matches:
        self.assertEqual(differ.child_ratio(left, right), 0.5)

        # These nodes should not be very similar
        left = differ.left.xpath('/document/story/section[3]')[0]
        right = differ.right.xpath('/document/story/section[3]')[0]
        self.assertEqual(differ.leaf_ratio(left, right), 1.0)
        self.assertEqual(differ.child_ratio(left, right), 1.0)

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

        differ = Differ()
        differ.set_trees(etree.fromstring(left), etree.fromstring(right))
        differ.match()

        # Make some choice comparisons here.

        left = differ.left.xpath('/document/story/section[1]')[0]
        right = differ.right.xpath('/document/story/section[1]')[0]

        # These have different id's
        self.assertEqual(differ.leaf_ratio(left, right), 0)
        # And one out of two children in common
        self.assertEqual(differ.child_ratio(left, right), 0.5)

        # Here's the ones with the same id:
        left = differ.left.xpath('/document/story/section[1]')[0]
        right = differ.right.xpath('/document/story/section[2]')[0]

        self.assertEqual(differ.leaf_ratio(left, right), 1.0)
        # And one out of two children in common
        self.assertEqual(differ.child_ratio(left, right), 0.5)

        # The last ones are completely similar, but only one
        # has an xml:id, so they do not match.
        left = differ.left.xpath('/document/story/section[3]')[0]
        right = differ.right.xpath('/document/story/section[3]')[0]
        self.assertEqual(differ.leaf_ratio(left, right), 0)
        self.assertEqual(differ.child_ratio(left, right), 1.0)


class MatchTests(unittest.TestCase):

    def _match(self, left, right):
        left_tree = etree.fromstring(left)
        right_tree = etree.fromstring(right)
        differ = Differ()
        differ.set_trees(left_tree, right_tree)
        matches = differ.match()
        lpath = differ.left.getroottree().getpath
        rpath = differ.right.getroottree().getpath
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

    def test_match_complex_text(self):
        left = """<wrap id="1533728456.41"><para>
            Consultant shall not indemnify and hold Company, its
            affiliates and their respective directors,
            officers, agents and employees harmless from and
            against all claims, demands, losses, damages and
            judgments, including court costs and attorneys'
            fees, arising out of or based upon (a) any claim
            that the Services provided hereunder or, any
            related Intellectual Property Rights or the
            exercise of any rights in or to any Company-Related
            Development or Pre-Existing Development or related
            Intellectual Property Rights infringe on,
            constitute a misappropriation of the subject matter
            of, or otherwise violate any patent, copyright,
            trade secret, trademark or other proprietary right
            of any person or breaches any person's contractual
            rights; This is strange, but <b>true</b>.
            </para></wrap>"""

        right = """<wrap id="1533728456.41"><para>

            Consultant <i>shall not</i> indemnify and hold
            Company, its affiliates and their respective
            directors, officers, agents and employees harmless
            from and against all claims, demands, losses,
            excluding court costs and attorneys' fees, arising
            out of or based upon (a) any claim that the
            Services provided hereunder or, any related
            Intellectual Property Rights or the exercise of any
            rights in or to any Company-Related Development or
            Pre-Existing Development or related Intellectual
            Property Rights infringe on, constitute a
            misappropriation of the subject matter of, or
            otherwise violate any patent, copyright, trade
            secret, trademark or other proprietary right of any
            person or breaches any person's contractual rights;
            This is very strange, but <b>true</b>.

            </para></wrap>"""

        result = self._match(left, right)
        self.assertEqual(result, [
            ('/wrap/para/b', '/wrap/para/b'),
            ('/wrap/para', '/wrap/para'),
            ('/wrap', '/wrap')
        ])

    def test_match_insert_node(self):
        left = u'''<document title="insert-node">
  <story id="id">

  </story>
</document>
'''
        right = u'''<document title="insert-node">
  <story id="id">

    <h1>Inserted <i>Node</i></h1>

  </story>
</document>'''
        result = self._match(left, right)
        self.assertEqual(result, [
            ('/document/story', '/document/story'),
            ('/document', '/document'),
        ])

    def test_entirely_different(self):
        left = u'''<document title="insert-node">
  <story id="id">

  </story>
</document>
'''
        right = u'''<document title="something else">
    <h1>Inserted <i>Node</i></h1>
</document>'''
        result = self._match(left, right)
        self.assertEqual(result, [
            ('/document', '/document'),
        ])


class UpdateNodeTests(unittest.TestCase):
    """Testing only the update phase of the diffing"""

    def _match(self, left, right):
        left_tree = etree.fromstring(left)
        right_tree = etree.fromstring(right)
        differ = Differ()
        differ.set_trees(left_tree, right_tree)
        matches = differ.match()
        steps = []
        for left, right, m in matches:
            steps.extend(differ.update_node_attr(left, right))
            steps.extend(differ.update_node_text(left, right))

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
                UpdateAttrib('/root/node[1]', 'attr2', 'uhhuh'),
                RenameAttrib('/root/node[1]', 'attr1', 'attr4'),
                InsertAttrib('/root/node[1]', 'attr5', 'new'),
                DeleteAttrib('/root/node[1]', 'attr0'),
                UpdateTextIn('/root/node[1]', 'The new text'),
                UpdateTextAfter('/root/node[1]', 'Also a tail!'),
            ]
        )


class AlignChildrenTests(unittest.TestCase):
    """Testing only the align phase of the diffing"""

    def _align(self, left, right):
        left_tree = etree.fromstring(left)
        right_tree = etree.fromstring(right)
        differ = Differ()
        differ.set_trees(left_tree, right_tree)
        matches = differ.match()
        steps = []
        for left, right, m in matches:
            steps.extend(differ.align_children(left, right))
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
                         [MoveNode('/document/story/section/para[1]',
                                   '/document/story/section[1]', 2)])


class DiffTests(unittest.TestCase):
    """Testing only the align phase of the diffing"""

    def _diff(self, left, right):
        parser = etree.XMLParser(remove_blank_text=True)
        left_tree = etree.fromstring(left, parser)
        right_tree = etree.fromstring(right, parser)
        differ = Differ()
        differ.set_trees(left_tree, right_tree)
        editscript = list(differ.diff())
        return editscript

    def test_process(self):
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
            [
                InsertNode('/document/story[1]', 'section', 1),
                InsertAttrib('/document/story/section[2]', 'ref', '4'),
                InsertAttrib('/document/story/section[2]', 'single-ref', '4'),
                MoveNode('/document/story/section[1]/para[3]',
                         '/document/story/section[2]', 0),
                InsertNode('/document/story/section[2]', 'para', 0),
                UpdateTextIn('/document/story/section[2]/para[1]',
                             'Fourth paragraph'),
                DeleteNode('/document/story/deleteme/para[1]'),
                DeleteNode('/document/story/deleteme[1]'),
            ]
        )

    def test_needs_align(self):
        left = "<root><n><p>1</p><p>2</p><p>3</p></n><n><p>4</p></n></root>"
        right = "<root><n><p>2</p><p>4</p></n><n><p>1</p><p>3</p></n></root>"
        result = self._diff(left, right)
        self.assertEqual(
            result,
            [
                MoveNode('/root/n[1]', '/root[1]', 1),
                MoveNode('/root/n[2]/p[2]', '/root/n[1]', 0),
            ]
        )

    def test_no_root_match(self):
        left = '<root attr="val"><n><p>1</p><p>2</p><p>3</p></n>'\
            '<n><p>4</p></n></root>'
        right = '<root><n><p>2</p><p>4</p></n><n><p>1</p><p>3</p></n></root>'
        result = self._diff(left, right)
        self.assertEqual(
            result,
            [
                DeleteAttrib(node='/root[1]', name='attr'),
                MoveNode('/root/n[1]', '/root[1]', 1),
                MoveNode('/root/n[2]/p[2]', '/root/n[1]', 0),
            ]
        )

    def test_rmldoc(self):
        here = os.path.split(__file__)[0]
        lfile = os.path.join(here, 'test_data', 'rmldoc.left.xml')
        rfile = os.path.join(here, 'test_data', 'rmldoc.right.xml')
        with open(lfile, 'rt', encoding='utf8') as infile:
            left = infile.read()
        with open(rfile, 'rt', encoding='utf8') as infile:
            right = infile.read()

        result = self._diff(left, right)
        self.assertEqual(
            result,
            [
                InsertNode(
                    '/document/story[1]',
                    '{http://namespaces.shoobx.com/application}section',
                    4),
                InsertAttrib(
                    '/document/story/app:section[4]', 'hidden', 'false'),
                InsertAttrib(
                    '/document/story/app:section[4]', 'name', 'sign'),
                InsertAttrib(
                    '/document/story/app:section[4]', 'ref', '3'),
                InsertAttrib(
                    '/document/story/app:section[4]', 'removed', 'false'),
                InsertAttrib(
                    '/document/story/app:section[4]', 'single-ref', '3'),
                InsertAttrib(
                 '/document/story/app:section[4]', 'title', 'Signing Bonus'),
                UpdateAttrib('/document/story/app:section[5]', 'ref', '4'),
                UpdateAttrib(
                    '/document/story/app:section[5]', 'single-ref', '4'),
                UpdateAttrib('/document/story/app:section[6]', 'ref', '5'),
                UpdateAttrib(
                    '/document/story/app:section[6]', 'single-ref', '5'),
                UpdateAttrib('/document/story/app:section[7]', 'ref', '6'),
                UpdateAttrib(
                    '/document/story/app:section[7]', 'single-ref', '6'),
                UpdateAttrib('/document/story/app:section[8]', 'ref', '7'),
                UpdateAttrib(
                    '/document/story/app:section[8]', 'single-ref', '7'),
                UpdateAttrib('/document/story/app:section[9]', 'ref', '8'),
                UpdateAttrib(
                    '/document/story/app:section[9]', 'single-ref', '8'),
                UpdateAttrib('/document/story/app:section[10]', 'ref', '9'),
                UpdateAttrib(
                    '/document/story/app:section[10]', 'single-ref', '9'),
                UpdateAttrib('/document/story/app:section[11]', 'ref', '10'),
                UpdateAttrib(
                    '/document/story/app:section[11]', 'single-ref', '10'),
                UpdateAttrib('/document/story/app:section[12]', 'ref', '11'),
                UpdateAttrib(
                    '/document/story/app:section[12]', 'single-ref', '11'),
                UpdateAttrib('/document/story/app:section[14]', 'ref', '12'),
                UpdateAttrib(
                    '/document/story/app:section[14]', 'single-ref', '12'),
                UpdateTextIn(
                    '/document/story/app:section[1]/para[2]/'
                    'app:placeholder[1]',
                    'Second Name'),
                InsertNode(
                 '/document/story/app:section[4]',
                 '{http://namespaces.shoobx.com/application}term',
                 0),
                InsertAttrib(
                 '/document/story/app:section[4]/app:term[1]', 'name',
                 'sign_bonus'),
                InsertAttrib(
                    '/document/story/app:section[4]/app:term[1]', 'set', 'ol'),
                InsertNode('/document/story/app:section[4]', 'para', 1),
                InsertNode(
                 '/document/story/app:section[4]/para[1]',
                 '{http://namespaces.shoobx.com/application}ref',
                 0),
                InsertAttrib(
                 '/document/story/app:section[4]/para/app:ref[1]', 'name',
                 'sign'),
                InsertAttrib(
                    '/document/story/app:section[4]/para/app:ref[1]',
                    '{http://namespaces.shoobx.com/preview}body',
                    '<Ref>'),
                UpdateTextIn(
                    '/document/story/app:section[4]/para/app:ref[1]', '3'),
                UpdateTextAfter(
                    '/document/story/app:section[4]/para/app:ref[1]', '. '),
                InsertNode('/document/story/app:section[4]/para[1]', 'u', 1),
                UpdateTextAfter(
                    '/document/story/app:section[4]/para/u[1]',
                    '.\n              You will also be paid a '),
                InsertNode(
                 '/document/story/app:section[4]/para[1]',
                 '{http://namespaces.shoobx.com/application}placeholder',
                 2),
                InsertAttrib(
                 '/document/story/app:section[4]/para/app:placeholder[1]',
                 'field',
                 'ol.sign_bonus_include_amt'),
                InsertAttrib(
                 '/document/story/app:section[4]/para/app:placeholder[1]',
                 'missing',
                 'Signing Bonus Amount'),
                UpdateTextAfter(
                    '/document/story/app:section[4]/para/app:placeholder[1]',
                    ' signing\n              bonus, which will be paid on the '
                    'next regularly scheduled pay date\n              after '
                    'you start employment with the Company.\n              \n'
                    '            '
                ),
                InsertNode('/document/story/app:section[4]/para/u[1]', 'b', 0),
                UpdateTextIn(
                    '/document/story/app:section[4]/para/u/b[1]',
                    'Signing Bonus'),
                UpdateTextIn(
                 '/document/story/app:section[5]/para/app:ref[1]',
                 '4'),
                UpdateTextIn(
                 '/document/story/app:section[6]/para/app:ref[1]',
                 '5'),
                UpdateTextIn(
                 '/document/story/app:section[7]/para/app:ref[1]',
                 '6'),
                UpdateTextIn(
                 '/document/story/app:section[8]/para/app:ref[1]',
                 '7'),
                UpdateTextIn(
                 '/document/story/app:section[9]/para/app:ref[1]',
                 '8'),
                UpdateTextIn(
                 '/document/story/app:section[10]/para/app:ref[1]',
                 '9'),
                UpdateTextIn(
                 '/document/story/app:section[11]/para/app:ref[1]',
                 '10'),
                UpdateTextIn(
                 '/document/story/app:section[12]/para/app:ref[1]',
                 '11')
            ]
        )

    def test_namespace(self):
        # Test changing nodes and attributes with namespaces
        left = u"""<document xmlns:app="someuri">
    <story app:foo="FirstPage">
        <app:section>
            <foo:para xmlns:foo="otheruri">Lorem ipsum dolor sit amet,
                consectetur adipiscing elit. Pellentesque feugiat metus quam.
                Suspendisse potenti. Vestibulum quis ornare felis,
                ac elementum sem.</foo:para>
            <app:para xmlns:foo="otheruri">Second paragraph</app:para>
            <app:para>Third paragraph</app:para>
            <app:para>
                Paragraph to tweak the matching of the section node
            </app:para>
            <app:para>
                By making many matching children
            </app:para>
            <app:para>
               Until the node matches properly.
            </app:para>
        </app:section>
    </story>
</document>
"""

        right = u"""<document xmlns:app="someuri">
    <story app:foo="FirstPage">
        <app:section>
            <app:para>Lorem ipsum dolor sit amet,
                consectetur adipiscing elit. Pellentesque feugiat metus quam.
                Suspendisse potenti. Vestibulum quis ornare felis,
                ac elementum sem.</app:para>
            <app:para>Second paragraph</app:para>
            <app:para app:attrib="value">Third paragraph</app:para>
            <app:para>
                Paragraph to tweak the matching of the section node
            </app:para>
            <app:para>
                By making many matching children
            </app:para>
            <app:para>
               Until the node matches properly.
            </app:para>
         </app:section>
    </story>
</document>
"""
        result = self._diff(left, right)
        self.assertEqual(
            result,
            [
                InsertNode(
                    '/document/story/app:section[1]',
                    '{someuri}para',
                    0),
                UpdateTextIn(
                    '/document/story/app:section/app:para[1]',
                    'Lorem ipsum dolor sit amet,\n                consectetur '
                    'adipiscing elit. Pellentesque feugiat metus quam.\n'
                    '                Suspendisse potenti. Vestibulum quis '
                    'ornare felis,\n                ac elementum sem.'),
                InsertAttrib('/document/story/app:section/app:para[3]',
                             '{someuri}attrib', 'value'),
                DeleteNode('/document/story/app:section/foo:para[1]'),
            ]
        )

    def test_multiple_tag_deletes(self):
        left = u"""<document title="delte-node-ul">
    <story id="id">

        <ul>
            <li>One</li>
            <li>Two</li>
            <li>Three</li>
        </ul>

    </story>
</document>"""

        right = u"""<document title="delte-node-ul">
    <story id="id">
    </story>
</document>"""

        result = self._diff(left, right)
        self.assertEqual(
            result,
            [UpdateTextIn(node='/document/story[1]', text='\n    '),
             DeleteNode(node='/document/story/ul/li[3]'),
             DeleteNode(node='/document/story/ul/li[2]'),
             DeleteNode(node='/document/story/ul/li[1]'),
             DeleteNode(node='/document/story/ul[1]'),
             ]
        )
