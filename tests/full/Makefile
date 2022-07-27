# Run local changes in tests/full
# We need to escape fmf root placed in tests/full
# so current repo is put to tar into directory which is copied
# to the VM
test: bundle
	tmt run -vvv -e COPY_IN=1
bundle: clean
	tar czf ./repo_copy.tgz --exclude repo_copy.tgz -C $(shell git rev-parse --show-toplevel) .
clean:
	test -e ./repo_copy.tgz && rm -f ./repo_copy.tgz || true
