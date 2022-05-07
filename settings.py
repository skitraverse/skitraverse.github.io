# -*- coding: utf-8 -*-

import os

from flask_flatorgpages import convert_org_to_html


def parent_dir(path):
    '''Return the parent of a directory.'''
    return os.path.abspath(os.path.join(path, os.pardir))


# Assumes the app is located in the same directory where this file resides
APP_DIR = os.path.dirname(os.path.abspath(__file__))

REPO_NAME = os.path.basename(APP_DIR)  # Used for FREEZER_BASE_URL
DEBUG = True

PROJECT_ROOT = APP_DIR
# In order to deploy to Github pages, you must build the static files to
# the project root
FREEZER_DESTINATION = APP_DIR
# Since this is a repo page (not a Github user page), we need to set the
# BASE_URL to the correct url as per GH Pages' standards

FREEZER_BASE_URL = "http://localhost/{0}".format(REPO_NAME)
FREEZER_REMOVE_EXTRA_FILES = False

FLATPAGES_HTML_RENDERER = convert_org_to_html

FLATPAGES_MARKDOWN_EXTENSIONS = []
FLATPAGES_ROOT = os.path.join(APP_DIR, 'content')
FLATPAGES_EXTENSION = '.org'
