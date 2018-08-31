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
WS_BOTH = 'both'  # Normalize ignorable whitespace and text whitespace
WS_TEXT = 'text'  # Normalize whitespace only inside text tags
WS_TAGS = 'tags'  # Delete ignorable whitespace (between tags)
WS_NONE = 'none'  # Preserve all whitespace


class TagPlaceholderReplacer(object):
    """Replace tags with unicode placeholders

    This class searches for certain tags in an XML tree and replaces them
    with unicode placeholders. The idea is to replace structured content
    (in this case XML elements) with unicode characters which then
    participate in the regular text diffing algorithm. This makes text
    diffing easier and faster.

    The code can then unreplace the unicode placeholders with the tags.
    """

    def __init__(self, text_tags=(), formatting_tags=(), normalize=WS_NONE):
        self.text_tags = text_tags
        self.formatting_tags = formatting_tags
        self.normalize = normalize
        self.placeholders2xml = {}
        self.xml2placeholders = {}
        # This number represents the beginning of the largest private-use
        #  block (13,000 characters) in the unicode space.
        self.placeholder = 0xf0000

    def get_placeholder(self, text):
        if text in self.xml2placeholders:
            return self.xml2placeholders[text]

        self.placeholder += 1
        ph = six.unichr(self.placeholder)
        self.placeholders2xml[ph] = text
        self.xml2placeholders[text] = ph
        return ph

    def do_element(self, element):
        for child in element:
            # Resolve all formatting text by allowing the inside text to
            # participate in the text diffing.
            if child.tag in self.formatting_tags:
                # If it's known text formatting tags, do this hierarchically.
                # All other tags are replaced as single unknown units.
                self.do_element(child)
                attrs = ' '.join('%s="%s"' % attr
                                 for attr in element.attrib.items())
                if attrs:
                    text = '<%s %s>' % (child.tag, attrs)
                else:
                    text = '<%s>' % child.tag
                open_ph = self.get_placeholder(text)
                close_ph = self.get_placeholder('</%s>' % child.tag)

                element.text = ((element.text or u'') + open_ph +
                                (child.text or u'') + close_ph +
                                (child.tail or u''))
            else:
                # Replace the whole tag, with content:
                tail = child.tail or u''
                child.tail = None
                text = etree.tounicode(child)
                ph = self.get_placeholder(text)
                element.text = (element.text or u'') + ph + tail

            # Remove the element from the tree now that we have inserted a
            # placeholder.
            element.remove(child)

        if element.text is not None:
            if self.normalize in (WS_BOTH, WS_TEXT):
                element.text = cleanup_whitespace(element.text)

    def do_tree(self, tree):
        if self.text_tags:
            for elem in tree.xpath('//'+'|//'.join(self.text_tags)):
                self.do_element(elem)

    def undo_string(self, text):
        regexp = u'([%s])' % u''.join(self.placeholders2xml)
        new_text = u''
        for seg in re.split(regexp, text, flags=re.MULTILINE):
            # Segments can be either plain string or placeholders.
            if len(seg) == 1 and seg in self.placeholders2xml:
                new_text += self.placeholders2xml[seg]
            else:
                new_text += seg

        if new_text == text:
            # Nothing left to replace
            return new_text

        # We can have multiple levels of things to replace here:
        return self.undo_string(new_text)

    def undo_element(self, elem):
        if self.placeholders2xml:

            if elem.text:
                new_text = self.undo_string(elem.text)
                if new_text != elem.text:
                    # Something was replaced, create the XML to insert.
                    content = etree.fromstring(u'<wrap>%s</wrap>' % new_text)
                    elem.text = content.text

                    for child in content:
                        elem.append(child)

            if elem.tail:
                new_text = self.undo_string(elem.tail)
                if new_text != elem.tail:
                    content = etree.fromstring(u'<wrap>%s</wrap>' % new_text)
                    elem.tail = content.text
                    parent = elem.getparent()
                    for child in content:
                        parent.append(child)

            for child in elem:
                self.undo_element(child)

    def undo_tree(self, tree):
        if self.text_tags:
            for elem in tree.xpath('//'+'|//'.join(self.text_tags)):
                self.undo_element(elem)


class XMLFormatter(object):
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
    WS_BOTH normalizes all whitespace in all texts, WS_TEXT normalizes only
    inside text_tags, WS_NONE will preserve all whitespace.
    """

    def __init__(self, pretty_print=True, remove_blank_text=False,
                 normalize=WS_NONE, text_tags=(), formatting_tags=()):
        # Mapping from placeholders -> structural content and vice versa.
        self.normalize = normalize
        self.pretty_print = pretty_print
        self.remove_blank_text = pretty_print
        self.text_tags = text_tags
        self.formatting_tags = formatting_tags
        self.placeholderer = TagPlaceholderReplacer(
            text_tags=text_tags, formatting_tags=formatting_tags,
            normalize=normalize)

    def prepare(self, left_tree, right_tree):
        """prepare() is run on the trees before diffing

        This is so the formatter can apply magic before diffing."""
        self.placeholderer.do_tree(left_tree)
        self.placeholderer.do_tree(right_tree)

    def finalize(self, result_tree):
        """finalize() is run on the resulting tree before returning it

        This is so the formatter cab apply magic after diffing."""
        self.placeholderer.undo_tree(result_tree)

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
        return etree.tounicode(result, pretty_print=self.pretty_print)

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
        if self.normalize in (WS_BOTH, WS_TAGS):
            left_value = cleanup_whitespace(left_value or u'').strip()
            right_value = cleanup_whitespace(right_value or u'').strip()

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


class RMLFormatter(XMLFormatter):

    def __init__(self, pretty_print=True, remove_blank_text=True,
                 normalize=WS_BOTH,
                 text_tags=('para', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'),
                 formatting_tags=('b', 'u', 'i', 'strike', 'em', 'super',
                                  'sup', 'sub', 'link', 'a', 'span')):
        super(RMLFormatter, self).__init__(
            pretty_print=pretty_print, remove_blank_text=remove_blank_text,
            normalize=normalize, text_tags=text_tags,
            formatting_tags=formatting_tags)
