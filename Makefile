# Prepare variables
TMP = $(CURDIR)/tmp
VERSION = $(shell grep ^Version did.spec | sed 's/.* //')
PACKAGE = did-$(VERSION)
FILES = LICENSE README.rst \
		Makefile did.spec \
		examples did bin
ifndef USERNAME
    USERNAME = echo $$USER
endif


# Define special targets
all: docs packages
.PHONY: docs hooks

# Temporary directory
tmp:
	mkdir $(TMP)

# Run the test suite, optionally with coverage
test: tmp
	DID_DIR=$(TMP) py.test tests
smoke: tmp
	DID_DIR=$(TMP) py.test tests/test_cli.py
coverage: tmp
	DID_DIR=$(TMP) coverage run --source=did,bin -m py.test tests
	coverage report
	coverage annotate


# Build documentation, prepare man page
docs: man
	cd docs && make html
man: source
	cp docs/header.txt $(TMP)/man.rst
	tail -n+7 README.rst | sed '/^Status/,$$d' >> $(TMP)/man.rst
	rst2man $(TMP)/man.rst | gzip > $(TMP)/$(PACKAGE)/did.1.gz


# RPM packaging
source:
	mkdir -p $(TMP)/SOURCES
	mkdir -p $(TMP)/$(PACKAGE)
	cp -a $(FILES) $(TMP)/$(PACKAGE)
	rm -rf $(TMP)/$(PACKAGE)/examples/mr.bob
tarball: source man
	cd $(TMP) && tar cfj SOURCES/$(PACKAGE).tar.bz2 $(PACKAGE)
rpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bb did.spec
srpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bs did.spec
packages: rpm srpm


# Python packaging
wheel:
	python setup.py bdist_wheel
upload:
	twine upload dist/*.whl


# Git hooks, vim tags and cleanup
hooks:
	ln -snf ../../hooks/pre-commit .git/hooks
	ln -snf ../../hooks/commit-msg .git/hooks
tags:
	find did -name '*.py' | xargs ctags --python-kinds=-i
clean:
	rm -rf $(TMP) build dist did.egg-info
	find . -type f -name "*.py[co]" -delete
	find . -type f -name "*,cover" -delete
	find . -type d -name "__pycache__" -delete
	cd docs && make clean
	rm -f .coverage tags


# Docker
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
