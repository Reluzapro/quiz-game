#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# IMPORTANT: Monkey patch eventlet AVANT tous les autres imports
import eventlet
eventlet.monkey_patch()

# Supprimer les warnings socket non critiques
import warnings
warnings.filterwarnings('ignore', message='.*Bad file descriptor.*')

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.pool import NullPool
import csv
import random
import os
import uuid
import json
import string
import logging
from datetime import datetime, timedelta
from pathlib import Path
from config import Config

# Réduire le niveau de log pour eventlet/socket
logging.getLogger('eventlet.wsgi.server').setLevel(logging.WARNING)

app = Flask(__name__)
app.config.from_object(Config)

# Configuration SQLAlchemy pour eventlet - QueuePool avec pool_pre_ping pour détecter les connexions mortes
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'max_overflow': 10,
    'pool_pre_ping': True,  # Vérifie que la connexion est vivante avant utilisation
    'pool_recycle': 300,    # Recycle les connexions après 5 minutes
}

db = SQLAlchemy(app)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='eventlet',
    logger=False,  # Désactive les logs verbeux de SocketIO
    engineio_logger=False,  # Désactive les logs verbeux de Engine.IO
    ping_timeout=60,
    ping_interval=25
)
login_manager = LoginManager(app)
login_manager.login_view = 'auth_page'
login_manager.login_message = None

# Configuration des matières disponibles avec hiérarchie
MATIERES = {
    'maths': {
        'nom': 'Mathématiques',
        'fichier': os.path.join('Questions', 'Maths', 'Questions_maths.csv'),
        'emoji': '📐',
        'categorie': None  # Matière directe (pas de sous-catégories)
    },
    'physique_thermo': {
        'nom': 'Thermodynamique',
        'fichier': os.path.join('Questions', 'Physique', 'Questions_thermodynamique.csv'),
        'emoji': '🔥',
        'categorie': 'physique',  # Sous-catégorie de Physique
    },
    'physique_thermique': {
        'nom': 'Thermique',
        'fichier': os.path.join('Questions', 'Physique', 'Questions_thermique.csv'),
        'emoji': '🔥',
        'categorie': 'physique',  # Sous-catégorie de Physique
    },
    'meca': {
        'nom': 'Mécanique',
        'fichier': os.path.join('Questions', 'Meca', 'Questions_meca.csv'),
        'emoji': '⚙️',
        'categorie': None
    },
    'elec': {
        'nom': 'Électricité',
        'fichier': os.path.join('Questions', 'Elec', 'Questions_elec.csv'),
        'emoji': '⚡',
        'categorie': None
    },
    'anglais': {
        'nom': 'Anglais',
        'fichier': os.path.join('Questions', 'Anglais', 'Questions_grammaire.csv'),
        'emoji': '🇬🇧',
        'categorie': None
    }
}

# Catégories principales (pour l'affichage du menu)
CATEGORIES = {
    'maths': {
        'nom': 'Mathématiques',
        'emoji': '📐',
        'matieres': ['maths']
    },
    'physique': {
        'nom': 'Physique',
        'emoji': '🔬',
        'matieres': ['physique_thermo', 'physique_thermique']  # Thermodynamique et Thermique
    },
    'meca': {
        'nom': 'Mécanique',
        'emoji': '⚙️',
        'matieres': ['meca']
    },
    'elec': {
        'nom': 'Électricité',
        'emoji': '⚡',
        'matieres': ['elec']
    },
    'anglais': {
        'nom': 'Anglais',
        'emoji': '🇬🇧',
        'matieres': ['anglais']
    }
}

# Stockage des parties en cours (en mémoire)
games = {}

# Modèles de base de données
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    total_score = db.Column(db.Integer, default=0)  # Score total cumulé de toutes les parties
    hints_count = db.Column(db.Integer, default=0)  # Nombre d'indices possédés
    current_theme = db.Column(db.String(50), default='default')  # Thème actuel équipé
    current_button_color = db.Column(db.String(50), default='default')  # Couleur des boutons
    current_background_color = db.Column(db.String(50), default='default')  # Couleur du rectangle blanc
    owned_emotes = db.Column(db.Text, default='')  # Émotes possédées (JSON array)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    games = db.relationship('SavedGame', backref='user', lazy=True)
    owned_themes = db.relationship('UserTheme', backref='user', lazy=True)
    owned_button_colors = db.relationship('UserButtonColor', backref='user', lazy=True)
    owned_background_colors = db.relationship('UserBackgroundColor', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def add_score(self, points):
        """Ajoute des points au score total (ne peut pas être négatif)."""
        new_score = self.total_score + points
        # Assurer que le score ne descend jamais en dessous de 0
        self.total_score = max(0, new_score)
    
    def owns_theme(self, theme_id):
        """Vérifie si l'utilisateur possède un thème."""
        if theme_id == 'default':
            return True
        return UserTheme.query.filter_by(user_id=self.id, theme_id=theme_id).first() is not None
    
    def buy_theme(self, theme_id, price):
        """Achète un thème si l'utilisateur a assez de points."""
        if self.total_score >= price and not self.owns_theme(theme_id):
            self.total_score -= price
            user_theme = UserTheme(user_id=self.id, theme_id=theme_id)
            db.session.add(user_theme)
            return True
        return False
    
    def owns_button_color(self, color_id):
        """Vérifie si l'utilisateur possède une couleur de bouton."""
        if color_id == 'default':
            return True
        return UserButtonColor.query.filter_by(user_id=self.id, color_id=color_id).first() is not None
    
    def buy_button_color(self, color_id, price):
        """Achète une couleur de bouton si l'utilisateur a assez de points."""
        if self.total_score >= price and not self.owns_button_color(color_id):
            self.total_score -= price
            user_button_color = UserButtonColor(user_id=self.id, color_id=color_id)
            db.session.add(user_button_color)
            return True
        return False
    
    def owns_background_color(self, color_id):
        """Vérifie si l'utilisateur possède une couleur de background."""
        if color_id == 'default':
            return True
        return UserBackgroundColor.query.filter_by(user_id=self.id, color_id=color_id).first() is not None
    
    def buy_background_color(self, color_id, price):
        """Achète une couleur de background si l'utilisateur a assez de points."""
        if self.total_score >= price and not self.owns_background_color(color_id):
            self.total_score -= price
            user_bg_color = UserBackgroundColor(user_id=self.id, color_id=color_id)
            db.session.add(user_bg_color)
            return True
        return False
    
    def get_owned_emotes(self):
        """Retourne la liste des émotes possédées."""
        if not self.owned_emotes:
            return []
        try:
            return json.loads(self.owned_emotes)
        except:
            return []
    
    def owns_emote(self, emote_id):
        """Vérifie si l'utilisateur possède une émote."""
        return emote_id in self.get_owned_emotes()
    
    def buy_emote(self, emote_id, price):
        """Achète une émote si l'utilisateur a assez de points."""
        if self.total_score >= price and not self.owns_emote(emote_id):
            self.total_score -= price
            owned = self.get_owned_emotes()
            owned.append(emote_id)
            self.owned_emotes = json.dumps(owned)
            return True
        return False

class UserTheme(db.Model):
    """Thèmes possédés par l'utilisateur."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    theme_id = db.Column(db.String(50), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserButtonColor(db.Model):
    """Couleurs de boutons possédées par l'utilisateur."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    color_id = db.Column(db.String(50), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserBackgroundColor(db.Model):
    """Couleurs de background possédées par l'utilisateur."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    color_id = db.Column(db.String(50), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

class SavedGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    matiere = db.Column(db.String(50), nullable=False, default='thermo')
    game_data = db.Column(db.Text, nullable=False)  # JSON data
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    questions_correctes = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    duration_seconds = db.Column(db.Integer, default=0)  # Durée de la partie en secondes (300s = 5min)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QuestionProgress(db.Model):
    """Suivi du progrès pour chaque question par utilisateur."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    matiere = db.Column(db.String(50), nullable=False)
    question_text = db.Column(db.Text, nullable=False)  # Texte de la question pour l'identifier
    status = db.Column(db.String(20), nullable=False, default='never_seen')  # never_seen, failed, success
    attempts = db.Column(db.Integer, default=0)
    last_attempt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='question_progress', lazy=True)

class Battle(db.Model):
    """Partie en mode Battle (2 joueurs)."""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False)  # Code unique à 6 caractères
    matiere = db.Column(db.String(50), nullable=False)
    is_public = db.Column(db.Boolean, default=False)  # True pour matchmaking, False pour battles privées
    player1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    player1_score = db.Column(db.Integer, default=0)
    player2_score = db.Column(db.Integer, default=0)
    player1_ready = db.Column(db.Boolean, default=False)
    player2_ready = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, playing, finished
    questions_data = db.Column(db.Text, nullable=True)  # JSON: liste des questions pour la battle
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    player1 = db.relationship('User', foreign_keys=[player1_id], backref='battles_as_player1')
    player2 = db.relationship('User', foreign_keys=[player2_id], backref='battles_as_player2')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Créer les tables et effectuer les migrations
