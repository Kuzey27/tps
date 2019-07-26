#!/bin/bash

set -euo pipefail

source "${INTERNALS}/util.sh"
source "${INTERNALS}/problem_util.sh"


function usage {
	errcho "Usage: <invoke> [options] <solution-path>"
	errcho "Options:"

	errcho -e "  -h, --help"

	errcho -e "  -s, --sensitive"
	errcho -e "\tTerminates on the first error."

	errcho -e "  -r, --show-reason"
	errcho -e "\tDisplays the reason for not being accepted, e.g. checker output"

	errcho -e "  -t, --test=<test-name-pattern>"
	errcho -e "\tInvokes only tests matching the given pattern. Examples: 1-01, '1-*', '1-0?'"
	errcho -e "\tNote: Use quotation marks when using wildcards in the pattern to prevent bash expansion."

	errcho -e "      --tests-dir=<tests-directory-path>"
	errcho -e "\tOverrides the location of the tests directory"

	errcho -e "      --no-check"

	errcho -e "      --no-sol-compile"

	errcho -e "      --no-tle"

	errcho -e "      --time-limit=<time-limit>"
	errcho -e "\tGiven in seconds, e.g. --time-limit=1.2 means 1.2 seconds"

	errcho -e "      --hard-time-limit=<hard-time-limit>"
	errcho -e "\tSolution code will be killed after <hard-time-limit> seconds,"
	errcho -e "\t\tdefaults to <time-limit> + 2"
}


tests_dir="${TESTS_DIR}"
SHOW_REASON="false"
SENSITIVE_RUN="false"
SPECIFIC_TESTS="false"
SPECIFIED_TESTS_PATTERN=""
SKIP_CHECK="false"
skip_compile_sol="false"


function handle_option {
    shifts=0
    case "${curr}" in
        -h|--help)
            usage
            exit 0
            ;;
        -s|--sensitive)
            SENSITIVE_RUN="true"
            ;;
        -r|--show-reason)
            SHOW_REASON="true"
            ;;
        -t|--test=*)
            fetch_arg_value "SPECIFIED_TESTS_PATTERN" "-t" "--test" "test name"
            SPECIFIC_TESTS="true"
            ;;
        --tests-dir=*)
            fetch_arg_value "tests_dir" "-@" "--tests-dir" "tests directory path"
            ;;
        --no-check)
            SKIP_CHECK="true"
            ;;
        --no-sol-compile)
            skip_compile_sol="true"
            ;;
        --no-tle)
            SOFT_TL=$((24*60*60))
            ;;
        --time-limit=*)
            fetch_arg_value "SOFT_TL" "-@" "--time-limit" "soft time limit"
            ;;
        --hard-time-limit=*)
            fetch_arg_value "HARD_TL" "-@" "--hard-time-limit" "hard time limit"
            ;;
        *)
            invalid_arg "undefined option"
            ;;
    esac
}

function handle_positional_arg {
    if variable_not_exists "solution" ; then
        solution="${curr}"
        return
    fi
    invalid_arg "meaningless argument"
}

argument_parser "handle_positional_arg" "handle_option" "$@"

if variable_not_exists "solution" ; then
    errcho "Solution is not specified."
    usage
    exit 2
fi

if ! python -c "import psutil" >/dev/null 2>/dev/null; then
    errcho "Error: Package 'psutil' is not installed. You can install it using:"
    errcho "pip install psutil"
    exit 1
fi

if variable_not_exists "SOFT_TL" ; then
    SOFT_TL="$(get_time_limit)"
fi

if ! check_float "${SOFT_TL}"; then
    errcho "Provided time limit '${SOFT_TL}' is not a positive real number"
    usage
    exit 2
fi

if variable_not_exists "HARD_TL" ; then
    HARD_TL="$(python -c "print(${SOFT_TL} + 2)")"
fi

if ! check_float "${HARD_TL}"; then
    errcho "Provided hard time limit '${HARD_TL}' is not a positive real number"
    usage
    exit 2
fi

gen_summary_file="${tests_dir}/${GEN_SUMMARY_FILE_NAME}"

sensitive check_file_exists "Solution file" "${solution}"
sensitive check_directory_exists "Tests directory" "${tests_dir}"
sensitive check_file_exists "Test generation summary file" "${gen_summary_file}" "Tests are not correctly generated.\n"

export SHOW_REASON SENSITIVE_RUN SPECIFIC_TESTS SPECIFIED_TESTS_PATTERN SKIP_CHECK SOFT_TL HARD_TL


recreate_dir "${LOGS_DIR}"

export STATUS_PAD=20

printf "%-${STATUS_PAD}scompile" "solution"
if "${skip_compile_sol}"; then
    echo_status "SKIP"
else
    sensitive reporting_guard "solution.compile" bash "${SCRIPTS}/compile.sh" "${solution}"
fi
echo

printf "%-${STATUS_PAD}scompile" "checker"
if "${SKIP_CHECK}"; then
    echo_status "SKIP"
else
    sensitive reporting_guard "checker.compile" make -C "${CHECKER_DIR}"
fi
echo

ret=0
python "${INTERNALS}/invoke.py" "${tests_dir}" "${gen_summary_file}" || ret=$?


echo

if [ ${ret} -eq 0 ]; then
    cecho green "Finished."
else
    cecho red "Terminated."
fi

exit ${ret}
