import yaml
import json
import random  # To generate random quality values

def generateSequences(actions, current, path, sequences, appName):
    path.append(current)
    
    if not actions[current].get("suivant"):  # If no successors, store the sequence
        sequences.append(", ".join(path))
    else:
        for next_action in actions[current]["suivant"]:
            generateSequences(actions, next_action, path[:], sequences, appName)  # Pass a copy of path
    
    result = {}
    for i, seq in enumerate(sequences, 1):
        result[f"{appName}.S{i}"] = {"actions": seq, "annotations": {"quality": round(random.uniform(0, 1), 2)}}
    
    return result


def parsing(input_yaml_path, output_yaml_path):
    with open(input_yaml_path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    
    manifest = {"packages": {}}
 
    for pckName, package in data.get("packages", {}).items():
        
        for appName, seq in package.get("app", {}).items():

            actions = data["packages"][pckName]["app"][appName]["actions"]
            start_action = "a0"
            sequences = generateSequences(actions, start_action, [], [], appName)

            # Remove "suivant" from actions
            for _, action in seq.get("actions", {}).items():
                del action["suivant"]

            manifest["packages"][pckName] = data["packages"][pckName]["app"][appName]

            manifest["packages"][pckName]["sequences"] = sequences
    

    with open(output_yaml_path, 'w', encoding='utf-8') as file:
        yaml.dump(manifest, file, allow_unicode=True, default_flow_style=False, sort_keys=False)
    

    # print(json.dumps(manifest, indent=4))


# # Example usage
parsing('manifest.yaml', 'Manifest.yaml')
