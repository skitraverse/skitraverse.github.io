#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pdb 
import time
import datetime
import sys
import os
import inspect

# Python 2: urlencoding
# from urllib import quote_plus
# Python 3
# from urllib.parse import quote_plus

from flask import Flask
from flask_frozen import Freezer
from flask import render_template, url_for


from flask_flatorgpages import FlatOrgPages


def whoami():
    return inspect.stack()[1][3]

# Build the website
app = Flask(__name__)

app.config.from_pyfile('settings.py')

pages = FlatOrgPages(app)

default_content = {
    'personal_bit': 'Opening eyes to the beauty of winter landscape, safely',
    'mission': u'Purpose',
    'contact_message': 'Get in touch',
    'copyleft': u'Copyleft &copy; Ski Traverse %i' % time.localtime().tm_year,
    'name': u'Ski Traverse',
    'location': 'Rüschlikon, Switzerland<br>8803',
    'page_title': 'Ski Traverse',
    'description': 'Ski traverse stuff',
    'slogan': 'Come out and play, in the snow'
}

special_content = {
    'home': {
        'template': 'home.html',
        'header_pic': "img/logo.svg",
        'email_subject': 'From Ski Traverse Homepage: ',
        'email_body': 'Dear Brian,\nI want to know more about skitraverses!'
        '\nKind Regards,',
    },
    'book': {
        'template': 'page.html',
        'email_subject': 'Please tell me more about this book.',
        'email_body': 'Dear Brian,\nI want some more info on this book.'
        '\nKind Regards,',
    },
    'cdtpage': {
        'template': 'page.html',
        'email_subject': 'I want more information: ',
        'email_body': 'Dear Brian,\nI want some more info.'
        '\nKind Regards,',
    },
    'tips': {
        'template': 'page.html',
        'email_subject': 'I want more tips: ',
        'email_body': 'Dear Brian,\nI want some more tips.'
        '\nKind Regards,',
    },
    'info': {
        'template': 'page.html',
        'email_subject': 'I want more information: ',
        'email_body': 'Dear Brian,\nI want some more info.'
        '\nKind Regards,',
    },
    'archive': {
        'template': 'archive.html',
        'title': 'Ski Traverse Event Archive',
        'email_subject': 'From Ski Traverse archive: ',
        'email_body': 'Dear Brian,\nWhat about this event archive?'
        '\nKind Regards,',
    },
    'disclaimer': {
        'template': 'page.html',
        'title': 'Disclaimer / Data Protection',
        'email_subject': 'about your disclaimer',
        'email_body': '',
    },
    'impressum': {
        'template': 'page.html',
        'title': 'Impressum / Datenschutz',
        'email_subject': 'Über das Impressum',
        'email_body': '',
    },
}


page_content = {}
for route in special_content:
    page_content[route] = default_content.copy()
    page_content[route].update(special_content[route])


# Views
@app.route('/')
def home():
    route = whoami()
    _ = [x.meta.update({'tags': ''}) for x in pages if 'tags' not in x.meta]
    _ = [x.meta.update({'order': 999}) for x in pages if 'order' not in x.meta]
    tips = [page for page in pages if 'tips' in page.meta['tags']]
    info = [page for page in pages if 'info' in page.meta['tags']]
    # reports = [page for page in pages if 'report' in page.meta['tags']]
    wintercdt = [page for page in pages if 'wintercdt' in page.meta['tags']]
    tips.sort(key=lambda x: x.meta['order'])
    info.sort(key=lambda x: x.meta['order'])
    wintercdt.sort(key=lambda x: x.meta['order'])
    return render_template(
        page_content[route]['template'],
        # upcoming=upcoming,
        info=info,
        tips=tips,
        # reports=reports,
        wintercdt = wintercdt,
        **page_content[route]
    )


@app.route('/tips/<path:path>/')
def tips(path):
    # 'path' is the filename of a page, without the file extension
    route = whoami()
    # set title etc. from org-file
    singlepage = pages.get_or_404(path)
    page_content[route].update(singlepage.meta)
    # pdb.set_trace()
    return render_template(
        page_content[route]['template'],
        page=singlepage,
        **page_content[route]
    )

# @app.route('/reports/<path:path>/')
# def reports(path):
#     # 'path' is the filename of a page, without the file extension
#     route = whoami()
#     # set title etc. from org-file
#     singlepage = pages.get_or_404(path)
#     page_content[route].update(singlepage.meta)
#     # pdb.set_trace()
#     return render_template(
#         page_content[route]['template'],
#         page=singlepage,
#         **page_content[route]
#     )

@app.route('/info/<path:path>/')
def info(path):
    # 'path' is the filename of a page, without the file extension
    route = whoami()
    # set title etc. from org-file
    singlepage = pages.get_or_404(path)
    page_content[route].update(singlepage.meta)
    # pdb.set_trace()
    return render_template(
        page_content[route]['template'],
        page=singlepage,
        **page_content[route]
    )


@app.route('/winter-cdt/<path:path>/')
def cdtpage(path):
    singlepage = pages.get_or_404(path)
    route = whoami()
    # description
    # set title etc. from org-file
    page_content[route].update(singlepage.meta)
    # pdb.set_trace()
    return render_template(
        page_content[route]['template'],
        page=singlepage,
        # past=singlepage.meta['date'] < datetime.date.today(),
        **page_content[route]
    )

@app.route('/disclaimer/')
def disclaimer():
    singlepage = pages.get_or_404('disclaimer')
    route = whoami()
    # pdb.set_trace()
    return render_template(
        page_content[route]['template'],
        page=singlepage,
        **page_content[route]
    )

@app.route('/impressum/')
def impressum():
    singlepage = pages.get_or_404('impressum')
    route = whoami()
    # pdb.set_trace()
    return render_template(
        page_content[route]['template'],
        page=singlepage,
        **page_content[route]
    )

if __name__ == '__main__':
    if "freeze" in sys.argv:
        # Freezer for static website
        freezer = Freezer(app)
        # pdb.set_trace()
        freezer.freeze()
    else:
        port = int(os.environ.get('PORT', 5000))
        # Port 0.0.0.0 so I can see things on a local network
        app.run(host='0.0.0.0', port=port, debug=True)
        # otherwise use the default for localhost (127.0.0.1)
        # app.run(debug=True)
