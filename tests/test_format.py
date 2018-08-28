import os
import re
import unittest

from io import open
from lxml import etree
from xmldiff2.diff import (Differ, UpdateTextIn, InsertNode, MoveNode,
                           DeleteNode, UpdateAttrib, InsertAttrib, MoveAttrib,
                           DeleteAttrib, UpdateTextAfter)
from xmldiff2.format import XMLFormatter, RMLFormatter

from .utils import make_test_function, generate_filebased_tests

START = u'<document xmlns:diff="http://namespaces.shoobx.com/diff"><node'
END = u'</node></document>'


class TestXMLFormat(unittest.TestCase):

    def _format_test(self, left, action, expected):
        formatter = XMLFormatter()
        result = formatter.format(etree.fromstring(left), [action])
        self.assertEqual(etree.tounicode(result), expected)

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
            '</diff:delete><diff:insert>ck</diff:insert></node></document>'

        self._format_test(left, action, expected)

    def test_update_text_after(self):
        left = u'<document><node/><node/></document>'
        action = UpdateTextAfter('/document/node[1]', 'Text')
        expected = START + u'/><diff:insert>Text</diff:insert><node/></document>'

        self._format_test(left, action, expected)

        left = u'<document><node/>This is a bit of text, right</document>'
        action = UpdateTextAfter('/document/node', 'Also a bit of text, rick')
        expected = START + u'/><diff:delete>This is</diff:delete><diff:insert>' \
            'Also</diff:insert> a bit of text, ri<diff:delete>ght' \
            '</diff:delete><diff:insert>ck</diff:insert></document>'

        self._format_test(left, action, expected)


class TestXMLFormatIntegration(unittest.TestCase):

    def no_test_match_complex_text(self):
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
        left = re.sub(u'\s+', u' ', left, flags=re.MULTILINE)

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
        right = re.sub(u'\s+', u' ', right, flags=re.MULTILINE)

        expected = ''

        parser = etree.XMLParser(remove_blank_text=True)
        left_tree = etree.fromstring(left, parser)
        right_tree = etree.fromstring(right, parser)
        differ = Differ()
        diff = list(differ.diff(left_tree, right_tree))
        formatter = XMLFormatter()
        result = formatter.format(etree.fromstring(left), diff)
        res = etree.tounicode(result, pretty_print=True)

        # We need to strip() them, because some editors mess up the newlines
        # of the last lines.
        self.maxDiff = None

        self.assertEqual(res.strip(), expected.strip())


class FormatFileTest(unittest.TestCase):

    formatter = None  # Override this

    def process(self, left_xml, right_xml):
        parser = etree.XMLParser(remove_blank_text=True)
        left_tree = etree.fromstring(left_xml, parser)
        right_tree = etree.fromstring(right_xml, parser)
        differ = Differ()
        formatter = self.formatter()
        formatter.prepare(left_tree, right_tree)
        diff = differ.diff(left_tree, right_tree)
        res = formatter.format(etree.fromstring(left_xml), diff)
        return etree.tounicode(res, pretty_print=True)


class XMLFormatFileTest(FormatFileTest):

    formatter = XMLFormatter


class PlaceholderFormatFileTest(FormatFileTest):

    # We use the RMLFormatter for the placeholder tests
    formatter = RMLFormatter


# Add the common file-based tests
data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
generate_filebased_tests(data_dir, XMLFormatFileTest)

# Add tests for plain XML
data_dir = os.path.join(os.path.dirname(__file__), 'test_format_data')
generate_filebased_tests(data_dir, XMLFormatFileTest)

# Add tests using the placeholder (ie RML)
data_dir = os.path.join(os.path.dirname(__file__), 'test_format_data')
generate_filebased_tests(data_dir, PlaceholderFormatFileTest, suffix='rml')
