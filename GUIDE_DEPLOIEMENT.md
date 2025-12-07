# 🚀 Guide de Déploiement sur AwardSpace.net

## 📋 Prérequis

Votre jeu de questions est une application Flask (Python). AwardSpace.net offre un hébergement gratuit mais avec des limitations. Voici les options :

### Option 1 : Hébergement Python sur PythonAnywhere (RECOMMANDÉ)
PythonAnywhere offre un hébergement gratuit spécialisé pour Flask/Django.

### Option 2 : Utiliser AwardSpace avec limitations
AwardSpace gratuit ne supporte pas Python. Vous devrez :
- Utiliser un hébergeur supportant Python/Flask
- Ou migrer vers PHP/MySQL (nécessite réécriture complète)

---

## 🎯 SOLUTION RECOMMANDÉE : PythonAnywhere (Gratuit)

### Étape 1 : Créer un compte
1. Allez sur https://www.pythonanywhere.com
2. Créez un compte gratuit (Beginner)
3. Confirmez votre email

### Étape 2 : Uploader les fichiers
1. Dans PythonAnywhere, allez dans **Files**
2. Créez un dossier `quiz_game`
3. Uploadez tous les fichiers :
   - `app.py`
   - `requirements.txt`
   - `wsgi.py`
   - `config.py`
   - Dossier `static/` (tout le contenu)
   - Dossier `templates/` (tout le contenu)
   - `Questions.csv`
   - `Questions_elec.csv`
   - `Questions_meca.csv`

### Étape 3 : Installer les dépendances
1. Ouvrez une **Bash console**
2. Exécutez :
```bash
cd quiz_game
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Étape 4 : Configurer Web App
1. Allez dans l'onglet **Web**
2. Cliquez sur **Add a new web app**
3. Choisissez **Manual configuration**
4. Choisissez **Python 3.10**
5. Dans **Code**, section **Source code**, mettez : `/home/VOTRE_USERNAME/quiz_game`
6. Dans **WSGI configuration file**, cliquez sur le lien et remplacez tout par :

```python
import sys
import os

# Ajouter le chemin de votre projet
path = '/home/VOTRE_USERNAME/quiz_game'
if path not in sys.path:
    sys.path.insert(0, path)

# Activer l'environnement virtuel
activate_this = '/home/VOTRE_USERNAME/quiz_game/venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# Importer l'application Flask
from app import app as application
```

7. Dans **Virtualenv**, mettez : `/home/VOTRE_USERNAME/quiz_game/venv`
8. Cliquez sur **Reload** en haut de la page

### Étape 5 : Créer le dossier instance
1. Dans **Files**, créez le dossier `quiz_game/instance`
2. La base de données sera créée automatiquement au premier accès

### Étape 6 : Accéder à votre site
Votre site sera disponible à : `https://VOTRE_USERNAME.pythonanywhere.com`

---

## 🔧 ALTERNATIVE : Autres Hébergeurs Python Gratuits

### 1. **Render.com** (Gratuit avec limitations)
- Supporte Flask nativement
- Redémarre après 15 min d'inactivité
- https://render.com

### 2. **Railway.app** (Gratuit limité)
- Très facile à déployer
- 500h gratuites/mois
- https://railway.app

### 3. **Fly.io** (Gratuit limité)
- Support complet Python
- Configuration via fichier
- https://fly.io

---

## 📦 Fichiers à Uploader

Assurez-vous d'uploader ces fichiers :

### Fichiers Python
- ✅ `app.py` - Application principale
- ✅ `wsgi.py` - Point d'entrée WSGI
- ✅ `config.py` - Configuration
- ✅ `requirements.txt` - Dépendances

### Fichiers de données
- ✅ `Questions.csv` - Questions Thermodynamique
- ✅ `Questions_elec.csv` - Questions Électricité  
- ✅ `Questions_meca.csv` - Questions Mécanique

### Dossiers
- ✅ `static/` - CSS, JS (style.css, script.js, auth.css, auth.js)
- ✅ `templates/` - HTML (index.html, auth.html)
- ✅ `instance/` - Base de données (créé automatiquement)

### Fichiers à NE PAS uploader
- ❌ `.venv/` - Environnement virtuel local
- ❌ `__pycache__/` - Cache Python
- ❌ `.DS_Store` - Fichiers Mac
- ❌ `app_backup.py`, `app_old_backup.py` - Anciennes versions
- ❌ `jeu_questions.py` - Ancienne version terminal
- ❌ `verifier_csv.py` - Outil de développement

---

## ⚙️ Configuration de Production

### Modifier app.py pour la production

Changez la dernière ligne de `app.py` :

**Local (développement)** :
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

**Production** :
```python
if __name__ == '__main__':
    app.run(debug=False)  # Désactiver le mode debug en production
```

### Sécurité

Dans `config.py`, changez la clé secrète :
```python
SECRET_KEY = 'VOTRE_CLE_SUPER_SECRETE_COMPLEXE_A_GENERER'
```

Générer une clé sécurisée :
```python
import secrets
print(secrets.token_hex(32))
```

---

## 🐛 Dépannage

### Erreur 500
- Vérifiez les logs dans PythonAnywhere
- Assurez-vous que tous les fichiers sont uploadés
- Vérifiez que le dossier `instance/` existe

### Erreur de base de données
- Supprimez `instance/thermodynamics_game.db`
- Rechargez l'application (elle recréera la DB)

### CSS/JS ne se charge pas
- Vérifiez que le dossier `static/` est au bon endroit
- Vérifiez les chemins dans les templates

### Compte gratuit PythonAnywhere limité
- 1 application web
- 512 MB d'espace disque
- Trafic limité
- Redémarrage automatique tous les 3 mois

---

## 📱 Fonctionnalités de votre jeu

✅ 3 matières disponibles :
- 🔥 Thermodynamique (50 questions)
- ⚡ Électricité (49 questions)
- ⚙️ Mécanique (49 questions)

✅ Système de scoring :
- +10 points pour bonne réponse
- -5 points pour mauvaise réponse
- 0 point si skip toutes les réponses

✅ Mode révision des questions ratées

✅ Sauvegarde/Reprise des parties

✅ Multi-joueurs avec classement

✅ Authentification utilisateurs

---

## 🆘 Support

Si vous rencontrez des problèmes :
1. Consultez les logs de l'hébergeur
2. Vérifiez que tous les fichiers sont présents
3. Testez localement d'abord avec `python app.py`

---

## 📊 Statistiques du Projet

- **Langage** : Python 3.10+
- **Framework** : Flask 2.3
- **Base de données** : SQLite
- **Frontend** : HTML5, CSS3, JavaScript (Vanilla)
- **Questions totales** : 148 questions
- **Thèmes** : Thermodynamique, Électricité, Mécanique

---

Bon déploiement ! 🚀
