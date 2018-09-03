xmldiff
========

.. image:: https://travis-ci.org/regebro/xmldiff2.svg?branch=master

.. image:: https://coveralls.io/repos/github/regebro/xmldiff2/badge.svg

xmldiff is a library and a command line utility for making diffs out of
XML.

xmldiff 2.0 is a complete, ground up pure-Python rewrite of xmldiff 1.x.
xmldiff 2.x had various problems, mainly that the code is complex and
unpythonic, making it hard to maintain and fix bugs, there is also an
infinite loop in certain cases, and the c implementation leaks memory,
as well as being hard to use as a library.

xmldiff 2.0 is currently significantly slower than xmldiff 2.x, but this may
change in the future. Currently we make no effort to make xmldiff 2.0 fast,
we concentrate on making it correct and usable.

xmldiff aims to have 100% test coverage.
Python 2.7 support will be dropped soon.

The diff algorithm is based on "`Change Detection in Hierarchically Structured Information
<http://ilpubs.stanford.edu/115/1/1995-46.pdf>`_",
and the text diff is using Googles diff_match_patch algorithm.

Contributors
------------

 * Lennart Regebro, lregebro@shoobx.com (main author)

 * Stephan Richter, srichter@shoobx.com

Quick usage
-----------

From the commandline::

  $ xmldiff file1.xml file2.xml

As a library::

  from lxml import etree
  from xmldiff import main, formatting

  differ = diff.Differ()
  diff = main.diff_files('file1.xml', 'file2.xml',
                         formatter=formatting.XMLFormatter())

  print(diff)

There is also a method ``diff_trees()`` that take two lxml trees, and
a method ``diff_texts()`` that will take strings containing XML.

