# Phase 3 status

## Implemented and locally verified

- Reassignment and `while` loops
- Typed top-level functions, calls, recursion and returns
- Static checks for new statements and calls
- TAC for branches, loops and calls; basic-block CFG
- Constant folding, safe algebraic identities and selected unreachable-code elimination
- Stack bytecode generator and bounded VM
- Original AST, optimized AST and VM output/state comparison
- Offline HTML explorer and user guide
- 27 passing automated tests and an end-to-end demo that prints 120

## Deliberately outside final scope

- SSA and phi nodes
- Advanced data-flow and loop optimizations
- Full instruction-by-instruction persistent provenance across every representation
- Interactive VM debugging and formal equivalence proof

The bytecode backend consumes the optimized AST. The TAC and its CFG are explanatory artifacts, not the bytecode input.
