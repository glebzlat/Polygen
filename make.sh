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
  exit $?
}

function run_generate {
  if [ "$1" = "polygen" ];
  then
    python -m polygen generate grammar/parser.peg -b python -o polygen
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
