# 🚀 Guide de Déploiement sur Render.com

## 📋 Pourquoi Render.com ?

- ✅ **Gratuit** (avec limitations)
- ✅ **Facile** à utiliser
- ✅ **Support Python/Flask** natif
- ✅ **Déploiement automatique** depuis GitHub
- ✅ **SSL gratuit** (HTTPS)
- ⚠️ Se met en veille après 15 min d'inactivité (gratuit)

---

## 🎯 Méthode 1 : Déploiement Direct (Recommandé)

### Étape 1 : Créer un compte Render

1. Allez sur https://render.com
2. Cliquez sur **"Get Started"**
3. Inscrivez-vous avec GitHub, Google ou email

### Étape 2 : Créer un dépôt GitHub (optionnel mais recommandé)

1. Allez sur https://github.com
2. Créez un nouveau dépôt (repository)
3. Uploadez tous les fichiers du dossier `quiz_game_deploy/`

**OU utilisez GitHub Desktop ou la ligne de commande :**

```bash
cd quiz_game_deploy
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/VOTRE_USERNAME/quiz-game.git
git push -u origin main
```

### Étape 3 : Créer un Web Service sur Render

1. Dans le dashboard Render, cliquez sur **"New +"**
2. Sélectionnez **"Web Service"**
3. Connectez votre compte GitHub (si vous avez créé un repo)
4. Sélectionnez votre dépôt `quiz-game`

**Configuration :**
- **Name** : `quiz-game` (ou votre choix)
- **Region** : `Frankfurt (Europe Central)` (plus proche)
- **Branch** : `main`
- **Runtime** : `Python 3`
- **Build Command** : `pip install -r requirements.txt`
- **Start Command** : `gunicorn --bind 0.0.0.0:$PORT app:app`
- **Instance Type** : `Free`

5. Cliquez sur **"Create Web Service"**

### Étape 4 : Variables d'Environnement

Dans les paramètres de votre service :

1. Allez dans **"Environment"**
2. Ajoutez les variables :

```
SECRET_KEY = votre_cle_secrete_super_complexe_a_generer
```

Pour générer une clé sécurisée :
```python
import secrets
print(secrets.token_hex(32))
```

### Étape 5 : Déploiement

Render va automatiquement :
- 📦 Installer les dépendances
- 🚀 Démarrer l'application
- 🌐 Vous donner une URL comme : `https://quiz-game-xxxx.onrender.com`

⏱️ Le premier déploiement prend 5-10 minutes.

---

## 🎯 Méthode 2 : Upload Direct (Sans GitHub)

Si vous ne voulez pas utiliser GitHub :

1. Créez un **nouveau Web Service** sur Render
2. Sélectionnez **"Build and deploy from a Git repository"**
3. Cliquez sur **"Public Git repository"**
4. Mettez l'URL d'un repo public OU uploadez manuellement

**Note** : L'upload manuel n'est pas directement supporté. Il faut utiliser Git.

---

## ⚙️ Configuration Avancée

### Fichier `render.yaml` (Déjà Créé)

Le fichier `render.yaml` dans votre package configure automatiquement :
- Type de service (web)
- Runtime Python
- Commandes de build et start
- Variables d'environnement

### Base de Données

Render utilise SQLite par défaut (inclus dans le package).

**⚠️ IMPORTANT** : Sur le plan gratuit, les données sont **perdues** lors du redémarrage du service !

Pour une base de données persistante, vous devrez :
- Upgrader vers un plan payant ($7/mois)
- OU utiliser une base de données externe (PostgreSQL gratuit sur Render)

---

## 🐛 Dépannage

### Service ne démarre pas

1. Vérifiez les **logs** dans Render dashboard
2. Assurez-vous que `gunicorn` est dans `requirements.txt`
3. Vérifiez la commande de démarrage

### Erreur "Application failed to respond"

- Le service se met en veille (gratuit)
- Premier chargement peut prendre 30 secondes
- Rechargez la page

### Base de données vide après redémarrage

- C'est normal sur le plan gratuit
- Les données sont en mémoire
- Solution : Plan payant ou base externe

---

## 📊 Limitations du Plan Gratuit

- ⚠️ **750 heures/mois** (environ 31 jours)
- ⚠️ **Se met en veille** après 15 min d'inactivité
- ⚠️ **Réveil lent** (30 sec au premier chargement)
- ⚠️ **Données non persistantes** (SQLite en mémoire)
- ✅ **SSL gratuit** (HTTPS)
- ✅ **Domaine personnalisé** possible

---

## 🚀 Après le Déploiement

### Votre application sera disponible à :
```
https://votre-nom-service.onrender.com
```

### Fonctionnalités :
- 🎮 **3 matières** : Thermodynamique, Électricité, Mécanique
- 📝 **148 questions** au total
- 🏆 **Système de scores** avec classement
- 👥 **Multi-joueurs** avec authentification
- 💾 **Sauvegarde/Reprise** des parties
- 📱 **Responsive** pour mobile

---

## 🔄 Mises à Jour

Pour mettre à jour votre application :

1. Modifiez les fichiers localement
2. Committez sur GitHub :
   ```bash
   git add .
   git commit -m "Mise à jour"
   git push
   ```
3. Render redéploie **automatiquement** !

---

## 💰 Upgrade vers Plan Payant (Optionnel)

Pour éviter les limitations :

**Starter Plan** ($7/mois) :
- ✅ Toujours actif (pas de veille)
- ✅ Données persistantes
- ✅ Plus de ressources
- ✅ Meilleure performance

---

## 🆘 Besoin d'Aide ?

1. Consultez les **logs** dans Render dashboard
2. Documentation Render : https://render.com/docs
3. Support Render : support@render.com

---

## ✅ Checklist de Déploiement

- [ ] Compte Render créé
- [ ] Dépôt GitHub créé (optionnel)
- [ ] Fichiers uploadés
- [ ] Web Service créé
- [ ] Variables d'environnement configurées
- [ ] Application déployée
- [ ] URL testée
- [ ] Création du premier compte utilisateur

---

**Bon déploiement sur Render ! 🎉**

*Votre jeu sera accessible en ligne en quelques minutes !*
