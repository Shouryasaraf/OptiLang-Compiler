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
    "while": "WHILE",
    "fn": "FN",
    "return": "RETURN",
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
    r"(?P<COLON>:)|(?P<SEMICOLON>;)|(?P<COMMA>,)|"
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
        if kind == "NUMBER":
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
class Call(Expr):
    name: Token
    arguments: list[Expr]


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
class AssignStmt(Stmt):
    name: Token
    value: Expr


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


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: BlockStmt


@dataclass
class ReturnStmt(Stmt):
    keyword: Token
    value: Expr


@dataclass
class FunctionStmt(Stmt):
    name: Token
    parameters: list[tuple[Token, str]]
    return_type: str
    body: BlockStmt


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
        if self.match("FN"):
            return self.function_statement()
        if self.match("LET"):
            return self.let_statement()
        if self.match("RETURN"):
            keyword = self.previous()
            value = self.expression()
            self.consume("SEMICOLON", "Expected ';' after return value")
            return ReturnStmt(keyword, value)
        if self.match("PRINT"):
            return self.print_statement()
        if self.match("IF"):
            return self.if_statement()
        if self.match("WHILE"):
            self.consume("LPAREN", "Expected '(' after while")
            condition = self.expression()
            self.consume("RPAREN", "Expected ')' after while condition")
            self.consume("LBRACE", "Expected '{' before while body")
            return WhileStmt(condition, BlockStmt(self.block()))
        if self.match("LBRACE"):
            return BlockStmt(self.block())
        if self.check("IDENTIFIER") and self.tokens[self.current + 1].kind == "ASSIGN":
            name = self.advance()
            self.advance()
            value = self.expression()
            self.consume("SEMICOLON", "Expected ';' after assignment")
            return AssignStmt(name, value)
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

    def function_statement(self) -> FunctionStmt:
        name = self.consume("IDENTIFIER", "Expected function name")
        self.consume("LPAREN", "Expected '(' after function name")
        parameters: list[tuple[Token, str]] = []
        if not self.check("RPAREN"):
            while True:
                parameter = self.consume("IDENTIFIER", "Expected parameter name")
                self.consume("COLON", "Expected ':' after parameter name")
                type_name = self.consume("TYPE", "Expected parameter type").lexeme
                parameters.append((parameter, type_name))
                if not self.match("COMMA"):
                    break
        self.consume("RPAREN", "Expected ')' after parameters")
        self.consume("COLON", "Expected ':' before return type")
        return_type = self.consume("TYPE", "Expected return type").lexeme
        self.consume("LBRACE", "Expected '{' before function body")
        return FunctionStmt(name, parameters, return_type, BlockStmt(self.block()))

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
            name = self.previous()
            if self.match("LPAREN"):
                arguments: list[Expr] = []
                if not self.check("RPAREN"):
                    while True:
                        arguments.append(self.expression())
                        if not self.match("COMMA"):
                            break
                self.consume("RPAREN", "Expected ')' after arguments")
                return Call(name, arguments)
            return Variable(name)
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
        self.functions: dict[str, tuple[list[str], str]] = {}
        self.return_type: str | None = None

    def analyze(self, program: list[Stmt]) -> dict[str, str]:
        for statement in program:
            if isinstance(statement, FunctionStmt):
                name = statement.name.lexeme
                if name in self.functions:
                    self.error(statement.name, "function already declared")
                self.functions[name] = (
                    [type_name for _, type_name in statement.parameters],
                    statement.return_type,
                )
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
        elif isinstance(statement, AssignStmt):
            target_type = self.resolve(statement.name)
            value_type = self.infer(statement.value)
            if value_type != target_type:
                self.error(statement.name, f"cannot assign {value_type} to {target_type}")
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
        elif isinstance(statement, WhileStmt):
            if self.infer(statement.condition) != "bool":
                raise CompileError("Semantic error: while condition must be bool")
            self.check_statement(statement.body)
        elif isinstance(statement, ReturnStmt):
            if self.return_type is None:
                self.error(statement.keyword, "return outside function")
            value_type = self.infer(statement.value)
            if value_type != self.return_type:
                self.error(statement.keyword, f"cannot return {value_type} from {self.return_type} function")
        elif isinstance(statement, FunctionStmt):
            if len(self.scopes) != 1 or self.return_type is not None:
                self.error(statement.name, "functions must be declared at top level")
            self.scopes.append({})
            self.return_type = statement.return_type
            for token, type_name in statement.parameters:
                if token.lexeme in self.scopes[-1]:
                    self.error(token, "duplicate parameter")
                self.scopes[-1][token.lexeme] = type_name
            self.check_statement(statement.body)
            self.scopes.pop()
            self.return_type = None
            if not self.always_returns(statement.body):
                self.error(statement.name, "function may finish without returning")

    @staticmethod
    def always_returns(statement: Stmt) -> bool:
        if isinstance(statement, ReturnStmt):
            return True
        if isinstance(statement, BlockStmt):
            return any(SemanticAnalyzer.always_returns(item) for item in statement.statements)
        if isinstance(statement, IfStmt):
            return statement.else_branch is not None and (
                SemanticAnalyzer.always_returns(statement.then_branch)
                and SemanticAnalyzer.always_returns(statement.else_branch)
            )
        return False

    def infer(self, expression: Expr) -> str:
        if isinstance(expression, Literal):
            return expression.type_name
        if isinstance(expression, Variable):
            return self.resolve(expression.name)
        if isinstance(expression, Call):
            signature = self.functions.get(expression.name.lexeme)
            if signature is None:
                self.error(expression.name, f"undefined function {expression.name.lexeme!r}")
            parameters, result_type = signature
            if len(parameters) != len(expression.arguments):
                self.error(expression.name, "wrong number of arguments")
            for argument, expected in zip(expression.arguments, parameters):
                actual = self.infer(argument)
                if actual != expected:
                    self.error(expression.name, f"expected {expected} argument, got {actual}")
            return result_type
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
    def __init__(self):
        self.changes: list[str] = []

    def fold_program(self, program: list[Stmt]) -> list[Stmt]:
        return [self.fold_statement(statement) for statement in program]

    def fold_statement(self, statement: Stmt) -> Stmt:
        if isinstance(statement, LetStmt):
            return LetStmt(
                statement.name,
                statement.type_name,
                self.fold_expression(statement.initializer),
            )
        if isinstance(statement, AssignStmt):
            return AssignStmt(statement.name, self.fold_expression(statement.value))
        if isinstance(statement, PrintStmt):
            return PrintStmt(self.fold_expression(statement.expression))
        if isinstance(statement, ExprStmt):
            return ExprStmt(self.fold_expression(statement.expression))
        if isinstance(statement, BlockStmt):
            retained: list[Stmt] = []
            for item in statement.statements:
                retained.append(self.fold_statement(item))
                if isinstance(item, ReturnStmt):
                    if len(retained) < len(statement.statements):
                        self.changes.append("unreachable-code elimination: statements after return removed")
                    break
            return BlockStmt(retained)
        if isinstance(statement, IfStmt):
            then_branch = self.fold_statement(statement.then_branch)
            else_branch = (
                self.fold_statement(statement.else_branch)
                if statement.else_branch is not None
                else None
            )
            assert isinstance(then_branch, BlockStmt)
            assert else_branch is None or isinstance(else_branch, BlockStmt)
            condition = self.fold_expression(statement.condition)
            if isinstance(condition, Literal):
                self.changes.append("unreachable-code elimination: constant if condition selects one branch")
                return then_branch if condition.value else (else_branch or BlockStmt([]))
            return IfStmt(
                condition,
                then_branch,
                else_branch,
            )
        if isinstance(statement, WhileStmt):
            condition = self.fold_expression(statement.condition)
            if isinstance(condition, Literal) and condition.value is False:
                self.changes.append("unreachable-code elimination: while(false) body removed")
                return BlockStmt([])
            return WhileStmt(condition, self.fold_statement(statement.body))
        if isinstance(statement, ReturnStmt):
            return ReturnStmt(statement.keyword, self.fold_expression(statement.value))
        if isinstance(statement, FunctionStmt):
            return FunctionStmt(statement.name, statement.parameters, statement.return_type,
                                self.fold_statement(statement.body))
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
                self.changes.append(f"{expression.operator.line}:{expression.operator.column} constant folding: {expression.operator.lexeme}{right.value!r} -> {value!r}; literal operand")
                return Literal(value, "bool" if isinstance(value, bool) else right.type_name)
            return Unary(expression.operator, right)
        if isinstance(expression, Binary):
            left = self.fold_expression(expression.left)
            if isinstance(left, Literal) and expression.operator.kind in {"AND", "OR"}:
                if (expression.operator.kind == "AND" and not left.value) or (
                    expression.operator.kind == "OR" and left.value
                ):
                    self.changes.append(f"{expression.operator.line}:{expression.operator.column} short circuit: right operand is not evaluated")
                    return left
            right = self.fold_expression(expression.right)
            if isinstance(left, Literal) and isinstance(right, Literal):
                try:
                    value = apply_operator(expression.operator.kind, left.value, right.value)
                except (CompileError, ZeroDivisionError, OverflowError):
                    return Binary(left, expression.operator, right)
                type_name = "bool" if isinstance(value, bool) else left.type_name
                self.changes.append(f"{expression.operator.line}:{expression.operator.column} constant folding: {left.value!r} {expression.operator.lexeme} {right.value!r} -> {value!r}; literal operands")
                return Literal(value, type_name)
            if expression.operator.kind in {"PLUS", "MINUS"} and isinstance(right, Literal) and right.value == 0 and right.type_name in {"int", "float"}:
                self.changes.append(f"{expression.operator.line}:{expression.operator.column} algebraic simplification: {expression.operator.lexeme} 0 removed; numeric operand")
                return left
            if expression.operator.kind == "PLUS" and isinstance(left, Literal) and left.value == 0 and left.type_name in {"int", "float"}:
                self.changes.append(f"{expression.operator.line}:{expression.operator.column} algebraic simplification: 0 + removed; numeric operand")
                return right
            if expression.operator.kind in {"STAR", "SLASH"} and isinstance(right, Literal) and right.value == 1 and right.type_name in {"int", "float"}:
                self.changes.append(f"{expression.operator.line}:{expression.operator.column} algebraic simplification: {expression.operator.lexeme} 1 removed; numeric operand")
                return left
            return Binary(left, expression.operator, right)
        if isinstance(expression, Call):
            return Call(expression.name, [self.fold_expression(arg) for arg in expression.arguments])
        return expression


