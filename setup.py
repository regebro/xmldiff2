from io import open
from setuptools import setup, find_packages

version = '0.0.1'

with open('README.rst', 'rt', encoding='utf8') as readme:
    description = readme.read()

with open('CHANGES.txt', 'rt', encoding='utf8') as changes:
    history = changes.read()


setup(name='xmldiff2',
      version=version,
      description="Creates diffs of XML files",
      long_description=description + '\n' + history,
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Development Status :: 3 - Alpha',
                   'Topic :: Text Processing :: Markup :: XML',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.5',
                   'Programming Language :: Python :: 3.6',
                   'License :: OSI Approved :: MIT License',
                   ],
      keywords='xml html diff',
      author='Lennart Regebro',
      author_email='lregebro@shoobx.com',
      url='https://github.com/Shoobx/xmldiff2',
      license='MIT',
      packages=find_packages(exclude=['doc', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'lxml>=3.1.0',
      ],
      tests_require=[
          'coverage',
      ],
      test_suite='tests',
      entry_points={
               'console_scripts': [
                   'xmldiff2 = xmldiff2.main:run',
               ],
      },
)
