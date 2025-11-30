import re

# Tokenizer

def tokenize(expr):
    token_specification = [
        ("NUMBER",   r"\d+(\.\d*)?"),
        ("ID",       r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("OP",       r"[+\-*/^()]"),
        ("SKIP",     r"\s+"),
        ("MISMATCH", r"."),
    ]
    tok_regex = "|".join(f"(?P<{name}>{regex})" for name, regex in token_specification)
    for mo in re.finditer(tok_regex, expr):
        kind = mo.lastgroup
        value = mo.group()
        if kind == "NUMBER":
            yield ("const", float(value) if '.' in value else int(value))
        elif kind == "ID":
            yield ("id", value)
        elif kind == "OP":
            yield ("op", value)
        elif kind == "SKIP":
            continue
        else:
            raise SyntaxError(f"Unexpected character: {value}")

# Parser

def parse(tokens):
    tokens = list(tokens)
    i = 0
    current_token = None
    current_token_type = None

    def advance():
        nonlocal i, current_token, current_token_type
        if i < len(tokens):
            current_token_type, current_token = tokens[i]
            i += 1
        else:
            current_token_type, current_token = None, None

    def expect(expected_type, expected_value=None):
        if current_token_type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {current_token_type}")
        if expected_value is not None and current_token != expected_value:
            raise SyntaxError(f"Expected {expected_value}, got {current_token}")
        advance()

    def parse_expression():
        node = parse_term()
        while current_token in ('+', '-'):
            op = current_token
            advance()
            right = parse_term()
            # node = ("add" if op == '+' else "add", node, ("multiply", ("const", -1), right))
            if op =="+":
                node = ("add",node,right)
            if op == "-":
                node = ("add",node,("multiply", ("const",-1,right)))
        return node

    def parse_term():
        node = parse_factor()
        while current_token in ('*', '/'):
            op = current_token
            advance()
            right = parse_factor()
            node = ("multiply" if op == '*' else "divide", node, right)
        return node

    def parse_factor():
        node = parse_atom()
        while current_token == '^':
            advance()
            exponent = parse_atom()
            node = ("exponent", node, exponent)
        return node

    def parse_atom():
        if current_token_type == "const":
            value = current_token
            advance()
            return ("const", value)
        elif current_token_type == "id":
            id_name = current_token
            advance()
            if current_token == '(':  # function call
                advance()
                arg = parse_expression()
                expect("op", ")")
                return (id_name, arg)
            else:  # variable
                return ("var", id_name)
        elif current_token == '(':
            advance()
            node = parse_expression()
            expect("op", ")")
            return node
        else:
            raise SyntaxError(f"Unexpected token: {current_token}")

    advance()
    return parse_expression()




function_derivatives = {
    "sin": lambda u, du: ("multiply", ("cos", u), du),
    "cos": lambda u, du: ("multiply", ("multiply", ("const", -1), ("sin", u)), du),
    "exp": lambda u, du: ("multiply", ("exp", u), du),
    "ln":  lambda u, du: ("multiply", ("divide", ("const", 1), u), du),
    "tan": lambda u, du: ("multiply", ("exponent", ("sec", u), ("const", 2)), du),
    "sec": lambda u, du: ("multiply", ("multiply", ("tan", u), ("sec", u)), du),
    "cosh": lambda u, du: ("multiply", ("sinh", u), du),
    "sinh": lambda u, du: ("multiply", ("cosh", u), du),
    "cot": lambda u, du: ("multiply", ("multipponent", ("add", ("const",1), ("multiply", ("const",-1), ("exponent",u, ("const",2)))), ("const", -1/2)), du),
    "arccos": lambda u, du: ("multiply", ("ly", ("const", -1), ("exponent", ("csc", u), ("const", 2))), du),
    "csc": lambda u, du: ("multiply", ("multiply", ("const", -1), ("multiply", ("cot", u), ("csc", u))), du),
    "arcsin": lambda u, du: ("multiply", ("exmultiply", ("const",-1), ("exponent", ("add", ("const",1), ("multiply", ("const",-1), ("exponent",u, ("const",2)))), ("const", -1/2))), du),
    "arctan": lambda u, du: ("multiply", ("exponent", ("add", ("const",1), ("exponent", u, ("const", 2))), ("const", -1)), du),
}


def diffy(expr):
    if expr[0] == "const":
        return ("const", 0)
    elif expr[0] == "var":
        return ("const", 1)
    elif expr[0] == "add":
        return ("add", diffy(expr[1]), diffy(expr[2]))
    elif expr[0] == "multiply":
        f, g = expr[1], expr[2]

        # Case: constant * expression
        if f[0] == "const":
            if f[1] == 0:
                return ("const", 0)
            return ("multiply", f, diffy(g))
        elif g[0] == "const":
            if g[1] == 0:
                return ("const", 0)
            return ("multiply", g, diffy(f))

        # General product rule
        return ("add",
                ("multiply", diffy(f), g),
                ("multiply", f, diffy(g)))


    elif expr[0] == "exponent":

        base = expr[1]

        power = expr[2]

        if power[0] == "const" and base[0]=="var":

            n = power[1]

            return ("multiply",

                    ("multiply", ("const", n),

                     ("exponent", base, ("const", n - 1))),

                    diffy(base))
        else:
            u = base
            v = power
            du = diffy(u)
            dv = diffy(v)
            return ("multiply",
                    ("exponent",u,v),
                    ("add",
                     ("multiply", ("ln",u),dv),
                     ("multiply",("divide",v,u),du))
                    )
    elif expr[0] in function_derivatives:
        u = expr[1]
        du = diffy(u)
        return function_derivatives[expr[0]](u, du)

    return ("NotSupported", expr)
def function_displayer(expression):
    if expression[0] == "const":
        return str(expression[1])
    if expression[0] == "var":
        return str(expression[1])
    elif expression[0] in function_derivatives:
        func = expression[0]
        input = function_displayer(expression[1])
        return f"{func}({input})"
    elif expression[0] == "add":
        left = function_displayer(expression[1])
        right = function_displayer(expression[2])
        return f"({left} + {right})"
    elif expression[0] == "multiply":
        left = function_displayer(expression[1])
        right = function_displayer(expression[2])
        return f"({left} * {right})"
    elif expression[0] == "divide":
        left = function_displayer(expression[1])
        right = function_displayer(expression[2])
        return f"({left} / {right})"
    elif expression[0] == "exponent":
        base = function_displayer(expression[1])
        exponent = function_displayer(expression[2])
        return f"({base}^{exponent})"
    else:
        return("Not supported")

def validate_tree(expr):
    if not isinstance(expr, tuple):
        print("Not a tuple:", expr)
        return False
    op = expr[0]

    if op in ["const", "var"]:
        return len(expr) == 2
    elif op in ["add", "multiply", "divide", "exponent"]:
        return len(expr) == 3 and validate_tree(expr[1]) and validate_tree(expr[2])
    elif op in function_derivatives:  # e.g., sin, cos, tan
        return len(expr) == 2 and validate_tree(expr[1])
    else:
        print("Unknown operator:", op)
        return False




print("Derivative Calculator!")
print("If you would like to see what functions are supported, type 'show me supported functions' '")
expr = input("Write the expression you want to differentiate: ")
question = 0
if expr == "show me supported functions":
    question = 1
if question == 1:
    print("The supported functions are:")
    print("Powers of x, Rationals, Composite, Exponentials of base e, logarithms of base e,\n trigonometric functions, hyperbolic functions, inverse trigonometric functions")
    print("Note: Division is not yet implemented. Use a*(b)^-1 in place of a/b if need be.")
    expr = input("Write the expression you want to differentiate: ")




tokens = tokenize(expr)
tree = parse(tokens)
output = diffy(tree)
pretty_output = function_displayer(output)
print(tree)
print("The derivative is: ")

print(pretty_output)
