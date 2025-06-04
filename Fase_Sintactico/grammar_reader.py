import re
from collections import defaultdict, OrderedDict

class GrammarError(Exception):
    pass

class Grammar:

    def __init__(self, yalp_path):
        with open(yalp_path, 'r', encoding='utf-8') as f:
            raw = f.read()

        # Inicializar estructuras vacías
        self.terminals = set()        # se completará tras parsear %token y RHS
        self.nonterminals = []        # se irá llenando en orden
        self.productions = []         # lista de (lhs, [símbolos en rhs])
        self.start_symbol = None

        # Paso 1: extraer tokens y producciones
        self._parse_yalp(raw)

        # Paso 2: deducir terminales de cualquier símbolo en RHS que no sea nonterminal
        self._infer_terminals_from_rhs()

        # Paso 3: computar FIRST y FOLLOW
        self._compute_first_sets()
        self._compute_follow_sets()

    def _parse_yalp(self, raw_text):
        # 1) Capturar todas las líneas '%token ...'
        token_pattern = re.compile(r"%token\s+([^\n]+)")
        for match in token_pattern.finditer(raw_text):
            partes = match.group(1).strip().split()
            self.terminals.update(partes)

        # 2) Separar cuerpo de la gramática tras '%%'
        parts = raw_text.split("%%", 1)
        if len(parts) < 2:
            raise GrammarError("No se encontró el separador '%%' en el archivo de gramática.")
        grammar_body = parts[1]

        # 3) Dividir por ';' cada bloque de producción
        prod_blocks = re.split(r";", grammar_body)
        for block in prod_blocks:
            block = block.strip()
            if not block:
                continue

            # Cada bloque debería tener 'LHS : ...'
            lhs_split = block.split(":", 1)
            if len(lhs_split) != 2:
                continue

            lhs = lhs_split[0].strip()
            if not lhs:
                continue

            # El primer nonterminal que encontremos lo tomamos como start_symbol
            if self.start_symbol is None:
                self.start_symbol = lhs

            # Añadir a lista de nonterminals (sin duplicados, en orden)
            if lhs not in self.nonterminals:
                self.nonterminals.append(lhs)

            rhs_part = lhs_split[1].strip()
            # Cada alternativa está separada por '|'
            alternatives = re.split(r"\|", rhs_part)
            for alt in alternatives:
                alt = alt.strip()
                if not alt:
                    continue
                symbols = alt.split()
                self.productions.append((lhs, symbols))

        # Verificar que ningún símbolo aparezca simultáneamente como terminal y nonterminal
        # (esto lo haremos después de inferir terminales para evitar falsos positivos)
        # la verificación final queda en _infer_terminals_from_rhs()

    def _infer_terminals_from_rhs(self):
        """
        Después de haber parseado las producciones y know nonterminals,
        buscamos en cada RHS cualquier símbolo que no esté en nonterminals.
        Esos símbolos los agregamos a terminals.
        Luego validamos que no exista solapamiento real.
        """
        all_rhs_symbols = set()
        for _, rhs in self.productions:
            all_rhs_symbols.update(rhs)

        # Cualquier símbolo en RHS que no sea un nonterminal, considérelo terminal
        for sym in all_rhs_symbols:
            if sym not in self.nonterminals:
                self.terminals.add(sym)

        # Verificar que no haya solapamiento real nonterminal/terminal
        overlap = set(self.nonterminals).intersection(self.terminals)
        if overlap:
            raise GrammarError(f"Símbolos no pueden ser a la vez terminal y no terminal: {overlap}")

    def _compute_first_sets(self):
        """
        FIRST sets: para cada símbolo (terminal o nonterminal), conjunto de terminales
        que pueden comenzar cadenas derivadas de él. 
        En esta versión sencilla, asumimos que no hay producciones epsilon explícitas.
        """
        # Inicializar FIRST vacío para cada nonterminal
        self.FIRST = {nt: set() for nt in self.nonterminals}

        # Para cada terminal, FIRST(terminal) = {terminal}
        for t in self.terminals:
            self.FIRST[t] = {t}

        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.productions:
                if not rhs:
                    # (Si en algún caso hubiera producción vacía, se omite aquí)
                    continue

                first_sym = rhs[0]
                before = set(self.FIRST[lhs])
                # Agregar FIRST del primer símbolo del RHS
                # Si es terminal, FIRST.get(first_sym) ya es {first_sym}
                # Si es nonterminal, es su conjunto FIRST calculado
                self.FIRST[lhs].update(self.FIRST.get(first_sym, set()))

                if self.FIRST[lhs] != before:
                    changed = True

    def _compute_follow_sets(self):
        """
        FOLLOW sets: para cada nonterminal, conjunto de terminales que pueden aparecer
        inmediatamente a su derecha en alguna derivación. El start_symbol incluye '$'.
        """
        # Inicializar FOLLOW vacío para cada nonterminal
        self.FOLLOW = {nt: set() for nt in self.nonterminals}
        # El símbolo inicial siempre incluye '$'
        self.FOLLOW[self.start_symbol].add('$')

        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.productions:
                trailer = set(self.FOLLOW[lhs])  # comienza con FOLLOW(LHS)
                # Recorremos RHS de derecha a izquierda
                for symbol in reversed(rhs):
                    if symbol in self.nonterminals:
                        before = set(self.FOLLOW[symbol])
                        # Agregar trailer (todos los terminales que vienen después de este nonterminal)
                        self.FOLLOW[symbol].update(trailer)
                        if self.FOLLOW[symbol] != before:
                            changed = True
                        # El trailer se incrementa con FIRST(symbol)
                        trailer = trailer.union(self.FIRST.get(symbol, set()))
                    else:
                        # Si es terminal, el trailer se reinicia a FIRST(terminal) = {terminal}
                        trailer = set(self.FIRST.get(symbol, set()))

    # Métodos auxiliares para depuración (opcional)
    def dump_first(self):
        print("FIRST sets:")
        for sym, fset in self.FIRST.items():
            print(f"  {sym}: {sorted(fset)}")

    def dump_follow(self):
        print("FOLLOW sets:")
        for nt, fset in self.FOLLOW.items():
            print(f"  {nt}: {sorted(fset)}")

    def dump_productions(self):
        print("Producciones:")
        for lhs, rhs in self.productions:
            print(f"  {lhs} → {' '.join(rhs)}")
