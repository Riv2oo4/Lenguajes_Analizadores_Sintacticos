# parser.py

from collections import deque
from error_handling import ParseError
from parse_table import SLRTable, Item
from lexer import Token   

class ParseTreeNode:
    def __init__(self, symbol, children=None, token=None):
        self.symbol = symbol
        self.children = children if children is not None else []
        self.token = token

    def __repr__(self):
        if self.token:
            return f"{self.symbol}('{self.token.lexeme}')"
        return f"{self.symbol}"


class Parser:


    def __init__(self, slr_table, grammar):
        self.table = slr_table
        self.grammar = grammar

    def parse(self, tokens):

        token_queue = deque(tokens)
        eof_token = tokens[-1] if tokens else None
        # Append a dummy EOF token
        token_queue.append(Token('$', '$', eof_token.line if eof_token else 1, eof_token.column if eof_token else 1))

        state_stack = [0]
        symbol_stack = []

        while True:
            current_state = state_stack[-1]
            lookahead = token_queue[0].kind if token_queue else '$'
            action_entry = self.table.action.get(current_state, {}).get(lookahead)

            if action_entry is None:
                raise ParseError(f"Unexpected token {lookahead!r} at state {current_state}")

            if action_entry[0] == "shift":
                next_state = action_entry[1]
                tok = token_queue.popleft()
                node = ParseTreeNode(tok.kind, children=[], token=tok)
                symbol_stack.append(node)
                state_stack.append(next_state)

            elif action_entry[0] == "reduce":
                prod_idx = action_entry[1]
                lhs, rhs = self.grammar.productions[prod_idx]
                nodes_to_attach = []
                for _ in rhs:
                    symbol_stack_top = symbol_stack.pop()
                    nodes_to_attach.insert(0, symbol_stack_top)
                    state_stack.pop()
                new_node = ParseTreeNode(lhs, children=nodes_to_attach, token=None)
                symbol_stack.append(new_node)
                goto_state = self.table.goto[state_stack[-1]].get(lhs)
                if goto_state is None:
                    raise ParseError(f"No GOTO for state {state_stack[-1]}, symbol {lhs}")
                state_stack.append(goto_state)

            elif action_entry[0] == "accept":
                if len(symbol_stack) != 1:
                    raise ParseError("Parse ended but parse-stack length != 1")
                return symbol_stack[0]

            else:
                raise ParseError(f"Unknown action {action_entry} at state {current_state}")