class TACGenerator:
    def __init__(self):
        self.instructions: list[str] = []
        self.temp_count = 0
        self.label_count = 0

    def generate(self, program: list[Stmt]) -> list[str]:
        for statement in program:
            if not isinstance(statement, FunctionStmt):
                self.emit_statement(statement)
        for statement in program:
            if isinstance(statement, FunctionStmt):
                self.emit_statement(statement)
        return self.instructions

    def emit_statement(self, statement: Stmt) -> None:
        if isinstance(statement, LetStmt):
            value = self.emit_expression(statement.initializer)
            self.instructions.append(f"{statement.name.lexeme} = {value}")
        elif isinstance(statement, AssignStmt):
            self.instructions.append(f"{statement.name.lexeme} = {self.emit_expression(statement.value)}")
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
        elif isinstance(statement, WhileStmt):
            start_label, end_label = self.new_label(), self.new_label()
            self.instructions.append(f"{start_label}:")
            condition = self.emit_expression(statement.condition)
            self.instructions.append(f"if_false {condition} goto {end_label}")
            self.emit_statement(statement.body)
            self.instructions.append(f"goto {start_label}")
            self.instructions.append(f"{end_label}:")
        elif isinstance(statement, ReturnStmt):
            self.instructions.append(f"return {self.emit_expression(statement.value)}")
        elif isinstance(statement, FunctionStmt):
            self.instructions.append(f"function {statement.name.lexeme}:")
            self.emit_statement(statement.body)

    def emit_expression(self, expression: Expr) -> str:
        if isinstance(expression, Literal):
            return repr(expression.value)
        if isinstance(expression, Variable):
            return expression.name.lexeme
        if isinstance(expression, Call):
            arguments = [self.emit_expression(arg) for arg in expression.arguments]
            result = self.new_temp()
            self.instructions.append(f"{result} = call {expression.name.lexeme}({', '.join(arguments)})")
            return result
        if isinstance(expression, Unary):
            operand = self.emit_expression(expression.right)
            result = self.new_temp()
            self.instructions.append(
                f"{result} = {expression.operator.lexeme}{operand}"
            )
            return result
        if isinstance(expression, Binary):
            left = self.emit_expression(expression.left)
            if expression.operator.kind in {"AND", "OR"}:
                result = self.new_temp()
                self.instructions.append(f"{result} = {left}")
                end = self.new_label()
                if expression.operator.kind == "AND":
                    self.instructions.append(f"if_false {left} goto {end}")
                else:
                    right_label = self.new_label()
                    self.instructions.append(f"if_false {left} goto {right_label}")
                    self.instructions.append(f"goto {end}")
                    self.instructions.append(f"{right_label}:")
                right = self.emit_expression(expression.right)
                self.instructions.append(f"{result} = {right}")
                self.instructions.append(f"{end}:")
                return result
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
    if kind in {"SLASH", "PERCENT"} and right == 0:
        raise CompileError("Runtime error: division by zero")
    if kind == "SLASH" and type(left) is int and type(right) is int:
        quotient = abs(left) // abs(right)
        return -quotient if (left < 0) != (right < 0) else quotient
    if kind == "PERCENT" and type(left) is int and type(right) is int:
        quotient = apply_operator("SLASH", left, right)
        return left - quotient * right
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
    def __init__(self, step_limit: int = 100_000, call_limit: int = 100):
        self.scopes: list[dict[str, Any]] = [{}]
        self.output: list[str] = []
        self.functions: dict[str, FunctionStmt] = {}
        self.step_limit = step_limit
        self.steps = 0
        self.call_limit = call_limit
        self.call_depth = 0

    def execute(self, program: list[Stmt]) -> list[str]:
        self.functions = {stmt.name.lexeme: stmt for stmt in program if isinstance(stmt, FunctionStmt)}
        for statement in program:
            self.execute_statement(statement)
        return self.output

    def execute_statement(self, statement: Stmt) -> None:
        self.steps += 1
        if self.steps > self.step_limit:
            raise CompileError("Runtime error: instruction limit exceeded")
        if isinstance(statement, LetStmt):
            value = self.evaluate(statement.initializer)
            self.scopes[-1][statement.name.lexeme] = value
        elif isinstance(statement, AssignStmt):
            value = self.evaluate(statement.value)
            for scope in reversed(self.scopes):
                if statement.name.lexeme in scope:
                    scope[statement.name.lexeme] = value
                    break
            else:
                raise CompileError(f"Runtime error: undefined variable {statement.name.lexeme}")
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
        elif isinstance(statement, WhileStmt):
            while self.evaluate(statement.condition):
                self.execute_statement(statement.body)
        elif isinstance(statement, ReturnStmt):
            raise ReturnValue(self.evaluate(statement.value))

    def call(self, expression: Call) -> Any:
        function = self.functions[expression.name.lexeme]
        arguments = [self.evaluate(arg) for arg in expression.arguments]
        if self.call_depth >= self.call_limit:
            raise CompileError("Runtime error: call depth limit exceeded")
        previous_scopes = self.scopes
        self.scopes = [previous_scopes[0], dict(zip((name.lexeme for name, _ in function.parameters), arguments))]
        self.call_depth += 1
        try:
            try:
                self.execute_statement(function.body)
            except ReturnValue as result:
                return result.value
            raise CompileError(f"Runtime error: function {function.name.lexeme} did not return")
        finally:
            self.call_depth -= 1
            self.scopes = previous_scopes

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
        if isinstance(expression, Call):
            return self.call(expression)
        if isinstance(expression, Unary):
            value = self.evaluate(expression.right)
            return -value if expression.operator.kind == "MINUS" else not value
        if isinstance(expression, Binary):
            left = self.evaluate(expression.left)
            if expression.operator.kind == "AND" and not left:
                return False
            if expression.operator.kind == "OR" and left:
                return True
            right = self.evaluate(expression.right)
            return apply_operator(expression.operator.kind, left, right)
        raise CompileError("Runtime error: unsupported expression")


