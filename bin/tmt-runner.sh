#!/bin/bash
# run.sh [-d] /path/to/workdir TYPE
#
#   TYPE of exectution:
#       shell | beakerlib
#
#   Supports __only__ one workdir to run in,
#       and only one TYPE to run the tests
#
#   Outputs results into folder specified by test name.
#       Resulting files:
#               stderr.log
#               stdout.log
#               exitcode.log
#
#   Options:
#       -d    DEBUG output
#
#

set -e
set -o pipefail

bash -n "$0"

tmt_WD=
tmt_VERBOSE=
tmt_TYPE='shell'

tmt_TESTS_D='discover'
tmt_TESTS_F="${tmt_TESTS_D}/tests.yaml"

tmt_LOG_D='execute'
tmt_LOGOUT_F="stdout.log"
tmt_LOGERR_F="stderr.log"
tmt_LOGCODE_F="exitcode.log"

set -x

# TESTS_F file is on stdin
# TYPE is ARG
tmt_main () {
    local name=''
    local test=''
    local path=''
    local duration=''
    local environment=''

    local last=''

    local IFS_b="$IFS"
    IFS=''
    while read -r line; do
        local key="$(cut -d':' -f1 <<< "$line" | tmt_trim)"
        local val="$(cut -d':' -f2- <<< "$line" | tmt_trim)"

        grep -q "^\s" <<< "${line}" && {
            tmt_verbose 1 "$line"

            m=
            [[ "$key" == 'test' ]] && { m=y; test="${val}"; }
            [[ "$key" == 'path' ]] && { m=y; path="${val}"; }
            [[ "$key" == 'duration' ]] && { m=y; duration="${val}"; }
            [[ "$key" == 'environment' ]] && { m=y; environment="${val}"; }

            [[ -n "$m" ]] || tmt_error "Unknown test variable: $line"
            :
        } || {
            [[ "$name" == "$last" ]] || {
                runtest "$name" "$test" "$path" "$duration" "$environment"
                last="$name"
            }

            tmt_verbose 1 "$line"

            name="$key"
            test=''
            path=''
            duration=''
            environment=''
        }
    done

    [[ "$name" == "$last" ]] \
        || runtest "$name" "$test" "$path" "$duration" "$environment"

    local IFS="$IFS_b"
    echo
}

runtest () {
    local name="$1"
    local test="$2"
    local path="$3"
    local duration="$4"
    local environment="$5"

    tmt_verbose 2 "runtest $name $test $path $duration $environment"

    [[ -n "$name" ]] || {
        tmt_error "Invalid test name: '$name'"
        return 1
    }
    [[ -z "$path" ]] || {
        path="$(readlink -f "$tmt_TESTS_D/$path")"
        [[ -d "$path" ]] || {
            tmt_error "[${name}]" "Could not find test dir: '$path'"
            return 2
        }
        path="cd '$path' && "
    }
    [[ -z "$environment" ]] || environment="env -i $environment "
    [[ -z "$duration" ]] || duration="timeout '$duration' "

    local log_dir="${tmt_LOG_D}/$name"
    mkdir -p "$log_dir" || {
        tmt_error "[${name}]" "Could not create log dir: '$log_dir'"
        return 3
    }
    cd "$log_dir" || {
        tmt_error "[${name}]" "Could not cd: '$log_dir'"
        return 4
    }
    touch "$tmt_LOGOUT_F" "$tmt_LOGERR_F" "$tmt_LOGCODE_F" || {
        tmt_error "[${name}]" "Could touch log files in '$log_dir'"
        return 5
    }

    local cmd="${path}${environment}${duration}${test}"
    tmt_verbose 2 "$cmd" "1>$tmt_LOGOUT_F" "2>$tmt_LOGERR_F" "$?>$tmt_LOGCODE_F"

    bash -c "$cmd" 1>"$tmt_LOGOUT_F" 2>"$tmt_LOGERR_F"
    echo "$?" >"$tmt_LOGCODE_F"

    [[ -z "$tmt_VERBOSE" ]] && {
      grep -q '^0$' "$tmt_LOGCODE_F" \
          && echo -n "." \
          || echo -n "F"
      :
    } || {
        {
            tmt_verbose 2 "$tmt_LOGOUT_F:"
            cat "$tmt_LOGOUT_F"

            tmt_verbose 2 "$tmt_LOGERR_F:"
            cat "$tmt_LOGERR_F"

            tmt_verbose 2 "$tmt_LOGCODE_F:"
            cat "$tmt_LOGCODE_F"

        } >&2
    }

    return 0
}

# Helpers
tmt_abort () {
    echo "Failure:" "$@" >&2
    exit 1
}

tmt_error () {
    echo "Error:" "$@" >&2
}

tmt_beakerlib () {
    tmt_abort "NYI: beakerlib tests run"
}

tmt_trim () {
    sed -e 's/ *$//g' \
        -e 's/^ *//g'
}

tmt_verbose () {
    [[ -z "$tmt_VERBOSE" ]] || {
        local i="$1"
        local p=
        shift

        while [[ $i -gt 0 ]]; do
            p="${p} >"
            let "i=$i-1"
        done

        echo "$p" "$@" >&2
    }
}

{ set +xe; } &>/dev/null

### INIT checks
[[ 'WORKS' == "$(tmt_trim <<< "    WORKS    ")" ]] || die 'tmt_trim does not work'
[[ 'key'   == "$(cut -d':' -f1 <<< "key:value")" ]] || die 'lcut does not work'
[[ 'value' == "$(cut -d':' -f2- <<< "key:value")" ]] || die 'rcut does not work'

### RUN
[[ "$1" == "-d" || "$1" == '--debug' ]] \
    && { shift; set -x; } ||:

[[ "$1" == "-v" || "$1" == '--verbose' ]] \
    && { shift; tmt_VERBOSE=y; } ||:

[[ -n "$1" ]] || tmt_abort "path to workdir is missing"
tmt_WD="$(readlink -f "$1")"
[[ -d "$tmt_WD" ]] || tmt_abort "Could not find Workdir: $tmt_WD"
shift

[[ -z "$1" ]] || {
    [[ "$1" == 'beakerlib' || "$1" == 'shell' ]] \
        || tmt_abort "Unknown tests execution TYPE: '$1'"

    tmt_TYPE="$1"
}
shift

cd "$tmt_WD" || tmt_ abort "Failed to cd: $tmt_WD"
[[ -r "$tmt_TESTS_F" ]] || tmt_abort "Could not find TESTS file: $tmt_TESTS_F"

tmt_TESTS_D="$(readlink -f "${tmt_WD}/${tmt_TESTS_D}")"
[[ -d "$tmt_TESTS_D" ]] || tmt_abort "Could not find Discover dir: $tmt_TESTS_D"

tmt_LOG_D="$(readlink -f "${tmt_WD}/${tmt_LOG_D}")"
[[ -d "$tmt_LOG_D" ]] || tmt_abort "Could not find Execute dir: $tmt_LOG_D"

tmt_verbose 0 "$tmt_WD $ main $tmt_TYPE < $tmt_TESTS_F"

tmt_main < <( grep -vE '^\s*$' "$tmt_TESTS_F" )
