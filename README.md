activate virtual environnement : . .venv/bin/activate

installer les dépendances : pip install -r requirements.txt

créer un fichier .env et ajouter OPENWHISK_AUTH = 'authentification_pour_openwhisk'

lancer l'api :  flask --app proxy.py run
