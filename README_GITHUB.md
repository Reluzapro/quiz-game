# 🎮 Jeu de Questions Multi-Matières

Application web de quiz interactif avec 3 matières : Thermodynamique, Électricité et Mécanique.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## 🚀 Déploiement sur Render

Ce projet est configuré pour un déploiement automatique sur Render.com.

### Déploiement en un clic

1. Cliquez sur le bouton "Deploy to Render" ci-dessus
2. Ou créez manuellement un Web Service et connectez ce repo

### Configuration automatique

Le fichier `render.yaml` configure automatiquement :
- Runtime Python 3.10
- Installation des dépendances
- Démarrage avec Gunicorn
- Variables d'environnement

## ✨ Fonctionnalités

- 🔥 **Thermodynamique** : 50 questions
- ⚡ **Électricité** : 49 questions
- ⚙️ **Mécanique** : 49 questions
- 🏆 Système de scoring (+10 bonne réponse, -5 mauvaise)
- 👥 Multi-joueurs avec authentification
- 💾 Sauvegarde et reprise des parties
- 📚 Mode révision pour les questions ratées
- 📱 Interface responsive (mobile-friendly)

## 🛠️ Technologies

- **Backend** : Flask (Python)
- **Base de données** : SQLite
- **Frontend** : HTML5, CSS3, JavaScript (Vanilla)
- **Authentification** : Flask-Login
- **Déploiement** : Gunicorn + Render.com

## 📋 Installation Locale

### Prérequis

- Python 3.10+
- pip

### Étapes

1. Clonez le dépôt :
```bash
git clone https://github.com/VOTRE_USERNAME/quiz-game.git
cd quiz-game
```

2. Créez un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Lancez l'application :
```bash
python app.py
```

5. Ouvrez votre navigateur :
```
http://localhost:5001
```

## 📊 Structure du Projet

```
quiz-game/
├── app.py                  # Application Flask principale
├── wsgi.py                 # Point d'entrée WSGI
├── config.py               # Configuration
├── requirements.txt        # Dépendances Python
├── render.yaml            # Configuration Render
├── Questions.csv          # Questions Thermodynamique
├── Questions_elec.csv     # Questions Électricité
├── Questions_meca.csv     # Questions Mécanique
├── static/                # CSS et JavaScript
│   ├── style.css
│   ├── script.js
│   ├── auth.css
│   └── auth.js
├── templates/             # Pages HTML
│   ├── index.html
│   └── auth.html
└── instance/              # Base de données SQLite
```

## 🎯 Règles du Jeu

1. Une réponse est proposée pour chaque question
2. Cliquez **"OUI"** si vous pensez que c'est la bonne réponse (+10 points)
3. Cliquez **"NON"** si vous pensez que c'est faux
4. ⚠️ Si vous dites "OUI" à une mauvaise réponse : -5 points
5. Si vous refusez toutes les réponses, la bonne réponse est affichée (0 point)

## 📝 Format des Questions CSV

Les fichiers CSV utilisent le point-virgule (`;`) comme séparateur :

```csv
Question;Bonne Réponse;Mauvaise 1;Mauvaise 2;Mauvaise 3
```

## 🔧 Configuration

### Variables d'Environnement

- `SECRET_KEY` : Clé secrète Flask (générée automatiquement sur Render)
- `PORT` : Port d'écoute (défini par Render)

### Base de Données

SQLite est utilisé par défaut. Sur Render (plan gratuit), les données ne sont pas persistantes.

Pour une base persistante :
- Upgrade vers un plan payant Render
- Ou utilisez PostgreSQL (gratuit sur Render)

## ⚠️ Limitations Plan Gratuit Render

- Se met en veille après 15 minutes d'inactivité
- Premier chargement lent (30 secondes)
- 750 heures/mois
- Données non persistantes (réinitialisation au redémarrage)

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Forkez le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Committez vos changements (`git commit -m 'Ajout fonctionnalité'`)
4. Pushez vers la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

## 📜 Licence

Ce projet est sous licence MIT.

## 👨‍💻 Auteur

Créé avec ❤️ pour l'apprentissage interactif

## 🆘 Support

Pour toute question ou problème :
- Consultez les [issues](https://github.com/VOTRE_USERNAME/quiz-game/issues)
- Documentation Render : https://render.com/docs

---

**Bon apprentissage ! 📚✨**
