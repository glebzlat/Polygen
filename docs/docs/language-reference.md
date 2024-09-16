# Polygen Language Reference

Polygen language is based on the original Bryan Ford's PEG definition and adds
convenient features like unicode characters, metarules, metanames, and
directives.

## Grammar entity

Polygen grammar consists of entities. Entity can be [a rule](#rule),
[metarule](#metarules-and-metavariables), and a [directive](#directives). Rules
describe language's syntax. Metarules define semantics. And directives allow to
control the grammar processing and manage auxiliary details.

Polygen is insensitive to whitespace characters (space ` `, newline `\n`,
carriage return `\r`, and tab `\t`), and thus whitespace is optional unless
otherwise stated.

## Rule

Rule is the main grammar entity. Its purpose is to define (some part of) the
syntax of the language. Rule's syntax follows the original PEG definition
and consists of the rule name, the left arrow and the body, or expression.

```text
Rule <- Identifier '<-' Expression
```

The following code snippets is a demonstration of the Rule definition. This
term is referenced throughout this document.

```peg
Rule <- Expression
```

## Expression

Expression represents the sequence of ordered choices - alternatives.
Alternatives are tested in order they are appeared in the sequence, and if
once the alternative succeeds, the whole expression succeeds and does not test
the remaining alternatives.

Alternatives in the expression are separated by the forward slash.

```text
Expression <- Alt 1 / Alt 2 / Alt N
```

## Alternative

Alternative is a sequence of parts, that are tested in order they appeared.
Part is tested when the previous part succeeded, and if the part failed, then
the whole alternative fails and the remaining parts are not tested.

Alternative has an optional metarule declaration or definition.

```text
Alternative <- Part1 Part2 PartN MetaRuleDeclOrDef?
```

## Part

Part consists of multiple components, where the most of the components are
optional. Optional components are followed by the question mark.

```text
Part <- Cut? MetaName? Lookahead? Primary Quantifier?
```

Components explanation:

- [Cut](#cut)

    Cut is the special operator that instructs the parser to wipe the
    backtracking information.

- [MetaName](#metavariable)

    MetaName can be seen as a variable name. It allows to reference the
    value of the parsed token in semantic action.

- [Lookahead](#lookahead)

    Lookahead is the special type of operators, whose name is self-explanatory:
    it looks ahead and matches the token without consuming it.

- [Primary](#primary)

    This is the actual value of the token.

- [Quantifier](#quantifier)

    Quantifiers are another type of operators that allow to specify how many
    times the token must or may be repeated.

## Primary

Primary value is the definition of what should be matched.

Primary value types are:
- Identifier
- Expression in parentheses
- String literal
- Character class
- Wildcard (dot)

### Identifier

Identifier is the name of the nonterminal. Rule names must be of Identifier
format. The Identifier consists of ASCII letters and digits and underscore,
and can not begin with the digit.

Subsequent identifiers must be separated by whitespace, otherwise they will
be treated as a single identifier.

```peg
Identifier <- [a-zA-Z_] [a-zA-Z0-9_]*
```

The asterisk `*` means "repeated zero or more times".

### String literal

String literal is the arbitrary sequence of characters in single or double
quotes. Matches the input string exactly.

Characters of a literal can be the general ASCII characters and special
characters. Special characters are escaped with the backward slash.

```peg
Char <- EscapeChar / .
```

The dot `.` means "any character".

Special characters are:

- `\n` newline
- `\r` carriage return
- `\t` tab
- `\'`, `\"` quote
- `\[`, `\]` square brackets
- `\\` backward slash
- `\nn` and `\nnn` octal character code
- `\uXXXX` UNICODE character

Escaped quote marks is used in case when the type of the quote mark matches the
type of opening and closing marks: `'my message: \'hello\''`,
`"my message: \"hello\""`.

Octal character code digits are in the range from 0 to 7 inclusively, and the
first digit can be maximum of 2: `\60`, `\141`.

UNICODE character digits are hexadecimal from 0 to 9 and from A to F. Lowercase
a to f are allowed: `\u03c0`, `\u03C0`, `\u00b5`.

### Character class

Character class matches single character from the range. Can contain multiple
ranges. Range consists either of a single character or two characters,
separated by the hyphen. In the latter case the range matches the starting
character, the ending character and all characters located lexicographically in
between. Starting character placed on first and must be less or equal than the
ending.

```peg
Class <- '[' CharRange* ']'
CharRange <- Char '-' Char
```

### Wildcard (dot)

Wildcard `.` matches any character.

## Lookahead

Lookahead (predicate) is the special operator used to test whether the
following token appear in the input string or not without advancing the
pointer. Lookahead defines the condition by which it succeeds or fails, and
preserves the knowledge whether the pattern succeeded or failed. If the
lookahead fails, it causes the whole alternative to fail.

There are two lookahead operators:

- And `&`: succeeds if the pattern succeeded
- Not `!`: succeeds if the pattern failed

The following example shows the usage of the Not predicate. It defines the
string, enclosed in double quotes with arbitrary characters except for
the double quote mark in between.

Examples:

```peg
EndOfFile <- !.
```

`EndOfFile` succeeds if Any Character did not match, that is, it matches "no
any character".

```peg
Comment   <- '//' (!'\n' .)* '\n'
```

`Comment` defines the syntax of the inline comment, that starts with the double
forward slash `'//'` and matches all characters until the newline, including
it. `!'\n'` is necessary due to possessive nature of the [Zero or more
operator](#quantifier). When the parser reads the newline, `(!'\n' .)*` fails
without consuming it, and then consumes final `'\n'` and succeeds.

```peg
Term <- Atom Spacing &(Not / Or / And)
      / Atom Spacing? &RightBrace
```

This code snippet describes the part of the conditional language grammar.
`Atom` must be followed by `Spacing`, if it is then followed by `Not`, `Or`, or
`And` to ensure that its contents are not "glued" to these keywords, or `Atom`
may be followed by `Spacing`, if it is then followed by the `RightBrace`.

And predicate does not consume the token, but remembers that it was
successfully parsed at the given position, which allows some outer rule that
uses `Term` rule to parse the rest of the input.

## Quantifier

Quantifiers are operators that define how many times the preceding pattern
should or must be repeated.

Types of quantifiers:

- `?`

    Optional (zero or one). Tries to consume preceding pattern and
    unconditionally succeeds (i.e. even if the pattern did not succeed once)

- `*`

    Zero or more. Tries to consume as many matches as possible and
    unconditionally succeeds.

- `+`

    One or more. Consumes one or more matches of the preceding pattern and
    succeeds if at least one match occured.

- `{}`

    Repetition. Attempts to match the preceding pattern specified number of
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
the expression `'a'* 'a'` would fail, because the expression `'a'*` does not
backtrack.

## Cut

Cut is an experimental feature that allows to wipe the previous parsing history
and ensures that the following token either succeeds, or, if it fails, the
parsing process terminates. It improves error reporting of the parser and may
decrease the space consumption, albeit it should be used with care, because,
inserted in the wrong place, it easily can change the meaning of the grammar.

Cut is represented by the caret `^` character.

Cut can be inserted after a token or a sequence of tokens if there is no
other expression that starts with the same token or sequence and reachable at
this position.

For example, the second alternative of the `Char` rule is unreachable, because
if the `'n'` string literal fails, parser will never backtrack to try the
`'\\' 'r'` sequence.

```peg
Char <- '\\' ^ 'n' / '\\' 'r'
```

## Metarules and Metavariables

Metarules are the special entry type of the Polygen grammar, that allows the
user to assign the semantics to the grammar. Unline the other parser generator
tools, Polygen allows the user to separate the syntax description and semantic
actions. Due to this, metarules have two syntax variations.

Metarules are assigned to alternatives, not whole rules. The same metarule can
be assigned to several alternatives. Metarule always comes at the end of the
alternative before the next forward slash (if appears).

Metarule starts with the dollar sign `$` and has a body enclosed in curly
brackets `{}`. Polygen reindents body contents when generates the parser.
Whitespace between the dollar sign and an identifier is disallowed in all
forms.

If metarule body contains closing curly bracket, it must be escaped: `\}`.

### Inline metarule

Inline metarule syntax is `${ ... }`, where the ellipsis denotes the metarule
body. Inline metarules have no names and are specified right inside the grammar.
Although this can be handy for the quick experiment, this usage is discouraged
because it impacts readability and portability of the grammar.

```peg
Rule <- Alternative ${ ... }
```

### Metarule declaration

The second variation of metarules consists of two parts: declaration and
definition.

Declaration follows the alternative and consists of an identifier, prepended by
the dollar sign:

```peg
Declaration <- '$' Identifier
```

Definition must have the same name as the declaration (metarule names are case
sensitive). It does not matter whether the definition appears before the
declaration if the file or after. Definition syntax is roughly this:

```peg
Declaration <- '$' Identifier '{' ... '}'
```

### Metavariable

Metavariable (or metaname) assigns the token the name by which it can be
referenced in the metarule. Metavariable's syntax is:

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

Polygen deduces metanames for all patterns, except patterns with predicates. If
the pattern is an identifier, then the metaname is lowercase identifier string.
If the pattern is a string literal, wildcard, or character class, then Polygen
assigns the index string to it.

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

Patterns with predicates can not be referenced from metarules because they
does not return anything meaningful. If the metarule is called then, obviously,
all predicates succeeded.

There is the special kind of metaname: ignore metaname. It is defined as an
underscore `_`. When it is assigned to a pattern, its return result is
discarded and cannot be retrieved from the metarule.

```text
Tuple <-   Number  ',' Number
Metanames: number  _1 number1
Returns:   Number, ',', Number

Tuple <-   Number _:',' Number
Metanames: number       number1
Returns    Number       Number
```

## Directives

Directives is an another special type of grammar entities. Directives does
not define the grammar syntax directly, as Rules do, and they does not define
semantics directly as well. Instead, directives are the "grammar meta rules".
Directives start with an at sign `@`.

Directives:

- `@entry`

    Entry directive marks the rule as the start rule of the grammar. Must be
    specified only once per grammar. Can be of two forms.

    The first form follows the normal rule definition:

        @entry
        Rule <- Expression

    In the second form directive requires only the name of the rule. Rule must
    appear in the grammar.

        @entry Rule

    `@entry` must be separated from the rule name by whitespace.

- `@include`

    Allows to include files into the grammar. When the file is specified in
    include directive, Polygen first processes all its directives (including
    `@include`, allowing for nested includes) and then concatenates grammars
    to one whole.

        @include "path"
        @include 'path'

- `@toplevel`

    Allows the nested grammar to be processed and included if and only if the
    file is first.

    The file that is specified in Polygen executable call is the first file.

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
    chosen backend's name is equal to the specified `BackendName`.

- `@ignore`

    Ignore directive assigns Ignore metaname to specified rule(s) globally. All
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
