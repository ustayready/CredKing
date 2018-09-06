lxml is a Pythonic, mature binding for the libxml2 and libxslt libraries.  It
provides safe and convenient access to these libraries using the ElementTree
API.

It extends the ElementTree API significantly to offer support for XPath,
RelaxNG, XML Schema, XSLT, C14N and much more.

To contact the project, go to the `project home page
<http://lxml.de/>`_ or see our bug tracker at
https://launchpad.net/lxml

In case you want to use the current in-development version of lxml,
you can get it from the github repository at
https://github.com/lxml/lxml .  Note that this requires Cython to
build the sources, see the build instructions on the project home
page.  To the same end, running ``easy_install lxml==dev`` will
install lxml from
https://github.com/lxml/lxml/tarball/master#egg=lxml-dev if you have
an appropriate version of Cython installed.


After an official release of a new stable series, bug fixes may become
available at
https://github.com/lxml/lxml/tree/lxml-4.2 .
Running ``easy_install lxml==4.2bugfix`` will install
the unreleased branch state from
https://github.com/lxml/lxml/tarball/lxml-4.2#egg=lxml-4.2bugfix
as soon as a maintenance branch has been established.  Note that this
requires Cython to be installed at an appropriate version for the build.

4.2.1 (2018-03-21)
==================

Bugs fixed
----------

* LP#1755825: ``iterwalk()`` failed to return the 'start' event for the initial
  element if a tag selector is used.

* LP#1756314: Failure to import 4.2.0 into PyPy due to a missing library symbol.

* LP#1727864, GH#258: Add "-isysroot" linker option on MacOS as needed by XCode 9.




