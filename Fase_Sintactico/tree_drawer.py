# tree_drawer.py

def generate_dot(root_node, filename):
    """
    Write a DOT-format file for the parse tree rooted at 'root_node'.
    Each node gets a unique ID; label = node.symbol (and if leaf, also lexeme).
    """
    counter = [0]
    lines = ["digraph ParseTree {", "  node [shape=plain];"]
    def _walk(node):
        node_id = counter[0]
        counter[0] += 1
        label = node.symbol
        if node.token:
            # Leaf: include lexeme
            label = f"{node.symbol}\\n'{node.token.lexeme}'"
        lines.append(f'  n{node_id} [label="{label}"];')
        for child in node.children:
            child_id = _walk(child)
            lines.append(f"  n{node_id} -> n{child_id};")
        return node_id

    _walk(root_node)
    lines.append("}")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
