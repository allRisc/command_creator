# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from command_creator import _info
from datetime import datetime
import importlib.util
import pathlib
import io
import sys

project = 'Command Creator'
copyright = f"{datetime.now().year}, {_info.__author__}"
author = _info.__author__
release = _info.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
  'sphinx.ext.autodoc',
  'sphinx.ext.autosummary',
  'sphinx.ext.napoleon',
]
autosummary_generate = True  # Turn on sphinx.ext.autosummary

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = []

# -- Generate some documentation at runtime -----------------------------------
_conf_root = pathlib.Path(__file__).parent
_tmp_dir = _conf_root.parent.joinpath("build", "_tmp")
_tmp_dir.mkdir(exist_ok=True)
_examples_spec = importlib.util.spec_from_file_location(
                                   "examples.example",
                                   _conf_root.parent.parent.joinpath("examples", "example.py")
                               )
_examples = importlib.util.module_from_spec(_examples_spec)
sys.modules["examples.example"] = _examples
_examples_spec.loader.exec_module(_examples)

with open(_tmp_dir.joinpath("example.out"), "w") as f:
  parser = _examples.CommandName.create_parser()
  str_io = io.StringIO()
  parser.print_help(str_io)
  f.write(str_io.getvalue())
