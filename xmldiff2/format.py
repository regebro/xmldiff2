from copy import deepcopy
from lxml import etree
from xmldiff2.diff_match_patch import diff_match_patch


DIFF_NS = 'http://namespaces.shoobx.com/diff'
DIFF_PREFIX = 'diff'


class XMLFormatter(object):

    def format(self, orig_tree, diff):
        # Make a new tree, both because we want to add the diff namespace
        # and also because we don't want to modify the original tree.

        result = deepcopy(orig_tree)
        etree.register_namespace(DIFF_PREFIX, DIFF_NS)

        for action in diff:
            action_type = '_handle_' + type(action).__name__
            method = getattr(self, action_type)
            method(action, result)

        etree.cleanup_namespaces(result, top_nsmap={DIFF_PREFIX: DIFF_NS})
        return result

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
