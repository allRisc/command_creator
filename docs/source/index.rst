.. Command Creator documentation master file, created by
   sphinx-quickstart on Sun Feb  4 00:10:24 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. The project README is embedded here as the landing page. It is parsed as
   MyST Markdown so its internal table-of-contents anchors resolve on this page.

.. include:: ../../README.md
   :parser: myst_parser.sphinx_

.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation:
   :hidden:

   CONTRIBUTING
   CHANGELOG
   license

.. autosummary::
   :toctree: _autosummary
   :caption: API
   :template: module-template.rst
   :recursive:

   command_creator

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
