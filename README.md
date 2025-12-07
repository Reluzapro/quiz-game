# Jeu de Questions Multi-Matières 🎮

Système de quiz interactif avec support de plusieurs matières (Thermodynamique et Électricité).

## 📁 Structure des fichiers

```
.
├── app.py                    # Application Flask actuelle (une matière)
├── app_multi_matieres.py     # Nouvelle version avec multi-matières
├── verifier_csv.py           # Outil de vérification des fichiers CSV
├── Questions.csv             # 50 questions de Thermodynamique
├── Questions_elec.csv        # 140 questions d'Électricité
├── templates/
│   ├── index.html
│   └── auth.html
└── static/
    ├── script.js
    ├── style.css
    ├── auth.js
    └── auth.css
```

## 🚀 Démarrage rapide

### Activer l'environnement virtuel
```bash
source .venv/bin/activate
```

### Lancer le serveur actuel (une matière)
```bash
python app.py
```

### Lancer le serveur multi-matières
```bash
python app_multi_matieres.py
```

Le serveur démarre sur http://127.0.0.1:5001 et http://172.20.10.2:5001

## 🔍 Vérification des fichiers CSV

### Utilisation de base
```bash
python verifier_csv.py Questions.csv
python verifier_csv.py Questions_elec.csv
```

### Vérifier plusieurs fichiers en une fois
```bash
python verifier_csv.py Questions.csv Questions_elec.csv
```

### Format attendu
Chaque ligne doit contenir **exactement 5 colonnes** séparées par des **points-virgules** :
```
Question;Réponse Correcte;Distracteur 1;Distracteur 2;Distracteur 3
```

### Exemple de ligne valide
```
Quelle est l'unité de la résistance électrique ?;Ohm (Ω);Volt (V);Ampère (A);Watt (W)
```

### ⚠️ Erreurs courantes à éviter
1. **Points-virgules dans les réponses** : Utiliser "à" au lieu de ";" dans les intervalles
   - ❌ `[0; f_p]`
   - ✅ `[0 à f_p]`

2. **Colonnes vides** : Toutes les 5 colonnes doivent contenir du texte

3. **Nombre incorrect de séparateurs** : Exactement 4 points-virgules par ligne

## 📚 Ajouter une nouvelle matière

### Étape 1 : Créer le fichier CSV
Créez un fichier `Questions_nommatiere.csv` avec le format :
```csv
Question;Réponse Correcte;Distracteur 1;Distracteur 2;Distracteur 3
Première question ?;Bonne réponse;Mauvaise 1;Mauvaise 2;Mauvaise 3
Deuxième question ?;Bonne réponse;Mauvaise 1;Mauvaise 2;Mauvaise 3
```

### Étape 2 : Vérifier le fichier
```bash
python verifier_csv.py Questions_nommatiere.csv
```

### Étape 3 : Ajouter dans app_multi_matieres.py
Modifier le dictionnaire `MATIERES` :
```python
MATIERES = {
    'thermo': {
        'nom': 'Thermodynamique',
        'fichier': 'Questions.csv',
        'emoji': '🔥'
    },
    'elec': {
        'nom': 'Électricité',
        'fichier': 'Questions_elec.csv',
        'emoji': '⚡'
    },
    'nouvelle': {
        'nom': 'Nouvelle Matière',
        'fichier': 'Questions_nommatiere.csv',
        'emoji': '🎯'
    }
}
```

## 🎮 Fonctionnalités

### Système de jeu
- ✅ Quiz avec 4 réponses proposées aléatoirement
- ✅ Score : +10 correct, -5 incorrect, 0 si refus de toutes les réponses
- ✅ Affichage de la bonne réponse si toutes refusées
- ✅ Mode révision pour les questions ratées/ignorées
- ✅ Sauvegarde/reprise de partie

### Système multi-joueurs
- ✅ Comptes utilisateurs (nom d'utilisateur + mot de passe)
- ✅ Tableau des scores par matière
- ✅ Synchronisation entre appareils

### Multi-matières (app_multi_matieres.py)
- ✅ Sélection de la matière avant de commencer
- ✅ Scores séparés par matière
- ✅ Parties sauvegardées séparées par matière

## 📊 Statistiques actuelles

- **Thermodynamique** : 50 questions
- **Électricité** : 140 questions
- **Total** : 190 questions

## 🔧 Migration vers multi-matières

Pour basculer vers la version multi-matières :

1. Arrêter le serveur actuel (Ctrl+C)
2. Renommer l'ancien fichier :
   ```bash
   mv app.py app_old.py
   mv app_multi_matieres.py app.py
   ```
3. Relancer le serveur :
   ```bash
   python app.py
   ```

⚠️ **Note** : La base de données devra être mise à jour avec la colonne `matiere`. Vous pouvez soit :
- Supprimer `thermodynamics_game.db` pour repartir de zéro
- Ou garder les données existantes (elles seront associées à 'thermo' par défaut)

## 🌐 Accès depuis mobile

### Option 1 : Réseau local
Accédez depuis votre téléphone via : http://172.20.10.2:5001

### Option 2 : Ngrok (accès internet)
```bash
ngrok http 5001
```
Utilisez l'URL fournie (ex: https://xxx.ngrok-free.dev)

## 📝 Notes techniques

- **Base de données** : SQLite (`thermodynamics_game.db`)
- **Port** : 5001
- **Encodage** : UTF-8 pour les fichiers CSV
- **Framework** : Flask avec Flask-Login et Flask-SQLAlchemy
