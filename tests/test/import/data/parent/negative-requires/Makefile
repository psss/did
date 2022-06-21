export TEST=/negative_reqs
export TESTVERSION=1.0

FILES=$(METADATA) Makefile

.PHONY: all install download clean

run: $(FILES)
	Makefile

clean:
	rm -f *~

include /usr/share/rhts/lib/rhts-make.include

$(METADATA): Makefile
	@echo "Owner:           Name <nobody@localhost.localdomain>" > $(METADATA)
	@echo "Name:            $(TEST)" >> $(METADATA)
	@echo "TestVersion:     $(TESTVERSION)" >> $(METADATA)
	@echo "Path:            $(TEST_DIR)" >> $(METADATA)
	@echo "Requires:        -fmf" >> $(METADATA)
	@echo "Description:     Negative requires" >> $(METADATA)
	@echo "License:         MIT" >> $(METADATA)
	@echo "TestTime:        5m" >> $(METADATA)

	rhts-lint $(METADATA)
