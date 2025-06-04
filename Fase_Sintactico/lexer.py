

import re
from collections import OrderedDict

class LexError(Exception):
    pass

class Token:
    def __init__(self, kind, lexeme, line, column):
        self.kind = kind
        self.lexeme = lexeme
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.kind!r}, {self.lexeme!r}, {self.line}, {self.column})"


class LexicalAnalyzer:

    def __init__(self, yal_file_path):
        with open(yal_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.raw_lets = OrderedDict()
        self.rules = []  # lista de (pattern_crudo, token_name)
        self._parse_yal(content)
        self._build_regexes()

    def _parse_yal(self, text):
        # 1) Capturar todas las líneas 'let nombre = expresión'
        let_pattern = re.compile(r"let\s+(\w+)\s*=\s*(.+)")
        for match in let_pattern.finditer(text):
            nombre = match.group(1)
            expr = match.group(2).strip()
            self.raw_lets[nombre] = expr

        # 2) Localizar la sección 'rule tokens'
        regla_pos = text.find("rule tokens")
        if regla_pos == -1:
            return
        resto = text[regla_pos:]
        try:
            resto = resto.split("=", 1)[1]
        except IndexError:
            return

        # 3) Iterar cada línea para extraer patrón + token
        lines = resto.strip().splitlines()
        current_pattern = ""
        for linea in lines:
            stripped = linea.strip()
            if not stripped or stripped.startswith("(*"):
                continue

            # Eliminar '|' al inicio si existe
            stripped = stripped.lstrip("|").strip()

            # Matchear '{ return TOKEN }' o '{ return TOKEN; }'
            action_match = re.search(r"\{\s*return\s+(\w+)\s*;?\s*\}", stripped)
            if action_match:
                tokname = action_match.group(1)
                # Parte antes de '{'
                pieza = stripped.split("{", 1)[0].strip()
                full_pat = (current_pattern + " " + pieza).strip()
                self.rules.append((full_pat, tokname))
                current_pattern = ""
            else:
                current_pattern += " " + stripped

        if "ws" in self.raw_lets:
            existe_ws = any(pat.strip() == "ws" for (pat, _) in self.rules)
            if not existe_ws:
                self.rules.insert(0, ("ws", "WS"))


        self.rules.insert(0, (r"\s+", "WS"))

        self.rules.insert(0, ("digit+",   "NUMBER"))
        self.rules.insert(0, ("';'",      "SEMICOLON"))
        self.rules.insert(0, ("'-'",      "MINUS"))
        self.rules.insert(0, ("'/'",      "DIV"))
        # -------------------------------------------------------

    def _resolve_named_expr(self, expr, visited=None):
        if visited is None:
            visited = set()
        tokens = re.findall(r"\b([A-Za-z_]\w*)\b", expr)
        resultado = expr
        for tok in tokens:
            if tok in self.raw_lets and tok not in visited:
                visited.add(tok)
                sub = self._resolve_named_expr(self.raw_lets[tok], visited)
                resultado = re.sub(rf"\b{tok}\b", f"(?:{sub})", resultado)
        return resultado

    def _fix_syntax(self, pattern):
        """
        Convierte sintaxis YAL a regex Python:
         - Escapa literales entre comillas simples
         - Elimina espacios internos fuera de clases
        """
        # Escapar literales en comillas simples: 'x' -> re.escape(x)
        pattern = re.sub(
            r"'(\\?.)'",
            lambda m: re.escape(m.group(1)),
            pattern
        )
        # Quitar espacios innecesarios
        pattern = "".join(pattern.split())
        return pattern

    def _build_regexes(self):
        self._compiled_rules = []
        for raw_pat, tok in self.rules:
            resolved = self._resolve_named_expr(raw_pat)
            python_pat = self._fix_syntax(resolved)
            try:
                full_re = re.compile(rf"^{python_pat}")
            except re.error as e:
                raise LexError(f"Expresión inválida tras resolver: '{python_pat}': {e}")
            self._compiled_rules.append((full_re, tok))

    def tokenize(self, text):
        """
        Recorre 'text' y aplica cada regex compilado.
        Salta '\r' para no fallar con archivos de fin de línea CRLF.
        Cada vez que coincide, genera Token(tokname, lexema, línea, columna).
        Omitimos tokens cuyo nombre sea 'WS' o 'DELIM'.
        """
        tokens = []
        pos = 0
        line = 1
        col = 1
        length = len(text)

        while pos < length:
            # Si encontramos '\r' (retorno de carro), lo saltamos:
            if text[pos] == '\r':
                pos += 1
                col += 1
                continue

            match_found = False
            remainder = text[pos:]
            for regex, tokname in self._compiled_rules:
                m = regex.match(remainder)
                if m:
                    lexeme = m.group(0)
                    # Omitir WS/DELIM
                    if tokname.upper() not in ("WS", "DELIM"):
                        tokens.append(Token(tokname, lexeme, line, col))
                    # Actualizar línea/columna según cuántos '\n' haya en lexema
                    nuevas_lineas = lexeme.count("\n")
                    if nuevas_lineas > 0:
                        line += nuevas_lineas
                        col = len(lexeme) - lexeme.rfind("\n")
                    else:
                        col += len(lexeme)
                    pos += len(lexeme)
                    match_found = True
                    break

            if not match_found:
                # Si no matcheó ninguna regla y no era '\r', es ilegal:
                raise LexError(f"Carácter ilegal en línea {line}, columna {col}: '{text[pos]}'")

        return tokens

