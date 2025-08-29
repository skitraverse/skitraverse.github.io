AUTHOR = 'Brian J. Oney'
SITENAME = 'Skitraverse'
SITEURL = "https://skitraverse.com"

PATH = "content"

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

DEFAULT_PAGINATION = 1

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True

PLUGIN_PATHS = ["pelican-plugins"]
PLUGINS = ["org_reader"]  # or: PLUGINS = ["pandoc_reader"]

MARKUP = ("org")
# Org metadata mapping (these are defaults; keep for clarity)
ORG_READER_SETTINGS = {
    "function": "read_org",  # leave as-is
    # Optional: pass extra args to emacs if you need custom init files
    # "emacs_binary": "/usr/bin/emacs",
    # "emacs_args": ["-Q"],  # quick emacs w/o init
}
