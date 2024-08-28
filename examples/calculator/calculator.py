import math

from argparse import ArgumentParser
from traceback import format_exception_only

from parser import Reader, Parser


WELCOME_MSG = """
interactive calculator
type .help to get help, .quit to quit
"""

HELP_MSG = """
interactive calculator -- help
operations:
  a + b
  a - b
  a ** b
  a * b
  a / b
functions:
  sqrt(x)   -- square root of x
  mod(a, b) -- a % b
commands:
  .help -- print this message
  .quit -- quit the calculator
"""

FUNCTIONS = {
    "sqrt": ((lambda x: math.sqrt(x)), 1),
    "mod": ((lambda a, b: a % b), 2)
}

VARIABLES = {
    "pi": math.pi
}


class CalculatorError(Exception):
    pass


class CalculatorState:

    def __init__(self, verbose: bool):
        self.verbose = verbose
        self.quit = False

    def help(self):
        print(HELP_MSG.strip())

    def print_result(self, result):
        print(f"= {result}")

    def function(self, name: str, *args: int | float):
        if self.verbose:
            args_str = ', '.join(str(i) for i in args)
            print(f"  (verbose) function: {name}, args: {args_str}")

        fn_info = FUNCTIONS.get(name)
        if not fn_info:
            raise CalculatorError(f"no such function: {name}")

        fn, args_count = fn_info
        if len(args) != args_count:
            raise CalculatorError(
                f"wrong number of arguments for function {name}: "
                f"expected {args_count}, got {len(args)}"
            )

        return fn(*args)

    def variable(self, name: str):
        if self.verbose:
            print(f"  (verbose) variable: {name}")

        var = VARIABLES.get(name)
        if not var:
            raise CalculatorError(f"no such variable: {name}")
        return var


def parse(parser, input):
    try:
        parser.parse(input)
    except SyntaxError as e:
        print(''.join(format_exception_only(SyntaxError, e)))
    except CalculatorError as e:
        print(e)
    except ZeroDivisionError:
        print("attempt to divide by zero")
    except KeyboardInterrupt:
        print()


def main():
    argparser = ArgumentParser()
    argparser.add_argument("file", nargs='?')
    argparser.add_argument("--verbose", "-v", action="store_true")
    ns = argparser.parse_args()

    reader = Reader(None)
    state = CalculatorState(ns.verbose)
    parser = Parser(reader, state)

    if ns.file:
        with open(ns.file, 'r', encoding="UTF-8") as fin:
            parse(parser, fin)
        return

    print(WELCOME_MSG.strip())

    while not state.quit:
        try:
            string = input('> ')
            parse(parser, string)
        except EOFError:
            print()
            break


if __name__ == "__main__":
    exit(main())
