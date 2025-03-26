import yaml
import random  # To generate random quality values
import itertools

def generate_parallel_combinations(branch_sequences):
    """ Génère toutes les combinaisons possibles en prenant une séquence par branche. """
    keys, values = zip(*branch_sequences.items())
    combinations = list(itertools.product(*values))
    return [dict(zip(keys, combo)) for combo in combinations]

def process_parallel_actions(actions):
    """ Réécrit le YAML en transformant les actions parallèles en actions combinées. """
    new_actions = {}
    sequences = {}
    
    for action, details in actions.items():
        if "parallel" in details:
            branches = details["parallel"]
            branch_sequences = {}

            for branch, sub_actions in branches.items():
                if isinstance(sub_actions, dict):  # Vérification que sub_actions est un dictionnaire
                    branch_start = next(iter(sub_actions))  # Récupérer la première clé
                    sequences_list = []
                    generate_sequences_parralel_action(sub_actions, branch_start, [], sequences_list, action, f"{action}.{branch}.seq")
                    sequences.update({seq_name: seq for seq_name, seq in sequences_list})
                    branch_sequences[branch] = list(sequences.keys())[-len(sequences_list):]  # Récupère les noms des séquences

                    # new_action_key = f"{branch}.{branch_start}"

                    # Ajoutez la première action de sub_actions a 'new_actions'
                    if branch_start not in new_actions:
                        new_actions[branch_start] = sub_actions[branch_start]

            # Générer toutes les combinaisons possibles
            combinations = generate_parallel_combinations(branch_sequences)
            new_action_names = []

            suivant = details.get("suivant", [])

            for i, combo in enumerate(combinations, 1):
                new_action_name = f"A{i}"
                new_action_names.append(new_action_name)
                new_actions[new_action_name] = {"function": f"../action/{new_action_name}.js", "suivant": [suivant[0]]}
                with open(f"../action/{new_action_name}.js", "w") as js_file:
                    js_file.write("// Parallel execution of: " + ", ".join(combo.values()))
            
            # Modifier l'action originale pour pointer vers les nouvelles actions combinées
            details["suivant"].extend(new_action_names) 

            del details["parallel"]
    
    actions.update(new_actions)
    return sequences

def generate_sequences_parralel_action(actions, current, path, sequences, appName, sequence_prefix="S"):
    path.append(current)
    
    if not actions[current].get("suivant"):  # If no successors, store the sequence
        sequence_name = f"{sequence_prefix}{len(sequences) + 1}"
        sequences.append((sequence_name, ", ".join(path)))
    else:
        for next_action in actions[current].get("suivant", []):
            generate_sequences_parralel_action(actions, next_action, path[:], sequences, appName, sequence_prefix)  # Pass a copy of path


def generate_sequences_without_parallelel(actions, current, path, sequences, appName):
    path.append(current)
    
    if not actions[current].get("suivant"):  # If no successors, store the sequence
        sequences.append(", ".join(path))
    else:
        for next_action in actions[current]["suivant"]:
            generate_sequences_without_parallelel(actions, next_action, path[:], sequences, appName)  # Pass a copy of path
        
    result = {}
    for i, seq in enumerate(sequences, 1):
        result[f"{appName}.S{i}"] = {"actions": seq, "annotations": {"quality": round(random.uniform(0, 1), 2)}}
    
    return result


def parsing_without_parallelel(data1, output_yaml_path):
    
    data = data1
    
    manifest = {"packages": {}}

    for pckName, package in data.get("packages", {}).items():
        # print(package.get("app", {}).items())
        for appName, seq in package.get("app", {}).items():
            actions = data["packages"][pckName]["app"][appName]["actions"]
            old_sequences = data["packages"][pckName]["app"][appName]["sequences"]
            # start_action = "start"
            start_action = next(iter(actions))
            sequences = generate_sequences_without_parallelel(actions, start_action, [], [], appName)

            sequences.update(old_sequences)

            # Remove "suivant" from actions
            for _, action in seq.get("actions", {}).items():
                del action["suivant"]

            manifest["packages"][pckName] = data["packages"][pckName]["app"][appName]

            manifest["packages"][pckName]["sequences"] = sequences
    
    with open(output_yaml_path, 'w', encoding='utf-8') as file:
        yaml.dump(manifest, file, allow_unicode=True, default_flow_style=False, sort_keys=False)
    

def parsing_parralel_action(input_yaml_path, output_yaml_path):
    with open(input_yaml_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    
    manifest = {"packages": {}}
    
    for pckName, package in data.get("packages", {}).items():
        for appName, seq in package.get("app", {}).items():
            actions = seq.get("actions", {})
            
            # Transformer les actions parallèles et récupérer les séquences générées
            sequences = process_parallel_actions(actions)
            
            formatted_sequences = {
                seq_name: {"actions": actions_seq}
                for seq_name, actions_seq in sequences.items()
            }
            
            manifest["packages"][pckName] = {
                "app": {appName: {"actions": actions, "sequences": formatted_sequences}}
            }
        
    parsing_without_parallelel(manifest, output_yaml_path)
    
# Example usage
parsing_parralel_action('../manifest/manifest.yaml', 'Manifest.yaml')
