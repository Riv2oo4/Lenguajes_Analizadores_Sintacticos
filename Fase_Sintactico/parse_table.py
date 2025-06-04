# parse_table.py

from collections import defaultdict
from copy import deepcopy

class Item:

    def __init__(self, lhs, rhs, dot):
        self.lhs = lhs
        self.rhs = list(rhs)
        self.dot = dot  

    def next_symbol(self):
        if self.dot < len(self.rhs):
            return self.rhs[self.dot]
        return None

    def is_complete(self):
        return self.dot >= len(self.rhs)

    def advance(self):
        if not self.is_complete():
            return Item(self.lhs, self.rhs, self.dot + 1)
        return None

    def __eq__(self, other):
        return (self.lhs, tuple(self.rhs), self.dot) == (other.lhs, tuple(other.rhs), other.dot)

    def __hash__(self):
        return hash((self.lhs, tuple(self.rhs), self.dot))

    def __repr__(self):
        before_dot = " ".join(self.rhs[:self.dot])
        after_dot = " ".join(self.rhs[self.dot:])
        return f"{self.lhs} -> {before_dot} · {after_dot}"


class LRAutomaton:


    def __init__(self, grammar):
        self.grammar = grammar
        self.start_symbol = grammar.start_symbol
        self.augmented_start = self.start_symbol + "'"
        self.grammar.nonterminals.insert(0, self.augmented_start)
        self.grammar.productions.insert(0, (self.augmented_start, [self.start_symbol]))
        self.states = []  
        self._build_states()

    def _closure(self, items):

        closure_set = set(items)
        added = True
        while added:
            added = False
            for it in list(closure_set):
                nxt = it.next_symbol()
                if nxt in self.grammar.nonterminals:
                    for prod_lhs, prod_rhs in self.grammar.productions:
                        if prod_lhs == nxt:
                            new_item = Item(prod_lhs, prod_rhs, 0)
                            if new_item not in closure_set:
                                closure_set.add(new_item)
                                added = True
        return closure_set

    def _goto(self, items, symbol):

        moved = set()
        for it in items:
            if it.next_symbol() == symbol:
                adv = it.advance()
                moved.add(adv)
        return self._closure(moved) if moved else set()

    def _build_states(self):

        start_item = Item(self.augmented_start, [self.start_symbol], 0)
        init_closure = self._closure({start_item})
        self.states = [frozenset(init_closure)]
        changed = True
        while changed:
            changed = False
            for I in list(self.states):
                for sym in self.grammar.terminals.union(set(self.grammar.nonterminals)):
                    goto_I = self._goto(I, sym)
                    if goto_I:
                        fr = frozenset(goto_I)
                        if fr not in self.states:
                            self.states.append(fr)
                            changed = True


