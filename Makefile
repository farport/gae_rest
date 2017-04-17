#!/bin/bash

# ===========================================================
# Author:   Marcos Lin
# Created:	14 Apr 2017
#
# Makefile used to setup GAE Rest Seed Application
#
# ===========================================================

SRC           = src
PYENV         = venv
PIP           = $(PYENV)/bin/pip
PYLIB_REQ     = requirements.txt
PYLIB_SRC     = $(SRC)/lib
PKG_DEF       = flask jinja2 markupsafe itsdangerous click werkzeug six
GAE_SDK       = "/Developer/Google/google_appengine"

# ------------------
# USAGE: First target called if no target specified
man :
	@cat readme.make
	@cat pylib_req.txt

# ------------------
# Define file needed
$(PIP) :
ifeq ($(shell which virtualenv),)
	$(error virtualenv command needed to be installed.)
endif
	@mkdir -p $(PYENV)
	@virtualenv $(PYENV)


$(PYENV)/pylib_req.txt : $(PYLIB_REQ)
	@$(PIP) install -r $(PYLIB_REQ)
	@cp -a $(PYLIB_REQ) $@
	@echo $(GAE_SDK) > $(PYENV)/lib/python2.7/site-packages/google_appengine.pth

$(PYLIB_SRC):
	@mkdir -p $(PYLIB_SRC)

# ------------------
# MAIN TARGETS	
virtualenv : $(PIP) $(PYENV)/pylib_req.txt $(PYLIB_SRC)

setup_lib : $(PYENV)/lib/python2.7/site-packages
	@for dir in $(PKG_DEF); do \
		if [ -f "$^/$$dir.py" ]; then \
			rsync -av "$^/$$dir.py" $(PYLIB_SRC)/; \
		else \
			mkdir -p $(PYLIB_SRC)/$$dir; \
			rsync -av $^/$$dir/ $(PYLIB_SRC)/$$dir/; \
		fi \
	done

setup : virtualenv setup_lib



# ------------------
# DEFINE PHONY TARGET: Basically all targets
.PHONY : \
	man virtualenv setup setup_lib

