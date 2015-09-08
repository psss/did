
TMP = $(CURDIR)/tmp
VERSION = $(shell grep ^Version did.spec | sed 's/.* //')

# Push files to the production web only when in the master branch
ifeq "$(shell git rev-parse --abbrev-ref HEAD)" "master"
PUSH_URL = fedorapeople.org:public_html/did
else
PUSH_URL = fedorapeople.org:public_html/did/testing
endif

PACKAGE = did-$(VERSION)
DOCS = $(TMP)/$(PACKAGE)/docs
EXAMPLES = $(TMP)/$(PACKAGE)/examples
CSS = --stylesheet=style.css --link-stylesheet
FILES = LICENSE README.rst \
		Makefile did.spec \
		docs examples did bin

ifndef USERNAME
    USERNAME = echo $$USER
endif

.PHONY: docs hooks

all: push clean

test:
	py.test tests

coverage:
	coverage run --source=did -m py.test tests
	coverage report

docs: README.rst docs/*.rst
	cd docs && make html

# Install commit hooks
hooks:
	ln -snf ../../hooks/pre-commit .git/hooks
	ln -snf ../../hooks/commit-msg .git/hooks

build:
	mkdir -p $(TMP)/{SOURCES,$(PACKAGE)}
	cp -a $(FILES) $(TMP)/$(PACKAGE)
	# Construct man page from header and README
	cp docs/header.txt $(TMP)/man.rst
	tail -n+7 README.rst | sed '/^Status/,$$d' >> $(TMP)/man.rst
	rst2man $(TMP)/man.rst | gzip > $(DOCS)/did.1.gz
	rst2html README.rst $(CSS) > $(DOCS)/index.html

tarball: build test
	cd $(TMP) && tar cfj SOURCES/$(PACKAGE).tar.bz2 $(PACKAGE)

rpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bb did.spec

srpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bs did.spec

packages: rpm srpm

push: packages
	# Documentation & examples
	scp $(DOCS)/*.{css,html} $(PUSH_URL)
	scp $(EXAMPLES)/* $(PUSH_URL)/examples
	# Archives & rpms
	scp did.spec \
		$(TMP)/SRPMS/$(PACKAGE)* \
		$(TMP)/RPMS/noarch/$(PACKAGE)* \
		$(TMP)/SOURCES/$(PACKAGE).tar.bz2 \
		$(PUSH_URL)/download

clean:
	rm -rf $(TMP)
	find did -name '*.pyc' -exec rm {} \;
	cd docs && make clean

run_docker: build_docker
	@echo
	@echo "Please note: this is a first cut at doing a container version as a result; known issues:"
	@echo "* kerberos auth may not be working correctly"
	@echo "* container runs as privileged to access the conf file"
	@echo "* output directory may not be quite right"
	@echo
	@echo "This does not actually run the docker image as it makes more sense to run it directly. Use:"
	@echo "docker run --privileged --rm -it -v $(HOME)/.did:/did.conf $(USERNAME)/did"
	@echo "If you want to add it to your .bashrc use this:"
	@echo "alias did=\"docker run --privileged --rm -it -v $(HOME)/.did:/did.conf $(USERNAME)/did\""

build_docker: examples/dockerfile
	docker build -t $(USERNAME)/did --file="examples/dockerfile" .
