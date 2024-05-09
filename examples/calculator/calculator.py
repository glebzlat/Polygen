from parser import Parser, CalculatorError


if __name__ == '__main__':
    from argparse import ArgumentParser, FileType
    import sys

    argparser = ArgumentParser()
    argparser.add_argument('input_file', nargs='?',
                           type=FileType('r', encoding='UTF-8'),
                           default=sys.stdin)

    ns = argparser.parse_args()

    constants = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "pi": 3.1415,
        "tau": 6.2831,
        "sq2": 1.1412,
        "euler": 2.7182
    }

    parser = Parser(ns.input_file, constants)

    try:
        result = parser.parse()
        print(f"Result: {result}")
    except CalculatorError as e:
        print(e)
        exit(1)

    exit(not result)  # Unix-style: 0 is success
