from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class CompileError(Exception):
    """Controlled error raised by an OptiLang compiler stage."""


@dataclass(frozen=True)
class Token:
    kind: str
    lexeme: str
    literal: Any
    line: int
    column: int


KEYWORDS = {
    "let": "LET",
    "print": "PRINT",
    "if": "IF",
    "else": "ELSE",
    "true": "TRUE",
    "false": "FALSE",
    "int": "TYPE",
    "float": "TYPE",
    "bool": "TYPE",
    "string": "TYPE",
}

TOKEN_PATTERN = re.compile(
    r"(?P<NEWLINE>\n)|"
    r"(?P<SPACE>[ \t\r]+)|"
    r"(?P<COMMENT>//[^\n]*)|"
    r"(?P<NUMBER>\d+(?:\.\d+)?)|"
    r'(?P<STRING>"[^"\n]*")|'
    r"(?P<EQEQ>==)|(?P<NE>!=)|(?P<LE><=)|(?P<GE>>=)|"
    r"(?P<AND>&&)|(?P<OR>\|\|)|"
    r"(?P<ASSIGN>=)|(?P<LT><)|(?P<GT>>)|"
    r"(?P<PLUS>\+)|(?P<MINUS>-)|(?P<STAR>\*)|"
    r"(?P<SLASH>/)|(?P<PERCENT>%)|(?P<BANG>!)|"
    r"(?P<LPAREN>\()|(?P<RPAREN>\))|"
    r"(?P<LBRACE>\{)|(?P<RBRACE>\})|"
    r"(?P<COLON>:)|(?P<SEMICOLON>;)|"
    r"(?P<IDENTIFIER>[A-Za-z_][A-Za-z0-9_]*)"
)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    position = 0
    line = 1
    column = 1
    while position < len(source):
        match = TOKEN_PATTERN.match(source, position)
        if match is None:
            bad = source[position]
            raise CompileError(
                f"Lexical error at {line}:{column}: unexpected {bad!r}"
            )
        kind = match.lastgroup or ""
        lexeme = match.group()
        start_column = column
        position = match.end()
        if kind == "NEWLINE":
            line += 1
            column = 1
            continue
        column += len(lexeme)
        if kind in {"SPACE", "COMMENT"}:
            continue
        literal: Any = None
        if kind == "IDENTIFIER":
            kind = KEYWORDS.get(lexeme, "IDENTIFIER")
        elif kind == "NUMBER":
            literal = float(lexeme) if "." in lexeme else int(lexeme)
        elif kind == "STRING":
            literal = lexeme[1:-1]
        elif kind == "TRUE":
            literal = True
        elif kind == "FALSE":
            literal = False
        tokens.append(Token(kind, lexeme, literal, line, start_column))
    tokens.append(Token("EOF", "", None, line, column))
    return tokens


class Expr:
    pass


@dataclass
class Literal(Expr):
    value: Any
    type_name: str


@dataclass
class Variable(Expr):
    name: Token


@dataclass
class Unary(Expr):
    operator: Token
    right: Expr


@dataclass
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr


class Stmt:
    pass


@dataclass
class LetStmt(Stmt):
    name: Token
    type_name: str
    initializer: Expr


@dataclass
class PrintStmt(Stmt):
    expression: Expr


@dataclass
class ExprStmt(Stmt):
    expression: Expr


