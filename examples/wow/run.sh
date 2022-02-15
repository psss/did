#!/bin/bash
# Example workflow-tomorrow command lines

# Git url, git ref and root path
url='https://github.com/teemtee/tmt'
ref='main'
path='/examples/wow'

# The mini test
wow fedora-32 x86_64 --whiteboard 'tmt mini test' \
    --fmf --fmf-id "{url: '$url', ref: '$ref', path: '$path', name: '/mini'}"

# The full test
wow fedora-32 x86_64 --whiteboard 'tmt full test' --host-filter HVM \
    --fmf --fmf-id "{url: '$url', ref: '$ref', path: '$path', name: '/full'}"
