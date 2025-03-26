# import yaml
# import json
# import random  # To generate random quality values

# def generateSequences(actions, current, path, sequences, appName):
#     path.append(current)
    
#     if not actions[current].get("suivant"):  # If no successors, store the sequence
#         sequences.append(", ".join(path))
#     else:
#         for next_action in actions[current]["suivant"]:
#             generateSequences(actions, next_action, path[:], sequences, appName)  # Pass a copy of path
    
#     result = {}
#     for i, seq in enumerate(sequences, 1):
#         result[f"{appName}.S{i}"] = {"actions": seq, "annotations": {"quality": round(random.uniform(0, 1), 2)}}
    
#     return result


# def parsing(input_yaml_path, output_yaml_path):
#     with open(input_yaml_path, 'r', encoding='utf-8') as file:
#         data = yaml.safe_load(file)
    
#     manifest = {"packages": {}}

 
#     for pckName, package in data.get("packages", {}).items():
#         # print(package.get("app", {}).items())
#         for appName, seq in package.get("app", {}).items():
#             actions = data["packages"][pckName]["app"][appName]["actions"]
#             start_action = "start"
#             sequences = generateSequences(actions, start_action, [], [], appName)

#             # Remove "suivant" from actions
#             for _, action in seq.get("actions", {}).items():
#                 del action["suivant"]

#             manifest["packages"][pckName] = data["packages"][pckName]["app"][appName]

#             manifest["packages"][pckName]["sequences"] = sequences
    

#     with open(output_yaml_path, 'w', encoding='utf-8') as file:
#         yaml.dump(manifest, file, allow_unicode=True, default_flow_style=False, sort_keys=False)
    

#     # print(json.dumps(manifest, indent=4))


# # # Example usage
# parsing('../manifest/manifest.yaml', 'Manifest.yaml')


import yaml
import random  # To generate random quality values

def generateSequences(actions, current, path, sequences, appName, sequence_prefix="S"):
    path.append(current)
    # print('current', current)
    
    if "parallel" in actions[current] :
        parallel_branches = actions[current]["parallel"]
        for i, (branch_name, branch_start) in enumerate(parallel_branches.items(), 1):
            branch_sequences = []
            actions_branch = actions[current]["parallel"][branch_name]
            generateSequences(actions_branch, list(branch_start.keys())[0], [], branch_sequences, appName, f"{current}.branche{i}.seq")
            sequences.extend(branch_sequences)
    elif not actions[current].get("suivant"):  # If no successors, store the sequence
        sequence_name = f"{sequence_prefix}{len(sequences) + 1}"
        sequences.append((sequence_name, ", ".join(path)))
    else:
        for next_action in actions[current]["suivant"]:
            generateSequences(actions, next_action, path[:], sequences, appName, sequence_prefix)  # Pass a copy of path

def parsing(input_yaml_path, output_yaml_path):
    with open(input_yaml_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    
    manifest = {"packages": {}}
    
    for pckName, package in data.get("packages", {}).items():
        for appName, seq in package.get("app", {}).items():
            actions = seq.get("actions", {})
            start_action = "start"
            sequences = []
            
            generateSequences(actions, start_action, [], sequences, appName)
            
            formatted_sequences = {
                f"{appName}.{seq_name}" if seq_name.startswith('S') else f"{seq_name}": {
                    "actions": actions_seq,
                    "annotations": {"quality": round(random.uniform(0, 1), 2)}
                }
                for seq_name, actions_seq in sequences
            }

            
            # Remove "suivant" from actions to avoid redundancy in output
            for action in actions.values():
                action.pop("suivant", None)
            
            manifest["packages"][pckName] = {
                "app": {appName: {"actions": actions, "sequences": formatted_sequences}}
            }
    
    with open(output_yaml_path, 'w', encoding='utf-8') as file:
        yaml.dump(manifest, file, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
# Example usage
parsing('../manifest/manifest.yaml', 'Manifest.yaml')
