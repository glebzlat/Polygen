# Interactive calculator

## Commands

To regenerate the parser (assuming current working directory is calculator/):

```sh
python -m polygen generate grammar.peg -b python -o .
```

Run the calculator:

```sh
python calculator.py [file] [-v|--verbose]
```

If `file` argument is not given, then the interactive mode starts.