with app.app_context():
    db.create_all()
    
    # Migration: Ajouter la colonne is_public si elle n'existe pas
    try:
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('battle')]
        
        if 'is_public' not in columns:
            print("🔨 Migration: Ajout de la colonne is_public...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE battle 
                    ADD COLUMN is_public BOOLEAN DEFAULT FALSE
                """))
                conn.commit()
                print("✅ Colonne is_public ajoutée avec succès!")
        else:
            print("✅ Colonne is_public existe déjà")
    except Exception as e:
        print(f"⚠️ Erreur lors de la migration is_public: {e}")
    
    # Migration: Ajouter la colonne current_background_color si elle n'existe pas
    try:
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        user_columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'current_background_color' not in user_columns:
            print("🔨 Migration: Ajout de la colonne current_background_color...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE "user" 
                    ADD COLUMN current_background_color VARCHAR(50) DEFAULT 'default'
                """))
                conn.commit()
                print("✅ Colonne current_background_color ajoutée avec succès!")
        else:
            print("✅ Colonne current_background_color existe déjà")
    except Exception as e:
        print(f"⚠️ Erreur lors de la migration current_background_color: {e}")

# Mapping pour compatibilité avec ancien code 'thermo' -> 'physique_thermo'
MATIERE_ALIASES = {
    'thermo': 'physique_thermo'
}

def normalize_matiere(matiere):
    """Normalise le code de matière (gère les anciens codes)."""
    return MATIERE_ALIASES.get(matiere, matiere)

def charger_questions(matiere='physique_thermo'):
    """Charge les questions depuis le fichier CSV de la matière."""
    matiere = normalize_matiere(matiere)
    
    if matiere not in MATIERES:
        matiere = 'physique_thermo'
    
    fichier = MATIERES[matiere]['fichier']
    fichier_path = os.path.join(os.path.dirname(__file__), fichier)
    
    if not Path(fichier_path).exists():
        return []
    
    questions = []
    with open(fichier_path, 'r', encoding='utf-8') as f:
        lecteur = csv.reader(f, delimiter=';')
        for ligne in lecteur:
            if len(ligne) >= 5:
                question = {
                    'question': ligne[0],
                    'bonne_reponse': ligne[1],
                    'mauvaises_reponses': [ligne[2], ligne[3], ligne[4]],
                    'source_matiere': matiere
                }
                questions.append(question)
    return questions

# Thèmes disponibles dans la boutique
THEMES = {
    'default': {
        'id': 'default',
        'nom': 'Violet Classique',
        'gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'prix': 0,
        'description': 'Le thème par défaut'
    },
    'ocean': {
        'id': 'ocean',
        'nom': 'Océan Profond',
        'gradient': 'linear-gradient(135deg, #2E3192 0%, #1BFFFF 100%)',
        'prix': 500,
        'description': 'Plongez dans les profondeurs'
    },
    'sunset': {
        'id': 'sunset',
        'nom': 'Coucher de Soleil',
        'gradient': 'linear-gradient(135deg, #FF6B6B 0%, #FFE66D 100%)',
        'prix': 500,
        'description': 'Chaleur du crépuscule'
    },
    'forest': {
        'id': 'forest',
        'nom': 'Forêt Mystique',
        'gradient': 'linear-gradient(135deg, #134E5E 0%, #71B280 100%)',
        'prix': 750,
        'description': 'Nature verdoyante'
    },
    'galaxy': {
        'id': 'galaxy',
        'nom': 'Galaxie Cosmique',
        'gradient': 'linear-gradient(135deg, #2C3E50 0%, #4CA1AF 100%)',
        'prix': 1000,
        'description': 'Voyage spatial'
    },
    'fire': {
        'id': 'fire',
        'nom': 'Flammes Ardentes',
        'gradient': 'linear-gradient(135deg, #F2994A 0%, #F2C94C 100%)',
        'prix': 1000,
        'description': 'Énergie incandescente'
    },
    'aurora': {
        'id': 'aurora',
        'nom': 'Aurore Boréale',
        'gradient': 'linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%)',
        'prix': 1500,
        'description': 'Lumières magiques du nord'
    },
    'royal': {
        'id': 'royal',
        'nom': 'Or Royal',
        'gradient': 'linear-gradient(135deg, #DAA520 0%, #FFD700 100%)',
        'prix': 2000,
        'description': 'Luxe et prestige'
    }
}

# Couleurs de boutons disponibles dans la boutique
BUTTON_COLORS = {
    'default': {
        'id': 'default',
        'nom': 'Bleu Standard',
        'couleur': '#4CAF50',
        'couleur_hover': '#45a049',
        'prix': 0,
        'description': 'La couleur par défaut'
    },
    'red': {
        'id': 'red',
        'nom': 'Rouge Passion',
        'couleur': '#FF5252',
        'couleur_hover': '#E53935',
        'prix': 150,
        'description': 'Boutons rouge vif'
    },
    'blue': {
        'id': 'blue',
        'nom': 'Bleu Électrique',
        'couleur': '#2196F3',
        'couleur_hover': '#1976D2',
        'prix': 150,
        'description': 'Boutons bleu éclatant'
    },
    'purple': {
        'id': 'purple',
        'nom': 'Violet Royal',
        'couleur': '#9C27B0',
        'couleur_hover': '#7B1FA2',
        'prix': 200,
        'description': 'Boutons violets élégants'
    },
    'orange': {
        'id': 'orange',
        'nom': 'Orange Solaire',
        'couleur': '#FF9800',
        'couleur_hover': '#F57C00',
        'prix': 200,
        'description': 'Boutons orange énergiques'
    },
    'pink': {
        'id': 'pink',
        'nom': 'Rose Bonbon',
        'couleur': '#E91E63',
        'couleur_hover': '#C2185B',
        'prix': 250,
        'description': 'Boutons rose éclatant'
    },
    'teal': {
        'id': 'teal',
        'nom': 'Turquoise Océan',
        'couleur': '#009688',
        'couleur_hover': '#00796B',
        'prix': 300,
        'description': 'Boutons turquoise apaisants'
    },
    'gold': {
        'id': 'gold',
        'nom': 'Or Prestigieux',
        'couleur': '#FFD700',
        'couleur_hover': '#DAA520',
        'prix': 500,
        'description': 'Boutons dorés luxueux'
    }
}

# Couleurs de background du rectangle blanc disponibles dans la boutique
BACKGROUND_COLORS = {
    'default': {
        'id': 'default',
        'nom': 'Blanc Standard',
        'gradient': 'linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%)',
        'prix': 0,
        'description': 'Le fond blanc classique'
    },
    'light_blue': {
        'id': 'light_blue',
        'nom': 'Bleu Clair',
        'gradient': 'linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%)',
        'prix': 1000,
        'description': 'Fond bleu pastel apaisant'
    },
    'light_green': {
        'id': 'light_green',
        'nom': 'Vert Clair',
        'gradient': 'linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%)',
        'prix': 1000,
        'description': 'Fond vert nature'
    },
    'light_pink': {
        'id': 'light_pink',
        'nom': 'Rose Clair',
        'gradient': 'linear-gradient(135deg, #FCE4EC 0%, #F8BBD0 100%)',
        'prix': 1200,
        'description': 'Fond rose délicat'
    },
    'light_purple': {
        'id': 'light_purple',
        'nom': 'Violet Clair',
        'gradient': 'linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%)',
        'prix': 1200,
        'description': 'Fond violet élégant'
    },
    'light_orange': {
        'id': 'light_orange',
        'nom': 'Orange Clair',
        'gradient': 'linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%)',
        'prix': 1500,
        'description': 'Fond orange chaleureux'
    },
    'light_yellow': {
        'id': 'light_yellow',
        'nom': 'Jaune Clair',
        'gradient': 'linear-gradient(135deg, #FFFDE7 0%, #FFF9C4 100%)',
        'prix': 1500,
        'description': 'Fond jaune lumineux'
    },
    'pastel_sky': {
        'id': 'pastel_sky',
        'nom': 'Ciel Pastel',
        'gradient': 'linear-gradient(135deg, #E0F7FA 0%, #B2EBF2 100%)',
        'prix': 2000,
        'description': 'Fond bleu ciel doux'
    },
    'pastel_mint': {
        'id': 'pastel_mint',
        'nom': 'Menthe Pastel',
        'gradient': 'linear-gradient(135deg, #E0F2F1 0%, #B2DFDB 100%)',
        'prix': 2000,
        'description': 'Fond menthe rafraîchissant'
    },
    'gradient_sunset': {
        'id': 'gradient_sunset',
        'nom': 'Coucher Pastel',
        'gradient': 'linear-gradient(135deg, #FFE8D6 0%, #FFCCB3 100%)',
        'prix': 3000,
        'description': 'Fond dégradé coucher doux'
    },
    'gradient_forest': {
        'id': 'gradient_forest',
        'nom': 'Forêt Légère',
        'gradient': 'linear-gradient(135deg, #E8F5E9 0%, #A5D6A7 100%)',
        'prix': 3000,
        'description': 'Fond vert nature lumineux'
    },
    'gradient_cosmic': {
        'id': 'gradient_cosmic',
        'nom': 'Cosmos Léger',
        'gradient': 'linear-gradient(135deg, #F3E5F5 0%, #CE93D8 100%)',
        'prix': 5000,
        'description': 'Fond cosmique délicat'
    },
    'gradient_ocean': {
        'id': 'gradient_ocean',
        'nom': 'Océan Léger',
        'gradient': 'linear-gradient(135deg, #E1F5FE 0%, #81D4FA 100%)',
        'prix': 5000,
        'description': 'Fond océan frais'
    },
    'gradient_fire': {
        'id': 'gradient_fire',
        'nom': 'Feu Doux',
        'gradient': 'linear-gradient(135deg, #FFF3E0 0%, #FFB74D 100%)',
        'prix': 7500,
        'description': 'Fond feu chaleureux'
    },
    'gradient_aurora': {
        'id': 'gradient_aurora',
        'nom': 'Aurore Légère',
        'gradient': 'linear-gradient(135deg, #F0F4C3 0%, #81C784 100%)',
        'prix': 10000,
        'description': 'Fond aurore magique'
    }
}