@dataclass
class BlockStmt(Stmt):
    statements: list[Stmt]


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: BlockStmt
    else_branch: BlockStmt | None


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self.check("EOF"):
            statements.append(self.statement())
        return statements

    def statement(self) -> Stmt:
        if self.match("LET"):
            return self.let_statement()
        if self.match("PRINT"):
            return self.print_statement()
        if self.match("IF"):
            return self.if_statement()
        if self.match("LBRACE"):
            return BlockStmt(self.block())
        expression = self.expression()
        self.consume("SEMICOLON", "Expected ';' after expression")
        return ExprStmt(expression)

    def let_statement(self) -> LetStmt:
        name = self.consume("IDENTIFIER", "Expected variable name")
        self.consume("COLON", "Expected ':' after variable name")
        type_token = self.consume("TYPE", "Expected declared type")
        self.consume("ASSIGN", "Expected '=' before initializer")
        initializer = self.expression()
        self.consume("SEMICOLON", "Expected ';' after declaration")
        return LetStmt(name, type_token.lexeme, initializer)

    def print_statement(self) -> PrintStmt:
        self.consume("LPAREN", "Expected '(' after print")
        expression = self.expression()
        self.consume("RPAREN", "Expected ')' after print value")
        self.consume("SEMICOLON", "Expected ';' after print statement")
        return PrintStmt(expression)

    def if_statement(self) -> IfStmt:
        self.consume("LPAREN", "Expected '(' after if")
        condition = self.expression()
        self.consume("RPAREN", "Expected ')' after condition")
        self.consume("LBRACE", "Expected '{' before if body")
        then_branch = BlockStmt(self.block())
        else_branch = None
        if self.match("ELSE"):
            self.consume("LBRACE", "Expected '{' before else body")
            else_branch = BlockStmt(self.block())
        return IfStmt(condition, then_branch, else_branch)

    def block(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self.check("RBRACE") and not self.check("EOF"):
            statements.append(self.statement())
        self.consume("RBRACE", "Expected '}' after block")
        return statements

    def expression(self) -> Expr:
        return self.logical_or()

    def logical_or(self) -> Expr:
        expression = self.logical_and()
        while self.match("OR"):
            expression = Binary(expression, self.previous(), self.logical_and())
        return expression

    def logical_and(self) -> Expr:
        expression = self.equality()
        while self.match("AND"):
            expression = Binary(expression, self.previous(), self.equality())
        return expression

    def equality(self) -> Expr:
        expression = self.comparison()
        while self.match("EQEQ", "NE"):
            expression = Binary(expression, self.previous(), self.comparison())
        return expression

    def comparison(self) -> Expr:
        expression = self.term()
        while self.match("LT", "LE", "GT", "GE"):
            expression = Binary(expression, self.previous(), self.term())
        return expression

    def term(self) -> Expr:
        expression = self.factor()
        while self.match("PLUS", "MINUS"):
            expression = Binary(expression, self.previous(), self.factor())
        return expression

    def factor(self) -> Expr:
        expression = self.unary()
        while self.match("STAR", "SLASH", "PERCENT"):
            expression = Binary(expression, self.previous(), self.unary())
        return expression

    def unary(self) -> Expr:
        if self.match("BANG", "MINUS"):
            return Unary(self.previous(), self.unary())
        return self.primary()

    def primary(self) -> Expr:
        if self.match("NUMBER"):
            value = self.previous().literal
            type_name = "float" if isinstance(value, float) else "int"
            return Literal(value, type_name)
        if self.match("STRING"):
            return Literal(self.previous().literal, "string")
        if self.match("TRUE", "FALSE"):
            return Literal(self.previous().literal, "bool")
        if self.match("IDENTIFIER"):
            return Variable(self.previous())
        if self.match("LPAREN"):
            expression = self.expression()
            self.consume("RPAREN", "Expected ')' after expression")
            return expression
        token = self.peek()
        raise CompileError(
            f"Syntax error at {token.line}:{token.column}: expected expression"
        )

    def match(self, *kinds: str) -> bool:
        for kind in kinds:
            if self.check(kind):
                self.advance()
                return True
        return False

    def consume(self, kind: str, message: str) -> Token:
        if self.check(kind):
            return self.advance()
        token = self.peek()
        raise CompileError(
            f"Syntax error at {token.line}:{token.column}: {message}"
        )

    def check(self, kind: str) -> bool:
        return self.peek().kind == kind

    def advance(self) -> Token:
        if not self.check("EOF"):
            self.current += 1
        return self.previous()

    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]


