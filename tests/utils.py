import os

from io import open


def make_test_function(left_filename):
    app_path = left_filename.replace('_left.xml', '')
    right_filename = app_path + '_right.xml'
    expected_filename = app_path + '_expected.xml'

    def test(self):
        # The input files are opened as binary, so that any xml encoding
        # can get passed through.
        with open(left_filename, 'rb') as input_file:
            left_xml = input_file.read()
        with open(right_filename, 'rb') as input_file:
            right_xml = input_file.read()
        # The output is in unicode, though, or we can't compare non-ascii chars
        with open(expected_filename, 'rt', encoding='utf8') as input_file:
            expected_xml = input_file.read()

        try:
            result_xml = self.process(left_xml, right_xml)
        except Exception as err:
            if u'.err' not in left_filename:
                raise
            result_xml = u'%s: %s' % (err.__class__.__name__, err)

        self.assertEqual(expected_xml.strip(), result_xml.strip())

    return test

def generate_filebased_tests(data_dir, test_class, ignore_files=()):
    for left_filename in os.listdir(data_dir):
        if not left_filename.endswith('_left.xml'):
            continue
        if left_filename in ignore_files:
            continue

        left_filename = os.path.join(data_dir, left_filename)
        test_function = make_test_function(left_filename)
        test_name = 'test_' + os.path.split(left_filename)[-1]
        setattr(test_class, test_name, test_function)

