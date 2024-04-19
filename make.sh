#!/bin/sh

USAGE=$(cat << END
make.sh [-h | --help] command [args...]
command:
  tests        run tests; args will be propagated to unittest discover
options:
  -h | --help  print help message and exit
END

)

function usage {
  echo "$USAGE"
}

function run_tests {
  python -m unittest discover "$@" tests
}

while [[ $# -gt 0 ]]; do
  case $1 in
    tests)
      shift
      run_tests $@
      exit 0
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
