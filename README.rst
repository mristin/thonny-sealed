*********************
thonny-sealed
*********************

.. image:: https://github.com/mristin/thonny-sealed/workflows/Continuous%20Integration%20-%20Ubuntu/badge.svg
    :alt: Continuous Integration - Ubuntu

.. image:: https://github.com/mristin/thonny-sealed/workflows/Continuous%20Integration%20-%20OSX/badge.svg
    :alt: Continuous Integration - OSX

.. image:: https://github.com/mristin/thonny-sealed/workflows/Continuous%20Integration%20-%20Windows/badge.svg
    :alt: Continuous Integration - Windows

.. image:: https://coveralls.io/repos/github/mristin/thonny-sealed/badge.svg?branch=main
    :target: https://coveralls.io/github/mristin/thonny-sealed?branch=main
    :alt: Test coverage

.. image:: https://badge.fury.io/py/thonny-sealed.svg
    :target: https://badge.fury.io/py/thonny-sealed
    :alt: PyPI - version

.. image:: https://img.shields.io/pypi/pyversions/thonny-sealed.svg
    :alt: PyPI - Python Version


thonny-sealed is a plug-in for `Thonny IDE`_ to restrict writing to certain blocks of text based on code comments.

.. _Thonny IDE: https://thonny.org/

This is especially practical for instructional sessions such as classroom exercises.
The teacher prepares the exercises and demarcates the "sealed" blocks using special comments (``# sealed: on`` and ``# sealed: off`` or, more visually appealing, ``# sealed: 🡻`` and ``# sealed: 🡹``, respectively).

Since we do not want the students to inadvertently introduce new sealed blocks during the exercises, the comment blocks are further sealed by using a hash of the content and their order.
To that end, the plug-in provides a command-line utility ``thonny-seal``.

Once the content was properly sealed, the teacher distributes the exercises.
The students open them in Thonny with ``thonny-sealed`` plug-in installed.
The sealed blocks can be copied in the editor, but not modified anymore.

.. image:: https://raw.githubusercontent.com/mristin/thonny-sealed/main/readme/screenshot.png
    :alt: Screenshot of the code view with the sealed content
    :width: 1290
    :height: 883

Installation
============
In Thonny
---------

The plug-in can be easily installed *via* Thonny.
Go to ``Tools`` menu and select ``Manage plug-ins...``:

.. image:: https://raw.githubusercontent.com/mristin/thonny-sealed/main/readme/manage_plugins.png
    :alt: Tools -> Manage plug-ins...
    :width: 916
    :height: 472

Search for ``thonny-sealed`` on PyPI and click on the link to install it:

.. image:: https://raw.githubusercontent.com/mristin/thonny-sealed/main/readme/search_on_pypi.png
    :alt: Search on PyPI
    :width: 1251
    :height: 984

With pip
--------
In your virtual environment, invoke:

.. code-block::

    pip install --user thonny-sealed

Usage
=====
Thonny-sealed inspects the blocks of code in your files based on the special comments.
The user is prevented from editing the content within the sealed blocks.

* Mark the start of every block with a comment line ``# sealed: on``. Analogously, mark the end of a sealed block with ``# sealed: off``. Alternatively, you can use the visually more appealing comments ``# sealed: 🡻`` and ``# sealed: 🡹``, respectively.

  Here is an example file:

.. code-block:: python

    """Provide some service."""

    # sealed: on
    def some_func() -> None:
        """Do something."""
        # sealed: off

* Call in the terminal (where plug-in has been installed) to "seal" the blocks with the hashes:

.. code-block::

    thonny-seal --input path/to/the/file.py --write

* Your file is now sealed and can be loaded in the plug-in.
  The content of the file is:

.. code-block:: python

    """Provide some service."""

    # sealed: on 3a9ff394
    def some_func() -> None:
        """Do something."""
        # sealed: off 3a9ff394

Alternatively, you can write the output to the STDOUT if you do not want to overwrite the file by omitting the ``--write`` argument:

.. code-block::

    thonny-sealed --input path/to/the/file.py

Contributing
============

Feature requests or bug reports are always very, very welcome!

Please see quickly if the issue does not already exist in the `issue section`_ and,
if not, create `a new issue`_.

.. _issue section: https://github.com/mristin/thonny-sealed/issues
.. _a new issue: https://github.com/mristin/thonny-sealed/issues/new

You can also contribute in code.
Please see `CONTRIBUTING.rst`_.

.. _CONTRIBUTING.rst: https://github.com/mristin/thonny-sealed/blob/main/CONTRIBUTING.rst

Versioning
==========

We follow `Semantic Versioning`_.
The version X.Y.Z indicates:

* X is the major version (backward-incompatible),
* Y is the minor version (backward-compatible), and
* Z is the patch version (backward-compatible bug fix).

.. _Semantic Versioning: http://semver.org/spec/v1.0.0.html