# Pouvoirs spéciaux disponibles dans la boutique
POWERS = {
    'time_freeze': {
        'id': 'time_freeze',
        'nom': '⏸️ Geler le Temps',
        'emoji': '⏸️',
        'prix': 300,
        'description': 'Gèle le temps pendant 1 minute - utilise dans une partie pour arrêter le chrono!',
        'duration_seconds': 60
    }
}

# Émotes disponibles pour le mode Battle
EMOTES = {
    'fire': {
        'id': 'fire',
        'nom': '🔥 Enflammé',
        'emoji': '🔥',
        'prix': 50,
        'description': 'T\'es en feu !'
    },
    'trophy': {
        'id': 'trophy',
        'nom': '🏆 Trophée',
        'emoji': '🏆',
        'prix': 100,
        'description': 'La victoire est proche'
    },
    'rocket': {
        'id': 'rocket',
        'nom': '🚀 Fusée',
        'emoji': '🚀',
        'prix': 100,
        'description': 'Vers l\'infini et au-delà'
    },
    'brain': {
        'id': 'brain',
        'nom': '🧠 Cerveau',
        'emoji': '🧠',
        'prix': 150,
        'description': 'Trop intelligent'
    },
    'lightning': {
        'id': 'lightning',
        'nom': '⚡ Éclair',
        'emoji': '⚡',
        'prix': 150,
        'description': 'Rapide comme l\'éclair'
    },
    'star': {
        'id': 'star',
        'nom': '⭐ Étoile',
        'emoji': '⭐',
        'prix': 100,
        'description': 'Tu brilles'
    },
    'exploding': {
        'id': 'exploding',
        'nom': '🤯 Esprit Soufflé',
        'emoji': '🤯',
        'prix': 200,
        'description': 'Incroyable'
    },
    'thinking': {
        'id': 'thinking',
        'nom': '🤔 Réflexion',
        'emoji': '🤔',
        'prix': 50,
        'description': 'Laisse-moi réfléchir'
    },
    'laugh': {
        'id': 'laugh',
        'nom': '😂 Rire',
        'emoji': '😂',
        'prix': 100,
        'description': 'Trop drôle'
    },
    'cool': {
        'id': 'cool',
        'nom': '😎 Cool',
        'emoji': '😎',
        'prix': 150,
        'description': 'Stylé'
    },
    'party': {
        'id': 'party',
        'nom': '🎉 Fête',
        'emoji': '🎉',
        'prix': 200,
        'description': 'C\'est la fête'
    },
    'love': {
        'id': 'love',
        'nom': '❤️ Amour',
        'emoji': '❤️',
        'prix': 100,
        'description': 'T\'es adorable'
    },
    'monster': {
        'id': 'monster',
        'nom': '👹 Monstre',
        'emoji': '👹',
        'prix': 150,
        'description': 'Peur! Peur!'
    },
    'smile': {
        'id': 'smile',
        'nom': '😊 Sourire',
        'emoji': '😊',
        'prix': 50,
        'description': 'Ça me plaît'
    },
    'angry': {
        'id': 'angry',
        'nom': '😠 Colère',
        'emoji': '😠',
        'prix': 100,
        'description': 'Furieux!'
    },
    'skull': {
        'id': 'skull',
        'nom': '💀 Mort',
        'emoji': '💀',
        'prix': 150,
        'description': 'Raté!'
    },
    'clap': {
        'id': 'clap',
        'nom': '👏 Applaudissements',
        'emoji': '👏',
        'prix': 75,
        'description': 'Bravo!'
    },
    'victory': {
        'id': 'victory',
        'nom': '✌️ Victoire',
        'emoji': '✌️',
        'prix': 100,
        'description': 'Youpi!'
    },
    'sweat': {
        'id': 'sweat',
        'nom': '😅 Sueur',
        'emoji': '😅',
        'prix': 75,
        'description': 'C\'est difficile!'
    },
    'eyes': {
        'id': 'eyes',
        'nom': '👀 Yeux',
        'emoji': '👀',
        'prix': 50,
        'description': 'Je regarde...'
    },
    'pray': {
        'id': 'pray',
        'nom': '🙏 Prière',
        'emoji': '🙏',
        'prix': 100,
        'description': 'Aide-moi!'
    },
    'diamond': {
        'id': 'diamond',
        'nom': '💎 Diamant',
        'emoji': '💎',
        'prix': 200,
        'description': 'Précieux!'
    },
    'crown': {
        'id': 'crown',
        'nom': '👑 Couronne',
        'emoji': '👑',
        'prix': 250,
        'description': 'Je suis le roi!'
    },
    'ghost': {
        'id': 'ghost',
        'nom': '👻 Fantôme',
        'emoji': '👻',
        'prix': 150,
        'description': 'Boo!'
    },
    'alien': {
        'id': 'alien',
        'nom': '👽 Alien',
        'emoji': '👽',
        'prix': 175,
        'description': 'Bizarre!'
    }
}

@app.route('/')
@login_required
def index():
    """Page d'accueil du jeu."""
    return render_template('index.html', user=current_user, matieres=MATIERES)

@app.route('/auth')
def auth_page():
    """Page d'authentification."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('auth.html')

@app.route('/api/matieres', methods=['GET'])
@login_required
def get_matieres():
    """Retourne la liste des matières disponibles."""
    matieres_disponibles = []
    for code, info in MATIERES.items():
        fichier_path = os.path.join(os.path.dirname(__file__), info['fichier'])
        if Path(fichier_path).exists():
            nb_questions = len(charger_questions(code))
            matieres_disponibles.append({
                'code': code,
                'nom': info['nom'],
                'emoji': info['emoji'],
                'nb_questions': nb_questions
            })
    return jsonify({'matieres': matieres_disponibles})

@app.route('/api/register', methods=['POST'])
def register():
    """Inscription d'un nouvel utilisateur."""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Tous les champs sont requis'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Le mot de passe doit contenir au moins 6 caractères'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 400
    
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    
    return jsonify({'success': True, 'username': username})

@app.route('/api/login', methods=['POST'])
def login():
    """Connexion d'un utilisateur."""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Tous les champs sont requis'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Identifiant ou mot de passe incorrect'}), 401
    
    login_user(user)
    
    return jsonify({'success': True, 'username': username})

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Déconnexion de l'utilisateur."""
    logout_user()
    return jsonify({'success': True})

