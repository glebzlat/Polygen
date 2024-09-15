# Polygen

**Poly**glot parser **Gen**erator - a tool for generating parsers in any
language.

## Table of Contents

- [Goals](#goals)
- [Installation](#installation)
- [Usage](#usage)
- [Language reference](#language-reference)
    - [Grammar](#grammar)
    - [Rules](#rules)
    - [Expressions](#expressions)
    - [String literals](#string-literals)
    - [Metavariables and metarules](#metavariables-and-metarules)
    - [Directives](#directives)
- [Main concepts](#main-concepts)
    - [Parser](#parser)
    - [Preprocessor](#preprocessor)
    - [Code generator](#code-generator)
    - [Grammar](#grammar-1)
    - [Parser equivalency](#parser-equivalency)
- [Todo](#todo)
- [Known bugs](#known-bugs)
- [License](#license)
- [References](#references)

## Goals

- The main goal of this project is to create a Packrat parser generator tool,
  which will be able to generate parsers in any language, removing the need of
  bunches of different generator tools that target only one or two languages and
  define its own syntax each.

- Comply with the original PEG grammar syntax[^peg-bf] as much as possible,
  only adding new features, not removing or changing.

- Implement the best possible left recursion algorithm[^lr][^lr-jrdouglass1].

- Implement cuts[^cuts1] to reduce parser space consumption and to provide an
  advanced error reporting mechanism.

## Installation

At this point Polygen is not published at [pypi.org](pypi.org), the only way
to install it is from this repository.

Run:

```sh
pip install git+https://github.com/glebzlat/Polygen

# or
git clone https://github.com/glebzlat/Polygen
pip install polygen
```

## Usage

To generate a parser from the grammar:

```sh
python -m polygen generate <grammar-file> -b <backend-name> -o <output-directory>
```

If generation process went successfully, then a file `parser.py` is created in
the output directory. You can run it passing an input file, in which case the
parser will parse the data in this file and output either the result or an
error. If input file is not specified, parser reads data from standard input.

```sh
python parser.py [input-file]
```

The only supported target language for now is Python: `-b python`.

To test the backend for parser equivalency, run:

```sh
python -m polygen test -b <backend-name>
```

## Language reference

### Grammar

Grammar is a sequence of rules, metarules, and directives.

### Rules

Rules has the following syntax:

```
Identifier <- Expression
```

`Identifier` consists of alphanumeric ASCII characters and an underscore
and cannot start with a digit. All subsequent occurencies of `Identifier` will
refer to this definition, unless otherwise stated.

`Expression` consists of zero or more alternatives, separated by a forward
slash `/`. Complies with the standard PEG definition of expressions[^peg-bf].

Rule can be marked as the start rule or as an ignore rule:

```
@entry
Identifier <- Expression

@ignore
Identifier <- Expression
```

Rule alternative consists of patterns, quantifiers, predicates, metavariables
and metarules, which are described below.

### Expressions

- `.`

    **Dot**. Matches any single character.

- `""` and `''`

    **String literal**. Characters enclosed in double or single quotes match
    exactly themselves.

- `[]`

    **Character class**. Matches any containing single character. E.g. `[a-z]`
    matches any lowercase ASCII letter, `[abc]` matches either 'a', 'b', or 'c',
    `[a-z0]` matches any lowercase ASCII letter or '0'.

- `?`

    **Optional (zero or more)**. Tries to consume preceding pattern and
    unconditionally succeeds.

- `*`

    **Zero-or-more**. Tries to consume as many matches as possible and
    unconditionally succeeds.

- `+`

    **One-or-more**. Consumes one or more matches of the preceding pattern and
    succeeds only if at least match occured.

- `{}`

    **Range**. Attempts to match the preceding pattern exact number of times.
    E.g. `e{2}` tries to match the pattern `e` exactly 2 times, `e{2,4}` tries
    to match the pattern between 2 and 4 times inclusively.

- `&`

    **And predicate**. Attempts to match the following pattern without
    advancing the pointer, preserving only the knowledge whether the pattern
    succeeded or failed. Succeeds if pattern succeeded.

- `!`

    **Not predicate**. Acts the same as And predicate except that succeeds only
    if the following pattern failed.


### String literals

String literal can contain either ASCII characters or special escape characters,
which can be:

- `\r` - carriage return
- `\n` - newline
- `\t` - tab
- Octal escape sequence: `\ab` or `\abc` where `a`, `b` and `c` are octal
  digits, and `a` can be maximum of 2.
- Unicode escape sequence: `\uHHHH`, where `H` is a hexadecimal digit.

### Metavariables and metarules

Metanames can be assigned to the expression parts to reference them in the
metarules. Metavariable has the syntax `Identifier:Identifier`.

Metarule has the following syntax:

```
# inline metarule
Rule <- Alternative ${ ... }

# declaration
Rule <- Alternative $metarule

# definition
$metarule {
  ...
}
```

Metarules are assigned to alternatives, not whole rules. That is, different
alternatives of the same rule can be handled by different metarules. Also, the
same metarule can be assigned to several alternatives:

```
Rule <- Alt1 $metarule_1
      / Alt2 $metarule_2
      / Alt3 $metarule_2
```

Metarule name format is the same as `Identifier`.

### Directives

Directives augment the grammar definition with meta information, which is used
to configure a code generator, include subgrammars and configure the grammar
itself.

- `@include <file>`

    Causes Polygen to search for the file `<file>` and merge the grammar from
    this file to the grammar from the source file. `<file>` is a sequence of
    characters, enclosed either in single or double quotes.

- `@entry Identifier`
    
    Marks the rule as an entry. This form is different from the first `@entry`
    form described above. This form requires only the rule name and is separate
    from the rule definition.

- `@ignore { Rules }`
    
    Marks `Rules` as ignored. `Rules` is a sequence of `Identifier`, separated
    by whitespace.

- `@backend(Name) { SubGrammar }`

    Includes `SubGrammar` into the file grammar, if backend's name is equal to
    `Name`. Backend names are of the same format as `Identifier`.

- `@toplevel { SubGrammar }`

    Includes `SubGrammar` into the file grammar, if the file processed first.

- `@backend.<directive> { ... }`
    
    Defines a directive for the postprocessor. String, enclosed in curly
    brackets, passed to postprocessor without change.

    Currently implemented custom postprocessor directives are:

    - `@backend.header`
    - `@backend.state_type`

    Postprocessor directives are described in more detail in Main concepts.

## Main concepts

Polygen grammar is a modified version of the original PEG, designed by Bryan
Ford[^peg-bf], with some extensions such as directives, semantic action
definitions, metavariables, and unicode escape characters.

Polygen consists of five main logical parts:
1. Parser. Reads the raw grammar representation and converts into the Grammar
   data structure.
2. Preprocessor. Handles directives in the grammar. Uses parser to assembly
   included grammars and queries into one tree.
3. Tree rewriter (modifier). Modifies Grammar structure, checks for semantic
   errors.
4. Code generator. Takes ready-to-use grammar and translates it into the a
   code. Invokes the postprocessor to insert the code into the parser skeleton.
5. Postprocessor. Reads the directives in the skeleton files and replaces
   found directives by their content, provided by the generator.

Preprocessor directives carries meta-information about the grammar. Directives
define which rule is the start rule of the grammar, conditionally include
grammar rules, metarules and other directives, and includes grammar files.
Also preprocessor allows to pass code generator directives.

### Parser

At this point parser is bootstrapped by the Polygen itself.

### Preprocessor

Preprocessor currently supports the following directives:
- `@include <path>`: includes the grammar, parsed from the `<path>`, into
  the grammar in this file. `<path>` is a sequence of characters, enclosed
  in single or double quotes.
- `@entry <rule>`: marks the rule `<rule>` as a start.
- `@ignore { <rules> }`: marks `<rules>` as unused. Unused rules have no
  metavariables and their corresponding tokens are excluded from the result.
- `@backend(<name>) { <grammar> }`: backend query. If the backend name is the
  same as `<name>`, then `<grammar>` is included.
- `@toplevel { <grammar> }`: toplevel query. If the file is first in the
  files tree, then `<grammar>` is included.
- `@backend.header { <string> }`: backend header definition. `<string>` is
  passed to the code generator as is and inserted into the resulting parser
  file at the beginning.
- `@backend.state_type { <string> }`: backend state type definition. `<string>`
  passed to the code generator as is and used to annotate the type of user's
  custom state object, passed to the parser.

One thing to mention: two last directives has the common form:
`@backend.<directive> { <string> }`. If a `<directive>` is unknown to the
code generator, it is omitted without error and left unused.

### Code generator

Code generator implements a backend interface and is mentioned just as the
"backend" here, unless otherwise stated. Backend interface aims to separate the
grammar transformation logic and test execution from the target language
peculiarities.

Backend consists of two parts: code generator itself and the runner. While the
role of a code generator is already explained, the runner is a new subject.
Runner is used by the parser equivalency test, and encapsulates parser set up,
tear down and execution logic. Runner is responsible for the compilation or
translation of the parser source code into an executable file, invocation
of the executable file, and cleanup.

Each backend parser must implement the same interface: it takes the path to the
grammar and returns parse result in acceptable format. See
`polygen/equivalency` for the details.

### Grammar

Polygen aims to support multiple target languages, which makes impossible and
undesirable to integrate semantic actions into the grammar definition tightly.
Semantic actions' syntax has two variations: inline actions and
declaration-definition separated actions.

First variation allows to write action's code inplace, which is designed for
quick-and-dirty prototyping and should be avoided, as it hurts readability
of the grammar and makes actions hard-coded:

```
Integer <- Digit+ ${ return int(''.join(digit)) }
```

Second variation involves semantic action declaration and corresponding
definition. This approach allows to separate the grammar syntax declaration and
semantic implementation. It even allows to write implementations for several
target languages, e.g. by placing action definitions into separate files and
including the right file in the backend query.

```
Integer <- Digit+              $int_action

$int_action {
    return int(''.join(digit))
}
```

Full grammar code:

```
@entry
Number <- Integer Spacing EOF
Integer <- Digit+              $int_action
Digit   <- [0-9]
Spacing <- [ \n\r\t]*
EOF     <- !.

$int_action {
    return int(''.join(digit))
}
```

Notice that `@entry` directive used to mark `Number` rule as the start rule.
This is actually the second form of this directive. It is mixed with the
rule definition.

The first form of `@entry` directive is handy for separating the grammar into
independent modules. Suppose that you have the grammar that defines numbers,
and the grammar that defines a calculator. You want to test numbers separately.
In this case you can use a `@toplevel` directive:

```
@toplevel {
  @entry
  Number <- ...
}

# OR

@toplevel {
  @entry Number
}

Number <- ...
```

Then specify your number grammar file instead of calculator grammar. When
number grammar file is included into another grammar, `@toplevel` does nothing.
So this is valid to define a start rule in the calculator grammar:

```
@include "number.peg"

@entry
Calculator <- ...
```

Polygen allows only one entry point in the grammar.

Metavariables used to assign names to parts of an expression. This may not be
too useful in case of nonterminals, because Polygen derives the name of the
metavariable from the nonterminal name. You could mention it in the grammar
snippet.

For terminals this is a bit more complicated, though. Suppose the following
rule:

```
MyRule <- "some string" $my_action

$my_action {
  return ??.uppercase()
}
```

Suppose that you want to acquire the parsed string in `$my_action`. How could
you reference it? Well, Polygen assigns serial numbers to terminals, so in
this case you can reference it as `_1`. But it is not very convenient. Another
way to reference this terminal in the semantic action is to assign a metaname
to it:

```
MyRule <- string:"some string" $my_action

$my_action {
  return string.uppercase()
}
```

On another hand, there may be the case, when you do not want terminal to appear
in the result. Suppose the following rule:

```
TwoNumbers <- Number ', ' Number
```

This rule will return the following: `[<number>, ', ', <number>]`. The list
of a number, a string and an another number. To remove this unneeded string
between numbers, assign an underscore to it:

```
TwoNumbers <- Number _:', ' Number
```

Underscore metavariable causes an item to be ignored. The same effect can be achieved
using `@ignore` directive (can be applied to nonterminals):

```
TwoNumbers <- Number Sep Number

@ignore { Sep }

Sep <- ', '

# OR

@ignore
Sep <- ', '
```

Ignored items are not returned by the rule when the rule succeeds and can not
be referenced in metarules.

Predicates can not have metavariables:

```
Char <- !'\\' .

# the same:
Char <- _:!'\\' .

# wrong:
Char <- not_pred:!'\\' .
```

### Parser equivalency

Parsers in all target languages must be fully compatible in terms of the
grammars they accept and reject and their output format. Polygen implements
built-in equivalency test to ensure this, although there is only one language
implemented so far. See `polygen/equivalency` for details.

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
- [x] Parser error reporting
- [ ] Documentation
    - [ ] Language reference
    - [ ] Backends documentation and API
    - [ ] Developer's documentation (the core)
    - [ ] Examples

## Known bugs

- Modifier errors report token positions erroneously:
  ```
  polygen: Undefined rule grammar_action:
      @entry
      Grammar <- Spacing Entity+ EndOfFile grammar_action
                                                                    ^~~~~~~~~~~~~~
  ```
- `@ignore` directive does not affect nonterminals in subexpressions:
  ```
  FnBody     <- expr:Expression next:(COMMA Expression)*

  @ignore { COMMA }
  ```
- Make cut error message more informative. Currently if cut fails, it can
  produce a message like this:
  ```
  SyntaxError: expected Literal__GEN_1* at 19
  ```
  In order to make this message more convenient for the end user, polygen
  should traverse the tree and retrieve the first terminal of `Literal__GEN_1`.

## License

Licensed under [MIT License](./LICENSE).

## References

[^peg-bf]: Parsing Expression Grammars: A Recognition-Based Syntastic
Foundation. Bryan Ford

[^lr]: Packrat Parsers Can Support Left Recursion.
A. Warth, J. R. Douglass, T. Millstein

[^lr-jrdouglass1]: Improved Packrat Parser Left Recursion Support.
J. R. Douglass

[^cuts1]: Packrat Parsers Can Handle Practical Grammars in Mostly Constant
Space. Kota Mizushima, Atusi Maeda, Yoshinori Yamaguchi
