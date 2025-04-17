from lark import Lark, Transformer
import yaml
import os

# Définition de la grammaire mise à jour
graph_grammar = """
    ?start: sequence

    ?sequence: expr
          | sequence "," expr     -> ensuite

    ?expr: factor
         | expr "or" factor     -> alternative

    ?factor: term
           | factor "and" term  -> parallel

    ?term: ACTION_NAME             -> action
         | "(" sequence ")"         -> group

    ACTION_NAME: /[a-zA-Z0-9_]+/

    %import common.WS
    %ignore WS
"""

class GraphTransformer(Transformer):
    def __init__(self, sequence_name, namespace, package_name):
        super().__init__()
        self.sequence_name = sequence_name
        self.parallel_count = 0
        self.sequence_count = 0
        self.new_actions = {}
        self.sequences = {}
        self.namespace = namespace
        self.package_name = package_name
        
    def action(self, items):
        # Retourne le nom de l'action
        return items[0].value
    
    def group(self, items):
        # Retourne le contenu du groupe
        return items[0]
    
    def ensuite(self, items):
        # Combine les éléments d'une séquence
        left, right = items
        
        # print("LeftEnsuite:", left)
        # print("RightEnsuite:", right)
        # Si l'un des éléments est un dictionnaire d'alternatives
        if isinstance(left, dict) and "alternatives" in left:
            # Pour chaque alternative, ajouter le côté droit
            new_alternatives = []
            for alt in left["alternatives"]:
                if isinstance(alt, list):
                    if isinstance(right, list):
                        new_alternatives.append(alt + right)
                    elif isinstance(right, dict) and "alternatives" in right:
                        for r_alt in right["alternatives"]:
                            if isinstance(r_alt, list):
                                new_alternatives.append(alt + r_alt)
                            else:
                                new_alternatives.append(alt + [r_alt])
                    else:
                        new_alternatives.append(alt + [right])
                else:
                    if isinstance(right, list):
                        new_alternatives.append([alt] + right)
                    elif isinstance(right, dict) and "alternatives" in right:
                        for r_alt in right["alternatives"]:
                            if isinstance(r_alt, list):
                                new_alternatives.append([alt] + r_alt)
                            else:
                                new_alternatives.append([alt, r_alt])
                    else:
                        new_alternatives.append([alt, right])
            return {"alternatives": new_alternatives}
        
        elif isinstance(right, dict) and "alternatives" in right:
            # Pour chaque alternative du côté droit, ajouter le côté gauche
            new_alternatives = []
            for alt in right["alternatives"]:
                if isinstance(alt, list):
                    if isinstance(left, list):
                        new_alternatives.append(left + alt)
                    else:
                        new_alternatives.append([left] + alt)
                else:
                    if isinstance(left, list):
                        new_alternatives.append(left + [alt])
                    else:
                        new_alternatives.append([left, alt])
            return {"alternatives": new_alternatives}
        
        # Si ce sont des cas simples
        if isinstance(left, list):
            if isinstance(right, list):
                return left + right
            else:
                return left + [right]
        else:
            if isinstance(right, list):
                return [left] + right
            else:
                return [left, right]
    
    def alternative(self, items):
        # Gère les alternatives (OR)
        left, right = items
        # print("LeftAlternative:", left)
        # print("RightAlternative:", right)
        # Convertir en listes si ce n'est pas déjà le cas
        if not isinstance(left, list) and not isinstance(left, dict):
            left = [left]
        if not isinstance(right, list) and not isinstance(right, dict):
            right = [right]
        
        # Créer les alternatives
        if isinstance(left, dict) and "alternatives" in left:
            if isinstance(right, dict) and "alternatives" in right:
                return {"alternatives": left["alternatives"] + right["alternatives"]}
            else:
                return {"alternatives": left["alternatives"] + [right]}
        else:
            if isinstance(right, dict) and "alternatives" in right:
                return {"alternatives": [left] + right["alternatives"]}
            else:
                return {"alternatives": [left, right]}
    
    def parallel(self, items):
        # Gère les exécutions parallèles (AND)
        left, right = items
        # print("LeftParallel:", left)
        # print("RightParallel:", right)
        self.parallel_count += 1
        parallel_prefix = f"parallel{self.parallel_count}.{self.sequence_name}"
        
        # Créer les branches parallèles
        branch1_name = f"{parallel_prefix}.branche1"
        branch2_name = f"{parallel_prefix}.branche2"
        
        # Traiter la branche gauche
        branch1_sequences = []
        if isinstance(left, list):
            self.sequences[branch1_name] = {"actions": ", ".join(left), "web" : True}
            branch1_sequences.append(branch1_name)
        elif isinstance(left, dict) and "alternatives" in left:
            for i, alt in enumerate(left["alternatives"]):
                alt_name = f"{branch1_name}.S{i+1}"
                if isinstance(alt, list):
                    self.sequences[alt_name] = {"actions": ", ".join(alt), "web" : True}
                else:
                    self.sequences[alt_name] = {"actions": alt, "web" : True}
                branch1_sequences.append(alt_name)
        else:
            self.sequences[branch1_name] = {"actions": left, "web" : True}
            branch1_sequences.append(branch1_name)
        
        # Traiter la branche droite
        branch2_sequences = []
        if isinstance(right, list):
            self.sequences[branch2_name] = {"actions": ", ".join(right), "web" : True}
            branch2_sequences.append(branch2_name)
        elif isinstance(right, dict) and "alternatives" in right:
            for i, alt in enumerate(right["alternatives"]):
                alt_name = f"{branch2_name}.S{i+1}"
                if isinstance(alt, list):
                    self.sequences[alt_name] = {"actions": ", ".join(alt), "web" : True}
                else:
                    self.sequences[alt_name] = {"actions": alt, "web" : True}
                branch2_sequences.append(alt_name)
        else:
            self.sequences[branch2_name] = {"actions": right, "web" : True}
            branch2_sequences.append(branch2_name)
        
        # Créer une action pour chaque combinaison possible
        parallel_actions = []
        action_count = 0
        for branch1 in branch1_sequences:
            for branch2 in branch2_sequences:
                action_count += 1
                parallel_name = f"A{self.parallel_count}_{action_count}"
                
                # Créer l'action qui exécute cette combinaison de branches en parallèle
                self.new_actions[parallel_name] = {
                    "function": f"../action/{parallel_name}.py",
                    # "annotations": {}
                }
                
                # Créer le contenu du fichier Python pour l'action parallèle
                with open("parallel_process_template.py", "r") as template_file:
                    parallel_code = template_file.read()

                # Ajouter l'argument "action_args" à la fonction "main"
                parallel_code = parallel_code.replace("action_args.items()", f"['{branch1}', '{branch2}']")
                parallel_code = parallel_code.replace("main(args, action_args)", "main(args)")
                parallel_code = parallel_code.replace("{namespace}/{package_name}", f"{self.namespace}/{self.package_name}")

