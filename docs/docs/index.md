# Polygen

**Poly**glot Parser **Gen**erator aims to be universal Packrat generator
for almost any high-level language.

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
python -m polygen generate <grammar-file> -b <backend-name> -o <output-directory>
```

To test the backend for parser equivalency:

```sh
python -m polygen test -b <backend-name>
```
