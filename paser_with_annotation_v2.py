import yaml
import random
import itertools


def generate_parallel_combinations(branch_sequences):
    """Génère toutes les combinaisons possibles en prenant une séquence par branche."""
    keys, values = zip(*branch_sequences.items())
    combinations = list(itertools.product(*values))
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
                    branch_start = next(iter(sub_actions))  # Récupérer la première clé
                    sequences_list = []
                    generate_sequences_parallel_action(sub_actions, branch_start, [], sequences_list, action, f"{action}.{branch}.seq")
                    sequences.update({seq_name: seq for seq_name, seq in sequences_list})
                    branch_sequences[branch] = list(sequences.keys())[-len(sequences_list):]  # Récupérer les noms des séquences

                    # new_action_key = f"{branch}.{branch_start}"

                    # Ajouter la première action de sub_actions à 'new_actions'
                    # if branch_start not in new_actions:
                    #     new_actions[branch_start] = sub_actions[branch_start]
                    for action_name, action_data in sub_actions.items():
                        if action_name not in new_actions:
                            new_actions[action_name] = action_data

            # Générer toutes les combinaisons possibles
            combinations = generate_parallel_combinations(branch_sequences)
            new_action_names = []

            suivant = details.get("suivant", [])

            for i, combo in enumerate(combinations, 1):
                new_action_name = f"A{i}"
                new_action_names.append(new_action_name)
                new_actions[new_action_name] = {
                    "function": f"../action/{new_action_name}.py",
                    "suivant": [suivant[0]] if suivant else []
                }

                # Préparation des arguments pour chaque processus
                action_args = {key: value for key, value in combo.items()}

                with open("parallel_process_template.py", "r") as template_file:
                    js_content = template_file.read()
                

                # Ajouter l'argument "action_args" à la fonction "main"
                js_content = js_content.replace("action_args.items()", f"{action_args}.items()")
                js_content = js_content.replace("main(args, action_args)", "main(args)")

                # Écrire le fichier JS avec le contenu modifié
                with open(f"../action/{new_action_name}.py", "w") as js_file:
                    js_file.write(js_content)

                # Écrire le fichier Python
                with open(f"../action/{new_action_name}.py", "w") as js_file:
                    js_file.write(js_content)
            
            # Modifier l'action originale pour pointer vers les nouvelles actions combinées
            details["suivant"].extend(new_action_names)
            del details["parallel"]

    actions.update(new_actions)
    return sequences


def generate_sequences_parallel_action(actions, current, path, sequences, app_name, sequence_prefix="S"):
    """Génère les séquences pour les actions parallèles."""
    path.append(current)

    if not actions[current].get("suivant"):  # Si aucune action suivante, stocker la séquence
        sequence_name = f"{sequence_prefix}{len(sequences) + 1}"
        sequences.append((sequence_name, ", ".join(path)))
    else:
        for next_action in actions[current].get("suivant", []):
            generate_sequences_parallel_action(actions, next_action, path[:], sequences, app_name, sequence_prefix)


def generate_sequences_without_parallel(actions, current, path, sequences, app_name):
    """Génère les séquences sans actions parallèles."""
    path.append(current)

    if not actions[current].get("suivant"):  # Si aucune action suivante, stocker la séquence
        sequences.append(", ".join(path))
    else:
        for next_action in actions[current]["suivant"]:
            generate_sequences_without_parallel(actions, next_action, path[:], sequences, app_name)

    result = {}
    for i, seq in enumerate(sequences, 1):
        result[f"{app_name}.S{i}"] = {
            "actions": seq,
            "annotations": {"quality": round(random.uniform(0, 1), 2)}
        }

    return result


def parsing_without_parallel(data, output_yaml_path):
    """Traite les actions sans parallèle et génère un fichier YAML."""
    manifest = {"packages": {}}

    for pck_name, package in data.get("packages", {}).items():
        for app_name, app in package.get("app", {}).items():
            actions = app["actions"]
            old_sequences = app["sequences"]
            # start_action = "start"
            start_action = next(iter(actions))  # Utilise la première action comme point de départ
            sequences = generate_sequences_without_parallel(actions, start_action, [], [], app_name)

            sequences.update(old_sequences)

            # Supprimer "suivant" des actions
            for _, action in app.get("actions", {}).items():
                del action["suivant"]

            manifest["packages"][pck_name] = package["app"][app_name]
            manifest["packages"][pck_name]["sequences"] = sequences

    # Sauvegarder le fichier YAML
    with open(output_yaml_path, 'w', encoding='utf-8') as file:
        yaml.dump(manifest, file, allow_unicode=True, default_flow_style=False, sort_keys=False)


def parsing_parallel_actions(input_yaml_path, output_yaml_path):
    """Traite les actions parallèles et génère un fichier YAML."""
    with open(input_yaml_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)

    manifest = {"packages": {}}

    for pck_name, package in data.get("packages", {}).items():
        for app_name, app in package.get("app", {}).items():
            actions = app.get("actions", {})

            # Transformer les actions parallèles et récupérer les séquences générées
            sequences = process_parallel_actions(actions)

            formatted_sequences = {
                seq_name: {"actions": actions_seq}
                for seq_name, actions_seq in sequences.items()
            }

            manifest["packages"][pck_name] = {
                "app": {app_name: {"actions": actions, "sequences": formatted_sequences}}
            }

    # Traiter les actions sans parallèle
    parsing_without_parallel(manifest, output_yaml_path)


# Exemple d'utilisation
parsing_parallel_actions('manifest.yaml', 'Manifest.yaml')
