import re
import six

from copy import deepcopy
from lxml import etree
from xmldiff2.diff_match_patch import diff_match_patch
from xmldiff2.diff import UpdateTextIn, UpdateTextAfter
from xmldiff2.utils import cleanup_whitespace


DIFF_NS = 'http://namespaces.shoobx.com/diff'
DIFF_PREFIX = 'diff'

# Flags for whitespace handling in the text aware formatters:
WS_ALL = 'all'  # Normalize all whitespace, even outside text tags
WS_TEXT = 'text'  # Normalize whitespace only in text tags
WS_NONE = 'none'  # Preserve all whitespace


class XMLFormatter(object):

    def prepare(self, left_tree, right_tree):
        """prepare() is run on the trees before diffing

        This is so the formatter can apply magic before diffing."""
        # By default, do nothing:
        pass

    def finalize(self, result_tree):
        """finalize() is run on the resulting tree before returning it

        This is so the formatter cab apply magic after diffing."""
        # By default, do nothing:
        pass

    def format(self, orig_tree, diff):
        # Make a new tree, both because we want to add the diff namespace
        # and also because we don't want to modify the original tree.

        result = deepcopy(orig_tree)
        etree.register_namespace(DIFF_PREFIX, DIFF_NS)

        deferred = []
        for action in diff:
            if isinstance(action, (UpdateTextIn, UpdateTextAfter)):
                # We need to do text updates last
                deferred.append(action)
                continue
            self.handle_action(action, result)

        for action in reversed(deferred):
            self.handle_action(action, result)


        self.finalize(result)

        etree.cleanup_namespaces(result, top_nsmap={DIFF_PREFIX: DIFF_NS})
        return result

    def handle_action(self, action, result):
        action_type = type(action)
        method = getattr(self, '_handle_' + action_type.__name__)
        method(action, result)

    def _xpath(self, node, xpath):
        # This method finds an element with xpath and makes sure that
        # one and exactly one element is found. This is to protect against
        # formatting a diff on the wrong tree, or against using ambigous
        # edit script xpaths.
        result = node.xpath(xpath, namespaces=node.nsmap)
        if len(result) == 0:
            raise ValueError('xpath %s not found.' % xpath)
        if len(result) > 1:
            raise ValueError('Multiple nodes found for xpath %s.' % xpath)
        return result[0]

    def _extend_diff_attr(self, node, action, value):
        diffattr = '{%s}%s-attr' % (DIFF_NS, action)
        oldvalue = node.attrib.get(diffattr, '')
        if oldvalue:
            value = oldvalue + ';' + value
        node.attrib[diffattr] = value

    def _delete_attrib(self, node, name):
        del node.attrib[name]
        self._extend_diff_attr(node, 'delete', name)

    def _handle_DeleteAttrib(self, action, tree):
        node = self._xpath(tree, action.node)
        self._delete_attrib(node, action.name)

    def _delete_node(self, node):
        node.attrib['{%s}delete' % DIFF_NS] = ''

    def _handle_DeleteNode(self, action, tree):
        node = self._xpath(tree, action.node)
        self._delete_node(node)

    def _insert_attrib(self, node, name, value):
        node.attrib[name] = value
        self._extend_diff_attr(node, 'add', name)

    def _handle_InsertAttrib(self, action, tree):
        node = self._xpath(tree, action.target)
        self._insert_attrib(node, action.name, action.value)

    def _insert_node(self, target, node, position):
        # Insert node as a child. However, position is the position in the
        # new tree, and the diff tree may have deleted children, so we must
        # adjust the position for that.
        pos = 0
        offset = 0
        for child in target.getchildren():
            if '{%s}delete' % DIFF_NS in child.attrib:
                offset += 1
            else:
                pos += 1
            if pos > position:
                # We found the right offset
                break

        node.attrib['{%s}insert' % DIFF_NS] = ''
        target.insert(position + offset, node)

    def _handle_InsertNode(self, action, tree):
        target = self._xpath(tree, action.target)
        new_node = target.makeelement(action.tag, nsmap=target.nsmap)
        self._insert_node(target, new_node, action.position)

    def _rename_attrib(self, node, oldname, newname):
        node.attrib[newname] = node.attrib[oldname]
        del node.attrib[oldname]
        self._extend_diff_attr(node, 'rename', '%s:%s' % (oldname, newname))

    def _handle_MoveAttrib(self, action, tree):
        source = self._xpath(tree, action.source)
        target = self._xpath(tree, action.target)
        if source is target:
            # This is a rename
            self._rename_attrib(source, action.oldname, action.newname)
        else:
            # This is a move (can rename at the same time)
            value = source.attrib[action.oldname]
            self._delete_attrib(source, action.oldname)
            self._insert_attrib(target, action.newname, value)

    def _handle_MoveNode(self, action, tree):
        node = self._xpath(tree, action.source)
        inserted = deepcopy(node)
        target = self._xpath(tree, action.target)
        self._delete_node(node)
        self._insert_node(target, inserted, action.position)

    def _update_attrib(self, node, name, value):
        oldval = node.attrib[name]
        node.attrib[name] = value
        self._extend_diff_attr(node, 'update', '%s:%s' % (name, oldval))

    def _handle_UpdateAttrib(self, action, tree):
        node = self._xpath(tree, action.node)
        self._update_attrib(node, action.name, action.value)

    def _insert_text_node(self, node, action, text, pos):
        new_node = node.makeelement('{%s}%s' % (DIFF_NS, action))
        new_node.text = text
        node.insert(pos, new_node)
        return new_node

    def _make_diff_tags(self, left_value, right_value, node, target=None):
        text_diff = diff_match_patch()
        diff = text_diff.diff_main(left_value or '', right_value or '')
        text_diff.diff_cleanupSemantic(diff)

        cur_child = None

        if target is None:
            target = node
            pos = 0
        else:
            pos = target.index(node) + 1

        for op, text in diff:
            if op == 0:
                if cur_child is None:
                    node.text = text
                else:
                    cur_child.tail = text
            elif op == -1:
                cur_child = self._insert_text_node(target, 'delete', text, pos)
                pos += 1
            elif op == 1:
                cur_child = self._insert_text_node(target, 'insert', text, pos)
                pos += 1

    def _handle_UpdateTextIn(self, action, tree):
        node = self._xpath(tree, action.node)
        left_value = node.text
        right_value = action.text
        node.text = None

        self._make_diff_tags(left_value, right_value, node)

        return node

    def _handle_UpdateTextAfter(self, action, tree):
        node = self._xpath(tree, action.node)
        left_value = node.tail
        right_value = action.text
        node.tail = None

        self._make_diff_tags(left_value, right_value, node, node.getparent())

        return node


