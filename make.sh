#!/bin/sh

USAGE=$(cat << END
make.sh [-h | --help] command [args...]
commands:
  tests        run tests; args will be propagated to unittest discover
  generate [polygen | *]
               generate parser;
               if "polygen" arg is passed, then regenerates polygen parser
               otherwise args are propagated to the polygen
options:
  -h | --help  print help message and exit
END

)

function usage {
  echo "$USAGE"
}

function run_tests {
  python -m unittest discover "$@" tests
  local exitcode=$1
  if [[ $exitcode -ne 0 ]]; then
    exit $exitcode
  fi
#   python tests/test_equivalency.py
  exit $?
}

function run_generate {
  if [ "$1" = "polygen" ];
  then
    shift
    python -m polygen generate polygen/grammar.peg -b python -o polygen \
      -d polygen_imports=true $@
    exit $?
  fi

  python -m polygen generate $@
  exit $?
}

while [[ $# -gt 0 ]]; do
  case $1 in
    tests)
      shift
      run_tests $@
      ;;
    generate)
      shift
      run_generate $@
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*|--*)
      echo "Unknown option $1"
      exit 1
      ;;
    *)
      echo "Unknown command $1"
      exit 1
      ;;
  esac
done

usage
