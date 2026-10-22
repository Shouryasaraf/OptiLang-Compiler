"""Stack bytecode backend and bounded virtual machine for OptiLang."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .compiler import (
    AssignStmt, Binary, BlockStmt, Call, CompileError, Expr, ExprStmt,
    FunctionStmt, IfStmt, LetStmt, Literal, PrintStmt, ReturnStmt, Stmt,
    Unary, Variable, WhileStmt, apply_operator,
)


@dataclass(frozen=True)
class Instruction:
    opcode: str
    argument: Any = None
    location: str = ""

    def __str__(self) -> str:
        suffix = "" if self.argument is None else f" {self.argument!r}"
        return f"{self.opcode}{suffix}"


@dataclass
class BytecodeProgram:
    main: list[Instruction]
    functions: dict[str, tuple[list[str], list[Instruction]]]

    def lines(self) -> list[str]:
        output = ["main:"]
        output.extend(f"  {i:04d} {item}" + (f" @{item.location}" if item.location else "")
                      for i, item in enumerate(self.main))
        for name, (parameters, code) in self.functions.items():
            output.append(f"function {name}({', '.join(parameters)}):")
            output.extend(f"  {i:04d} {item}" + (f" @{item.location}" if item.location else "")
                          for i, item in enumerate(code))
        return output

    def cfg_lines(self) -> list[str]:
        result: list[str] = []
        for section, code in [("main", self.main), *(
            (f"function {name}", body) for name, (_, body) in self.functions.items()
        )]:
            leaders = {0}
            for index, item in enumerate(code):
                if item.opcode in {"JUMP", "JUMP_IF_FALSE", "JUMP_IF_TRUE"}:
                    leaders.add(item.argument)
                    if index + 1 < len(code):
                        leaders.add(index + 1)
            starts = sorted(index for index in leaders if index < len(code))
            blocks = [(start, starts[i + 1] if i + 1 < len(starts) else len(code))
                      for i, start in enumerate(starts)]
            result.append(f"{section}:")
            for start, end in blocks:
                last = code[end - 1]
                successors: list[int] = []
                if last.opcode == "JUMP":
                    successors = [last.argument]
                elif last.opcode in {"JUMP_IF_FALSE", "JUMP_IF_TRUE"}:
                    successors = [last.argument]
                    if end < len(code):
                        successors.insert(0, end)
                elif last.opcode not in {"RETURN", "HALT"} and end < len(code):
                    successors = [end]
                result.append(f"  B{start} [{start}..{end - 1}] -> " +
                              (", ".join(f"B{index}" for index in successors) or "exit"))
        return result


class Emitter:
    def __init__(self):
        self.code: list[Instruction] = []

    def add(self, opcode: str, argument: Any = None, location: str = "") -> int:
        self.code.append(Instruction(opcode, argument, location))
        return len(self.code) - 1

    def patch(self, index: int) -> None:
        old = self.code[index]
        self.code[index] = Instruction(old.opcode, len(self.code), old.location)


class BytecodeCompiler:
    def compile(self, program: list[Stmt]) -> BytecodeProgram:
        main = Emitter()
        functions: dict[str, tuple[list[str], list[Instruction]]] = {}
        for statement in program:
            if isinstance(statement, FunctionStmt):
                body = Emitter()
                self.statement(body, statement.body)
                functions[statement.name.lexeme] = (
                    [token.lexeme for token, _ in statement.parameters], body.code,
                )
            else:
                self.statement(main, statement)
        main.add("HALT")
        return BytecodeProgram(main.code, functions)

    def statement(self, out: Emitter, statement: Stmt) -> None:
        if isinstance(statement, LetStmt):
            self.expression(out, statement.initializer)
            out.add("DECLARE", statement.name.lexeme, self.location(statement.name))
        elif isinstance(statement, AssignStmt):
            self.expression(out, statement.value)
            out.add("STORE", statement.name.lexeme, self.location(statement.name))
        elif isinstance(statement, PrintStmt):
            self.expression(out, statement.expression)
            out.add("PRINT")
        elif isinstance(statement, ExprStmt):
            self.expression(out, statement.expression)
            out.add("POP")
        elif isinstance(statement, BlockStmt):
            out.add("ENTER_SCOPE")
            for nested in statement.statements:
                self.statement(out, nested)
            out.add("EXIT_SCOPE")
        elif isinstance(statement, IfStmt):
            self.expression(out, statement.condition)
            to_else = out.add("JUMP_IF_FALSE")
            self.statement(out, statement.then_branch)
            to_end = out.add("JUMP")
            out.patch(to_else)
            if statement.else_branch is not None:
                self.statement(out, statement.else_branch)
            out.patch(to_end)
        elif isinstance(statement, WhileStmt):
            start = len(out.code)
            self.expression(out, statement.condition)
            to_end = out.add("JUMP_IF_FALSE")
            self.statement(out, statement.body)
            out.add("JUMP", start)
            out.patch(to_end)
        elif isinstance(statement, ReturnStmt):
            self.expression(out, statement.value)
            out.add("RETURN", location=self.location(statement.keyword))
        else:
            raise CompileError("Bytecode error: unsupported statement")

    def expression(self, out: Emitter, expression: Expr) -> None:
        if isinstance(expression, Literal):
            out.add("PUSH", expression.value)
        elif isinstance(expression, Variable):
            out.add("LOAD", expression.name.lexeme, self.location(expression.name))
        elif isinstance(expression, Call):
            for argument in expression.arguments:
                self.expression(out, argument)
            out.add("CALL", (expression.name.lexeme, len(expression.arguments)), self.location(expression.name))
        elif isinstance(expression, Unary):
            self.expression(out, expression.right)
            out.add("UNARY", expression.operator.kind, self.location(expression.operator))
        elif isinstance(expression, Binary):
            kind = expression.operator.kind
            if kind in {"AND", "OR"}:
                self.expression(out, expression.left)
                out.add("DUP")
                short = out.add("JUMP_IF_FALSE" if kind == "AND" else "JUMP_IF_TRUE")
                out.add("POP")
                self.expression(out, expression.right)
                out.patch(short)
            else:
                self.expression(out, expression.left)
                self.expression(out, expression.right)
                out.add("BINARY", kind, self.location(expression.operator))
        else:
            raise CompileError("Bytecode error: unsupported expression")

    @staticmethod
    def location(token: Any) -> str:
        return f"{token.line}:{token.column}"


class VirtualMachine:
    def __init__(self, program: BytecodeProgram, step_limit: int = 100_000,
                 call_limit: int = 100, trace_limit: int = 80):
        self.program = program
        self.step_limit = step_limit
        self.call_limit = call_limit
        self.trace_limit = trace_limit
        self.steps = 0
        self.trace: list[str] = []
        self.output: list[str] = []
        self.globals: dict[str, Any] = {}

    def execute(self) -> list[str]:
        self.run(self.program.main, [self.globals], 0)
        return self.output

    def run(self, code: list[Instruction], scopes: list[dict[str, Any]], depth: int) -> Any:
        stack: list[Any] = []
        pc = 0
        while pc < len(code):
            self.steps += 1
            if self.steps > self.step_limit:
                raise CompileError("Runtime error: instruction limit exceeded")
            instruction = code[pc]
            if len(self.trace) < self.trace_limit:
                self.trace.append(f"depth={depth} pc={pc:04d} {instruction}")
            pc += 1
            op, arg = instruction.opcode, instruction.argument
            if op == "PUSH":
                stack.append(arg)
            elif op == "LOAD":
                for scope in reversed(scopes):
                    if arg in scope:
                        stack.append(scope[arg])
                        break
                else:
                    raise CompileError(f"Runtime error: undefined variable {arg}")
            elif op == "DECLARE":
                scopes[-1][arg] = stack.pop()
            elif op == "STORE":
                value = stack.pop()
                for scope in reversed(scopes):
                    if arg in scope:
                        scope[arg] = value
                        break
                else:
                    raise CompileError(f"Runtime error: undefined variable {arg}")
            elif op == "ENTER_SCOPE":
                scopes.append({})
            elif op == "EXIT_SCOPE":
                scopes.pop()
            elif op == "UNARY":
                value = stack.pop()
                stack.append(-value if arg == "MINUS" else not value)
            elif op == "BINARY":
                right, left = stack.pop(), stack.pop()
                stack.append(apply_operator(arg, left, right))
            elif op == "DUP":
                stack.append(stack[-1])
            elif op == "POP":
                stack.pop()
            elif op == "JUMP":
                pc = arg
            elif op == "JUMP_IF_FALSE":
                if not stack.pop():
                    pc = arg
            elif op == "JUMP_IF_TRUE":
                if stack.pop():
                    pc = arg
            elif op == "PRINT":
                self.output.append(str(stack.pop()))
            elif op == "CALL":
                name, count = arg
                if depth >= self.call_limit:
                    raise CompileError("Runtime error: call depth limit exceeded")
                if name not in self.program.functions:
                    raise CompileError(f"Runtime error: undefined function {name}")
                parameters, function_code = self.program.functions[name]
                arguments = [stack.pop() for _ in range(count)][::-1]
                function_scopes = [self.globals, dict(zip(parameters, arguments))]
                stack.append(self.run(function_code, function_scopes, depth + 1))
            elif op == "RETURN":
                return stack.pop()
            elif op == "HALT":
                return None
            else:
                raise CompileError(f"Bytecode error: unknown opcode {op}")
        raise CompileError("Runtime error: function finished without returning")
