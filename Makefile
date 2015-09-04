
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
FILES = LICENSE README.rst \
		Makefile status-report.spec \
		docs examples source

ifndef USERNAME
    USERNAME = echo $$USER
endif

all: push clean

build:
	mkdir -p $(TMP)/{SOURCES,$(PACKAGE)}
	cp -a $(FILES) $(TMP)/$(PACKAGE)
	# Construct man page from header and README
	cp docs/header.txt $(TMP)/man.rst
	tail -n+7 README.rst | sed '/^Status/,$$d' >> $(TMP)/man.rst
	rst2man $(TMP)/man.rst | gzip > $(DOCS)/status-report.1.gz
	rst2html README.rst $(CSS) > $(DOCS)/index.html

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

run_docker: build_docker
	@echo
	@echo "Please note: this is a first cut at doing a container version as a result; known issues:"
	@echo "* kerberos auth may not be working correctly"
	@echo "* container runs as privileged to access the conf file"
	@echo "* output directory may not be quite right"
	@echo
	@echo "This does not actually run the docker image as it makes more sense to run it directly. Use:"
	@echo "docker run --privileged --rm -it -v $(HOME)/.status-report:/status-report.conf $(USERNAME)/status-report"
	@echo "If you want to add it to your .bashrc use this:"
	@echo "alias status-report=\"docker run --privileged --rm -it -v $(HOME)/.status-report:/status-report.conf $(USERNAME)/status-report\""

build_docker: docker/Dockerfile
	docker build -t $(USERNAME)/status-report --file="docker/Dockerfile" .
