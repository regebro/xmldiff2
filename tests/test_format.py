import os
import unittest

from io import open
from lxml import etree
from xmldiff2.diff import (Differ, UpdateNode, InsertNode, MoveNode,
                           DeleteNode, UpdateAttrib, InsertAttrib, MoveAttrib,
                           DeleteAttrib)
from xmldiff2.format import XMLFormatter


START = u'<document xmlns:diff="http://namespaces.shoobx.com/diff"><node'
END = u'</node></document>'

class TestXMLFormat(unittest.TestCase):

    def _format_test(self, left, right, action, expected):
        formatter = XMLFormatter()
        result = formatter.format(etree.fromstring(left), [action])
        self.assertEqual(etree.tounicode(result), expected)

    def test_del_attr(self):

        left = u'<document><node a="v">Text</node></document>'
        right = u'<document><node>Text</node></document>'
        action = DeleteAttrib('/document/node', 'a')
        expected = START + u' diff:delete-attr="a">Text' + END

        self._format_test(left, right, action, expected)

    def test_del_node(self):

        left = u'<document><node attr="val">Text</node></document>'
        right = u'<document></document>'
        action = DeleteNode('/document/node')
        expected = START + u' attr="val" diff:delete="">Text' + END

        self._format_test(left, right, action, expected)

    def test_del_text(self):
        left = u'<document><node attr="val">Text</node></document>'
        right = u'<document><node attr="val" /></document>'
        action = UpdateNode('/document/node', None)
        expected = START + u' attr="val"><diff:delete>Text</diff:delete>' + END

        self._format_test(left, right, action, expected)

    def test_insert_attr(self):
        left = u'<document><node>We need more text</node></document>'
        right = u'<document><node attr="val">We need more text</node></document>'
        action = InsertAttrib('/document/node', 'attr', 'val')
        expected = START + u' attr="val" diff:add-attr="attr">' \
                   'We need more text' + END

        self._format_test(left, right, action, expected)

    def test_insert_node(self):
        left = u'<document></document>'
        right = u'<document><node></node></document>'
        action = InsertNode('/document', 'node', 0)
        expected = START + u' diff:insert=""/></document>'

        self._format_test(left, right, action, expected)

    def test_move_attr(self):
        # The library currently only uses move attr for when attributes are
        # renamed:
        left = u'<document><node attr="val">Text</node></document>'
        right = u'<document><node bottr="val">Text</node></document>'
        action = MoveAttrib('/document/node', '/document/node', 'attr', 'bottr')
        expected = START + u' bottr="val" diff:rename-attr="attr:bottr"' \
                  '>Text' + END

        self._format_test(left, right, action, expected)

        # But it could conceivably be used to move attributes between nodes.
        # So we test that as well:
        left = u'<document><node attr="val"><b>Text</b></node></document>'
        right = u'<document><node><b attr="val">Text</b></node></document>'
        action = MoveAttrib('/document/node', '/document/node/b',
                            'attr', 'attr')
        expected = START + u' diff:delete-attr="attr"><b attr="val" ' \
                   'diff:add-attr="attr">Text</b>' + END

        self._format_test(left, right, action, expected)

    def test_move_node(self):
        # Move 1 down
        left = u'<document><node id="1" /><node id="2" /></document>'
        right = u'<document><node id="2" /><node id="1" /></document>'
        action = MoveNode('/document/node[1]', '/document', 1)
        expected = START + u' id="1" diff:delete=""/><node id="2"/><node ' \
            'id="1" diff:insert=""/></document>'

        self._format_test(left, right, action, expected)

        # Move 2 up (same result, different diff)
        left = u'<document><node id="1" /><node id="2" /></document>'
        right = u'<document><node id="2" /><node id="1" /></document>'
        action = MoveNode('/document/node[2]', '/document', 0)
        expected = START + u' id="2" diff:insert=""/><node id="1"/><node ' \
            'id="2" diff:delete=""/></document>'

        self._format_test(left, right, action, expected)

    def test_update_attr(self):
        left = u'<document><node attr="val"/></document>'
        right = u'<document><node attr="newval"/></document>'
        action = UpdateAttrib('/document/node', 'attr', 'newval')
        expected = START + u' attr="newval" diff:update-attr="attr:val"/>'\
                   '</document>'

        self._format_test(left, right, action, expected)

    def test_update_node(self):
        left = u'<document><node attr="val"/></document>'
        right = u'<document><node attr="val">Text</node></document>'
        action = UpdateNode('/document/node', 'Text')
        expected = START + u' attr="val"><diff:insert>Text</diff:insert>' + END

        self._format_test(left, right, action, expected)

        left = u'<document><node>This is a bit of text, right</node></document>'
        right = u'<document><node>Also a bit of text, rick</node></document>'
        action = UpdateNode('/document/node', 'Also a bit of text, rick')
        expected = START + u'><diff:delete>This is</diff:delete><diff:insert>' \
            'Also</diff:insert> a bit of text, ri<diff:delete>ght' \
            '</diff:delete><diff:insert>ck</diff:insert></node></document>'

        self._format_test(left, right, action, expected)

    def test_rmldoc_format(self):
        here = os.path.split(__file__)[0]
        lfile = os.path.join(here, 'data', 'rmldoc_left.xml')
        rfile = os.path.join(here, 'data', 'rmldoc_right.xml')
        efile = os.path.join(here, 'data', 'rmldoc_expected.xml')
        with open(lfile, 'rt', encoding='utf8') as l:
            left = l.read()
        with open(rfile, 'rt', encoding='utf8') as r:
            right = r.read()
        with open(efile, 'rt', encoding='utf8') as e:
            expected = e.read()

        parser = etree.XMLParser(remove_blank_text=True)
        left_tree = etree.XML(left, parser)
        right_tree = etree.XML(right, parser)
        differ = Differ()
        diff = differ.diff(left_tree, right_tree)
        formatter = XMLFormatter()
        result = formatter.format(etree.fromstring(left), diff)
        res = etree.tounicode(result, pretty_print=True)

        # We need to strip() them, because some editors mess up the newlines
        # of the last lines.
        self.assertEqual(res.strip(), expected.strip())
