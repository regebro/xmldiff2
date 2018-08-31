import os

from io import open


def make_test_function(left_filename):
    right_filename = left_filename.replace('.left.', '.right.')
    expected_filename = left_filename.replace('.left.', '.expected.')

    def test(self):
        with open(expected_filename, 'rt', encoding='utf8') as input_file:
            expected_xml = input_file.read()

        try:
            result_xml = self.process(left_filename, right_filename)
        except Exception as err:
            if u'.err' not in left_filename:
                raise
            result_xml = u'%s: %s' % (err.__class__.__name__, err)

        import pdb;pdb.set_trace()
        open('tests/test_data/rmldoc.expected.rml', 'wb').write(expected_xml.encode('utf8'))
        self.assertEqual(expected_xml.strip(), result_xml.strip())

    return test


def generate_filebased_tests(data_dir, test_class, suffix='xml', ignore=()):
    for left_filename in os.listdir(data_dir):
        if not left_filename.endswith('.left.' + suffix):
            continue
        if left_filename in ignore:
            continue

        left_filename = os.path.join(data_dir, left_filename)
        test_function = make_test_function(left_filename)
        test_name = 'test_' + os.path.split(left_filename)[-1].replace('.', '-')
        setattr(test_class, test_name, test_function)