#                 parallel_code = f"""# Action parallèle {parallel_name}
# # Exécute les branches {branch1} et {branch2} en parallèle
# branches = ["{branch1}", "{branch2}"]
# """
                # S'assurer que le dossier existe
                os.makedirs("../action", exist_ok=True)
                
                # Écrire le fichier Python
                with open(f"../action/{parallel_name}.py", "w") as f:
                    f.write(parallel_code)
                
                parallel_actions.append(parallel_name)
        
        # Si plusieurs actions parallèles ont été créées, retourner comme alternatives
        if len(parallel_actions) > 1:
            return {"alternatives": [[action] for action in parallel_actions]}
        else:
            return parallel_actions[0]

def parse_and_transform_graph(graph_expression, sequence_name, namespace="guest", package_name="default"):
    parser = Lark(graph_grammar, start='start')
    try:
        tree = parser.parse(graph_expression)
        transformer = GraphTransformer(sequence_name, namespace, package_name)
        result = transformer.transform(tree)
        # print("Result:", result)
        # Traiter le résultat selon son type
        if isinstance(result, list):
            # Si c'est une simple séquence
            transformer.sequences[f"{sequence_name}.S1"] = {"actions": ", ".join(result)}
        elif isinstance(result, dict) and "alternatives" in result:
            # Si ce sont des alternatives
            for i, alt in enumerate(result["alternatives"]):
                if isinstance(alt, list):
                    transformer.sequences[f"{sequence_name}.S{i+1}"] = {"actions": ", ".join(alt)}
                else:
                    transformer.sequences[f"{sequence_name}.S{i+1}"] = {"actions": alt}
        elif isinstance(result, str):
            # Si c'est une action simple
            transformer.sequences[f"{sequence_name}.S1"] = {"actions": result}
        else:
            # Cas spécial où result contient des éléments mixtes
            try:
                result_str = []
                for item in result:
                    if isinstance(item, str):
                        result_str.append(item)
                    elif isinstance(item, list):
                        result_str.extend(item)
                if result_str:
                    transformer.sequences[f"{sequence_name}.S1"] = {"action": ", ".join(result_str)}
            except Exception:
                pass
        
        return transformer.new_actions, transformer.sequences
    except Exception as e:
        print(f"Error parsing expression: {e}")
        return {}, {}

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def save_yaml(data, file_path):
    with open(file_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)

def process_yaml_file(input_file, output_file):
    # Charger le fichier YAML d'entrée
    yaml_data = load_yaml(input_file)

    # Recuperer le namespace et le nom du package
    namespace = yaml_data.get("namespace", "guest")

    for pck_name, package in yaml_data.get("packages", {}).items():
    
        # Trouver la séquence à traiter
        sequences = yaml_data.get('packages', {}).get(pck_name, {}).get('sequences', {})
        for seq_name, seq_info in sequences.items():
            graph_expression = seq_info.get('action', '')
            
            # Transformer l'expression en séquences
            new_actions, new_sequences = parse_and_transform_graph(graph_expression, seq_name, namespace, pck_name)
            
            # Ajouter les nouvelles actions au YAML
            actions = yaml_data['packages'][pck_name].get('actions', {})
            for action_name, action_info in new_actions.items():
                actions[action_name] = action_info
            yaml_data['packages'][pck_name]['actions'] = actions
            
            # Remplacer la séquence originale par les nouvelles séquences
            yaml_data['packages'][pck_name]['sequences'] = new_sequences
    
    # Sauvegarder le fichier YAML résultant
    save_yaml(yaml_data, output_file)
    return yaml_data

# Exemple d'utilisation
if __name__ == "__main__":
    # Traiter le fichier YAML
    result = process_yaml_file("manifest.yaml", "output.yaml")