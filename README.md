# OptiLang Compiler

OptiLang is a small statically typed language created for the Compiler Design
Laboratory project. This Phase 2 repository implements the first complete
source-to-execution path:

```text
source -> lexer -> parser -> AST -> semantic analysis
       -> three-address code -> constant folding -> interpreter
```

The implementation is deliberately compact and uses only the Python standard
library. It exposes the token stream, AST, symbol table, unoptimized TAC,
optimized TAC and program output for transparent inspection of each compiler
stage.

## Implemented Phase 2 features

- Position-aware lexical analysis with comments and structured errors
- Recursive-descent parsing with operator precedence
- Explicit AST nodes for declarations, expressions, blocks and conditionals
- Nested symbol tables and static type checking
- Three-address code with temporaries, labels and branches
- Constant folding for literal unary and binary expressions
- AST interpreter for deterministic demonstration output
- Automated tests for valid programs and lexical, syntax and semantic errors
- Command-line output for every implemented compiler stage

## Requirements

- Python 3.11 or newer
- No third-party runtime dependencies

## Install locally

```powershell
python -m pip install -e .
```

## Run the demonstration

```powershell
optilang examples/demo.ol
```

You can also run the package directly after installation:

```powershell
python -m optilang examples/demo.ol
```

The final output for the supplied example is `14`.

## Run the tests

```powershell
python -m unittest discover -s tests -v
```

## Repository structure

```text
OptiLang-Compiler/
|-- docs/
|   `-- PHASE2_STATUS.md
|-- examples/
|   `-- demo.ol
|-- src/optilang/
|   |-- __init__.py
|   |-- __main__.py
|   |-- cli.py
|   `-- compiler.py
|-- tests/
|   `-- test_compiler.py
|-- .gitignore
|-- pyproject.toml
`-- README.md
```

## Current boundary

Functions, loops, reassignment, SSA, bytecode generation, the bounded virtual
machine and the graphical explorer remain Phase 3 work. The Phase 2 interpreter
executes the optimized AST directly.
