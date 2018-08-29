xmldiff2
========

xmldiff2 is a library and a command line utility for making diffs out of
XML.

It's called xmldiff2, because there is already a library and utility called
xmldiff. xmldiff has various problems though, mainly that the code is complex
and unpythonic, making it hard to maintain and fix bugs. xmldiff2 is currently
significantly slower than xmldiff, at least when you use xmldiff's
C-extensions, but this may change in the future, currently we make no
effort to make xmldiff2 fast, we concentrate on making it correct and usable.

xmldiff2 aims to have 100% test coverage, and the initial releases will also
run on Python 2.7, but this may change soon.


Quick usage
-----------

From the commandline::

  $ xmldiff2 file1.xml file2.xml

As a library::

  from lxml import etree
  from xmldiff2 import main

  differ = diff.Differ()
  diff = main.diff_files('file1.xml', 'file2.xml',
                         formatter=format.XMLFormatter())

  print(diff)

There is also a method ``diff_trees()`` that take two lxml trees, and
a method ``diff_texts()`` that will take strings containing XML.
