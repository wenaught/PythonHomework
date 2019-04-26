"""The script itself."""

import math
import argparse
import sys
import operator
import re
from collections import namedtuple


class OperandsError(Exception):
    pass


class OperatorsError(Exception):
    pass


class WhitespaceError(Exception):
    pass


class UnbalancedBracketsError(Exception):
    pass


class UnexpectedCommaError(Exception):
    pass


class EmptyExpressionError(Exception):
    pass


class ParseError(Exception):
    pass


class UnknownTokensError(Exception):
    pass


sys.tracebacklimit = 0

op = namedtuple('op', ['prec', 'func'])

operators = {
    '^': op(4, operator.pow),
    '*': op(3, operator.mul),
    '/': op(3, operator.truediv),
    '//': op(3, operator.floordiv),
    '%': op(3, operator.mod),
    '+': op(2, operator.add),
    '-': op(2, operator.sub)
}

prefix = namedtuple('prefix', ['func', 'args'])

prefixes = {
    'sin': prefix(math.sin, 1),
    'cos': prefix(math.cos, 1),
    'tan': prefix(math.tan, 1),
    'asin': prefix(math.asin, 1),
    'acos': prefix(math.acos, 1),
    'atan': prefix(math.atan, 1),
    'sqrt': prefix(math.sqrt, 1),
    'exp': prefix(math.exp, 1),
    'log': prefix(math.log, 2),
    'log1p': prefix(math.log1p, 1),
    'log10': prefix(math.log10, 1),
    'factorial': prefix(math.factorial, 1),
    'pow': prefix(math.pow, 2),
    'abs': prefix(abs, 1),
    'round': prefix(round, 1),
    'p': prefix(operator.pos, 1),
    'n': prefix(operator.neg, 1)
}

constants = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau
}

comparators = {
    '<': operator.lt,
    '>': operator.gt,
    '<=': operator.le,
    '>=': operator.ge,
    '==': operator.eq,
    '!=': operator.ne
}


def isnumber(num):
    try:
        float(num)
        return True
    except ValueError:
        return False


def check_whitespace(expression):
    """Check for whitespace breaking comparison operators and numbers in a given expression."""
    expression = expression.strip()
    token = re.search(r'[><=!]\s+=|\*\s+\*|\d\.?\s+\.?\d|\/\s+\/', expression)
    if token is not None:
        raise WhitespaceError("ERROR: unexpected whitespace in the expression.")


def check_brackets(expression):
    """Check whether brackets are balanced in the expression."""
    symbol_count = 0
    for symbol in expression:
        if symbol == '(':
            symbol_count += 1
        elif symbol == ')':
            symbol_count -= 1
        if symbol_count < 0:
            raise UnbalancedBracketsError("ERROR: brackets are not balanced.")
    if symbol_count > 0:
        raise UnbalancedBracketsError("ERROR: brackets are not balanced.")


def check_commas(expression):
    """Check for commas in unexpected places."""
    token = re.search(r'[^\)ieu\d]\,|\,[^\dpet\(]|^\,|\,$', expression)
    if token is not None:
        raise UnexpectedCommaError("ERROR: unexpected comma.")


def get_tokens(expression, input_queue=None):
    """Recursively split expression string into tokens and store them in input_queue."""
    if expression is '':
        raise EmptyExpressionError("ERROR: no expression provided.")
    if input_queue is None:
        expression = expression.strip().lower().replace(' ', '')
        input_queue = []
    token = re.match(r'\)|\(|\d+\.?\d*|[-+*/,^]|\.\d+|\w+|\W+', expression)
    try:
        token.group()
    except Exception:
        raise ParseError("ERROR: couldn't parse this expression.")
    input_queue.append(token.group())
    if len(token.group()) < len(expression):
        return get_tokens(expression[token.end():], input_queue)
    else:
        for index, token in enumerate(input_queue):
            if (input_queue[index - 1] in operators or
                input_queue[index - 1] is 'p' or
                input_queue[index - 1] is 'n' or
                input_queue[index - 1] is '(' or
                    index is 0):
                if token is '+':
                    input_queue[index] = 'p'
                if token is '-':
                    input_queue[index] = 'n'
        return input_queue


