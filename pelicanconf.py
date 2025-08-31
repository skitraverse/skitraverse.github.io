AUTHOR = 'Brian J. Oney'
SITENAME = 'Skitraverse'
SITEURL = "https://skitraverse.com"

PATH = "content"
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

# Force all content to be articles (not pages) to enable tag processing
ARTICLE_PATHS = [""]
PAGE_PATHS = []
DEFAULT_METADATA = {
    'template': 'article',
}

MARKUP = ("org")
# Org metadata mapping (these are defaults; keep for clarity)
ORG_READER_SETTINGS = {
    "function": "read_org", 
    "extra_export_excludes": ["DATE"],
    "extra_export_includes": ["SCHEDULED", "ORDER"],
    "emacs_settings": {
        "org-export-with-toc": "nil",
        "org-html-with-latex": "nil",
        "org-export-with-timestamps": "active",
        "org-export-with-planning": "t",
    },
    "emacs_eval": [
        "(setq org-export-with-toc nil)",
        "(setq org-html-with-latex nil)",
        "(setq org-export-with-section-numbers nil)",
        "(setq org-export-with-timestamps 'active)",
        "(setq org-export-with-planning t)"
    ]
}
ORG_READER_EMACS_LOCATION = "/usr/bin/emacs"

# Use filesystem dates for files without explicit dates
DEFAULT_DATE = 'fs'

# Override metadata processors to handle empty dates and SCHEDULED
from pelican.utils import get_date as pelican_get_date
from datetime import datetime

def custom_get_date(date_str, settings=None):
    if not date_str or date_str.strip() == '':
        return pelican_get_date('2023-01-01')  # Return default date
    return pelican_get_date(date_str.replace("_", " "))

def process_scheduled(scheduled_str, settings=None):
    """Process SCHEDULED property from org-mode"""
    if not scheduled_str or scheduled_str.strip() == '':
        return None
    # Parse org-mode timestamp format: <2025-01-01 Wed>
    import re
    match = re.search(r'<(\d{4}-\d{2}-\d{2})', scheduled_str)
    if match:
        return pelican_get_date(match.group(1))
    return scheduled_str

def process_order(order_str, settings=None):
    """Process ORDER property from org-mode"""
    if not order_str or order_str.strip() == '':
        return 999  # Default high number for unordered items
    try:
        return int(order_str.strip())
    except ValueError:
        return 999

# Override processors
import pelican.readers
pelican.readers.METADATA_PROCESSORS['date'] = custom_get_date
pelican.readers.METADATA_PROCESSORS['scheduled'] = process_scheduled
pelican.readers.METADATA_PROCESSORS['order'] = process_order

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
EMAIL_BODY = "Dear Brian,%0AI want some more info.%0AKind Regards,"
CONTACT_MESSAGE = "Contact"

# Header image
HEADER_PIC = "img/logo.jpg"
HEADER_PIC_ALT = "Skitraverse Logo"

# Make all these available to templates
TEMPLATE_DEBUG = True

# Custom URL structure using category as routing
ARTICLE_URL = '{category}/{slug}/'
ARTICLE_SAVE_AS = '{category}/{slug}/index.html'
CATEGORY_URL = '{slug}/'
CATEGORY_SAVE_AS = '{slug}/index.html'

# Disable tag page generation to avoid duplicates
TAG_SAVE_AS = ''
TAGS_SAVE_AS = ''
