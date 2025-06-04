# main_app.py

import sys
import os
from lexer import LexicalAnalyzer, Token as LexToken, LexError
from grammar_reader import Grammar, GrammarError
from parse_table import LRAutomaton, SLRTable
from parser import Parser, ParseTreeNode
from tree_drawer import generate_dot
from error_handling import ParseError

def print_menu():
    print("""
Choose an option:
  1) Load and show tokens from a .yal lexer specification
  2) Load and display tokens from an input file using current lexer (and create <input>_tokens.txt)
  3) Load grammar (.yalp) and build SLR(1) parse table
  4) Print ACTION and GOTO tables
  5) Parse a sample input file & print the parse tree (in memory)
  6) Parse a file de tokens (uno por línea) & print the parse tree
  7) Generate DOT file for last parse tree
  8) Exit
""")

class REPL:
    def __init__(self):
        self.lexer = None
        self.grammar = None
        self.automaton = None
        self.table = None
        self.parse_tree = None
        self.last_tokens = None

    def run(self):
        while True:
            print_menu()
            choice = input("Option> ").strip()

            if choice == "1":
                path = input("Path to .yal file: ").strip()
                try:
                    self.lexer = LexicalAnalyzer(path)
                    print("Lexer loaded successfully.")
                    print("Rules:")
                    for pat_crudo, nombre_token in self.lexer.rules:
                        print(f"  patrón_crudo: '{pat_crudo}'  → token: '{nombre_token}'")
                except Exception as e:
                    print(f"[Error loading lexer] {e}")

            elif choice == "2":
                if not self.lexer:
                    print("Load a lexer first (option 1).")
                    continue
                src = input("Path to input text file to tokenize: ").strip()
                if not os.path.isfile(src):
                    print(f"[Error] El archivo '{src}' no existe.")
                    continue
                try:
                    txt = open(src, 'r', encoding='utf-8').read()
                    tokens = self.lexer.tokenize(txt)
                    self.last_tokens = tokens
                    print("Tokens:")
                    for t in tokens:
                        print(f"  {t}")
                    # --- NUEVO: Crear archivo de tokens ---
                    base, _ = os.path.splitext(os.path.basename(src))
                    tokens_filename = f"{base}_tokens.txt"
                    with open(tokens_filename, 'w', encoding='utf-8') as tf:
                        for t in tokens:
                            tf.write(f"{t.kind} {t.lexeme}\n")
                    print(f"Archivo de tokens creado: {tokens_filename}")
                    # ---------------------------------------
                except LexError as e:
                    print(f"[Lexical error] {e}")
                except Exception as e:
                    print(f"[Unexpected error] {e}")

            elif choice == "3":
                path = input("Path to .yalp grammar file: ").strip()
                try:
                    self.grammar = Grammar(path)
                    self.automaton = LRAutomaton(self.grammar)
                    self.table = SLRTable(self.automaton, self.grammar)
                    print("Grammar and SLR table built successfully.")
                except Exception as e:
                    print(f"[Grammar/Table error] {e}")

            elif choice == "4":
                if not self.table:
                    print("Build a grammar+table first (option 3).")
                    continue
                print("\nACTION table:")
                action = self.table.dump_action_table()
                for state, row in action.items():
                    print(f"State {state}:")
                    for term, act in row.items():
                        print(f"  On '{term}': {act}")
                print("\nGOTO table:")
                goto = self.table.dump_goto_table()
                for state, row in goto.items():
                    print(f"State {state}:")
                    for nt, st2 in row.items():
                        print(f"  On '{nt}': goto {st2}")

            elif choice == "5":
                if not self.table or not self.lexer:
                    print("Load both lexer (1) and grammar/table (3) first.")
                    continue
                src = input("Path to sample input to lex+parse: ").strip()
                if not os.path.isfile(src):
                    print(f"[Error] El archivo '{src}' no existe.")
                    continue
                try:
                    txt = open(src, 'r', encoding='utf-8').read()
                    tokens = self.lexer.tokenize(txt)
                    # Agregar EOF
                    eof = LexToken('$', '$', 0, 0)
                    tokens.append(eof)
                    parser = Parser(self.table, self.grammar)
                    self.parse_tree = parser.parse(tokens)
                    print("Parse succeeded. Parse-tree root:", self.parse_tree)
                except (LexError, ParseError) as e:
                    print(f"[Parsing error] {e}")
                except Exception as e:
                    print(f"[Unexpected error] {e}")

            elif choice == "6":
                if not self.table:
                    print("Primero debes cargar la gramática (opción 3).")
                    continue
                path_tokens = input("Path al archivo de tokens (uno por línea): ").strip()
                if not os.path.isfile(path_tokens):
                    print(f"[Error] El archivo '{path_tokens}' no existe.")
                    continue

                try:
                    # Paso 1: Leer todas las líneas "TOKNAME LEXEMA" (o solo "WHITESPACE"/"SEMICOLON"/"CARACTER_NO_DEFINIDO")
                    token_list = []
                    with open(path_tokens, 'r', encoding='utf-8') as f:
                        for idx, line in enumerate(f, start=1):
                            line = line.strip()
                            if not line:
                                continue

                            parts = line.split(maxsplit=1)
                            # Si la línea solo tiene WHITESPACE, SEMICOLON o CARACTER_NO_DEFINIDO, la consideramos delimitador
                            if len(parts) == 1 and parts[0] in ("WHITESPACE", "SEMICOLON", "CARACTER_NO_DEFINIDO"):
                                tokname = parts[0]
                                lexeme = ""
                            elif len(parts) == 2:
                                tokname, lexeme = parts
                            else:
                                raise ValueError(f"Línea malformada en {path_tokens} (línea {idx}): '{line}'")

                            token_list.append(LexToken(tokname, lexeme, idx, 1))

                    # Paso 2: Partir token_list en sublistas separadas por SEMICOLON, WHITESPACE o CARACTER_NO_DEFINIDO
                    chunks = []
                    current = []
                    for t in token_list:
                        if t.kind in ("SEMICOLON", "WHITESPACE", "CARACTER_NO_DEFINIDO"):
                            if current:
                                chunks.append(current)
                                current = []
                        else:
                            current.append(t)
                    if current:
                        chunks.append(current)

                    # Paso 3: Para cada sublista, añadir EOF y parsear
                    all_trees = []
                    parser = Parser(self.table, self.grammar)
                    for i, sub in enumerate(chunks, start=1):
                        eof = LexToken('$', '$', 0, 0)
                        sub_with_eof = sub + [eof]
                        try:
                            tree = parser.parse(sub_with_eof)
                            all_trees.append((i, tree))
                        except Exception as e:
                            raise ParseError(f"Error al parsear expresión #{i}: {e}")

                    # Paso 4: Mostrar resultados
                    for (i, tree) in all_trees:
                        print(f"Parse succeeded for expression #{i}. Root: {tree}")

                    # Guardar en self.parse_tree el árbol de la última expresión
                    if all_trees:
                        self.parse_tree = all_trees[-1][1]

                except Exception as e:
                    print(f"[Parsing error] {e}")

            elif choice == "7":
                if not self.parse_tree:
                    print("No parse tree available. Run option 5 or 6 first.")
                    continue
                out = input("Output DOT file path (e.g. tree.dot): ").strip() or "parse_tree.dot"
                try:
                    generate_dot(self.parse_tree, out)
                    print(f"DOT file written to {out}.")
                except Exception as e:
                    print(f"[Error writing DOT] {e}")

            elif choice == "8":
                print("Goodbye.")
                sys.exit(0)

            else:
                print("Invalid option.")

def main():
    repl = REPL()
    repl.run()

if __name__ == "__main__":
    main()