def convert_infix_to_postfix(input_queue):
    if input_queue[-1] in operators or input_queue[-1] in prefixes:
        raise OperatorsError("ERROR: trailing operators.")
    output_queue = []
    operator_stack = []
    while len(input_queue):
        token = input_queue[0]
        if isnumber(token):
            output_queue.append(float(input_queue.pop(0)))
        elif token in constants:
            output_queue.append(constants[token])
            input_queue.pop(0)
        elif token in prefixes:
            operator_stack.append(input_queue.pop(0))
        elif token is '(':
            operator_stack.append(input_queue.pop(0))
        elif token is ',':
            # since a comma can appear only after a logarithm or power, a check is implemented here
            if 'log' not in operator_stack and 'pow' not in operator_stack:
                raise UnexpectedCommaError("ERROR: unexpected comma.")
            try:
                while operator_stack[-1] is not '(':
                    output_queue.append(operator_stack.pop())
                input_queue.pop(0)
            except IndexError:
                raise UnexpectedCommaError("ERROR: unexpected comma.")
        elif token in operators:
            while True:
                if not operator_stack:
                    operator_stack.append(input_queue.pop(0))
                    break
                if ((operator_stack[-1] is not '(')
                    and (operator_stack[-1] in prefixes
                         or operators[token].prec < operators[operator_stack[-1]].prec
                         or (operators[operator_stack[-1]].prec == operators[token].prec
                             and token is not '^'))):
                    output_queue.append(operator_stack.pop())
                else:
                    operator_stack.append(input_queue.pop(0))
                    break
        elif token is ')':
            while operator_stack[-1] is not '(':
                output_queue.append(operator_stack.pop())
            operator_stack.pop()
            input_queue.pop(0)
        else:
            raise UnknownTokensError("ERROR: unknown tokens.")
    while len(operator_stack):
        output_queue.append(operator_stack.pop())
    return output_queue


def split_comparison(expression):
    """
    Split given expression into two to compare them.
    When given a non-comparison statement, return it without modifying.
    """
    check_whitespace(expression)
    check_brackets(expression)
    expression = re.sub(r'\s', '', expression)
    check_commas(expression)
    token = re.findall(r'==|>=|<=|>|<|!=', expression)
    if len(token) > 1:
        raise OperatorsError("ERROR: more than one comparison operator.")
    elif len(token) is 0:
        return expression, None
    else:
        expressions = expression.split(token[0])
        return expressions, token[0]


def calculate(expression):
    """Calculate a postfix notation expression."""
    stack = []
    while expression:
        token = expression.pop(0)
        if isnumber(token):
            stack.append(token)
        elif token in operators:
            operand_2 = stack.pop()
            operand_1 = stack.pop()
            result = operators[token].func(operand_1, operand_2)
            stack.append(result)
        elif token in prefixes:
            if prefixes[token].args is 2:
                if len(stack) is 1:
                    operand = stack.pop()
                    result = prefixes[token].func(operand)
                    stack.append(result)
                else:
                    operand_2 = stack.pop()
                    operand_1 = stack.pop()
                    result = prefixes[token].func(operand_1, operand_2)
                    stack.append(result)
            else:
                operand = stack.pop()
                result = prefixes[token].func(operand)
                stack.append(result)
    if len(stack) is 1:
        return stack[0]
    else:
        raise OperandsError("ERROR: wrong number of operands.")


def get_result(expression):
    expression = get_tokens(expression)
    expression = convert_infix_to_postfix(expression)
    try:
        expression = calculate(expression)
    except ZeroDivisionError as err:
        print("ERROR: {err}.".format(err=err))
    return expression


def compare(expressions, comparator):
    calculated_expressions = [get_result(expr) for expr in expressions]
    return comparators[comparator](expressions[0], expressions[1])


def main():
    parser = argparse.ArgumentParser(description='Pure-python command-line calculator.')
    parser.add_argument('EXPRESSION', action="store", help="expression string to evaluate")
    args = parser.parse_args()
    if args.EXPRESSION is not None:
        try:
            expression = args.EXPRESSION
            expressions, comparator = split_comparison(expression)
            if not comparator:
                print(get_result(expressions))
            else:
                print(compare(expressions, comparator))
        except Exception as exception:
            print(exception)


if __name__ == '__main__':
    main()
