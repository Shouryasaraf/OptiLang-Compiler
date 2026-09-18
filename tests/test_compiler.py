from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from optilang import CompileError, compile_source, tokenize


class LexerTests(unittest.TestCase):
    def test_keywords_identifiers_and_positions(self):
        tokens = tokenize("let total: int = 42;")
        self.assertEqual(
            [token.kind for token in tokens[:7]],
            [
                "LET",
                "IDENTIFIER",
                "COLON",
                "TYPE",
                "ASSIGN",
                "NUMBER",
                "SEMICOLON",
            ],
        )
        self.assertEqual(tokens[1].lexeme, "total")
        self.assertEqual((tokens[1].line, tokens[1].column), (1, 5))

    def test_lexical_error(self):
        with self.assertRaisesRegex(CompileError, "Lexical error"):
            tokenize("let x: int = 2 @ 3;")


class PipelineTests(unittest.TestCase):
    def test_precedence_and_execution(self):
        result = compile_source("let x: int = 2 + 3 * 4; print(x);")
        self.assertEqual(result.output, ["14"])
        self.assertIn("t1 = 3 * 4", result.tac)

    def test_if_statement(self):
        source = "let x: int = 14; if (x > 10) { print(x); }"
        self.assertEqual(compile_source(source).output, ["14"])

    def test_constant_folding(self):
        result = compile_source("let x: int = 2 + 3 * 4; print(x);")
        self.assertIn("x = 14", result.optimized_tac)

    def test_undefined_variable(self):
        with self.assertRaisesRegex(CompileError, "undefined variable"):
            compile_source("print(missing);")

    def test_type_mismatch(self):
        with self.assertRaisesRegex(CompileError, "cannot assign bool to int"):
            compile_source("let x: int = true;")

    def test_redeclaration(self):
        source = "let x: int = 1; let x: int = 2;"
        with self.assertRaisesRegex(CompileError, "already declared"):
            compile_source(source)

    def test_missing_semicolon(self):
        with self.assertRaisesRegex(CompileError, "Expected ';'"):
            compile_source("let x: int = 1")


if __name__ == "__main__":
    unittest.main()