@app.route('/api/current_user', methods=['GET'])
def get_current_user():
    """Retourne l'utilisateur actuellement connecté."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username
        })
    return jsonify({'authenticated': False})

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    """Retourne la liste des catégories et leurs matières."""
    categories_list = []
    for cat_id, cat_data in CATEGORIES.items():
        # Récupérer les matières de cette catégorie
        matieres_list = []
        for matiere_id in cat_data['matieres']:
            if matiere_id in MATIERES:
                matiere_info = MATIERES[matiere_id]
                matieres_list.append({
                    'id': matiere_id,
                    'nom': matiere_info['nom'],
                    'emoji': matiere_info['emoji']
                })
        
        categories_list.append({
            'id': cat_id,
            'nom': cat_data['nom'],
            'emoji': cat_data['emoji'],
            'matieres': matieres_list,
            'has_subcategories': len(matieres_list) > 1  # True si plusieurs sous-catégories
        })
    
    return jsonify({'categories': categories_list})

@app.route('/api/start', methods=['POST'])
@login_required
def start_game():
    """Démarre une nouvelle partie."""
    data = request.json or {}
    matiere = data.get('matiere', 'physique_thermo')
    timer_minutes = data.get('timer_minutes', 0)  # 0 = mode classique, 5 ou 10 = mode chronométré
    mode = data.get('mode', 'single')  # 'single', 'mixed_category', 'mixed_all', 'revision_category'
    revision_category = data.get('revision_category', None)  # ex: 'physique' pour réviser toute la physique
    category = data.get('category', None)  # ex: 'physique' pour mélanger toutes les matières de physique

    if matiere not in MATIERES and mode == 'single':
        return jsonify({'error': 'Matière invalide'}), 400

    # Charger les questions selon le mode demandé
    all_questions = []
    if mode == 'revision_category' and revision_category:
        # Réviser une catégorie complète (ex: Physique = thermo + thermique)
        if revision_category in CATEGORIES:
            for m in CATEGORIES[revision_category]['matieres']:
                all_questions.extend(charger_questions(m))
        else:
            return jsonify({'error': 'Catégorie invalide pour la révision'}), 400
    elif mode == 'mixed_all':
        for m in MATIERES.keys():
            all_questions.extend(charger_questions(m))
    elif mode == 'mixed_category':
        # Mélanger toutes les matières d'une catégorie (ex: physique_thermo + physique_thermique)
        target_category = category if category else MATIERES.get(normalize_matiere(matiere), {}).get('categorie')
        if target_category and target_category in CATEGORIES:
            for m in CATEGORIES[target_category]['matieres']:
                all_questions.extend(charger_questions(m))
        else:
            all_questions = charger_questions(matiere)
    else:
        all_questions = charger_questions(matiere)

    if not all_questions:
        return jsonify({'error': 'Aucune question trouvée'}), 400

    # En mode chronométré, filtrer pour ne garder que les questions non réussies
    if timer_minutes > 0:
        questions_to_practice = []
        for q in all_questions:
            source = q.get('source_matiere', matiere)
            progress = QuestionProgress.query.filter_by(
                user_id=current_user.id,
                matiere=source,
                question_text=q['question']
            ).first()
            if not progress or progress.status in ['never_seen', 'failed']:
                questions_to_practice.append(q)
        questions = questions_to_practice if questions_to_practice else all_questions
    else:
        questions = all_questions

    random.shuffle(questions)

    game_id = str(uuid.uuid4())
    start_time = datetime.utcnow() if timer_minutes > 0 else None

    games[game_id] = {
        'user_id': current_user.id,
        'username': current_user.username,
        'matiere': matiere,
        'questions': questions,
        'current_index': 0,
        'score': 0,
        'reponses_restantes': [],
        'questions_correctes': [],
        'questions_a_reviser': [],
        'timer_minutes': timer_minutes,
        'start_time': start_time,
        'mode': mode
    }

    session['game_id'] = game_id

    mode_str = f"{timer_minutes} min" if timer_minutes > 0 else "classique"
    print(f"Jeu démarré: {len(questions)} questions, Mode: {mode} ({mode_str}), ID: {game_id}, Joueur: {current_user.username}")
    
    return jsonify({
        'success': True,
        'total_questions': len(questions),
        'matiere': matiere,
        'matiere_nom': MATIERES[matiere]['nom'],
        'matiere_emoji': MATIERES[matiere]['emoji'],
        'timer_minutes': timer_minutes
    })

@app.route('/api/time_remaining', methods=['GET'])
def get_time_remaining():
    """Retourne le temps restant dans la partie chronométrée."""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
    
    game = games[game_id]
    timer_minutes = game.get('timer_minutes', 0)
    start_time = game.get('start_time')
    
    if timer_minutes == 0 or not start_time:
        return jsonify({'timer_enabled': False})
    
    elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
    total_seconds = timer_minutes * 60
    remaining_seconds = max(0, total_seconds - elapsed_seconds)
    
    return jsonify({
        'timer_enabled': True,
        'remaining_seconds': int(remaining_seconds),
        'is_expired': remaining_seconds <= 0
    })

@app.route('/api/question', methods=['GET'])
def get_question():
    """Retourne la question actuelle."""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
    
    game = games[game_id]
    questions = game['questions']
    current_index = game['current_index']
    timer_minutes = game.get('timer_minutes', 0)
    
    # Si on a fini toutes les questions et qu'on est en mode chrono, recommencer un cycle
    if current_index >= len(questions):
        if timer_minutes > 0:
            # Recommencer le cycle avec les mêmes questions
            game['current_index'] = 0
            game['reponses_restantes'] = []
            current_index = 0
            random.shuffle(questions)  # Mélanger pour varier
        else:
            # Mode classique: montrer l'écran de fin
            questions_a_reviser = game.get('questions_a_reviser', [])
            if questions_a_reviser:
                return jsonify({
                    'finished': True, 
                    'score': game['score'],
                    'has_revision': True,
                    'revision_count': len(questions_a_reviser)
                })
            return jsonify({'finished': True, 'score': game['score'], 'has_revision': False})
    
    question_data = questions[current_index]
    
    if not game['reponses_restantes']:
        toutes_reponses = [question_data['bonne_reponse']] + question_data['mauvaises_reponses']
        random.shuffle(toutes_reponses)
        game['reponses_restantes'] = toutes_reponses
    
    reponses_restantes = game['reponses_restantes']
    
    if not reponses_restantes:
        game['current_index'] = current_index + 1
        game['reponses_restantes'] = []
        return get_question()
    
    reponse_proposee = reponses_restantes[0]
    
    # Sauvegarder la réponse proposée pour l'indice
    game['current_proposed_answer'] = reponse_proposee
    
    # Informations sur la source (matière/fichier) pour affichage UI
    source_code = question_data.get('source_matiere')
    source_info = MATIERES.get(source_code, None)
    source_nom = source_info['nom'] if source_info else source_code
    source_emoji = source_info['emoji'] if source_info else ''

    return jsonify({
        'finished': False,
        'question': question_data['question'],
        'reponse_proposee': reponse_proposee,
        'question_number': current_index + 1,
        'total_questions': len(questions),
        'score': game['score'],
        'reponses_restantes': len(reponses_restantes),
        'source_matiere': source_code,
        'source_nom': source_nom,
        'source_emoji': source_emoji
    })

@app.route('/api/answer', methods=['POST'])
def submit_answer():
    """Traite la réponse du joueur."""
    data = request.json
    reponse_joueur = data.get('answer')
    
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
    
    game = games[game_id]
    questions = game['questions']
    current_index = game['current_index']
    score = game['score']
    reponses_restantes = game['reponses_restantes']
    
    if current_index >= len(questions) or not reponses_restantes:
        return jsonify({'error': 'Invalid state'}), 400
    
    question_data = questions[current_index]
    reponse_proposee = reponses_restantes[0]
    est_bonne_reponse = (reponse_proposee == question_data['bonne_reponse'])
    
    result = {
        'correct': False,
        'points': 0,
        'message': '',
        'bonne_reponse': question_data['bonne_reponse'],
        'next_question': False
    }
    
    if reponse_joueur and est_bonne_reponse:
        score += 10
        result['correct'] = True
        result['points'] = 10
        result['message'] = "✅ CORRECT! C'était bien la bonne réponse! Vous gagnez 10 points! 🎉"
        result['next_question'] = True
        game['current_index'] = current_index + 1
        game['reponses_restantes'] = []
        if 'questions_correctes' not in game:
            game['questions_correctes'] = []
        game['questions_correctes'].append(current_index)
        
        # Sauvegarder le progrès : question réussie
        if current_user.is_authenticated:
            matiere = game.get('matiere', 'thermo')
            progress = QuestionProgress.query.filter_by(
                user_id=current_user.id,
                matiere=matiere,
                question_text=question_data['question']
            ).first()
            
            if progress:
                progress.status = 'success'
                progress.attempts += 1
                progress.last_attempt = datetime.utcnow()
            else:
                progress = QuestionProgress(
                    user_id=current_user.id,
                    matiere=matiere,
                    question_text=question_data['question'],
                    status='success',
                    attempts=1
                )
                db.session.add(progress)
            db.session.commit()
            
    elif reponse_joueur and not est_bonne_reponse:
        score -= 5
        result['correct'] = False
        result['points'] = -5
        result['message'] = f"❌ FAUX! Ce n'était pas la bonne réponse. Vous perdez 5 points! 😞"
        result['next_question'] = True
        game['current_index'] = current_index + 1
        game['reponses_restantes'] = []
        if 'questions_a_reviser' not in game:
            game['questions_a_reviser'] = []
        if current_index not in game['questions_a_reviser']:
            game['questions_a_reviser'].append(current_index)
        
        # Sauvegarder le progrès : question échouée
        if current_user.is_authenticated:
            matiere = game.get('matiere', 'thermo')
            progress = QuestionProgress.query.filter_by(
                user_id=current_user.id,
                matiere=matiere,
                question_text=question_data['question']
            ).first()
            
            if progress:
                progress.status = 'failed'
                progress.attempts += 1
                progress.last_attempt = datetime.utcnow()
            else:
                progress = QuestionProgress(
                    user_id=current_user.id,
                    matiere=matiere,
                    question_text=question_data['question'],
                    status='failed',
                    attempts=1
                )
                db.session.add(progress)
            db.session.commit()
    else:
        reponses_restantes.pop(0)
        game['reponses_restantes'] = reponses_restantes
        
        if not reponses_restantes:
            result['message'] = f"❓ Vous avez refusé toutes les réponses.\n\nLa bonne réponse était: {question_data['bonne_reponse']}\n\nAucun point gagné ou perdu."
            result['next_question'] = True
            game['current_index'] = current_index + 1
            game['reponses_restantes'] = []
            if 'questions_a_reviser' not in game:
                game['questions_a_reviser'] = []
            if current_index not in game['questions_a_reviser']:
                game['questions_a_reviser'].append(current_index)
        else:
            result['message'] = "➡️ Vous passez à une autre réponse..."
    
    game['score'] = score
    result['score'] = score
    
    return jsonify(result)

@app.route('/api/start_revision', methods=['POST'])
def start_revision():
    """Démarre le mode révision avec les questions à réviser."""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
    
    game = games[game_id]
    questions_a_reviser = game.get('questions_a_reviser', [])
    
    if not questions_a_reviser:
        return jsonify({'error': 'No questions to review'}), 400
    
    all_questions = game['questions']
    revision_questions = [all_questions[i] for i in questions_a_reviser]
    random.shuffle(revision_questions)
    
    game['questions'] = revision_questions
    game['current_index'] = 0
    game['reponses_restantes'] = []
    game['questions_a_reviser'] = []
    
    return jsonify({'success': True, 'total_questions': len(revision_questions)})

@app.route('/api/stats', methods=['POST'])
@login_required
def get_stats():
    """Retourne les statistiques de progression pour une matière."""
    data = request.json or {}
    matiere = data.get('matiere', 'thermo')
    
    if matiere not in MATIERES:
        return jsonify({'error': 'Matière invalide'}), 400
    
    # Compter les questions par statut
    success_count = QuestionProgress.query.filter_by(
        user_id=current_user.id,
        matiere=matiere,
        status='success'
    ).count()
    
    failed_count = QuestionProgress.query.filter_by(
        user_id=current_user.id,
        matiere=matiere,
        status='failed'
    ).count()
    
    # Nombre total de questions disponibles
    total_questions = len(charger_questions(matiere))
    never_seen = total_questions - success_count - failed_count
    
    return jsonify({
        'matiere': matiere,
        'matiere_nom': MATIERES[matiere]['nom'],
        'matiere_emoji': MATIERES[matiere]['emoji'],
        'total_questions': total_questions,
        'success_count': success_count,
        'failed_count': failed_count,
        'never_seen_count': max(0, never_seen),
        'completion_percent': round((success_count / total_questions * 100) if total_questions > 0 else 0, 1)
    })

@app.route('/api/scores', methods=['POST'])
@login_required
def get_scores():
    """Retourne les meilleurs scores pour une matière (parties de 5 minutes uniquement)."""
    data = request.json or {}
    matiere = data.get('matiere', 'thermo')
    
    # Récupérer uniquement les parties de 5 minutes (300 secondes)
    best_games = SavedGame.query.filter_by(
        is_completed=True,
        matiere=matiere,
        duration_seconds=300
    ).order_by(SavedGame.score.desc()).limit(10).all()
    
    scores = [{
        'username': game.user.username,
        'score': game.score,
        'date': game.created_at.strftime('%d/%m/%Y %H:%M')
    } for game in best_games]
    
    return jsonify({
        'scores': scores,
        'matiere': matiere,
        'matiere_nom': MATIERES[matiere]['nom']
    })

@app.route('/api/scores/total', methods=['POST'])
@login_required
def get_total_scores():
    """Retourne le classement des scores totaux de tous les utilisateurs."""
    # Récupérer les 10 meilleurs utilisateurs par score total (score > 0 uniquement)
    top_users = User.query.filter(User.total_score > 0).order_by(User.total_score.desc()).limit(10).all()
    
    scores = [{
        'username': user.username,
        'total_score': user.total_score,
        'games_played': len([g for g in user.games if g.is_completed and g.duration_seconds == 300])
    } for user in top_users]
    
    return jsonify({
        'scores': scores,
        'current_user_score': current_user.total_score
    })

@app.route('/api/shop/themes', methods=['GET'])
@login_required
def get_themes():
    """Retourne la liste des thèmes disponibles avec leur statut d'achat."""
    themes_list = []
    for theme_id, theme_data in THEMES.items():
        themes_list.append({
            'id': theme_data['id'],
            'nom': theme_data['nom'],
            'gradient': theme_data['gradient'],
            'prix': theme_data['prix'],
            'description': theme_data['description'],
            'owned': current_user.owns_theme(theme_id),
            'equipped': current_user.current_theme == theme_id
        })
    
    return jsonify({
        'themes': themes_list,
        'user_score': current_user.total_score,
        'current_theme': current_user.current_theme
    })

