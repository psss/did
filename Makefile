
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

# Looking for HTML docs? Could copy them too or just check out http://status-report.readthedocs.org/
# To build locally; cd docs; make html
#rst2man README | gzip > $(DOCS)/status-report.1.gz
#rst2html README $(CSS) > $(DOCS)/index.html
#rst2man $(DOCS)/notes.rst | gzip > $(DOCS)/status-report-notes.1.gz
#rst2html $(DOCS)/notes.rst $(CSS) > $(DOCS)/notes.html

build:
	mkdir -p $(TMP)/{SOURCES,$(PACKAGE)}
	cp -a $(FILES) $(TMP)/$(PACKAGE)
	cd docs && make man SPHINXOPTS=-Q && gzip -c _build/man/status-report.1 > $(DOCS)/status-report.1.gz

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
