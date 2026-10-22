# Final review demonstration

1. State the problem: compiler decisions between source and output are hard to inspect.
2. Open `examples/phase3.ol`. Point out its loop, reassignment, recursive function, and `+ 0` optimization opportunity.
3. Run `python -m unittest discover -s tests -v`. Show the summary with 27 passing tests.
4. Run `optilang examples/phase3.ol --html phase3-explorer.html`.
5. In the console, show the AST, TAC loop back edge, CFG, optimization record at source position 13:36, bytecode `CALL` and `JUMP`, validation line, and final output `120`.
6. Open `phase3-explorer.html` and switch between source, TAC, optimization record, bytecode and output.
7. Explain the implementation boundary: the optimized AST is lowered to bytecode; TAC is an inspectable representation. Three execution paths agree on output and final global state for the example.
8. Demonstrate a controlled error with `let x: int = true;` in a separate file and explain why static checking rejects it.

Likely viva questions: What is the AST? Why does `3 * 4` bind before addition? How does a scoped symbol table work? Where does a loop back edge appear? Why is `x + 0` safe for numeric expressions? How does the VM terminate an infinite loop? What is the difference between the AST interpreter and the bytecode VM?