class ReturnValue(Exception):
    def __init__(self, value: Any):
        self.value = value


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
        elif isinstance(node, Call):
            label += f" name={node.name.lexeme}"
        elif isinstance(node, AssignStmt):
            label += f" name={node.name.lexeme}"
        elif isinstance(node, FunctionStmt):
            label += f" name={node.name.lexeme} returns={node.return_type}"
        elif isinstance(node, Literal):
            label += f" value={node.value!r} type={node.type_name}"
        lines.append(prefix + label)
        child_prefix = prefix + "  "
        if isinstance(node, LetStmt):
            walk(node.initializer, child_prefix)
        elif isinstance(node, AssignStmt):
            walk(node.value, child_prefix)
        elif isinstance(node, ReturnStmt):
            walk(node.value, child_prefix)
        elif isinstance(node, FunctionStmt):
            walk(node.body, child_prefix)
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
        elif isinstance(node, WhileStmt):
            walk(node.condition, child_prefix)
            walk(node.body, child_prefix)
        elif isinstance(node, Call):
            for argument in node.arguments:
                walk(argument, child_prefix)
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
    cfg: list[str]
    bytecode_cfg: list[str]
    bytecode: list[str]
    vm_trace: list[str]
    optimizations: list[str]
    validated: bool


def compile_source(source: str) -> CompilationResult:
    from .bytecode import BytecodeCompiler, VirtualMachine
    from .cfg import cfg_lines

    tokens = tokenize(source)
    program = Parser(tokens).parse()
    symbols = SemanticAnalyzer().analyze(program)
    tac = TACGenerator().generate(program)
    optimizer = ConstantFolder()
    optimized_program = optimizer.fold_program(program)
    SemanticAnalyzer().analyze(optimized_program)
    optimized_tac = TACGenerator().generate(optimized_program)
    reference = Interpreter()
    reference_output = reference.execute(program)
    optimized_reference = Interpreter()
    optimized_output = optimized_reference.execute(optimized_program)
    bytecode_program = BytecodeCompiler().compile(optimized_program)
    vm = VirtualMachine(bytecode_program)
    output = vm.execute()
    if (reference_output != optimized_output or output != reference_output
            or reference.scopes[0] != optimized_reference.scopes[0]
            or vm.globals != reference.scopes[0]):
        raise CompileError("Validation error: original, optimized and VM states disagree")
    return CompilationResult(
        tokens=tokens,
        ast=ast_lines(program),
        symbols=symbols,
        tac=tac,
        optimized_tac=optimized_tac,
        output=output,
        cfg=cfg_lines(optimized_tac),
        bytecode_cfg=bytecode_program.cfg_lines(),
        bytecode=bytecode_program.lines(),
        vm_trace=vm.trace,
        optimizations=optimizer.changes,
        validated=True,
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
    lines.extend(["", "CONTROL-FLOW GRAPH (TAC)", *result.cfg])
    lines.extend(["", "CONTROL-FLOW GRAPH (BYTECODE)", *result.bytecode_cfg])
    lines.extend(["", "OPTIMIZATION RECORD", *(result.optimizations or ["No rewrite applied"])])
    lines.extend(["", "BYTECODE", *result.bytecode])
    lines.extend(["", "VM TRACE", *result.vm_trace])
    lines.extend(["", "VALIDATION", "Original AST, optimized AST and VM outputs and global state agree"])
    lines.extend(["", "OUTPUT", *result.output])
    return "\n".join(lines)