@app.route('/api/shop/buy', methods=['POST'])
@login_required
def buy_theme():
    """Achète un thème avec les points de l'utilisateur."""
    data = request.json or {}
    theme_id = data.get('theme_id')
    
    if not theme_id or theme_id not in THEMES:
        return jsonify({'error': 'Thème invalide'}), 400
    
    theme = THEMES[theme_id]
    
    if current_user.owns_theme(theme_id):
        return jsonify({'error': 'Vous possédez déjà ce thème'}), 400
    
    if current_user.total_score < theme['prix']:
        return jsonify({'error': 'Points insuffisants'}), 400
    
    if current_user.buy_theme(theme_id, theme['prix']):
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Thème {theme["nom"]} acheté !',
            'new_score': current_user.total_score
        })
    
    return jsonify({'error': 'Erreur lors de l\'achat'}), 400

@app.route('/api/shop/equip', methods=['POST'])
@login_required
def equip_theme():
    """Équipe un thème possédé par l'utilisateur."""
    data = request.json or {}
    theme_id = data.get('theme_id')
    
    if not theme_id or theme_id not in THEMES:
        return jsonify({'error': 'Thème invalide'}), 400
    
    if not current_user.owns_theme(theme_id):
        return jsonify({'error': 'Vous ne possédez pas ce thème'}), 400
    
    current_user.current_theme = theme_id
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Thème {THEMES[theme_id]["nom"]} équipé !',
        'gradient': THEMES[theme_id]['gradient']
    })

@app.route('/api/shop/buy_hints', methods=['POST'])
@login_required
def buy_hints():
    """Achète des indices (25 points l'unité)."""
    data = request.json or {}
    quantity = data.get('quantity', 1)
    
    try:
        quantity = int(quantity)
        if quantity < 1 or quantity > 100:
            return jsonify({'error': 'Quantité invalide (1-100)'}), 400
        
        price = quantity * 25
        
        if current_user.total_score < price:
            return jsonify({'error': f'Points insuffisants ! Il vous faut {price} points'}), 400
        
        current_user.total_score -= price
        current_user.hints_count += quantity
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{quantity} indice{"s" if quantity > 1 else ""} acheté{"s" if quantity > 1 else ""} !',
            'new_score': current_user.total_score,
            'hints_count': current_user.hints_count
        })
    except ValueError:
        return jsonify({'error': 'Quantité invalide'}), 400

