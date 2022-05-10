# -*- coding: utf-8 -*-

import os
import pypandoc
import re
from flask_flatpages.utils import pygmented_markdown


def custom_convert_org_to_html(text):
    md = pypandoc.convert_text(text, to="markdown_strict", format='org')
    output = pygmented_markdown(md)

    if '<table>' in output:
        output = re.sub('<table>', '<table class="table table-sm table-striped">', output)
    if 'img alt="" src="' in output:
        output = re.sub('src="([^"]+)"', lambda x: f'src="{ url_for("static", filename=x.group(1)) }"', output)
    # print(output)
    return output

# Assumes the app is located in the same directory where this file resides
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# REPO_NAME = os.path.basename(APP_DIR)  # Used for FREEZER_BASE_URL
REPO_NAME = 'skitraverse.github.io'
DEBUG = True

PROJECT_ROOT = APP_DIR
# In order to deploy to Github pages, you must build the static files to
# the project root
FREEZER_DESTINATION = APP_DIR
# Since this is a repo page (not a Github user page), we need to set the
# BASE_URL to the correct url as per GH Pages' standards

FREEZER_BASE_URL = "http://localhost/{0}".format(REPO_NAME)
FREEZER_REMOVE_EXTRA_FILES = False

FLATPAGES_HTML_RENDERER = custom_convert_org_to_html

FLATPAGES_MARKDOWN_EXTENSIONS = []
FLATPAGES_ROOT = os.path.join(APP_DIR, 'content')
FLATPAGES_EXTENSION = '.org'