class SemanticAnalyzer:
    def __init__(self):
        self.scopes: list[dict[str, str]] = [{}]

    def analyze(self, program: list[Stmt]) -> dict[str, str]:
        for statement in program:
            self.check_statement(statement)
        return dict(self.scopes[0])

    def check_statement(self, statement: Stmt) -> None:
        if isinstance(statement, LetStmt):
            current = self.scopes[-1]
            if statement.name.lexeme in current:
                self.error(statement.name, "variable already declared in this scope")
            value_type = self.infer(statement.initializer)
            if value_type != statement.type_name:
                self.error(
                    statement.name,
                    f"cannot assign {value_type} to {statement.type_name}",
                )
            current[statement.name.lexeme] = statement.type_name
        elif isinstance(statement, (PrintStmt, ExprStmt)):
            self.infer(statement.expression)
        elif isinstance(statement, BlockStmt):
            self.scopes.append({})
            for nested in statement.statements:
                self.check_statement(nested)
            self.scopes.pop()
        elif isinstance(statement, IfStmt):
            if self.infer(statement.condition) != "bool":
                raise CompileError("Semantic error: if condition must be bool")
            self.check_statement(statement.then_branch)
            if statement.else_branch is not None:
                self.check_statement(statement.else_branch)

    def infer(self, expression: Expr) -> str:
        if isinstance(expression, Literal):
            return expression.type_name
        if isinstance(expression, Variable):
            return self.resolve(expression.name)
        if isinstance(expression, Unary):
            right_type = self.infer(expression.right)
            if expression.operator.kind == "BANG" and right_type == "bool":
                return "bool"
            if expression.operator.kind == "MINUS" and right_type in {"int", "float"}:
                return right_type
            self.error(expression.operator, "invalid unary operand")
        if isinstance(expression, Binary):
            left_type = self.infer(expression.left)
            right_type = self.infer(expression.right)
            if left_type != right_type:
                self.error(expression.operator, "operands must have matching types")
            if expression.operator.kind in {"PLUS", "MINUS", "STAR", "SLASH", "PERCENT"}:
                if left_type not in {"int", "float"}:
                    self.error(expression.operator, "arithmetic requires numeric operands")
                return left_type
            if expression.operator.kind in {"LT", "LE", "GT", "GE"}:
                if left_type not in {"int", "float"}:
                    self.error(expression.operator, "comparison requires numeric operands")
                return "bool"
            if expression.operator.kind in {"EQEQ", "NE"}:
                return "bool"
            if expression.operator.kind in {"AND", "OR"} and left_type == "bool":
                return "bool"
            self.error(expression.operator, "invalid binary operands")
        raise CompileError("Semantic error: unknown expression node")

    def resolve(self, token: Token) -> str:
        for scope in reversed(self.scopes):
            if token.lexeme in scope:
                return scope[token.lexeme]
        self.error(token, f"undefined variable {token.lexeme!r}")

    @staticmethod
    def error(token: Token, message: str) -> None:
        raise CompileError(
            f"Semantic error at {token.line}:{token.column}: {message}"
        )


class ConstantFolder:
    def fold_program(self, program: list[Stmt]) -> list[Stmt]:
        return [self.fold_statement(statement) for statement in program]

    def fold_statement(self, statement: Stmt) -> Stmt:
        if isinstance(statement, LetStmt):
            return LetStmt(
                statement.name,
                statement.type_name,
                self.fold_expression(statement.initializer),
            )
        if isinstance(statement, PrintStmt):
            return PrintStmt(self.fold_expression(statement.expression))
        if isinstance(statement, ExprStmt):
            return ExprStmt(self.fold_expression(statement.expression))
        if isinstance(statement, BlockStmt):
            return BlockStmt(
                [self.fold_statement(item) for item in statement.statements]
            )
        if isinstance(statement, IfStmt):
            then_branch = self.fold_statement(statement.then_branch)
            else_branch = (
                self.fold_statement(statement.else_branch)
                if statement.else_branch is not None
                else None
            )
            assert isinstance(then_branch, BlockStmt)
            assert else_branch is None or isinstance(else_branch, BlockStmt)
            return IfStmt(
                self.fold_expression(statement.condition),
                then_branch,
                else_branch,
            )
        return statement

    def fold_expression(self, expression: Expr) -> Expr:
        if isinstance(expression, Unary):
            right = self.fold_expression(expression.right)
            if isinstance(right, Literal):
                value = (
                    -right.value
                    if expression.operator.kind == "MINUS"
                    else not right.value
                )
                return Literal(value, right.type_name)
            return Unary(expression.operator, right)
        if isinstance(expression, Binary):
            left = self.fold_expression(expression.left)
            right = self.fold_expression(expression.right)
            if isinstance(left, Literal) and isinstance(right, Literal):
                value = apply_operator(
                    expression.operator.kind,
                    left.value,
                    right.value,
                )
                type_name = "bool" if isinstance(value, bool) else left.type_name
                return Literal(value, type_name)
            return Binary(left, expression.operator, right)
        return expression