class XMLPlaceholderFormatter(XMLFormatter):
    """A formatter that also replaces formatting tags with unicode characters

    The idea of this differ is to replace structured content (in this case XML
    elements) with unicode characters which then participate in the regular
    text diffing algorithm. This is done in the prepare() step.

    Each identical XML element will get a unique unicode character. If the
    node is changed for any reason, a new unicode character is assigned to the
    node. This allows identity detection of structured content between the
    two text versions while still allowing customization during diffing time,
    such as marking a new formatting node. The latter feature allows for
    granular style change detection independently of text changes.

    In order for the algorithm to not go crazy and convert entire XML
    documents to text (though that is perfectly doable), a few rules have been
    defined.

    - The `textTags` attribute lists all the XML nodes by name which can
      contain text. All XML nodes within those text nodes are converted to
      unicode placeholders. If you want better control over which parts of
      your XML document are considered text, you can simply override the
      ``insert_placeholders(tree)`` function. It is purposefully kept small to
      allow easy subclassing.

    - By default, all tags inside text tags are treated as immutable
      units. That means the node itself including its entire sub-structure is
      assigned one unicode character.

    - The ``formattingTags`` attribute is used to specify tags that format the
      text. For these tags, the opening and closing tags receive unique
      unicode characters, allowing for sub-structure change detection and
      formatting changes. During the diff markup phase, formatting notes are
      annotated to mark them as inserted or deleted allowing for markup
      specific to those formatting changes.

    The diffed version of the structural tree is passed into the
    ``finalize(tree)`` method to convert all the placeholders back into
    structural content before formatting.

    The ``normalize`` parameter decides how to normalize whitespace.
    WS_ALL normalizes all whitespace in all texts, WS_TEXT normalizes only
    inside text_tags, WS_NONE will preserve all whitespace.
    """

    text_tags = ()
    formatting_tags = ()

    # This number represents the beginning of the largest private-use block in
    # (13,000 characters) the unicode space.
    placeholder = 0xf0000

    nsmap = None

    def __init__(self, text_tags=None, formatting_tags=None, normalize=WS_ALL):
        # Mapping from placeholders -> structural content and vice versa.
        self.placeholders2xml = {}
        self.xml2placeholders = {}
        self.format_placeholders = u''
        self.normalize = normalize
        if text_tags is not None:
            self.text_tags = text_tags
        if formatting_tags is not None:
            self.formatting_tags = formatting_tags

    def prepare(self, left_tree, right_tree):
        self._prepare_tree(left_tree)
        self._prepare_tree(right_tree)

    def _prepare_tree(self, tree):
        for elem in tree.xpath('//'+'|//'.join(self.text_tags)):
            self._insert_placeholders(elem)

    def _insert_placeholders(self, elem):
        for child in elem:
            # Resolve all formatting text by allowing the inside text to
            # participate in the text diffing.
            if child.tag in self.formatting_tags:
                # If it's known text formmating tags, do this hierarchically.
                # All other tags are replaced as single unknown units.
                self._insert_placeholders(child)

            # Replace the tag:
            tail = child.tail or u''
            child.tail = None
            text = etree.tounicode(child)

            if text in self.xml2placeholders:
                ph = self.xml2placeholders[text]
            else:
                self.placeholder += 1
                ph = six.unichr(self.placeholder)
                self.placeholders2xml[ph] = text
                self.xml2placeholders[text] = ph

            elem.text = (elem.text or u'') + ph + tail
            # Remove the element from the tree now that we have inserted a
            # placeholder.
            elem.remove(child)

        if elem.text is not None:
            if self.normalize in (WS_ALL, WS_TEXT):
                elem.text = cleanup_whitespace(elem.text)

    def finalize(self, result_tree):
        self._finalize_tree(result_tree)

    def _finalize_tree(self, tree):
        for elem in tree.xpath('//'+'|//'.join(self.text_tags)):
            self._replace_placeholders(elem)

    def _replace_placeholders(self, elem):
        if elem.text:
            xml_str = u''
            for seg in re.split(u'([%s])' % u''.join(self.placeholders2xml),
                                elem.text, flags=re.MULTILINE):
                # Segments can be either plain string or placeholders.
                if len(seg) == 1 and seg in self.placeholders2xml:
                    xml_str += self.placeholders2xml[seg]
                else:
                    xml_str += seg

            # Now create the XML to insert.
            content = etree.fromstring(u'<wrap>' + xml_str + u'</wrap>')
            elem.text = content.text

            for child in content:
                elem.append(child)

        for child in elem:
            self._replace_placeholders(child)

    def _make_diff_tags(self, left_value, right_value, node, target=None):
        if self.normalize == WS_ALL:
            left_value = cleanup_whitespace(left_value or u'').strip()
            right_value = cleanup_whitespace(right_value or u'').strip()

        super(XMLPlaceholderFormatter, self)._make_diff_tags(
            left_value, right_value, node, target=None)


class XHTMLFormatter(XMLPlaceholderFormatter):
    text_tags = ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li')
    formatting_tags = ('b', 'u', 'i', 'strike', 'em',
                       'super', 'sup', 'sub', 'link', 'a',
                       'span')


class RMLFormatter(XMLPlaceholderFormatter):
    text_tags = ('para', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',)
    formatting_tags = ('b', 'u', 'i', 'strike', 'em',
                       'super', 'sup', 'sub', 'link', 'a',
                       'span')
