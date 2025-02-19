from flask import Flask, request, jsonify # type: ignore
import requests
import random
from dotenv import dotenv_values # type: ignore


AUTH = dotenv_values(".env")['OPENWHISK_AUTH']  
BASE_URL = "/api/v1/namespaces"
OPENWHISK_URL = f"http://{AUTH}@172.17.0.1:3233/api/v1"


app = Flask(__name__)

def handle_request(namespace, filter_string, package_name=None):

    if not namespace:  
        namespace = '_'

    # Récupérer les query params 
    min_quality = request.args.get("min_quality", type=float, default=0)
    max_quality = request.args.get("max_quality", type=float, default=1)

    try:
        # Récupérer toutes les actions du namespace depuis OpenWhisk
        actions_url = f"{OPENWHISK_URL}/namespaces/{namespace}/actions"
        response = requests.get(actions_url)

        if response.status_code != 200:
            return jsonify({"error": "Erreur lors de la récupération des actions"}), response.status_code

        actions = response.json()

        # Filtrer les séquences qui commencent par filter_string et respectent min/max
        sequences = [
            action for action in actions
            if action['name'].startswith(filter_string)
            and min_quality <= next((ann["value"] for ann in action["annotations"] if ann["key"] == "quality"), 0) <= max_quality
        ]

        if not sequences:
            return jsonify({"error": "Aucune séquence trouvée avec ce filtre"}), 404

        random_sequence = random.choice(sequences)
        print(f"Séquence sélectionnée : {random_sequence['name']}")

        if package_name:
            openwhisk_url = f"{OPENWHISK_URL}/namespaces/{namespace}/actions/{package_name}/{random_sequence['name']}"
        else:
            openwhisk_url = f"{OPENWHISK_URL}/namespaces/{namespace}/actions/{random_sequence['name']}"

        # Invoquer la séquence sélectionnée sur OpenWhisk
        invoke_response = requests.post(openwhisk_url)

        return jsonify({
            "openwhisk_response": invoke_response.json() 
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/namespaces/<namespace>/actions/<package_name>/<filter_string>', methods=['GET'])
@app.route('/api/v1/namespaces/actions/<package_name>/<filter_string>', methods=['GET'])
def proxy_with_package(namespace='_', package_name=None, filter_string=None):
    return handle_request(namespace, filter_string, package_name)

@app.route('/api/v1/namespaces/<namespace>/actions/<filter_string>', methods=['GET'])
@app.route('/api/v1/namespaces/actions/<filter_string>', methods=['GET'])
def proxy_without_package(namespace='_', filter_string=None):
    return handle_request(namespace, filter_string)