class TACGenerator:
    def __init__(self):
        self.instructions: list[str] = []
        self.temp_count = 0
        self.label_count = 0

    def generate(self, program: list[Stmt]) -> list[str]:
        for statement in program:
            self.emit_statement(statement)
        return self.instructions

    def emit_statement(self, statement: Stmt) -> None:
        if isinstance(statement, LetStmt):
            value = self.emit_expression(statement.initializer)
            self.instructions.append(f"{statement.name.lexeme} = {value}")
        elif isinstance(statement, PrintStmt):
            value = self.emit_expression(statement.expression)
            self.instructions.append(f"print {value}")
        elif isinstance(statement, ExprStmt):
            self.emit_expression(statement.expression)
        elif isinstance(statement, BlockStmt):
            for nested in statement.statements:
                self.emit_statement(nested)
        elif isinstance(statement, IfStmt):
            condition = self.emit_expression(statement.condition)
            else_label = self.new_label()
            end_label = self.new_label()
            self.instructions.append(f"if_false {condition} goto {else_label}")
            self.emit_statement(statement.then_branch)
            self.instructions.append(f"goto {end_label}")
            self.instructions.append(f"{else_label}:")
            if statement.else_branch is not None:
                self.emit_statement(statement.else_branch)
            self.instructions.append(f"{end_label}:")

    def emit_expression(self, expression: Expr) -> str:
        if isinstance(expression, Literal):
            return repr(expression.value)
        if isinstance(expression, Variable):
            return expression.name.lexeme
        if isinstance(expression, Unary):
            operand = self.emit_expression(expression.right)
            result = self.new_temp()
            self.instructions.append(
                f"{result} = {expression.operator.lexeme}{operand}"
            )
            return result
        if isinstance(expression, Binary):
            left = self.emit_expression(expression.left)
            right = self.emit_expression(expression.right)
            result = self.new_temp()
            self.instructions.append(
                f"{result} = {left} {expression.operator.lexeme} {right}"
            )
            return result
        raise CompileError("IR error: unsupported expression")

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"


def apply_operator(kind: str, left: Any, right: Any) -> Any:
    operations = {
        "PLUS": lambda: left + right,
        "MINUS": lambda: left - right,
        "STAR": lambda: left * right,
        "SLASH": lambda: left / right,
        "PERCENT": lambda: left % right,
        "LT": lambda: left < right,
        "LE": lambda: left <= right,
        "GT": lambda: left > right,
        "GE": lambda: left >= right,
        "EQEQ": lambda: left == right,
        "NE": lambda: left != right,
        "AND": lambda: left and right,
        "OR": lambda: left or right,
    }
    return operations[kind]()


