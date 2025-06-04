#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import traceback
from datetime import datetime

# -------------------------------------------------------------------------------
# 1) Ajustar sys.path para importar ambos conjuntos de módulos
# -------------------------------------------------------------------------------
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "Fase_Compilacion"))
sys.path.append(os.path.join(base_dir, "Fase_Sintactico"))

# -------------------------------------------------------------------------------
# 2) Importar funciones / clases de la Fase_Compilación (léxico)
# -------------------------------------------------------------------------------
from actiontodot import action_table_to_dot
from lexerProcesador import AnalizadorLexico, tokenizar, minimizar_afd, Token as LexProcToken
from yalex_parser import YALexParser

def leerArchivo(archivo_fuente, archivo_yalex, visualizar=False):
    """Procesa el archivo fuente con la gramática YALex y devuelve lista de LexProcToken."""
    from m import leerArchivo as _leer  # si la tienes en un archivo separado
    return _leer(archivo_fuente, archivo_yalex, visualizar)


# -------------------------------------------------------------------------------
# 3) Importar módulos de la Fase_Sintactico (sintáctico)
# -------------------------------------------------------------------------------
from lexer import LexicalAnalyzer, Token as LexToken, LexError
from grammar_reader import Grammar, GrammarError
from parse_table import LRAutomaton, SLRTable
from parser import Parser, ParseTreeNode
from error_handling import ParseError
from tree_drawer import generate_dot

# -------------------------------------------------------------------------------
# 4) Función para registrar errores en un archivo sin interrumpir el REPL
# -------------------------------------------------------------------------------
def log_error(exc: Exception):
    """Registra la traza de excepción en 'registro_errores.txt' con timestamp."""
    ruta_log = os.path.join(base_dir, "registro_errores.txt")
    with open(ruta_log, "a", encoding="utf-8") as log:
        log.write(f"\n----- {datetime.now():%Y-%m-%d %H:%M:%S} -----\n")
        traceback.print_exc(file=log)
        log.write("\n")

# -------------------------------------------------------------------------------
# 5) Menú y clase REPL integrada
# -------------------------------------------------------------------------------
def print_menu():
    print("""
Elige una opción:
  0) Ejecutar léxico (Fase_Compilación) para generar <fuente>.tokens
  1) Cargar y mostrar tokens desde una especificación .yal (fase sintáctica)
  2) Cargar gramática (.yalp) y construir la tabla SLR(1)
  3) Imprimir tablas ACTION y GOTO
  4) Analizar un archivo de tokens (uno por línea) e imprimir el árbol de análisis
  5) Generar archivo DOT para el último árbol de análisis
  6) Diagrama de estados
  7) SALIR
""")

