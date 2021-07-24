import sys

PY3_9 = sys.version_info >= (3, 9)


if not PY3_9:
    import ast

    import astor.code_gen

    ast.unparse = astor.code_gun.to_source
