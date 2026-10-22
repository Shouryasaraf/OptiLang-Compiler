from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from optilang import CompileError, compile_source, tokenize
from optilang.bytecode import BytecodeCompiler, VirtualMachine
from optilang.compiler import Parser
from optilang.explorer import render_html


class Phase3Tests(unittest.TestCase):
    def test_loop_assignment_and_cfg_back_edge(self):
        source = "let n: int = 0; while (n < 4) { n = n + 1; } print(n);"
        result = compile_source(source)
        self.assertEqual(result.output, ["4"])
        self.assertTrue(any("-> B" in line for line in result.cfg))
        self.assertIn("STORE 'n'", "\n".join(result.bytecode))

    def test_recursive_function_and_forward_call(self):
        source = """print(fact(5));
        fn fact(n: int): int {
          if (n <= 1) { return 1; }
          else { return n * fact(n - 1); }
        }"""
        result = compile_source(source)
        self.assertEqual(result.output, ["120"])
        self.assertTrue(result.validated)
        self.assertIn("fact:", result.cfg)

    def test_multiple_arguments_and_scope_shadowing(self):
        source = """fn add(a: int, b: int): int { return a + b; }
        let x: int = 4; { let x: int = 7; print(add(x, 1)); } print(x);"""
        self.assertEqual(compile_source(source).output, ["8", "4"])

    def test_function_updates_global_state(self):
        source = """let total: int = 0;
        fn bump(n: int): int { total = total + n; return total; }
        print(bump(2)); print(bump(3));"""
        self.assertEqual(compile_source(source).output, ["2", "5"])

    def test_while_false_and_else(self):
        source = "let x: int = 1; while (false) { x = 2; } if (x == 1) { print(x); } else { print(0); }"
        self.assertEqual(compile_source(source).output, ["1"])

    def test_algebraic_simplification_record(self):
        result = compile_source("let x: int = 6; print(x + 0);")
        self.assertEqual(result.output, ["6"])
        self.assertTrue(any("algebraic simplification" in item for item in result.optimizations))
        self.assertNotIn(" + 0", "\n".join(result.optimized_tac))

    def test_unreachable_branch_is_removed(self):
        result = compile_source("if (false) { print(99); } else { print(7); }")
        self.assertEqual(result.output, ["7"])
        self.assertNotIn("print 99", "\n".join(result.optimized_tac))
        self.assertTrue(any("unreachable-code elimination" in change for change in result.optimizations))

    def test_short_circuit_avoids_division_by_zero(self):
        result = compile_source("let x: bool = false && (1 / 0 == 0); print(x);")
        self.assertEqual(result.output, ["False"])
        self.assertTrue(result.validated)

    def test_integer_division_and_remainder(self):
        self.assertEqual(compile_source("print(-7 / 3); print(-7 % 3);").output, ["-2", "-1"])

    def test_controlled_division_by_zero(self):
        with self.assertRaisesRegex(CompileError, "division by zero"):
            compile_source("print(1 / 0);")

    def test_undefined_assignment(self):
        with self.assertRaisesRegex(CompileError, "undefined variable"):
            compile_source("x = 2;")

    def test_wrong_assignment_type(self):
        with self.assertRaisesRegex(CompileError, "cannot assign bool to int"):
            compile_source("let x: int = 2; x = false;")

    def test_wrong_argument_count(self):
        with self.assertRaisesRegex(CompileError, "wrong number of arguments"):
            compile_source("fn f(x: int): int { return x; } print(f());")

    def test_wrong_argument_type(self):
        with self.assertRaisesRegex(CompileError, "expected int argument"):
            compile_source("fn f(x: int): int { return x; } print(f(true));")

    def test_missing_return_and_return_outside_function(self):
        with self.assertRaisesRegex(CompileError, "may finish without returning"):
            compile_source("fn f(): int { print(1); }")
        with self.assertRaisesRegex(CompileError, "return outside function"):
            compile_source("return 2;")

    def test_non_boolean_loop_condition(self):
        with self.assertRaisesRegex(CompileError, "while condition must be bool"):
            compile_source("while (1) { print(1); }")

    def test_vm_instruction_limit(self):
        program = Parser(tokenize("while (true) {} ")).parse()
        bytecode = BytecodeCompiler().compile(program)
        with self.assertRaisesRegex(CompileError, "instruction limit exceeded"):
            VirtualMachine(bytecode, step_limit=20).execute()

    def test_visual_explorer_escapes_source_and_has_stage_data(self):
        source = 'print("<tag>");'
        page = render_html(source, compile_source(source))
        self.assertIn("&lt;tag&gt;", page)
        self.assertNotIn('<tag>', page)
        self.assertIn('Optimization record', page)
        self.assertIn('Bytecode', page)
        self.assertIn('VM trace', page)


if __name__ == "__main__":
    unittest.main()
