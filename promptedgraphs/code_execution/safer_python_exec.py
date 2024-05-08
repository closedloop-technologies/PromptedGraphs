import ast
from logging import getLogger

import black

logger = getLogger(__name__)


def is_potentially_unsafe(node):  # sourcery skip: low-code-quality
    if isinstance(node, ast.Call):
        # Check for dangerous built-in functions
        unsafe_functions = {"eval", "exec", "open", "os.system"}
        if isinstance(node.func, ast.Name) and node.func.id in unsafe_functions:
            return True
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        # Disallow dynamic imports
        allowed_imports = {"json", "math", "__future__", "pydantic", "promptedgraphs"}
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in allowed_imports:
                    return True
        elif isinstance(node, ast.ImportFrom):
            return node.module not in allowed_imports
    elif isinstance(node, ast.FunctionDef):
        # Disallow functions that use exec
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and (
                    isinstance(stmt.value.func, ast.Name)
                    and stmt.value.func.id == "exec"
                )
            ):
                return True
    elif isinstance(node, ast.Assign):
        # Disallow assignments of potentially unsafe values
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {
                "__builtins__",
                "eval",
                "exec",
                "open",
            }:
                return True
    elif isinstance(node, ast.Attribute):
        # Disallow dynamic attribute access
        if isinstance(node.value, ast.Name) and node.value.id == "__import__":
            return True
    elif isinstance(node, ast.Expr):
        # Disallow potentially unsafe expressions
        if isinstance(node.value, ast.Call) and (
            isinstance(node.value.func, ast.Name) and node.value.func.id == "eval"
        ):
            return True
    return False


def format_code(code):
    return black.format_str(code, mode=black.FileMode())


def safer_exec(model_code):
    logger.warning("Executing generated data model code from datamodel_code_generator")
    exec_variables = {}

    # Parse the code and generate the AST
    parsed_code = ast.parse(model_code, filename="<string>", mode="exec")

    # Filter out potentially unsafe constructs
    safe_code_body = [
        node for node in parsed_code.body if not is_potentially_unsafe(node)
    ]
    safe_code_ast = ast.Module(body=safe_code_body, type_ignores=[])

    # Compile the parsed code into a safe code object
    safe_code = compile(safe_code_ast, filename="data_model.py", mode="exec")

    # Execute the safe code within a restricted environment
    exec(safe_code, exec_variables)

    return exec_variables
