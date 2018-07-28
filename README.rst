xmldiff2
========

xmldiff2 is a library and a command line utility for making diffs out of
XML and XML derived formats, such as XHTML.

It's called xmldiff2, because there is already a library and utility called
xmldiff. xmldiff has various problems though, mainly that the code is complex
and unpythonic, making it hard to maintain and fix bugs. xmldiff2 is currently
significantly slower than xmldiff, at least when you use xmldiff's
C-extensions, but this may change in the future, currently we make no
effort to make xmldiff2 fast, we concentrate on making it correct and usable,

xmldiff2 aims to have 100% test coverage, and the initial releases will also
run on Python 2.7, but this may change soon.


Quick usage
-----------

From the commandline::

  $ xmldiff2 file1.xml file2.xml

As a library::

  from lxml import etree
  from xmldiff2 import match, format

  with open('file1.xml', 'rt', encoding='utf8') as f:
      file1 = etree.parse(f)

  with open('file2.xml', 'rt', encoding='utf8') as f:
      file2 = etree.parse(f)

  matcher = match.Matcher()
  diff = matcher.diff(file1.getroot(), file2.getroot())

  print(format.TextFormatter(diff))
