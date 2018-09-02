# -*- coding: UTF-8 -*-
import os
import re
import unittest

from io import open
from lxml import etree
from xmldiff2.diff import (Differ, UpdateTextIn, InsertNode, MoveNode,
                           DeleteNode, UpdateAttrib, InsertAttrib, MoveAttrib,
                           DeleteAttrib, UpdateTextAfter)
from xmldiff2.format import (WS_TEXT, XMLFormatter,
                             RMLFormatter, PlaceholdererMaker,
                             DIFF_NS, DIFF_PREFIX, T_OPEN, T_CLOSE)
from xmldiff2.main import diff_texts, diff_trees, diff_files

from .utils import make_test_function, generate_filebased_tests

START = u'<document xmlns:diff="http://namespaces.shoobx.com/diff"><node'
END = u'</node></document>'


class TestTagPlaceholderReplacer(unittest.TestCase):

    def test_get_placeholder(self):
        replacer = PlaceholdererMaker()
        # Get a placeholder:
        ph = replacer.get_placeholder(etree.Element('tag'), T_OPEN, None)
        self.assertEqual(ph, u'\U000f0005')
        # Do it again:
        ph = replacer.get_placeholder(etree.Element('tag'), T_OPEN, None)
        self.assertEqual(ph, u'\U000f0005')
        # Get another one
        ph = replacer.get_placeholder(etree.Element('tag'), T_CLOSE, ph)
        self.assertEqual(ph, u'\U000f0006')

    def test_do_element(self):
        replacer = PlaceholdererMaker(['p'], ['b'])

        # Formatting tags get replaced, and the content remains
        text = u'<p>This is a tag with <b>formatted</b> text.</p>'
        element = etree.fromstring(text)
        replacer.do_element(element)

        self.assertEqual(
            etree.tounicode(element),
            u'<p>This is a tag with \U000f0006formatted\U000f0005 text.</p>')

        replacer.undo_element(element)
        self.assertEqual(etree.tounicode(element), text)

        # Non formatting tags get replaced with content
        text = u'<p>This is a tag with <foo>formatted</foo> text.</p>'
        element = etree.fromstring(text)
        replacer.do_element(element)
        result = etree.tounicode(element)
        self.assertEqual(
            result,
            u'<p>This is a tag with \U000f0007 text.</p>')

        # Single formatting tags still get two placeholders.
        text = u'<p>This is a <b/> with <foo/> text.</p>'
        element = etree.fromstring(text)
        replacer.do_element(element)
        result = etree.tounicode(element)
        self.assertEqual(
            result,
            u'<p>This is a \U000f0009\U000f0008 with \U000f000a text.</p>')

    def test_do_undo_element(self):
        replacer = PlaceholdererMaker(['p'], ['b'])

        # Formatting tags get replaced, and the content remains
        text = u'<p>This <is/> a <f>tag</f> with <b>formatted</b> text.</p>'
        element = etree.fromstring(text)
        replacer.do_element(element)

        self.assertEqual(
            element.text,
            u'This \U000f0005 a \U000f0006 with \U000f0008formatted\U000f0007 text.')

        replacer.undo_element(element)
        result = etree.tounicode(element)
        self.assertEqual(result, text)

    def test_do_undo_element_double_format(self):
        replacer = PlaceholdererMaker(['p'], ['b', 'u'])

        # Formatting tags get replaced, and the content remains
        text = u'<p>This is <u>doubly <b>formatted</b></u> text.</p>'
        element = etree.fromstring(text)
        replacer.do_element(element)

        self.assertEqual(
            element.text,
            u'This is \U000f0006doubly \U000f0008formatted\U000f0007\U000f0005 text.')

        replacer.undo_element(element)
        result = etree.tounicode(element)
        self.assertEqual(result, text)

    def test_rml_bug(self):
        etree.register_namespace(DIFF_PREFIX, DIFF_NS)
        before_diff = u"""<document xmlns:diff="http://namespaces.shoobx.com/diff">
  <section>
    <para>
      <ref>4</ref>.
      <u><b>At Will Employment</b></u>
      .\u201cText\u201d
    </para>
  </section>
</document>"""
        tree = etree.fromstring(before_diff)
        replacer = PlaceholdererMaker(text_tags=('para',),
                                      formatting_tags=('b', 'u', 'i',))
        replacer.do_tree(tree)
        after_diff = u"""<document xmlns:diff="http://namespaces.shoobx.com/diff">
  <section>
    <para>
      <insert>\U000f0005</insert>.
      \U000f0007\U000f0009At Will Employment\U000f0008\U000f0006
      .\u201c<insert>New </insert>Text\u201d
    </para>
  </section>
</document>"""

        # The diff formatting will find some text to insert.
        delete_attrib = u'{%s}delete-format' % DIFF_NS
        replacer.placeholder2tag[u'\U000f0006'].element.attrib[delete_attrib] = ''
        replacer.placeholder2tag[u'\U000f0007'].element.attrib[delete_attrib] = ''
        tree = etree.fromstring(after_diff)
        replacer.undo_tree(tree)
        result = etree.tounicode(tree)
        expected = u"""<document xmlns:diff="http://namespaces.shoobx.com/diff">
  <section>
    <para>
      <insert><ref>4</ref></insert>.
      <u diff:delete-format=""><b>At Will Employment</b></u>
      .\u201c<insert>New </insert>Text\u201d
    </para>
  </section>
</document>"""
        self.assertEqual(result, expected)