@app.route('/api/shop/button_colors', methods=['GET'])
@login_required
def get_button_colors():
    """Retourne la liste des couleurs de boutons disponibles."""
    colors_with_status = []
    
    for color_id, color_data in BUTTON_COLORS.items():
        colors_with_status.append({
            'id': color_id,
            'nom': color_data['nom'],
            'couleur': color_data['couleur'],
            'couleur_hover': color_data['couleur_hover'],
            'prix': color_data['prix'],
            'description': color_data['description'],
            'owned': current_user.owns_button_color(color_id),
            'equipped': current_user.current_button_color == color_id
        })
    
    return jsonify({
        'colors': colors_with_status,
        'user_score': current_user.total_score
    })

@app.route('/api/shop/buy_button_color', methods=['POST'])
@login_required
def buy_button_color():
    """Achète une couleur de bouton."""
    data = request.json or {}
    color_id = data.get('color_id')
    
    if not color_id or color_id not in BUTTON_COLORS:
        return jsonify({'error': 'Couleur invalide'}), 400
    
    color_data = BUTTON_COLORS[color_id]
    
    if current_user.owns_button_color(color_id):
        return jsonify({'error': 'Vous possédez déjà cette couleur'}), 400
    
    if current_user.total_score < color_data['prix']:
        return jsonify({'error': f'Points insuffisants ! Il vous faut {color_data["prix"]} points'}), 400
    
    if current_user.buy_button_color(color_id, color_data['prix']):
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Couleur {color_data["nom"]} achetée !',
            'new_score': current_user.total_score
        })
    
    return jsonify({'error': 'Erreur lors de l\'achat'}), 500

@app.route('/api/shop/equip_button_color', methods=['POST'])
@login_required
def equip_button_color():
    """Équipe une couleur de bouton."""
    data = request.json or {}
    color_id = data.get('color_id')
    
    if not color_id or color_id not in BUTTON_COLORS:
        return jsonify({'error': 'Couleur invalide'}), 400
    
    if not current_user.owns_button_color(color_id):
        return jsonify({'error': 'Vous ne possédez pas cette couleur'}), 400
    
    current_user.current_button_color = color_id
    db.session.commit()
    
    color_data = BUTTON_COLORS[color_id]
    
    return jsonify({
        'success': True,
        'message': f'Couleur {color_data["nom"]} équipée !',
        'couleur': color_data['couleur'],
        'couleur_hover': color_data['couleur_hover']
    })

@app.route('/api/shop/background_colors', methods=['GET'])
@login_required
def get_background_colors():
    """Retourne la liste des couleurs de background disponibles."""
    colors_with_status = []
    
    for color_id, color_data in BACKGROUND_COLORS.items():
        colors_with_status.append({
            'id': color_id,
            'nom': color_data['nom'],
            'gradient': color_data['gradient'],
            'prix': color_data['prix'],
            'description': color_data['description'],
            'owned': current_user.owns_background_color(color_id),
            'equipped': current_user.current_background_color == color_id
        })
    
    return jsonify({'background_colors': colors_with_status})

@app.route('/api/shop/buy_background_color', methods=['POST'])
@login_required
def buy_background_color():
    """Achète une couleur de background."""
    data = request.json or {}
    color_id = data.get('color_id')
    
    if not color_id or color_id not in BACKGROUND_COLORS:
        return jsonify({'error': 'Couleur invalide'}), 400
    
    color_data = BACKGROUND_COLORS[color_id]
    
    if current_user.owns_background_color(color_id):
        return jsonify({'error': 'Vous possédez déjà cette couleur'}), 400
    
    if current_user.total_score < color_data['prix']:
        return jsonify({'error': f'Points insuffisants ! Il vous faut {color_data["prix"]} points'}), 400
    
    if current_user.buy_background_color(color_id, color_data['prix']):
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Couleur {color_data["nom"]} achetée !',
            'new_score': current_user.total_score
        })
    
    return jsonify({'error': 'Erreur lors de l\'achat'}), 400

@app.route('/api/shop/equip_background_color', methods=['POST'])
@login_required
def equip_background_color():
    """Équipe une couleur de background."""
    data = request.json or {}
    color_id = data.get('color_id')
    
    if not color_id or color_id not in BACKGROUND_COLORS:
        return jsonify({'error': 'Couleur invalide'}), 400
    
    if not current_user.owns_background_color(color_id):
        return jsonify({'error': 'Vous ne possédez pas cette couleur'}), 400
    
    current_user.current_background_color = color_id
    db.session.commit()
    
    color_data = BACKGROUND_COLORS[color_id]
    
    return jsonify({
        'success': True,
        'message': f'Fond {color_data["nom"]} équipé !',
        'gradient': color_data['gradient']
    })

@app.route('/api/shop/emotes', methods=['GET'])
@login_required
def get_emotes():
    """Retourne la liste des émotes disponibles."""
    emotes_with_status = []
    
    for emote_id, emote_data in EMOTES.items():
        emotes_with_status.append({
            'id': emote_id,
            'nom': emote_data['nom'],
            'emoji': emote_data['emoji'],
            'prix': emote_data['prix'],
            'description': emote_data['description'],
            'owned': current_user.owns_emote(emote_id)
        })
    
    return jsonify({
        'emotes': emotes_with_status,
        'user_score': current_user.total_score,
        'owned_emotes': current_user.get_owned_emotes()
    })

@app.route('/api/shop/buy_emote', methods=['POST'])
@login_required
def buy_emote():
    """Achète une émote."""
    data = request.json or {}
    emote_id = data.get('emote_id')
    
    if not emote_id or emote_id not in EMOTES:
        return jsonify({'error': 'Émote invalide'}), 400
    
    emote_data = EMOTES[emote_id]
    
    if current_user.owns_emote(emote_id):
        return jsonify({'error': 'Vous possédez déjà cette émote'}), 400
    
    if current_user.total_score < emote_data['prix']:
        return jsonify({'error': f'Points insuffisants ! Il vous faut {emote_data["prix"]} points'}), 400
    
    if current_user.buy_emote(emote_id, emote_data['prix']):
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Émote {emote_data["nom"]} achetée !',
            'new_score': current_user.total_score
        })
    
    return jsonify({'error': 'Erreur lors de l\'achat'}), 500

@app.route('/api/game/use_hint', methods=['POST'])
@login_required
def use_hint():
    """Utilise un indice pour révéler si la réponse est bonne ou mauvaise."""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'Aucune partie en cours'}), 400
    
    if current_user.hints_count <= 0:
        return jsonify({'error': 'Vous n\'avez plus d\'indices !'}), 400
    
    game = games[game_id]
    current_question = game['questions'][game['current_index']]
    proposed_answer = game.get('current_proposed_answer')
    
    if not proposed_answer:
        return jsonify({'error': 'Aucune réponse proposée'}), 400
    
    # Décrémenter le nombre d'indices
    current_user.hints_count -= 1
    db.session.commit()
    
    # Vérifier si c'est la bonne réponse
    is_correct = proposed_answer == current_question['bonne_reponse']
    
    return jsonify({
        'success': True,
        'is_correct': is_correct,
        'hints_remaining': current_user.hints_count,
        'message': '✅ C\'est la bonne réponse !' if is_correct else '❌ Ce n\'est pas la bonne réponse !'
    })

@app.route('/api/user/hints', methods=['GET'])
@login_required
def get_hints_count():
    """Retourne le nombre d'indices de l'utilisateur."""
    return jsonify({
        'hints_count': current_user.hints_count
    })

@app.route('/api/user/button_color', methods=['GET'])
@login_required
def get_user_button_color():
    """Retourne la couleur de bouton actuelle de l'utilisateur."""
    color_id = current_user.current_button_color
    if color_id and color_id in BUTTON_COLORS:
        color_data = BUTTON_COLORS[color_id]
        return jsonify({
            'color_id': color_id,
            'couleur': color_data['couleur'],
            'couleur_hover': color_data['couleur_hover']
        })
    return jsonify({
        'color_id': 'default',
        'couleur': BUTTON_COLORS['default']['couleur'],
        'couleur_hover': BUTTON_COLORS['default']['couleur_hover']
    })

@app.route('/api/dev/add_points', methods=['POST'])
@login_required
def dev_add_points():
    """Ajoute des points (mode développeur uniquement)."""
    data = request.json or {}
    password = data.get('password', '')
    points = data.get('points', 0)
    
    # Vérifier le mot de passe (10 espaces)
    if password != '          ':
        return jsonify({'error': 'Mot de passe incorrect'}), 403
    
    try:
        points = int(points)
        if points < 0 or points > 10000:
            return jsonify({'error': 'Nombre de points invalide (0-10000)'}), 400
        
        current_user.add_score(points)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{points} points ajoutés !',
            'new_score': current_user.total_score
        })
    except ValueError:
        return jsonify({'error': 'Nombre de points invalide'}), 400

