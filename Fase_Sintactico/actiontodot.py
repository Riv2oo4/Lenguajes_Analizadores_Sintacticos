
import re

def action_table_to_dot(action_table, filename):
    """
    action_table: dict-of-dicts tal como lo devuelve table.dump_action_table()
    filename: ruta donde escribir el archivo .dot
    """

    lines = ["digraph ACTION_TABLE {", "  node [shape=box];"]
    # Nodo raíz
    lines.append('  root [label="ACTION"];')

    for state, row in action_table.items():
        state_id = f"state{state}"
        # Nodo del estado
        lines.append(f'  "{state_id}" [label="State {state}"];')
        # Arista desde el root
        lines.append(f'  root -> "{state_id}";')

        for term, act in row.items():
            # Construcción de la descripción de la acción
            if act[0] == "shift":
                act_desc = f"on '{term}' → shift {act[1]}"
            elif act[0] == "reduce":
                act_desc = f"on '{term}' → reduce by prod {act[1]}"
            elif act[0] == "accept":
                act_desc = f"on '{term}' → accept"
            else:
                act_desc = f"on '{term}' → {act}"

            # Generamos un identificador crudo para el nodo de esa transición
            raw_id = f"{state_id}_{term}"
            # Reemplazamos cualquier carácter distinto de letras, dígitos o guión bajo por "_"
            node_id = re.sub(r'[^A-Za-z0-9_]', '_', raw_id)

            # Escapamos posibles comillas en la etiqueta
            label = act_desc.replace('"', '\\"')

            lines.append(f'  "{node_id}" [label="{label}"];')
            lines.append(f'  "{state_id}" -> "{node_id}";')

    lines.append("}")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))