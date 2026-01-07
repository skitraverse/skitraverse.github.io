PY?=python3
PELICAN?=pelican
PELICANOPTS=
VENV_DIR=venv

BASEDIR=$(CURDIR)
INPUTDIR=$(BASEDIR)/content
OUTPUTDIR=$(BASEDIR)/docs
CONFFILE=$(BASEDIR)/pelicanconf.py
PUBLISHCONF=$(BASEDIR)/publishconf.py

GITHUB_PAGES_BRANCH=main
GITHUB_PAGES_COMMIT_MESSAGE=Generate Skitraverse site


DEBUG ?= 0
ifeq ($(DEBUG), 1)
	PELICANOPTS += -D
endif

RELATIVE ?= 0
ifeq ($(RELATIVE), 1)
	PELICANOPTS += --relative-urls
endif

SERVER ?= "0.0.0.0"

PORT ?= 0
ifneq ($(PORT), 0)
	PELICANOPTS += -p $(PORT)
endif


venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		$(PY) -m venv $(VENV_DIR); \
		$(VENV_DIR)/bin/pip install -r requirements.txt; \
	fi
	# TODO when pelican org stuff is in pelican-plugins @git submodule update --init --recursive

# Helper to activate venv only if not already active
ACTIVATE_VENV = if [ -z "$$VIRTUAL_ENV" ]; then . $(VENV_DIR)/bin/activate; fi &&

help:
	@echo 'Makefile for a pelican Web site                                           '
	@echo '                                                                          '
	@echo 'Usage:                                                                    '
	@echo '   make venv                           create python virtual environment  '
	@echo '   make html                           (re)generate the web site          '
	@echo '   make clean                          remove the generated files         '
	@echo '   make regenerate                     regenerate files upon modification '
	@echo '   make publish                        generate using production settings '
	@echo '   make serve [PORT=8000]              serve site at http://localhost:8000'
	@echo '   make serve-global [SERVER=0.0.0.0]  serve (as root) to $(SERVER):80    '
	@echo '   make devserver [PORT=8000]          serve and regenerate together      '
	@echo '   make devserver-global               regenerate and serve on 0.0.0.0    '
	@echo '   make github                         upload the web site via gh-pages   '
	@echo '                                                                          '
	@echo 'Set the DEBUG variable to 1 to enable debugging, e.g. make DEBUG=1 html   '
	@echo 'Set the RELATIVE variable to 1 to enable relative urls                    '
	@echo '                                                                          '

html: venv
	$(ACTIVATE_VENV) "$(PELICAN)" "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)
	$(ACTIVATE_VENV) python3 -m pagefind --site "$(OUTPUTDIR)"

clean:
	[ ! -d "$(OUTPUTDIR)" ] || rm -rf "$(OUTPUTDIR)"

regenerate: venv
	$(ACTIVATE_VENV) "$(PELICAN)" -r "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

serve: venv
	$(ACTIVATE_VENV) "$(PELICAN)" -l "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

serve-global: venv
	$(ACTIVATE_VENV) "$(PELICAN)" -l "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS) -b $(SERVER)

devserver: venv
	$(ACTIVATE_VENV) "$(PELICAN)" -lr "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS) -b 0.0.0.0

devserver-global: venv
	$(ACTIVATE_VENV) "$(PELICAN)" -lr "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS) -b 0.0.0.0

publish: venv
	$(ACTIVATE_VENV) "$(PELICAN)" "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(PUBLISHCONF)" $(PELICANOPTS)
	$(ACTIVATE_VENV) python3 -m pagefind --site "$(OUTPUTDIR)"

github: publish
	git add "$(OUTPUTDIR)"
	git commit -m "$(GITHUB_PAGES_COMMIT_MESSAGE)"
	git push origin $(GITHUB_PAGES_BRANCH)

test-seo: html
	@echo "Running SEO validation tests..."
	@python3 test_seo.py

.PHONY: venv html help clean regenerate serve serve-global devserver devserver-global publish github test-seo
