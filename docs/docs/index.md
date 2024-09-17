# Polygen

**Poly**glot Parser **Gen**erator aims to be universal Packrat generator
for almost any high-level language.

Briefly, what is it and why you may want to use it? Polygen is a (yet another)
parser generator that generates Packrat parsers. It uses the original Bryan
Ford's definition of Parsing Expression Grammar with additional features like
UNICODE characters, preprocessor directives, and semantic actions.

Unlike the vast majority of similar tools, Polygen aims to be universal
generator, not hardwired to only one target language. It allows user to split
the definition of language syntax, or the grammar, and semantic actions, which
are essentially the code attached to the grammar. It makes the grammar more
readable and greatly improves portability.

## Installation

```sh
pip install git+https://github.com/glebzlat/polygen

# or
git clone https://github.com/glebzlat/polygen
pip install polygen
```

## Usage

To generate a parser from the grammar:

```sh
polygen generate <grammar-file> -b <backend-name> -o <output-directory>
```

To test the backend for parser equivalency:

```sh
polygen test -b <backend-name>
```