class REPL:
    def __init__(self):
        # Fase léxica
        self.analizador_lexico = None       #
        self.ultimo_tokens_lexproc = None  

        # Fase sintáctica
        self.lexer_sint = None    
        self.grammar = None       
        self.automaton = None     
        self.table = None         
        self.parse_tree = None    
        self.last_tokens = None   

    def run(self):
        while True:
            try:
                print_menu()
                choice = input("Option> ").strip()

                # ---------------------------------------------------------------
                # Opción 0: Correr la fase léxica completa (Fase_Compilación)
                # ---------------------------------------------------------------
                if choice == "0":
                    try:
                        archivo_fuente = input("  Ruta al archivo fuente (.txt, .c, etc.): ").strip()
                        if not os.path.isfile(archivo_fuente):
                            print(f"    [Error] No existe '{archivo_fuente}'")
                            continue

                        archivo_yalex = input("  Ruta al .yal (especificación léxica): ").strip()
                        if not os.path.isfile(archivo_yalex):
                            print(f"    [Error] No existe '{archivo_yalex}'")
                            continue

                        # Llamamos a la Fase_Compilación para generar <fuente>.tokens
                        tokens_lexproc = leerArchivo(archivo_fuente, archivo_yalex, False)
                        if tokens_lexproc is None:
                            print("    No se generaron tokens (fase léxica). Revisa errores.")
                            continue

                        self.analizador_lexico = True
                        self.ultimo_tokens_lexproc = tokens_lexproc
                        print(f"    Léxico terminado. Archivo '{os.path.splitext(os.path.basename(archivo_fuente))[0]}.tokens' creado.")

                    except Exception as e:
                        print("    [Error en fase léxica] Se ha registrado en 'registro_errores.txt'")
                        log_error(e)

                # ---------------------------------------------------------------
                # Opción 1: Load and show tokens from un .yal lexer spec (sintáctico)
                # ---------------------------------------------------------------
                elif choice == "1":
                    try:
                        path = input("  Path to .yal file: ").strip()
                        self.lexer_sint = LexicalAnalyzer(path)
                        print("    Lexer (sintáctico) cargado exitosamente.")
                        print("    Rules:")
                        for pat_crudo, nombre_token in self.lexer_sint.rules:
                            print(f"      patrón_crudo: '{pat_crudo}'  → token: '{nombre_token}'")
                    except Exception as e:
                        print("    [Error cargando lexer sintáctico] Se ha registrado en 'registro_errores.txt'")
                        log_error(e)

                # ---------------------------------------------------------------
                # Opción 2: Cargar gramática .yalp y construir tabla SLR(1)
                # ---------------------------------------------------------------
                elif choice == "2":
                    try:
                        path = input("  Path to .yalp grammar file: ").strip()
                        self.grammar = Grammar(path)
                        self.automaton = LRAutomaton(self.grammar)
                        self.table = SLRTable(self.automaton, self.grammar)
                        print("    Gramática y tabla SLR(1) construidas exitosamente.")
                    except (GrammarError, Exception) as e:
                        print("    [Grammar/Table error] Se ha registrado en 'registro_errores.txt'")
                        log_error(e)

                # ---------------------------------------------------------------
                # Opción 3: Imprimir tablas ACTION y GOTO
                # ---------------------------------------------------------------
                elif choice == "3":
                    try:
                        if not self.table:
                            print("    Primero construye gramática+tabla (opción 3).")
                            continue
                        print("\n    ACTION table:")
                        action = self.table.dump_action_table()
                        for state, row in action.items():
                            print(f"      State {state}:")
                            for term, act in row.items():
                                print(f"        On '{term}': {act}")

                        print("\n    GOTO table:")
                        goto = self.table.dump_goto_table()
                        for state, row in goto.items():
                            print(f"      State {state}:")
                            for nt, st2 in row.items():
                                print(f"        On '{nt}': goto {st2}")
                    except Exception as e:
                        print("    [Error imprimiendo tablas] Se ha registrado en 'registro_errores.txt'")
                        log_error(e)

                # ---------------------------------------------------------------
                # Opción 4: Parsear un archivo de tokens (uno por línea)
                # ---------------------------------------------------------------
                elif choice == "4":
                    try:
                        if not self.table:
                            print("    Primero carga la gramática (opción 3).")
                            continue
                        path_tokens = input("  Path al archivo de tokens (uno por línea): ").strip()
                        if not os.path.isfile(path_tokens):
                            print(f"    [Error] El archivo '{path_tokens}' no existe.")
                            continue

                        # Leer todas las líneas "TOKNAME LEXEMA" o solo "WHITESPACE"/"SEMICOLON"/"CARACTER_NO_DEFINIDO"
                        token_list = []
                        with open(path_tokens, 'r', encoding='utf-8') as f:
                            for idx, line in enumerate(f, start=1):
                                line = line.strip()
                                if not line:
                                    continue
                                parts = line.split(maxsplit=1)
                                if len(parts) == 1 and parts[0] in ("WHITESPACE", "SEMICOLON", "CARACTER_NO_DEFINIDO"):
                                    tokname = parts[0]
                                    lexeme = ""
                                elif len(parts) == 2:
                                    tokname, lexeme = parts
                                else:
                                    raise ValueError(f"Línea malformada en {path_tokens} (línea {idx}): '{line}'")
                                token_list.append(LexToken(tokname, lexeme, idx, 1))

                        # Partir token_list en sublistas separadas por delimitadores
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

                        # Parsear cada sublista
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

                        # Mostrar resultados
                        for (i, tree) in all_trees:
                            print(f"    Parse succeeded for expression #{i}. Root: {tree}")

                        # Guardar el último árbol
                        if all_trees:
                            self.parse_tree = all_trees[-1][1]

                    except Exception as e:
                        print("    [Parsing error] Se ha registrado en 'registro_errores.txt'")
                        log_error(e)

                # ---------------------------------------------------------------
                # Opción 5: Generar DOT del último parse tree
                # ---------------------------------------------------------------
                elif choice == "5":
                    try:
                        if not self.parse_tree:
                            print("    No hay parse tree disponible. Ejecuta la opción 5 o 6 primero.")
                            continue
                        out = input("  Output DOT file path (e.g. tree.dot): ").strip() or "parse_tree.dot"
                        generate_dot(self.parse_tree, out)
                        print(f"    DOT file escrito en: {out}")
                    except Exception as e:
                        print("    [Error escribiendo DOT] Se ha registrado en 'registro_errores.txt'")
                        log_error(e)
                        
                elif choice == "6":
                    if not self.table:
                        print("Build a grammar+table first (option 3).")
                        continue
                    filename = input("Output DOT file for ACTION table (e.g. action_table.dot): ").strip()
                    if not filename:
                        print("No filename provided.")
                        continue
                    try:
                        action_dict = self.table.dump_action_table()
                        action_table_to_dot(action_dict, filename)
                        print(f"ACTION table DOT written to '{filename}'.")
                    except Exception as e:
                        print(f"[Error writing ACTION DOT] {e}")

                # ---------------------------------------------------------------
                # Opción 7: Salir
                # ---------------------------------------------------------------
                elif choice == "7":
                    print("    Goodbye.")
                    sys.exit(0)

                else:
                    print("    Invalid option. Intenta de nuevo.")

            except KeyboardInterrupt:
                print("\n    Programa terminado por el usuario.")
                sys.exit(0)
            except Exception as e:
                # Cualquier excepción inesperada en el bucle global
                print("    [Error inesperado en REPL] Se ha registrado en 'registro_errores.txt'")
                log_error(e)


def main():
    repl = REPL()
    repl.run()

if __name__ == "__main__":
    main()
