# Prepare variables
TMP = $(CURDIR)/tmp
VERSION = $(shell grep ^Version tmt.spec | sed 's/.* //')
PACKAGE = tmt-$(VERSION)
FILES = LICENSE README.rst \
		Makefile tmt.spec setup.py \
		examples tmt bin tests

# Define special targets
all: docs packages
.PHONY: docs

# Temporary directory, include .fmf to prevent exploring tests there
tmp:
	mkdir -p $(TMP)/.fmf


# Run the test suite, optionally with coverage
test: tmp
	python3 -m pytest tests
smoke: tmp
	python3 -m pytest tests/test_smoke.py
coverage: tmp
	coverage run --source=tmt,bin -m py.test tests
	coverage report
	coverage annotate


# Build documentation, prepare man page
docs: man
	cd docs && make html
man: source
	cp docs/header.txt $(TMP)/man.rst
	tail -n+7 README.rst >> $(TMP)/man.rst
	rst2man $(TMP)/man.rst > $(TMP)/$(PACKAGE)/tmt.1


# RPM packaging and Packit
source: clean tmp
	mkdir -p $(TMP)/SOURCES
	mkdir -p $(TMP)/$(PACKAGE)
	cp -a $(FILES) $(TMP)/$(PACKAGE)
	rm $(TMP)/$(PACKAGE)/tmt/steps/provision/{base,vagrant}.py
tarball: source man
	cd $(TMP) && tar cfz SOURCES/$(PACKAGE).tar.gz $(PACKAGE)
	@echo ./tmp/SOURCES/$(PACKAGE).tar.gz
version:
	@echo "$(VERSION)"
rpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bb tmt.spec
srpm: tarball
	rpmbuild --define '_topdir $(TMP)' -bs tmt.spec
packages: rpm srpm


# Python packaging
wheel:
	python setup.py bdist_wheel
	python3 setup.py bdist_wheel
upload:
	twine upload dist/*.whl


# Git vim tags and cleanup
tags:
	find tmt -name '*.py' | xargs ctags --python-kinds=-i
clean:
	rm -rf $(TMP) build dist .cache .pytest_cache
	rm -rf docs/_build docs/stories docs/spec
	find . -type f -name "*.py[co]" -delete
	find . -type f -name "*,cover" -delete
	find . -type d -name "__pycache__" -delete
	rm -f .coverage tags
	rm -f examples/convert/main.fmf
