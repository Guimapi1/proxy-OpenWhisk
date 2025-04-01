# parallel_process_template.py

import requests
from multiprocessing import Process, Manager, Lock
import os

AUTH = "23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP"
OPENWHISK_URL = f"http://{AUTH}@172.17.0.1:3233/api/v1"

def start(action, args, result, lock):
    # action : le nom de l'action
    # result : Le dict pour garder les résultats
    
    apihost = f"{OPENWHISK_URL}/namespaces/_/actions/greenFaas/{action}?blocking=true&result=true"

    # print(f"hello, I'm {action}")
    
    r = requests.post(apihost, 
                    headers={"Content-Type": "application/json"}, 
                    params=args)
    with lock:
        result.update(r.json())  # Met à jour le résultat avec la réponse de l'API

def main(args):

    # Initialiser le lock, le manager et le dictionnaire partagé pour les résultats
    lock = Lock()
    manager = Manager()
    result = manager.dict()

    # Créer un processus pour chaque élément de combo
    processes = []
    for _, action_name in {'branche1': 'a9.branche1.seq1', 'branche2': 'a9.branche2.seq1'}.items():
        p = Process(target=start, args=(action_name, args, result, lock))
        processes.append(p)
        p.start()

    # Attendre que tous les processus se terminent
    for p in processes:
        p.join()

    # Convertir le résultat en dict normal et ajouter les valeurs de validation
    result = dict(result)

    return result
