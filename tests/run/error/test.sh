#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "run=\$(mktemp -d)" 0 "Creating run directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    # 2 ... Errors occured during test execution.
    ECODE=2

    rlPhaseStartTest "Truncated"
        for v in '' '-v'; do
          rlRun -s "tmt run --id $run --scratch --all \
            provision $v --how local \
            execute --how tmt --script true \
            prepare --how shell --script 'for i in {001..101}; do echo OUT-\$i; done; false'" "$ECODE"

          # Prepare is never in verbose mode
          rlAssertNotGrep 'OUT-001' $rlRun_LOG -F
          rlAssertGrep 'stdout (100/101 lines)' $rlRun_LOG -F
        done
    rlPhaseEnd

    rlPhaseStartTest "Not Truncated"
        # Whole run is in verbose mode
        rlRun -s "tmt run -v --id $run --scratch --all \
          provision $v --how local \
          execute --how tmt --script true \
          prepare --how shell --script 'for i in {001..101}; do echo OUT-\$i; done; false'" "$ECODE"

        rlAssertGrep 'stdout (101 lines)' $rlRun_LOG -F
        rlAssertGrep 'OUT-001' $rlRun_LOG -F

        # Prepare is in verbose mode
        rlRun -s "tmt run --id $run --scratch --all \
          provision --how local \
          execute --how tmt --script true \
          prepare -v --how shell --script 'for i in {001..101}; do echo OUT-\$i; done; false'" "$ECODE"

        rlAssertGrep 'stdout (101 lines)' $rlRun_LOG -F
        rlAssertGrep 'OUT-001' $rlRun_LOG -F
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
        rlRun "rm -r $run" 0 "Removing run directory"
    rlPhaseEnd
rlJournalEnd
