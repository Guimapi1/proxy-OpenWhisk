import yaml
import random
import itertools
import math


def find_initial_nodes(actions):
    
    # Step 1: Collect all action names
    all_nodes = set(actions.keys())
    
    # Step 2: Collect all nodes that appear in "suivant" not forget nodes in parallel actions
    referenced_nodes = set()
    for action in actions.values():
        if "suivant" in action:
            referenced_nodes.update(action.get("suivant", []))
        if "parallel" in action:
            referenced_nodes.update(action.get("parallel", {}).get("suivant", [])) 

    # Step 3: Find nodes that are not in "suivant" of any action
    initial_nodes = all_nodes - referenced_nodes
    
    return list(initial_nodes)


def generate_parallel_combinations(branch_sequences):
    
    """Génère toutes les combinaisons possibles en prenant une séquence par branche."""
    
    keys, values = zip(*branch_sequences.items())
    print(keys)
    combinations = list(itertools.product(*values))
    print(combinations)
    
    return [dict(zip(keys, combo)) for combo in combinations]

def process_parallel_actions(actions):
    
    """Réécrit le YAML en transformant les actions parallèles en actions combinées."""
    
    new_actions = {}
    sequences = {}
    
    for action, details in actions.items():
        if "parallel" in details:
            branches = details["parallel"]
            branch_sequences = {}

            for branch, sub_actions in branches.items():
                
                if isinstance(sub_actions, dict):  # Vérifier si sub_actions est un dictionnaire  
                    starts = find_initial_nodes(sub_actions)
                    sequences_list = []
                    
                    for branch_start in starts:
                        generate_sequences_parallel_action(sub_actions, branch_start, [], sequences_list, action, [], f"{action}.{branch}.seq")
                        
                    sequences.update({seq_name: (quality, seq) for seq_name, quality, seq in sequences_list})
                    branch_sequences[branch] = list(sequences.keys())[-len(sequences_list):]  # Récupérer les noms des séquences il faut passer les autres infos 
                   
                    for action_name, action_data in sub_actions.items():
                        if action_name not in new_actions:
                            new_actions[action_name] = action_data
            
            combinations = generate_parallel_combinations(branch_sequences)  # Générer toutes les combinaisons possibles
            suivant = details["parallel"].get("suivant", [])
            new_action_names = []
            
            for i, combo in enumerate(combinations, 1):
                new_action_name = f"A{i}"
                quality = []
                new_action_names.append(new_action_name)
                
                for _, action_name in combo.items(): 
                    quality.append(sequences[action_name][0])
                    
                new_actions[new_action_name] = {
                    "function": f"./action/{new_action_name}.py",
                    "suivant": suivant,   
                    "annotations" : {"quality" : math.prod(quality)} 
                }
                
                action_args = {key: value for key, value in combo.items()}  # est ce que la variable action_args est utilisé ? 
                
                with open("template.py", "r") as template:
                    content = template.read()
                
               
                content = content.replace("action_args.items()", f"{combo}.items()")
                content = content.replace("main(args, action_args)", "main(args)") # pourquoi "action_args" ?

                # Écrire le fichier Python
                with open(f"./action/{new_action_name}.py", "w") as file: # les deux écritures ne sont peut être pas necessaire. 
                    file.write(content)
            
            # Modifier l'action originale pour pointer vers les nouvelles actions combinées
            details["suivant"] = new_action_names
            del details["parallel"]

    actions.update(new_actions)
    return sequences


def generate_sequences_parallel_action(actions, current, path, sequences, app_name, quality, sequence_prefix="S"):
    
    """Génère les séquences pour les actions parallèles."""
    
    path.append(current)
    quality.append(actions[current].get("annotations", {}).get("quality", 1))

    if not actions[current].get("suivant"):  # Si aucune action suivante, stocker la séquence
        sequence_name = f"{sequence_prefix}{len(sequences) + 1}"
        sequences.append((sequence_name, math.prod(quality), ", ".join(path)))
    else:
        for next_action in actions[current].get("suivant", []):
            generate_sequences_parallel_action(actions, next_action, path[:], sequences, app_name, quality[:], sequence_prefix)


def generate_sequences_without_parallel(actions, current, path, sequences, app_name, quality):
     
    """Génère les séquences sans actions parallèles."""
    
    path.append(current)
    quality.append(actions[current].get("annotations", {}).get("quality", 1))

    if not actions[current].get("suivant"):  # Si aucune action suivante, stocker la séquence
            sequences.append((", ".join(path), quality ))
    else:
        for next_action in actions[current]["suivant"]:
            generate_sequences_without_parallel(actions, next_action, path[:], sequences, app_name, quality[:])


def parsing_without_parallel(data, output_yaml_path, start_actions):
    
    """Traite les actions sans parallèle et génère un fichier YAML."""
    
    manifest = {"packages": {}}
    for pck_name, package in data.get("packages", {}).items():
        
        for app_name, app in package.get("app", {}).items():
            actions = app["actions"]
            sequences = app["sequences"]
            newsequences = []
            
            for start_action in start_actions:
                generate_sequences_without_parallel(actions, start_action, [], newsequences, app_name, [])
            
            for i, seq in enumerate(newsequences, 1):
                sequences[f"{app_name}.S{i}"] = {
                    "actions": seq[0],
                    "annotations": {"quality":  math.prod(seq[1])}  
                }
 
            # Supprimer "suivant" des actions
            for _, action in app.get("actions", {}).items():
                if "suivant" in action: 
                    del action["suivant"]
                 

            manifest["packages"][pck_name] = package["app"][app_name]
            manifest["packages"][pck_name]["sequences"] = sequences

    with open(output_yaml_path, 'w', encoding='utf-8') as file: # Sauvegarder le fichier YAML
        yaml.dump(manifest, file, allow_unicode=True, default_flow_style=False, sort_keys=False)


def parsing_parallel_actions(input_yaml_path, output_yaml_path):
    
    """Traite les actions parallèles et génère un fichier YAML."""
    
    with open(input_yaml_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)

    manifest = {"packages": {}}
    formatted_sequences = {}

    for pck_name, package in data.get("packages", {}).items():
        
        for app_name, app in package.get("app", {}).items():
            actions = app.get("actions", {})
            start_actions = find_initial_nodes(actions)
            sequences = process_parallel_actions(actions) # Créer les actions parallèles et récupérer les séquences générées
            
            formatted_sequences = {
                seq_name: {
                    "actions": actions_seq,
                    "annotations" : { "quality" : quality}
                }
                for seq_name, (quality, actions_seq) in sequences.items()
            }
            
              
            manifest["packages"][pck_name] = {
                "app": {app_name: {"actions": actions, "sequences": formatted_sequences}}
            }
   
    parsing_without_parallel(manifest, output_yaml_path, start_actions)  # Traiter les actions non parallèle


# Exemple d'utilisation
parsing_parallel_actions('manifest.yaml', 'Manifest.yaml')
