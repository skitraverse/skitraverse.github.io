AUTHOR = 'Brian J. Oney'
SITENAME = 'Skitraverse'
SITEURL = "https://skitraverse.com"

PATH = "content"
# Keep content as pages but customize URLs  
PAGE_PATHS = [""]
ARTICLE_PATHS = []
DISPLAY_PAGES_ON_MENU = False

TIMEZONE = 'Europe/Rome'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (
    ("Instagram", "https://instagram.com/skitraverse"),
)

# Social widget
SOCIAL = (
    ("You can add links in your config file", "#"),
    ("Another social link", "#"),
)

DEFAULT_PAGINATION = False
DEFAULT_DATE_FORMAT = '%Y-%m-%d'
DEFAULT_METADATA = {
    'date': '2023-01-01',
}

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True

PLUGIN_PATHS = ["pelican-plugins", "."]
PLUGINS = ["org_reader"]

# Force all content to be articles by default
DEFAULT_METADATA = {
    'template': 'article',
}

MARKUP = ("org")
# Org metadata mapping (these are defaults; keep for clarity)
ORG_READER_SETTINGS = {
    "function": "read_org", 
    "extra_export_excludes": ["DATE"],
    "emacs_settings": {
        "org-export-with-toc": "nil",
    }
}
ORG_READER_EMACS_LOCATION = "/usr/bin/emacs"

# Use filesystem dates for files without explicit dates
DEFAULT_DATE = 'fs'

# Override metadata processors to handle empty dates
from pelican.utils import get_date as pelican_get_date
from datetime import datetime

def custom_get_date(date_str, settings=None):
    if not date_str or date_str.strip() == '':
        return pelican_get_date('2023-01-01')  # Return default date
    return pelican_get_date(date_str.replace("_", " "))

# Override processors
import pelican.readers
pelican.readers.METADATA_PROCESSORS['date'] = custom_get_date

# Use our working templates directory
THEME = "."
THEME_STATIC_DIR = "static"

# Site variables
DESCRIPTION = "Ski traverse stuff" 
SLOGAN = "Come out and play, in the snow"
LOCATION = "Rüschlikon, Switzerland<br>8803"

# Custom template variables

# Contact form variables
EMAIL_SUBJECT = "RE: Skitraverse"
EMAIL_BODY = "Dear Brian,\\nI want some more info.\\nKind Regards,"
CONTACT_MESSAGE = "Contact"

# Header image
HEADER_PIC = "img/logo.jpg"
HEADER_PIC_ALT = "Skitraverse Logo"

# Make all these available to templates
TEMPLATE_DEBUG = True

# Custom URL structure using tags as routing
# Map first tag to directory structure
PAGE_URL = '{category}/{slug}.html'
PAGE_SAVE_AS = '{category}/{slug}.html'

# Category-based URLs for articles  
ARTICLE_URL = '{category}/{slug}.html'
ARTICLE_SAVE_AS = '{category}/{slug}.html'
CATEGORY_URL = '{slug}/'
CATEGORY_SAVE_AS = '{slug}/index.html'