class TestXMLFormat(unittest.TestCase):

    def _format_test(self, left, action, expected):
        formatter = XMLFormatter(pretty_print=False)
        result = formatter.format(etree.fromstring(left), [action])
        self.assertEqual(result, expected)

    def test_incorrect_xpaths(self):
        left = u'<document><node a="v"/><node>Text</node></document>'
        expected = START + u' diff:delete-attr="a">Text' + END

        with self.assertRaises(ValueError):
            action = DeleteAttrib('/document/node', 'a')
            self._format_test(left, action, expected)

        with self.assertRaises(ValueError):
            action = DeleteAttrib('/document/ummagumma', 'a')
            self._format_test(left, action, expected)

    def test_del_attr(self):
        left = u'<document><node a="v">Text</node></document>'
        action = DeleteAttrib('/document/node', 'a')
        expected = START + u' diff:delete-attr="a">Text' + END

        self._format_test(left, action, expected)

    def test_del_node(self):
        left = u'<document><node attr="val">Text</node></document>'
        action = DeleteNode('/document/node')
        expected = START + u' attr="val" diff:delete="">Text' + END

        self._format_test(left, action, expected)

    def test_del_text(self):
        left = u'<document><node attr="val">Text</node></document>'
        action = UpdateTextIn('/document/node', None)
        expected = START + u' attr="val"><diff:delete>Text</diff:delete>' + END

        self._format_test(left, action, expected)

    def test_insert_attr(self):
        left = u'<document><node>We need more text</node></document>'
        action = InsertAttrib('/document/node', 'attr', 'val')
        expected = START + u' attr="val" diff:add-attr="attr">' \
                   'We need more text' + END

        self._format_test(left, action, expected)

    def test_insert_node(self):
        left = u'<document></document>'
        action = InsertNode('/document', 'node', 0)
        expected = START + u' diff:insert=""/></document>'

        self._format_test(left, action, expected)

    def test_move_attr(self):
        # The library currently only uses move attr for when attributes are
        # renamed:
        left = u'<document><node attr="val">Text</node></document>'
        action = MoveAttrib('/document/node', '/document/node', 'attr', 'bottr')
        expected = START + u' bottr="val" diff:rename-attr="attr:bottr"' \
                  '>Text' + END

        self._format_test(left, action, expected)

        # But it could conceivably be used to move attributes between nodes.
        # So we test that as well:
        left = u'<document><node attr="val"><b>Text</b></node></document>'
        action = MoveAttrib('/document/node', '/document/node/b',
                            'attr', 'attr')
        expected = START + u' diff:delete-attr="attr"><b attr="val" ' \
                   'diff:add-attr="attr">Text</b>' + END

        self._format_test(left, action, expected)

    def test_move_node(self):
        # Move 1 down
        left = u'<document><node id="1" /><node id="2" /></document>'
        action = MoveNode('/document/node[1]', '/document', 1)
        expected = START + u' id="1" diff:delete=""/><node id="2"/><node ' \
            'id="1" diff:insert=""/></document>'

        self._format_test(left, action, expected)

        # Move 2 up (same result, different diff)
        left = u'<document><node id="1" /><node id="2" /></document>'
        action = MoveNode('/document/node[2]', '/document', 0)
        expected = START + u' id="2" diff:insert=""/><node id="1"/><node ' \
            'id="2" diff:delete=""/></document>'

        self._format_test(left, action, expected)

    def test_update_attr(self):
        left = u'<document><node attr="val"/></document>'
        action = UpdateAttrib('/document/node', 'attr', 'newval')
        expected = START + u' attr="newval" diff:update-attr="attr:val"/>'\
                   '</document>'

        self._format_test(left, action, expected)

    def test_update_text_in(self):
        left = u'<document><node attr="val"/></document>'
        action = UpdateTextIn('/document/node', 'Text')
        expected = START + u' attr="val"><diff:insert>Text</diff:insert>' + END

        self._format_test(left, action, expected)

        left = u'<document><node>This is a bit of text, right</node></document>'
        action = UpdateTextIn('/document/node', 'Also a bit of text, rick')
        expected = START + u'><diff:delete>This is</diff:delete><diff:insert>' \
            'Also</diff:insert> a bit of text, ri<diff:delete>ght' \
            '</diff:delete><diff:insert>ck</diff:insert>' + END

        self._format_test(left, action, expected)

    def test_update_text_after_1(self):
        left = u'<document><node/><node/></document>'
        action = UpdateTextAfter('/document/node[1]', 'Text')
        expected = START + u'/><diff:insert>Text</diff:insert><node/></document>'

        self._format_test(left, action, expected)

    def test_update_text_after_2(self):
        left = u'<document><node/>This is a bit of text, right</document>'
        action = UpdateTextAfter('/document/node', 'Also a bit of text, rick')
        expected = START + u'/><diff:delete>This is</diff:delete><diff:insert>' \
            'Also</diff:insert> a bit of text, ri<diff:delete>ght' \
            '</diff:delete><diff:insert>ck</diff:insert></document>'

        self._format_test(left, action, expected)


class FormatFileTest(unittest.TestCase):

    formatter = None  # Override this
    maxDiff = None

    def process(self, left, right):
        return diff_files(left, right, formatter=self.formatter)


class XMLFormatFileTest(FormatFileTest):

    formatter = XMLFormatter(pretty_print=False, normalize=WS_TEXT)


class RMLFormatFileTest(FormatFileTest):

    # We use the RMLFormatter for the placeholder tests
    formatter = RMLFormatter()


# Add tests that use no placeholder replacement (ie plain XML)
data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
generate_filebased_tests(data_dir, XMLFormatFileTest)

# Add tests that use placeholder replacement (ie RML)
data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
generate_filebased_tests(data_dir, RMLFormatFileTest, suffix='rml')
