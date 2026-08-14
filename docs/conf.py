"""Sphinx configuration for the AlgoSystem docs site."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "AlgoSystem"
copyright = "AlgoGators"
author = "AlgoGators Team"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
]

myst_enable_extensions = ["colon_fence"]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = []
