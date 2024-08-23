# Polygen

**P**olyglot parser **G**enerator - a tool for generating parsers in any
language.

## Main concepts

Polygen consists of three main logical modules:
1. Parser. Uses reader to read grammar from the file and convert it to
    grammar data structure.
2. Tree modifier. Takes raw grammar tree and traverses it, applying rewriting
    rules and performing checks.
3. Code generator. Takes ready-to-use grammar, translates it to code and
    uses preprocessor to insert the code into a skeleton file.

The grammar Polygen recognizes is an extended version of the original
PEG, designed by Bryan Ford[^peg-bf]

### Code generation

Code generator is a protocol, implemented by backends. Each backend generates
code in its language. Prior to code generation it is needed to find a backend,
source and setup it.

Backends must generate the equivalent parsers, which means that any parser,
created from the same grammar, accepts and rejects the same sets of strings.
In order to do this, resulting parsers are tested on the same data.

In order to treat all parsers in one way, no matter how their source language
is compiled or interpreted, there is a need for an abstraction level. Calling
code should not know, how to compile and execute a parser - all it should know
is that the parser takes the grammar and returns the result.

### Runner interface

I call this abstraction level a Runner. Each backend implements a Runner
interface, which encapsulates the details about how to compile or interpret
the source code of the parser, where to save an executable and how to execute
it.

Resulting parsers must implement the same input-output data format. Parser
takes a filename in command line arguments and prints the result to the
standard output. If an input data is successfully parsed, the exit code must
be 0. If an error occured, the exit code must be not 0, and the error message
should be printed. Errors must be printed to stdout.

### Grammar

Due to the multiple target language support there is a need to separate
the grammar rules and the implementation of semantic actions. In order to do
this, the grammar has a concept of metarule declaration and definition.

Consider the following grammar that parses integer numbers.

```
@entry
Grammar <- Integer Spacing EOF
Integer <- Digit+              $int_action
Digit   <- [0-9]
Spacing <- [ \n\r\t]*
EOF     <- !.

$int_action {
    return int(''.join(digit))
}
```

Here the `$int_action` after the `Integer` rule is a declaration, and
the same name with the curly braces after it is a definition. This approach
will be more powerful with the include mechanism: write the grammar into
a grammar file, put definitions into definitions file and include the latter
into the grammar file.

## Todo

- [x] Bootstrap a parser
- [x] Write unit tests
- [ ] Test Polygen with older Python versions
- [x] Left recursion support[^lr-jrdouglass1]
    - [x] direct
    - [x] indirect
    - [x] diverging
    - [x] merging
    - [x] mutual
    - [x] nested
- [ ] Cut operator[^cuts1]
- [ ] Add backend for another language
    - [x] Write backend runner module
    - [ ] Approve an API for backends
    - [x] Write cross-backend unit tests
- [x] Grammar file preprocessor
    - [x] `include` directive
    - [x] queries - rules, metarules and directives added to the grammar
          only if the query condition satisfied
    - [x] `@toplevel` query - satisfied only if the file is parsed first
    - [x] `@backend` query - satisfied only if the backend with the specific
          name chosen
- [ ] Source code preprocessor definitions from grammar file (e.g. imports)
- [ ] Enhanced skeleton file preprocessor
    - [ ] Allow consequtive directives
    - [ ] Directive default value
- [ ] Parser error handling mechanism
- [ ] Documentation
    - [ ] Language reference
    - [ ] Backends documentation and API
    - [ ] Developer's documentation (the core)
    - [ ] Examples

## Known bugs

- Grammar processor queries can not be nested.

## License

Licensed under [MIT License](./LICENSE).

## References

[^peg-bf]: Parsing Expression Grammars: A Recognition-Based Syntastic
Foundation. Bryan Ford

[^lr-jrdouglass1]: Improved Packrat Parser Left Recursion Support.
J. R. Douglass

[^cuts1]: Packrat Parsers Can Handle Practical Grammars in Mostly Constant
Space. Kota Mizushima, Atusi Maeda, Yoshinori Yamaguchi
