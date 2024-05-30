name = "python"
language = "Python"
version = "0.0.1"

# Capabilities enable tree modifier rules and control the appearance of
# certain node types in the final grammar tree.
capabilities = {
    "leftrec": True,

    # FIXME: Currently these modifiers are inversed,
    # e.g. do not replace Rep nodes -> ReplaceRep(apply=False)
    "repetition": False,
    "char-class": False
}

# Map skeleton files to the default output files. User may override the
# defaults.
files = {
    "parser.py.in": "parser.py"
}

# Main generator script filename. Default: gen.py.
generator = "gen.py"

# Preprocessor definitions. These definitions will be passed to the
# skeleton file preprocessor.
definitions = {
    "standalone": False
}

# `datetime` is one of the predefined preprocessor directives.
# Here the default value is given. Though codegen allows user to override
# this value.
datetime_format = "%Y-%m-%dT%H:%M"

# Backend can add options through `options` field. This might be useful
# e.g. to pass custom options to the generator.
options = {}
