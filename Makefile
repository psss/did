
TMP = $(CURDIR)/tmp
VERSION = $(shell grep ^Version status-report.spec | sed 's/.* //')

# Push files to the production web only when in the master branch
ifeq "$(shell git rev-parse --abbrev-ref HEAD)" "master"
PUSH_URL = fedorapeople.org:public_html/status-report
else
PUSH_URL = fedorapeople.org:public_html/status-report/testing
endif

PACKAGE = status-report-$(VERSION)
DOCS = $(TMP)/$(PACKAGE)/docs
EXAMPLES = $(TMP)/$(PACKAGE)/examples
CSS = --stylesheet=style.css --link-stylesheet
FILES = LICENSE README \
		Makefile status-report.spec \
		docs examples source

all: push clean

build:
	mkdir -p $(TMP)/{SOURCES,$(PACKAGE)}
	cp -a $(FILES) $(TMP)/$(PACKAGE)
	rst2man README | gzip > $(DOCS)/status-report.1.gz
	rst2html README $(CSS) > $(DOCS)/index.html
	rst2man $(DOCS)/notes.rst | gzip > $(DOCS)/status-report-notes.1.gz
	rst2html $(DOCS)/notes.rst $(CSS) > $(DOCS)/notes.html

tarball: build
	cd $(TMP) && tar cfj SOURCES/$(PACKAGE).tar.bz2 $(PACKAGE)

rpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bb status-report.spec

srpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bs status-report.spec

packages: rpm srpm

push: packages
	# Documentation & examples
	scp $(DOCS)/*.{css,html} $(PUSH_URL)
	scp $(EXAMPLES)/* $(PUSH_URL)/examples
	# Archives & rpms
	scp status-report.spec \
		$(TMP)/SRPMS/$(PACKAGE)* \
		$(TMP)/RPMS/noarch/$(PACKAGE)* \
		$(TMP)/SOURCES/$(PACKAGE).tar.bz2 \
		$(PUSH_URL)/download

clean:
	rm -rf $(TMP)
	find source -name '*.pyc' -exec rm {} \;