class Interpreter:
    def __init__(self):
        self.scopes: list[dict[str, Any]] = [{}]
        self.output: list[str] = []

    def execute(self, program: list[Stmt]) -> list[str]:
        for statement in program:
            self.execute_statement(statement)
        return self.output

    def execute_statement(self, statement: Stmt) -> None:
        if isinstance(statement, LetStmt):
            value = self.evaluate(statement.initializer)
            self.scopes[-1][statement.name.lexeme] = value
        elif isinstance(statement, PrintStmt):
            self.output.append(str(self.evaluate(statement.expression)))
        elif isinstance(statement, ExprStmt):
            self.evaluate(statement.expression)
        elif isinstance(statement, BlockStmt):
            self.scopes.append({})
            for nested in statement.statements:
                self.execute_statement(nested)
            self.scopes.pop()
        elif isinstance(statement, IfStmt):
            if self.evaluate(statement.condition):
                self.execute_statement(statement.then_branch)
            elif statement.else_branch is not None:
                self.execute_statement(statement.else_branch)

    def evaluate(self, expression: Expr) -> Any:
        if isinstance(expression, Literal):
            return expression.value
        if isinstance(expression, Variable):
            for scope in reversed(self.scopes):
                if expression.name.lexeme in scope:
                    return scope[expression.name.lexeme]
            raise CompileError(
                f"Runtime error: undefined variable {expression.name.lexeme}"
            )
        if isinstance(expression, Unary):
            value = self.evaluate(expression.right)
            return -value if expression.operator.kind == "MINUS" else not value
        if isinstance(expression, Binary):
            left = self.evaluate(expression.left)
            right = self.evaluate(expression.right)
            return apply_operator(expression.operator.kind, left, right)
        raise CompileError("Runtime error: unsupported expression")


def ast_lines(program: list[Stmt]) -> list[str]:
    lines: list[str] = ["Program"]

    def walk(node: Any, prefix: str) -> None:
        label = type(node).__name__
        if isinstance(node, LetStmt):
            label += f" name={node.name.lexeme} type={node.type_name}"
        elif isinstance(node, Binary):
            label += f" operator={node.operator.lexeme}"
        elif isinstance(node, Unary):
            label += f" operator={node.operator.lexeme}"
        elif isinstance(node, Variable):
            label += f" name={node.name.lexeme}"
        elif isinstance(node, Literal):
            label += f" value={node.value!r} type={node.type_name}"
        lines.append(prefix + label)
        child_prefix = prefix + "  "
        if isinstance(node, LetStmt):
            walk(node.initializer, child_prefix)
        elif isinstance(node, (PrintStmt, ExprStmt)):
            walk(node.expression, child_prefix)
        elif isinstance(node, BlockStmt):
            for item in node.statements:
                walk(item, child_prefix)
        elif isinstance(node, IfStmt):
            walk(node.condition, child_prefix)
            walk(node.then_branch, child_prefix)
            if node.else_branch is not None:
                walk(node.else_branch, child_prefix)
        elif isinstance(node, Binary):
            walk(node.left, child_prefix)
            walk(node.right, child_prefix)
        elif isinstance(node, Unary):
            walk(node.right, child_prefix)

    for statement in program:
        walk(statement, "  ")
    return lines


@dataclass
class CompilationResult:
    tokens: list[Token]
    ast: list[str]
    symbols: dict[str, str]
    tac: list[str]
    optimized_tac: list[str]
    output: list[str]


def compile_source(source: str) -> CompilationResult:
    tokens = tokenize(source)
    program = Parser(tokens).parse()
    symbols = SemanticAnalyzer().analyze(program)
    tac = TACGenerator().generate(program)
    optimized_program = ConstantFolder().fold_program(program)
    SemanticAnalyzer().analyze(optimized_program)
    optimized_tac = TACGenerator().generate(optimized_program)
    output = Interpreter().execute(optimized_program)
    return CompilationResult(
        tokens=tokens,
        ast=ast_lines(program),
        symbols=symbols,
        tac=tac,
        optimized_tac=optimized_tac,
        output=output,
    )


def format_result(result: CompilationResult) -> str:
    lines = ["TOKENS"]
    for token in result.tokens:
        lines.append(
            f"{token.line}:{token.column} "
            f"{token.kind:<12} {token.lexeme!r}"
        )
    lines.extend(["", "AST", *result.ast, "", "SYMBOLS"])
    for name, type_name in result.symbols.items():
        lines.append(f"{name}: {type_name}")
    lines.extend(["", "TAC", *result.tac])
    lines.extend(["", "OPTIMIZED TAC", *result.optimized_tac])
    lines.extend(["", "OUTPUT", *result.output])
    return "\n".join(lines)

