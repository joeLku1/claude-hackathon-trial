"""Small, bounded spreadsheet evaluator. No eval, code execution or external IO."""
import ast
import math
import operator
import re

CELL = re.compile(r'([A-Z]+)([1-9][0-9]*)$')
RANGE = re.compile(r'\b([A-Z]+[1-9][0-9]*):([A-Z]+[1-9][0-9]*)\b')
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Mod: operator.mod}


class FormulaError(ValueError):
    pass


def address(row, col):
    letters = ''
    col += 1
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return f'{letters}{row + 1}'


def coordinates(ref):
    match = CELL.fullmatch(ref)
    if not match:
        raise FormulaError('Invalid cell reference')
    col = 0
    for letter in match[1]:
        col = col * 26 + ord(letter) - 64
    return int(match[2]) - 1, col - 1


class Sheet:
    def __init__(self, cells):
        self.cells = cells
        self.cache = {}
        self.active = set()

    def cell(self, row, col):
        key = (row, col)
        if key in self.cache:
            return self.cache[key]
        if not (0 <= row < len(self.cells) and 0 <= col < len(self.cells[0])):
            raise FormulaError('Reference outside the data table')
        if key in self.active:
            raise FormulaError('Circular reference')
        if len(self.active) >= 64:
            raise FormulaError('Formula dependency chain is too deep')
        raw = str(self.cells[row][col]).strip()
        if not raw.startswith('='):
            try:
                result = self.finite(float(raw)) if raw else 0.0
            except ValueError:
                result = raw
            self.cache[key] = result
            return result
        self.active.add(key)
        try:
            expression = RANGE.sub(r'RANGE("\1","\2")', raw[1:].upper())
            node = ast.parse(expression, mode='eval')
            if sum(1 for _ in ast.walk(node)) > 160:
                raise FormulaError('Formula is too complex')
            result = self.finite(self.evaluate(node.body))
            self.cache[key] = result
            return result
        except (SyntaxError, TypeError, ZeroDivisionError, OverflowError, RecursionError) as exc:
            raise FormulaError('Invalid formula or division by zero') from exc
        finally:
            self.active.remove(key)

    @staticmethod
    def finite(value):
        if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e15:
            raise FormulaError('Expected a finite number between -1e15 and 1e15')
        return float(value)

    def evaluate(self, node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return self.finite(node.value)
        if isinstance(node, ast.Name) and CELL.fullmatch(node.id):
            return self.finite(self.cell(*coordinates(node.id)))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return self.finite((-1 if isinstance(node.op, ast.USub) else 1) * self.evaluate(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return self.finite(OPS[type(node.op)](self.evaluate(node.left), self.evaluate(node.right)))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            name = node.func.id
            if name == 'RANGE':
                if len(node.args) != 2 or not all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in node.args):
                    raise FormulaError('Invalid range')
                r1, c1 = coordinates(node.args[0].value)
                r2, c2 = coordinates(node.args[1].value)
                if r2 < r1 or c2 < c1 or r2 >= len(self.cells) or c2 >= len(self.cells[0]):
                    raise FormulaError('Invalid range boundaries')
                values = [self.cell(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]
                return [x for x in values if isinstance(x, (int, float))]
            values = []
            for arg in node.args:
                value = self.evaluate(arg)
                values.extend(value if isinstance(value, list) else [value])
            if name == 'SUM':
                return self.finite(sum(values))
            if name == 'COUNT':
                return float(len(values))
            if name in ('AVERAGE', 'MIN', 'MAX') and values:
                return self.finite({'AVERAGE': lambda x: sum(x) / len(x), 'MIN': min, 'MAX': max}[name](values))
            if name == 'ROUND' and len(values) in (1, 2):
                digits = int(values[1]) if len(values) == 2 else 0
                if not -10 <= digits <= 10:
                    raise FormulaError('ROUND digits must be between -10 and 10')
                return self.finite(round(values[0], digits))
        raise FormulaError('Use cell references, + - * / %, SUM, AVERAGE, MIN, MAX, COUNT or ROUND')

    def calculate(self):
        values, errors = [], {}
        for r, row in enumerate(self.cells):
            result = []
            for c in range(len(row)):
                try:
                    result.append(self.cell(r, c))
                except FormulaError as exc:
                    errors[address(r, c)] = str(exc)
                    result.append(None)
            values.append(result)
        return values, errors
