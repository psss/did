#!/bin/bash

# Because of shell's notion of `0` being a success, `test -t $fd` exit code
# of `1` means *false*, i.e. `nope, not a TTY`. Therefore adding `!` to negate
# the exit code, to 1. present more expected `0` as "not a tty" in output, and
# 2. use this negation in the `&&` sequence, to validate all interesting channels.

set +x

! test -t 0; echo "$STEP: stdin: $?";
! test -t 1; echo "$STEP: stdout: $?";
! test -t 2; echo "$STEP: stderr: $?";

(! test -t 0) && (! test -t 1) && (! test -t 2)