class SLRTable:


    def __init__(self, automaton, grammar, resolve_conflicts=True):
        self.automaton = automaton
        self.grammar = grammar
        self.action = defaultdict(dict)  #
        self.goto = defaultdict(dict)    
        self.conflicts = []  
        self.resolve_conflicts = resolve_conflicts
        self._build_tables()

    def _build_tables(self):

        G = self.grammar
        C = self.automaton.states
        FOLLOW = G.FOLLOW

        for idx, I in enumerate(C):
            for it in I:
                nxt = it.next_symbol()
                if nxt in G.terminals:
                    # shift case
                    J = self._find_state(self.automaton._goto(I, nxt))
                    if J is not None:
                        if nxt in self.action[idx]:
                            existing = self.action[idx][nxt]
                            # Handle conflict
                            conflict_info = {
                                'state': idx,
                                'symbol': nxt,
                                'existing': existing,
                                'new': ("shift", J),
                                'items': list(I)
                            }
                            self.conflicts.append(conflict_info)
                            
                            if self.resolve_conflicts:
                                # Default resolution: prefer shift over reduce (shift/reduce conflict)
                                if existing[0] == "reduce":
                                    self.action[idx][nxt] = ("shift", J)
                                    print(f"Warning: Resolved shift/reduce conflict at state {idx}, symbol {nxt}. Choosing shift.")
                                else:
                                    print(f"Warning: Shift/shift conflict at state {idx}, symbol {nxt}. Keeping existing shift to state {existing[1]}.")
                            else:
                                raise Exception(f"Shift/shift or shift/reduce conflict at state {idx}, symbol {nxt}. Existing: {existing}")
                        else:
                            self.action[idx][nxt] = ("shift", J)
                elif it.is_complete():
                    if it.lhs == self.automaton.augmented_start:
                        # Accept
                        self.action[idx]['$'] = ("accept",)
                    else:
                        # reduce by A -> alpha
                        prod_index = self._prod_index(it.lhs, it.rhs)
                        for b in FOLLOW[it.lhs]:
                            if b in self.action[idx]:
                                existing = self.action[idx][b]
                                # Handle conflict
                                conflict_info = {
                                    'state': idx,
                                    'symbol': b,
                                    'existing': existing,
                                    'new': ("reduce", prod_index),
                                    'items': list(I)
                                }
                                self.conflicts.append(conflict_info)
                                
                                if self.resolve_conflicts:
                                    if existing[0] == "shift":
                                        print(f"Warning: Resolved shift/reduce conflict at state {idx}, symbol {b}. Choosing shift.")
                                    else:
                                        if prod_index < existing[1]:
                                            self.action[idx][b] = ("reduce", prod_index)
                                            print(f"Warning: Resolved reduce/reduce conflict at state {idx}, symbol {b}. Choosing production {prod_index}.")
                                        else:
                                            print(f"Warning: Resolved reduce/reduce conflict at state {idx}, symbol {b}. Keeping production {existing[1]}.")
                                else:
                                    raise Exception(f"Reduce/shift or reduce/reduce conflict at state {idx}, symbol {b}. Existing: {existing}")
                            else:
                                self.action[idx][b] = ("reduce", prod_index)

            # Fill GOTO for nonterminals
            for A in G.nonterminals:
                if A == self.automaton.augmented_start:
                    continue
                to_items = self.automaton._goto(I, A)
                if to_items:
                    J = self._find_state(to_items)
                    if J is not None:
                        self.goto[idx][A] = J

    def _find_state(self, item_set):

        f = frozenset(item_set)
        try:
            return self.automaton.states.index(f)
        except ValueError:
            return None

    def _prod_index(self, lhs, rhs):
 
        for i, (L, R) in enumerate(self.grammar.productions):
            if lhs == L and rhs == R:
                return i
        raise KeyError(f"Production {lhs} -> {rhs} not found.")

    def dump_action_table(self):
 
        return dict(self.action)

    def dump_goto_table(self):

        return dict(self.goto)
    
    def print_conflicts(self):

        if not self.conflicts:
            print("No conflicts found.")
            return
            
        print(f"\nTotal conflicts found: {len(self.conflicts)}")
        for i, conflict in enumerate(self.conflicts):
            print(f"\nConflict {i+1}:")
            print(f"  State: {conflict['state']}")
            print(f"  Symbol: {conflict['symbol']}")
            print(f"  Existing action: {conflict['existing']}")
            print(f"  New action: {conflict['new']}")
            print(f"  Items in state:")
            for item in conflict['items']:
                print(f"    {item}")
    
    def analyze_grammar(self):
  
        if not self.conflicts:
            print("Grammar is SLR(1) - no conflicts!")
            return
            
        print("\nGrammar Analysis:")
        print("=================")
        
        shift_reduce = 0
        reduce_reduce = 0
        shift_shift = 0
        
        for conflict in self.conflicts:
            existing_type = conflict['existing'][0]
            new_type = conflict['new'][0]
            
            if existing_type == "shift" and new_type == "shift":
                shift_shift += 1
            elif (existing_type == "shift" and new_type == "reduce") or \
                 (existing_type == "reduce" and new_type == "shift"):
                shift_reduce += 1
            else:
                reduce_reduce += 1
        
        print(f"Shift/Reduce conflicts: {shift_reduce}")
        print(f"Reduce/Reduce conflicts: {reduce_reduce}")
        print(f"Shift/Shift conflicts: {shift_shift}")
        
        print("\nPossible solutions:")
        print("1. Rewrite grammar to be unambiguous")
        print("2. Add precedence and associativity rules")
        print("3. Use more powerful parsing method (LALR or LR(1))")
        print("4. Use conflict resolution (shift preferred over reduce)")