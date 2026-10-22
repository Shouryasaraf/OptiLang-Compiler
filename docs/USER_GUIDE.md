# OptiLang user guide

## Install and run

Requires Python 3.11 or later. In a terminal opened at the repository root:

```bash
python -m pip install -e .
optilang examples/phase3.ol --html phase3-explorer.html
```

On Windows PowerShell without installation:

```powershell
$env:PYTHONPATH='src'
python -m optilang examples\phase3.ol --html phase3-explorer.html
```

The console prints token positions, AST, symbols, TAC, TAC and bytecode control-flow graphs, optimization records, bytecode, VM trace, validation status and `OUTPUT` followed by `120`. Open the HTML file in a browser to inspect the same stages. `--html` is optional.

## Language

Use `let name: type = expression;` to declare a variable, and `name = expression;` to assign an existing variable. Types are `int`, `float`, `bool`, and `string`. Blocks use braces and create variable scope. Conditions of `if` and `while` must be Boolean. Expressions support arithmetic, comparisons, equality, Boolean operators and function calls. Functions use `fn name(parameter: type): return_type { ... return value; }`. Return a value on every reachable branch of an explicit `if/else` path.

Example:

```text
fn twice(n: int): int { return n * 2; }
let x: int = 1;
while (x < 3) { x = x + 1; }
print(twice(x));
```

The output is `6`.

## Errors and limits

The CLI reports lexical, syntax, semantic and runtime errors with a nonzero exit code. Tokens and most semantic errors carry a line and column. A loop exceeding the VM instruction budget raises `Runtime error: instruction limit exceeded`; deep recursion raises a call-depth error. Some evaluator errors have no source coordinate. Input and output files use UTF-8. The HTML file is self-contained and can be opened offline.

Run the test suite with `python -m unittest discover -s tests -v`.
