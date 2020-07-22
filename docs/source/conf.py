# -*- coding: utf-8 -*-
#
# plexstuff documentation build configuration file, created by
# sphinx-quickstart on Sun Jun 23 11:03:17 2019.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os, sys, datetime
from functools import reduce
from sphinx.util import logging
_mainDir = reduce(lambda x,y: os.path.dirname( x ),
                  range(2), os.path.abspath('.'))
sys.path.insert( 0, _mainDir )

is_in_readthedocs = ( os.environ.get( 'READTHEDOCS' ) is not None )

logger = logging.getLogger( __name__ )
logger.info( "mainDir = %s" % _mainDir)
logger.info( 'READTHEDOCS: %s.' % os.environ.get('READTHEDOCS') )

#
## now don't verify the TLS if not in READTHEDOCS
tls_verify = is_in_readthedocs

#
## following instructions on https://docs.readthedocs.io/en/latest/faq.html#i-get-import-errors-on-libraries-that-depend-on-c-modules
## and instructions on https://stackoverflow.com/questions/28178644/python-readthedocs-how-to-satisfy-the-requirement-sip-or-pyqt/37363830#37363830
## because CANNOT install PyQt4 and stuff in readthedocs
#autodoc_mock_imports = [ 'sip', 'PyQt4', 'PyQt4.QtGui', 'PyQt4.QtCore' ]
#autodoc_mock_imports = ['sip', 'PyQt5', 'PyQt5.QtGui', 'PyQt5.QtCore', 'PyQt5.QtWidgets' ]
#if os.environ.get( 'READTHEDOCS' ):
#    MOCK_MODULES = ['sip', 'PyQt4', 'PyQt4.QtGui', 'PyQt4.QtCore' ]
#    sys.modules.update((mod_name, mock.MagicMock()) for mod_name in MOCK_MODULES)


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.mathjax',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinxcontrib.youtube',
    'sphinx_issues',
    'sphinxarg.ext'
]

#
## following instructions here (https://github.com/svenevs/exhale/tree/master/docs/_intersphinx) to fix beautifulsoup doc.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ( 'https://requests.kennethreitz.org/en/master/', None),
    'beautifulsoup' : ( 'https://www.crummy.com/software/BeautifulSoup/bs4/doc/', "_intersphinx/bs4_objects.inv"),
    'geoip2' : ( 'https://geoip2.readthedocs.io/en/latest', None),
    'gmusicapi' : ( 'https://unofficial-google-music-api.readthedocs.io/en/latest', None ),
    'imdbpy' : ( 'https://imdbpy.readthedocs.io/en/latest', None),
    'pyqt5' : ( 'https://www.riverbankcomputing.com/static/Docs/PyQt5', "_intersphinx/pyqt5_objects.inv" ),
    'requests_oauthlib' : ( 'https://requests-oauthlib.readthedocs.io/en/latest', None ),
    'oauth2client' : ( 'https://oauth2client.readthedocs.io/en/latest', None ),
    'google-auth' : ( 'https://google-auth.readthedocs.io/en/latest', None ),
    'deluge' : ( 'https://deluge.readthedocs.io/en/latest', None ),
    'plexapi' : ( 'https://python-plexapi.readthedocs.io/en/latest', None ),
    'sqlalchemy' : ( 'https://docs.sqlalchemy.org', None ),
    'subliminal' : ( 'https://python-plexapi.readthedocs.io/en/latest', None ),
    'musicbrainzngs' : ( 'https://python-musicbrainzngs.readthedocs.io/en/latest', None ),
    'pillow' : ( 'https://pillow.readthedocs.io/en/stable', None ),
}

#
## write out todos
todo_include_todos = True

verify = False

# numfig stuff
numfig = True

# Add any paths that contain templates here, relative to this directory.
templates_path = [ '_templates' ]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'plexstuff'
copyright = u'%d' % datetime.datetime.now( ).year
author = u'Tanim Islam'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = u'1.0'
# The full version, including alpha/beta/rc tags.
release = u'1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_sidebars = {
   '**': ['globaltoc.html', 'sourcelink.html', 'searchbox.html'],
   'using/windows': ['windowssidebar.html', 'searchbox.html'],
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# dark mode if uncommented
# html_css_files = [ 'rtd_dark.css' ]

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
        'donate.html',
    ]
}


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'plexstuffdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'plexstuff.tex', u'Plexstuff Documentation',
     u'Plex Utility Functionality', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'plexstuff', u'Plexstuff Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'plexstuff', u'plexstuff Documentation',
     author, 'plexstuff', 'One line description of project.',
     'Miscellaneous'),
]
