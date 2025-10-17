#!/bin/bash
# shellcheck source=/dev/null
. /usr/share/beakerlib/beakerlib.sh || exit 1

mkdir ~/.did
cat > ~/.did/config <<EOF
[general]
email = Name Surname <email@example.org>
EOF

rlJournalStart
    rlPhaseStartTest
        rlRun "did --test last quarter"
    rlPhaseEnd
rlJournalEnd