@app.route('/api/save', methods=['POST'])
@login_required
def save_game():
    """Sauvegarde la partie dans la base de données."""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
    
    game = games[game_id]
    matiere = game.get('matiere', 'thermo')
    timer_minutes = game.get('timer_minutes', 0)
    start_time = game.get('start_time')
    
    # Calculer le temps écoulé pour les parties chronométrées
    elapsed_seconds = 0
    if timer_minutes > 0 and start_time:
        elapsed_seconds = int((datetime.utcnow() - start_time).total_seconds())
    
    game_data = {
        'questions': game['questions'],
        'current_index': game['current_index'],
        'score': game['score'],
        'questions_correctes': game.get('questions_correctes', []),
        'questions_a_reviser': game.get('questions_a_reviser', []),
        'reponses_restantes': game.get('reponses_restantes', []),
        'timer_minutes': timer_minutes,
        'elapsed_seconds': elapsed_seconds
    }
    
    # Supprimer ancienne sauvegarde non terminée de cette matière
    SavedGame.query.filter_by(
        user_id=current_user.id,
        matiere=matiere,
        is_completed=False
    ).delete()
    
    # Créer nouvelle sauvegarde
    saved_game = SavedGame(
        user_id=current_user.id,
        matiere=matiere,
        game_data=json.dumps(game_data),
        score=game['score'],
        total_questions=len(game['questions']),
        questions_correctes=len(game.get('questions_correctes', []))
    )
    db.session.add(saved_game)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Partie sauvegardée'})

@app.route('/api/check_saved', methods=['POST'])
@login_required
def check_saved():
    """Vérifie s'il existe une partie sauvegardée pour une matière."""
    data = request.json or {}
    matiere = data.get('matiere', 'thermo')
    
    saved_game = SavedGame.query.filter_by(
        user_id=current_user.id,
        matiere=matiere,
        is_completed=False
    ).first()
    
    return jsonify({
        'has_saved_game': saved_game is not None,
        'matiere': matiere
    })

@app.route('/api/complete_game', methods=['POST'])
@login_required
def complete_game():
    """Marque la partie comme terminée."""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
    
    game = games[game_id]
    matiere = game.get('matiere', 'thermo')
    timer_minutes = game.get('timer_minutes', 0)
    start_time = game.get('start_time')
    
    # Calculer la durée réelle de la partie
    duration_seconds = 0
    if timer_minutes > 0 and start_time:
        # En mode chrono, la durée est toujours la durée du timer (5 min = 300s)
        duration_seconds = timer_minutes * 60
    
    # Supprimer sauvegarde non terminée
    SavedGame.query.filter_by(
        user_id=current_user.id,
        matiere=matiere,
        is_completed=False
    ).delete()
    
    # Créer sauvegarde terminée
    game_data = {
        'questions': game['questions'],
        'current_index': game['current_index'],
        'score': game['score'],
        'questions_correctes': game.get('questions_correctes', []),
        'questions_a_reviser': game.get('questions_a_reviser', [])
    }
    
    saved_game = SavedGame(
        user_id=current_user.id,
        matiere=matiere,
        game_data=json.dumps(game_data),
        score=game['score'],
        total_questions=len(game['questions']),
        questions_correctes=len(game.get('questions_correctes', [])),
        is_completed=True,
        duration_seconds=duration_seconds
    )
    db.session.add(saved_game)
    
    # Mettre à jour le score total de l'utilisateur (ne peut pas être négatif)
    current_user.add_score(game['score'])
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/restore', methods=['POST'])
@login_required
def restore_game():
    """Restaure une partie sauvegardée depuis la base de données."""
    data = request.json or {}
    matiere = data.get('matiere', 'thermo')
    
    saved_game = SavedGame.query.filter_by(
        user_id=current_user.id,
        matiere=matiere,
        is_completed=False
    ).order_by(SavedGame.updated_at.desc()).first()
    
    if not saved_game:
        return jsonify({'error': 'Aucune partie sauvegardée trouvée'}), 404
    
    game_data = json.loads(saved_game.game_data)
    game_id = str(uuid.uuid4())
    
    # Récupérer les infos du timer
    timer_minutes = game_data.get('timer_minutes', 0)
    elapsed_seconds = game_data.get('elapsed_seconds', 0)
    
    # Calculer le nouveau start_time en soustrayant le temps déjà écoulé
    start_time = None
    if timer_minutes > 0:
        start_time = datetime.utcnow() - timedelta(seconds=elapsed_seconds)
    
    games[game_id] = {
        'user_id': current_user.id,
        'username': current_user.username,
        'matiere': matiere,
        'questions': game_data['questions'],
        'current_index': game_data['current_index'],
        'score': game_data['score'],
        'reponses_restantes': game_data.get('reponses_restantes', []),
        'questions_correctes': game_data.get('questions_correctes', []),
        'questions_a_reviser': game_data.get('questions_a_reviser', []),
        'timer_minutes': timer_minutes,
        'start_time': start_time
    }
    
    session['game_id'] = game_id
    
    return jsonify({
        'success': True,
        'total_questions': len(game_data['questions']),
        'current_index': game_data['current_index'],
        'score': game_data['score'],
        'matiere': matiere,
        'matiere_nom': MATIERES[matiere]['nom'],
        'matiere_emoji': MATIERES[matiere]['emoji'],
        'timer_minutes': timer_minutes
    })

# ==================== MODE BATTLE ====================

def generate_battle_code():
    """Génère un code de battle unique à 6 caractères."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Battle.query.filter_by(code=code).first():
            return code

@app.route('/api/battle/create', methods=['POST'])
@login_required
def create_battle():
    """Crée une nouvelle bataille et retourne le code."""
    data = request.json or {}
    matiere = data.get('matiere')
    
    if not matiere or matiere not in MATIERES:
        return jsonify({'error': 'Matière invalide - veuillez en choisir une'}), 400
    
    # Charger les questions de la matière choisie
    questions = charger_questions(matiere)
    if not questions:
        return jsonify({'error': 'Aucune question trouvée pour cette matière'}), 400
    
    # Créer une nouvelle battle
    code = generate_battle_code()
    questions_json = json.dumps([{
        'question': q['question'],
        'bonne_reponse': q['bonne_reponse'],
        'mauvaises_reponses': q['mauvaises_reponses']
    } for q in questions])
    
    battle = Battle(
        code=code,
        matiere=matiere,
        player1_id=current_user.id,
        questions_data=questions_json
    )
    db.session.add(battle)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'code': code,
        'battle_id': battle.id,
        'matiere': matiere,
        'matiere_nom': MATIERES[matiere]['nom'],
        'total_questions': len(questions)
    })

@app.route('/api/battle/join/<code>', methods=['POST'])
@login_required
def join_battle(code):
    """Rejoindre une bataille avec un code."""
    battle = Battle.query.filter_by(code=code.upper()).first()
    
    if not battle:
        return jsonify({'error': 'Code de battle invalide'}), 404
    
    if battle.status != 'waiting':
        return jsonify({'error': 'Cette battle a déjà commencé ou est terminée'}), 400
    
    if battle.player1_id == current_user.id:
        return jsonify({'error': 'Vous êtes déjà dans cette battle'}), 400
    
    if battle.player2_id:
        return jsonify({'error': 'Cette battle est déjà complète'}), 400
    
    # Rejoindre la battle
    battle.player2_id = current_user.id
    db.session.commit()
    
    # Notifier via SocketIO que le joueur 2 a rejoint
    socketio.emit('player_joined', {
        'player2_name': current_user.username
    }, room=f'battle_{battle.id}')
    
    return jsonify({
        'success': True,
        'battle_id': battle.id,
        'matiere': battle.matiere
    })

@app.route('/api/battle/matchmaking', methods=['POST'])
@login_required
def battle_matchmaking():
    """Trouve ou crée une battle publique pour le matchmaking."""
    data = request.json or {}
    matiere = data.get('matiere', 'thermo')
    
    if matiere not in MATIERES:
        return jsonify({'error': 'Matière invalide'}), 400
    
    # Chercher une battle publique en attente pour cette matière (UNIQUEMENT publiques)
    waiting_battle = Battle.query.filter_by(
        matiere=matiere,
        status='waiting',
        is_public=True,  # Seulement les battles de matchmaking
        player2_id=None
    ).filter(
        Battle.player1_id != current_user.id  # Pas sa propre battle
    ).first()
    
    if waiting_battle:
        # Rejoindre la battle existante
        waiting_battle.player2_id = current_user.id
        # Marquer automatiquement les deux joueurs comme prêts pour le matchmaking
        waiting_battle.player1_ready = True
        waiting_battle.player2_ready = True
        db.session.commit()
        
        # Notifier via SocketIO que le joueur 2 a rejoint
        socketio.emit('player_joined', {
            'player2_name': current_user.username
        }, room=f'battle_{waiting_battle.id}')
        
        return jsonify({
            'matched': True,
            'battle_id': waiting_battle.id,
            'code': waiting_battle.code
        })
    else:
        # Créer une nouvelle battle publique
        code = generate_battle_code()
        battle = Battle(
            code=code,
            matiere=matiere,
            is_public=True,  # Marquer comme battle publique
            player1_id=current_user.id
        )
        db.session.add(battle)
        db.session.commit()
        
        return jsonify({
            'waiting': True,
            'battle_id': battle.id,
            'code': code
        })

@app.route('/api/battle/cancel/<int:battle_id>', methods=['POST'])
@login_required
def cancel_battle_matchmaking(battle_id):
    """Annule une battle en attente de matchmaking."""
    battle = Battle.query.get(battle_id)
    
    if not battle:
        return jsonify({'error': 'Battle introuvable'}), 404
    
    # Seul le créateur peut annuler si personne n'a rejoint
    if battle.player1_id != current_user.id or battle.player2_id is not None:
        return jsonify({'error': 'Impossible d\'annuler cette battle'}), 403
    
    db.session.delete(battle)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/battle/<int:battle_id>', methods=['GET'])
@login_required
def get_battle(battle_id):
    """Récupère les informations d'une battle."""
    battle = Battle.query.get_or_404(battle_id)
    
    # Vérifier que l'utilisateur fait partie de cette battle
    if battle.player1_id != current_user.id and battle.player2_id != current_user.id:
        return jsonify({'error': 'Vous ne faites pas partie de cette battle'}), 403
    
    return jsonify({
        'id': battle.id,
        'code': battle.code,
        'matiere': battle.matiere,
        'player1_name': battle.player1.username,
        'player2_name': battle.player2.username if battle.player2 else None,
        'player1_score': battle.player1_score,
        'player2_score': battle.player2_score,
        'status': battle.status,
        'player1_ready': battle.player1_ready,
        'player2_ready': battle.player2_ready
    })

