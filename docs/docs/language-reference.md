# Polygen Language Reference

Polygen language is based on the original Bryan Ford's PEG definition and adds
convenient features like unicode characters, metarules, metanames, and
directives.

## Grammar

Polygen grammar consists of entities. Entity can be [a rule](#rule), [a
metarule](#metarules-and-metavariables), and [a directive](#directives). Rules
describe language's syntax, metarules define semantics, and directives allow
controlling the grammar processing.

Polygen is insensitive to whitespace characters (space `' '`, newline `'\n'`,
carriage return `'\r'`, and tab `'\t'`), thus whitespace is optional unless
otherwise stated.

## Rule

Rule is the main grammar entity. Its purpose is to define the syntax of the
language. Rule's syntax follows the original PEG definition and consists of the
rule name, a left arrow and the body (expression).

```text
Rule <- Identifier '<-' Expression
```

A demonstration of a rule:

```peg
Rule <- Expression
```

## Expression

Expression represents the sequence of ordered choices - alternatives.
Alternatives are tested in the order they appear in the sequence, and once the
alternative succeeds, the whole expression succeeds and does not test the
remaining alternatives.

Alternatives in the expression are separated by forward slash.

```text
Expression <- Alt 1 / Alt 2 / Alt N
```

## Alternative

Alternative is a sequence of parts tested in order they appear. Part is
tested when the previous part succeeded, and if the part failed, then the whole
alternative fails and remaining parts will not be tested.

Alternative can be followed by optional metarule:

```text
Alternative <- Part1 Part2 PartN MetaRuleDeclOrDef?
```

## Part

Parts consist of multiple components, most of which are optional. Optional
components are followed by the question mark.

```text
Part <- Cut? MetaName? Lookahead? Primary Quantifier?
```

Components explanation:

- [Cut](#cut)

    Cut is a special operator that instructs the parser to wipe the
    backtracking information.

- [MetaName](#metavariable)

    MetaName can be seen as a variable name. It allows referencing the value of
    the parsed token in a semantic action.

- [Lookahead](#lookahead)

    Lookahead is a special type of operator, which name is self-explanatory:
    it looks ahead and matches the token without consuming it.

- [Primary](#primary)

    This is the pattern that matches input string.

- [Quantifier](#quantifier)

    Quantifiers are another type of operator that allows specifying how many
    times the token must or may be repeated.

## Primary

Primary is a definition of a matching pattern or a reference to another rule.

Primary value types are:
- Identifier
- Expression in parentheses
- String literal
- Character class
- Wildcard (dot)

### Identifier

An Identifier is the name of a nonterminal. Rule names must follow the
Identifier format. An Identifier consists of ASCII letters, digits, and
underscore, and can not begin with the digit.

Subsequent identifiers must be separated by whitespace; otherwise, they will
be treated as a single identifier.

```peg
Identifier <- [a-zA-Z_] [a-zA-Z0-9_]*
```

An asterisk `*` means "repeated zero or more times".

### String literal

String literal is an arbitrary sequence of characters between single or
double quotes that matches exactly its content.

Allowed characters in a string literal are ASCII characters and escape
sequences, described below.

```peg
Char <- EscapeChar / .
```

Dot `.` is a wildcard that matches any single character.

Special characters are:

- `\n` newline
- `\r` carriage return
- `\t` tab
- `\'`, `\"` quote
- `\[`, `\]` square brackets
- `\\` backward slash
- `\nn` and `\nnn` octal character code
- `\uXXXX` UNICODE character

Escaped quote marks are used in case where the type of quote mark matches the
type of opening and closing marks: `'my message: \'hello\''`,
`"my message: \"hello\""`.

Octal character code digits are in the range from 0 to 7 inclusively, and the
first digit can be maximum of 2: `\60`, `\141`.

UNICODE characters are hexadecimal digits from 0 to 9 and from A to F.
Lowercase digits are allowed: `\u03c0`, `\u03C0`, `\u00b5`.

### Character class

Character class matches single character from a range. It can contain multiple
ranges. A range consists either of a single character or two characters
separated by a hyphen. In the latter case the range matches the starting
character, the ending character, and all characters located lexicographically
in between. The starting character must come first and must be less or equal
than the ending character.

```peg
Class <- '[' CharRange* ']'
CharRange <- Char / Char '-' Char
```

Escape sequences are allowed in character class

Note: closing square brackets inside the class must be escaped: `[\]]`.

### Wildcard (dot)

Wildcard `.` matches any character.

## Lookahead

Lookahead (predicate) is a special operator used to test whether the following
token appear in the input string or not without advancing a pointer. Lookahead
defines a condition by which it succeeds or fails, and preserves the knowledge
whether the pattern succeeded or failed. If lookahead fails, it causes the
whole alternative to fail.

There are two lookahead operators:

- And `&`: succeeds if the pattern succeeded
- Not `!`: succeeds if the pattern failed

The following example shows the usage of the Not predicate. It defines the
string, enclosed in double quotes with arbitrary characters except for the
double quote mark in between.

Examples:

```peg
EndOfFile <- !.
```

`EndOfFile` succeeds if Any Character did not match, that is, it matches "no
any character".

```peg
Comment   <- '//' (!'\n' .)* '\n'
```

`Comment` defines syntax of an inline comment that starts with a double forward
slash `'//'` and matches all characters until and including a newline. `!'\n'`
is necessary due to possessive nature of the [Zero or more
operator](#quantifier). When the parser reads a newline, `(!'\n' .)*` fails
without consuming it, and then consumes final `'\n'` and succeeds.

```peg
Term <- Atom Spacing &(Not / Or / And)
      / Atom Spacing? &RightBrace
```

This code snippet describes a part of the conditional language grammar.
`Atom` must be followed by `Spacing` if it is then followed by `Not`, `Or`, or
`And`, to ensure that its contents are not "glued" to these keywords; or `Atom`
may be followed by `Spacing` if it is then followed by the `RightBrace`.

And predicate does not consume the token, but remembers that it was
successfully parsed at the given position, which allows some outer rule that
uses `Term` rule to parse the rest of the input.

## Quantifier

Quantifiers are operators that define how many times the preceding pattern
should or must be repeated.

Types of quantifiers:

- `?`

    Optional (zero or one). Tries to consume preceding pattern and
    unconditionally succeeds (even if the pattern did not succeed once)

- `*`

    Zero or more. Tries to consume as many matches as possible and
    unconditionally succeeds.

- `+`

    One or more. Consumes one or more matches of the pattern and succeeds if at
    least one match occured.

- `{}`

    Repetition. Attempts to match the pattern specified number of
    times. Can be of two forms:

    - `{n}` matches the pattern exact number of times
    - `{n1-n2}` matches the pattern between n1 and n2 times inclusively

```peg
# Optional line ending
Statement <- Expression ';'?

# Sequence of digits, separated by comma
Sequence <- [0-9] (',' [0-9])*

# Integer
Integer <- [0-9]+
```

Zero or more `*` and one or more `+` quantifiers are possessive, i.e.
the expression `'a'* 'a'` would fail because the expression `'a'*` consumes
all matching text and does not backtrack.

## Cut

Cut is an experimental feature that allows to wipe previous parsing history and
ensures that the following token either succeeds or, if it fails, the parsing
process terminates. It improves error reporting and may decrease the space
consumption, albeit it should be used with care because, inserted in the wrong
place, it easily can change the meaning of the grammar.

Cut is represented by caret `^` character.

Cut can be inserted after a token or a sequence of tokens if there is no
other expression that starts with the same token or sequence and reachable at
this position.

For example, second alternative of the `Char` rule is unreachable, because
if the `'n'` string literal fails, parser will never backtrack to try the
`'\\' 'r'` sequence.

```peg
Char <- '\\' ^ 'n' / '\\' 'r'
```

## Metarules and Metavariables

Metarules are a special entry type of a grammar that allows a user to assign
semantics to a grammar. Unlike other parser generator tools, Polygen allows
user to separate a syntax description and semantic actions. Metarule syntax is
of two variations: inline, and splitted into a declaration and a definition.

Metarules are assigned to alternatives, not whole rules. The same metarule can
be assigned to several alternatives. Metarule always comes at the end of an
alternative before the next forward slash (if it appears).

Metarule starts with the dollar sign `$` and has a body enclosed in curly
brackets `{}`. Polygen reindents body contents when generates the parser.
Whitespace between the dollar sign and an identifier is disallowed in all
forms.

If metarule body contains closing curly bracket, it must be escaped: `\}`.

### Inline metarule

Inline metarule syntax is `${ ... }`, where ellipsis denotes the metarule body.
Inline metarules have no names and are specified right inside the grammar.
Although this can be handy for quick experiment, this usage is discouraged
because it makes readability and portability of a grammar worse.

```peg
Rule <- Alternative1 ${ ... }
      / Alternative2 ${ ... }
```

### Metarule declaration

Second variation of metarule syntax consists of the two parts: the declaration
and the definition.

Declaration comes after an alternative and consists of a dollar sign followed
by an identifier:

```peg
Declaration <- '$' Identifier
```

Definition must have the same name as the corresponding declaration (metarule
names are case sensitive). It does not matter whether the definition appears
before the declaration in a grammar or after. Definition syntax is roughly
this:

```peg
Declaration <- '$' Identifier '{' ... '}'
```

Example:

```peg
Integer <- Digit* $integer

$integer {
    return int(''.join(digit))
}
```

### Metavariable

Metavariable (or metaname) assigns a name to a pattern. This name can be used
by a metarule to acquire the value, returned by the pattern. Metavariable's
syntax is:

```peg
Metavariable <- Identifier ':'
```

Metavariable prefixes the pattern:

```text
metavar:'literal'
metavar:"literal"
metavar:.
metavar:[abc]
metavar:("hello" / "world")
```

Polygen deduces metanames for all patterns except patterns with predicates. If
the pattern is an identifier, then the metaname is lowercase identifier string.
If the pattern is a string literal, wildcard, or character class, then Polygen
assigns an index string to it.

```text
Expression: If '(' Condition ')' Space '{' Body '}'
Metanames:  if _1  condition _2  space _3  body _4
```

If the same identifier appears multiple times, metarules of subsequent
occurences are indexed.

```text
Expression: Char Char  Char
Metanames:  char char1 char2
```

Patterns with predicates can not be referenced from metarules because they does
not return anything meaningful. If the metarule is called, then, obviously, all
predicates succeeded.

There is a special kind of metaname: ignore metaname. It is represented by an
underscore `_`, and it discards the return result of a pattern. Pattern with an
ignore metaname can not be referenced from metarule, and its value is excluded
from the return result of a rule.

```text
Tuple <-   Number  ',' Number
Metanames: number  _1 number1
Returns:   Number, ',', Number

Tuple <-   Number _:',' Number
Metanames: number       number1
Returns    Number       Number
```

## Directives

Directives are another special type of grammar entities. Directives do not
define grammar syntax directly, as Rules do, as well as they do not define
semantics. Instead they are the "grammar meta rules". Directives start with an
at sign `@`.

Directives:

- `@entry`

    Entry directive marks a rule the start rule of the grammar. It must be
    specified only once per grammar. Can be of two forms.

    First form follows the normal rule definition:

        @entry
        Rule <- Expression

    In second form the directive requires only the name of a rule. Note that
    the rule must exist in the grammar.

        @entry Rule

    `@entry` must be separated from the rule name by whitespace.

- `@include`

    Allows to include files into the grammar. When the file is specified in the
    directive, Polygen first processes all directives it contains (including
    `@include`, allowing for nested includes) and then concatenates grammars to
    one whole.

        @include "path"
        @include 'path'

- `@toplevel`

    Allows the nested grammar to be processed and included if and only if the
    file, where it appears, is first.

    File that is specified in Polygen executable call is the first file.

    `SubGrammar` complies to the definition of `Grammar`.

        @toplevel {
            SubGrammar
        }

- `@backend`

    Looks somewhat similar to CSS media query.

        @backend(BackendName) {
            SubGrammar
        }

    Allows the nested grammar to be processed and included if and only if the
    name of a backend is equal to `BackendName`.

- `@ignore`

    Ignore directive assigns ignore metaname to specified rule(s) globally. All
    occurences of specified rule(s) will be discarded, unless the user assigns
    a metaname manually. Ignore directive has two forms.

    In the first form it prefixes the rule definition

        @ignore
        Rule <- Expression

    The second form allows to list multiple rules. Rules in the list are
    separated by whitespace (spaces or newlines).

        @ignore {
            Rule1 Rule2 ... RuleN
        }