# ==================== SOCKETIO EVENTS ====================

@socketio.on('connect')
def handle_connect():
    """Gère la connexion d'un client."""
    print(f'Client connecté: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    """Gère la déconnexion d'un client."""
    try:
        print(f'Client déconnecté: {request.sid}')
    except Exception as e:
        # Ignorer les erreurs de déconnexion
        pass

@socketio.on('join_battle')
def handle_join_battle(data):
    """Un joueur rejoint la room de la battle."""
    battle_id = data.get('battle_id')
    if not battle_id:
        return
    
    room = f'battle_{battle_id}'
    join_room(room)
    print(f'Joueur {current_user.username if current_user.is_authenticated else "?"} a rejoint la battle {battle_id}')

@socketio.on('ready')
def handle_player_ready(data):
    """Un joueur est prêt à commencer."""
    battle_id = data.get('battle_id')
    if not battle_id or not current_user.is_authenticated:
        return
    
    battle = Battle.query.get(battle_id)
    if not battle:
        return
    
    # Marquer le joueur comme prêt
    if battle.player1_id == current_user.id:
        battle.player1_ready = True
    elif battle.player2_id == current_user.id:
        battle.player2_ready = True
    
    db.session.commit()
    
    # Notifier l'autre joueur
    emit('player_ready', {
        'player_name': current_user.username,
        'both_ready': battle.player1_ready and battle.player2_ready
    }, room=f'battle_{battle_id}')
    
    # Si les deux joueurs sont prêts, démarrer la battle
    if battle.player1_ready and battle.player2_ready and battle.status == 'waiting':
        # Charger les questions
        questions = charger_questions(battle.matiere)
        random.shuffle(questions)
        
        battle.status = 'playing'
        battle.start_time = datetime.utcnow()
        battle.questions_data = json.dumps(questions)
        db.session.commit()
        
        emit('battle_start', {
            'questions_count': len(questions),
            'start_time': battle.start_time.isoformat()
        }, room=f'battle_{battle_id}')

@socketio.on('answer')
def handle_answer(data):
    """Un joueur répond à une question."""
    battle_id = data.get('battle_id')
    is_correct = data.get('is_correct', False)
    points = data.get('points', 0)
    
    if not battle_id or not current_user.is_authenticated:
        return
    
    battle = Battle.query.get(battle_id)
    if not battle:
        return
    
    # Mettre à jour le score
    if battle.player1_id == current_user.id:
        battle.player1_score += points
    elif battle.player2_id == current_user.id:
        battle.player2_score += points
    
    db.session.commit()
    
    # Diffuser les scores aux deux joueurs
    emit('scores_update', {
        'player1_score': battle.player1_score,
        'player2_score': battle.player2_score
    }, room=f'battle_{battle_id}')

@socketio.on('battle_end')
def handle_battle_end(data):
    """Un joueur a terminé sa partie."""
    battle_id = data.get('battle_id')
    
    if not battle_id or not current_user.is_authenticated:
        return
    
    battle = Battle.query.get(battle_id)
    if not battle:
        return
    
    # Vérifier si le temps est écoulé pour tout le monde
    if battle.start_time:
        elapsed = (datetime.utcnow() - battle.start_time).total_seconds()
        if elapsed >= 300:  # 5 minutes
            battle.status = 'finished'
            battle.end_time = datetime.utcnow()
            
            # Déterminer le gagnant et appliquer les points
            winner = None
            loser = None
            if battle.player1_score > battle.player2_score:
                winner = battle.player1
                loser = battle.player2
                winner_msg = battle.player1.username
            elif battle.player2_score > battle.player1_score:
                winner = battle.player2
                loser = battle.player1
                winner_msg = battle.player2.username
            else:
                winner_msg = 'Égalité'
                winner = None
                loser = None
            
            # Appliquer les modifications de points globaux
            if winner and loser:
                # Gagnant gagne 50 points en plus
                winner.add_score(50)
                # Perdant perd 50 points (minimum 0)
                loser.add_score(-50)
            
            # Ajouter les scores au score total des joueurs
            if battle.player1:
                battle.player1.add_score(battle.player1_score)
            if battle.player2:
                battle.player2.add_score(battle.player2_score)
            
            # Sauvegarder les parties Battle dans l'historique
            if battle.player1:
                battle_game1 = SavedGame(
                    user_id=battle.player1_id,
                    matiere=battle.matiere,
                    game_data=json.dumps({'battle_id': battle.id}),
                    score=battle.player1_score,
                    total_questions=0,
                    questions_correctes=0,
                    is_completed=True,
                    duration_seconds=300  # 5 minutes
                )
                db.session.add(battle_game1)
            
            if battle.player2:
                battle_game2 = SavedGame(
                    user_id=battle.player2_id,
                    matiere=battle.matiere,
                    game_data=json.dumps({'battle_id': battle.id}),
                    score=battle.player2_score,
                    total_questions=0,
                    questions_correctes=0,
                    is_completed=True,
                    duration_seconds=300  # 5 minutes
                )
                db.session.add(battle_game2)
            
            db.session.commit()
            
            emit('battle_finished', {
                'player1_name': battle.player1.username,
                'player2_name': battle.player2.username if battle.player2 else 'Aucun',
                'player1_score': battle.player1_score,
                'player2_score': battle.player2_score,
                'winner': winner_msg
            }, room=f'battle_{battle_id}')

@socketio.on('send_emote')
def handle_send_emote(data):
    """Envoie une émote dans un battle."""
    battle_id = data.get('battle_id')
    emote_id = data.get('emote_id')
    
    if not battle_id or not emote_id or not current_user.is_authenticated:
        return
    
    # Vérifier que l'utilisateur possède l'émote
    if not current_user.owns_emote(emote_id):
        return
    
    battle = Battle.query.get(battle_id)
    if not battle:
        return
    
    # Vérifier que l'utilisateur fait partie du battle
    if current_user.id not in [battle.player1_id, battle.player2_id]:
        return
    
    if emote_id in EMOTES:
        emote_data = EMOTES[emote_id]
        
        # Déterminer l'adversaire
        opponent_id = battle.player2_id if current_user.id == battle.player1_id else battle.player1_id
        
        # Envoyer l'émote UNIQUEMENT à l'adversaire (broadcast=False pour exclure l'expéditeur)
        emit('emote_received', {
            'sender': current_user.username,
            'emote_id': emote_id,
            'emoji': emote_data['emoji'],
            'nom': emote_data['nom']
        }, room=f'battle_{battle_id}', include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
