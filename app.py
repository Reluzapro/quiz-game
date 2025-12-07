#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import random
import os
import uuid
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete_123456'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///thermodynamics_game.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth_page'
login_manager.login_message = None

# Configuration des matières disponibles
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
    'meca': {
        'nom': 'Mécanique',
        'fichier': 'Questions_meca.csv',
        'emoji': '⚙️'
    }
}

# Stockage des parties en cours (en mémoire)
games = {}

# Modèles de base de données
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    games = db.relationship('SavedGame', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SavedGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    matiere = db.Column(db.String(50), nullable=False, default='thermo')
    game_data = db.Column(db.Text, nullable=False)  # JSON data
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    questions_correctes = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Créer les tables
with app.app_context():
    db.create_all()

def charger_questions(matiere='thermo'):
    """Charge les questions depuis le fichier CSV de la matière."""
    if matiere not in MATIERES:
        matiere = 'thermo'
    
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
                    'mauvaises_reponses': [ligne[2], ligne[3], ligne[4]]
                }
                questions.append(question)
    return questions

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

@app.route('/api/start', methods=['POST'])
@login_required
def start_game():
    """Démarre une nouvelle partie."""
    data = request.json or {}
    matiere = data.get('matiere', 'thermo')
    timer_minutes = data.get('timer_minutes', 0)  # 0 = mode classique, 5 ou 10 = mode chronométré
    
    if matiere not in MATIERES:
        return jsonify({'error': 'Matière invalide'}), 400
    
    all_questions = charger_questions(matiere)
    
    if not all_questions:
        return jsonify({'error': f'Aucune question trouvée pour {MATIERES[matiere]["nom"]}'}), 400
    
    # En mode chronométré, filtrer pour ne garder que les questions non réussies
    if timer_minutes > 0:
        questions_to_practice = []
        for q in all_questions:
            progress = QuestionProgress.query.filter_by(
                user_id=current_user.id,
                matiere=matiere,
                question_text=q['question']
            ).first()
            
            # Inclure si jamais vue OU échouée
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
        'start_time': start_time
    }
    
    session['game_id'] = game_id
    
    mode = f"{timer_minutes} min" if timer_minutes > 0 else "classique"
    print(f"Jeu démarré: {MATIERES[matiere]['nom']} ({len(questions)} questions), Mode: {mode}, ID: {game_id}, Joueur: {current_user.username}")
    
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
    
    if current_index >= len(questions):
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
    
    return jsonify({
        'finished': False,
        'question': question_data['question'],
        'reponse_proposee': reponse_proposee,
        'question_number': current_index + 1,
        'total_questions': len(questions),
        'score': game['score'],
        'reponses_restantes': len(reponses_restantes)
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
    """Retourne les meilleurs scores pour une matière."""
    data = request.json or {}
    matiere = data.get('matiere', 'thermo')
    
    # Récupérer les meilleures parties terminées pour cette matière
    best_games = SavedGame.query.filter_by(
        is_completed=True,
        matiere=matiere
    ).order_by(SavedGame.score.desc()).limit(10).all()
    
    scores = [{
        'username': game.user.username,
        'score': game.score,
        'questions_correctes': game.questions_correctes,
        'total_questions': game.total_questions,
        'date': game.created_at.strftime('%d/%m/%Y')
    } for game in best_games]
    
    return jsonify({
        'scores': scores,
        'matiere': matiere,
        'matiere_nom': MATIERES[matiere]['nom']
    })

@app.route('/api/save', methods=['POST'])
@login_required
def save_game():
    """Sauvegarde la partie dans la base de données."""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
    
    game = games[game_id]
    matiere = game.get('matiere', 'thermo')
    
    game_data = {
        'questions': game['questions'],
        'current_index': game['current_index'],
        'score': game['score'],
        'questions_correctes': game.get('questions_correctes', []),
        'questions_a_reviser': game.get('questions_a_reviser', []),
        'reponses_restantes': game.get('reponses_restantes', [])
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
        is_completed=True
    )
    db.session.add(saved_game)
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
    
    games[game_id] = {
        'user_id': current_user.id,
        'username': current_user.username,
        'matiere': matiere,
        'questions': game_data['questions'],
        'current_index': game_data['current_index'],
        'score': game_data['score'],
        'reponses_restantes': game_data.get('reponses_restantes', []),
        'questions_correctes': game_data.get('questions_correctes', []),
        'questions_a_reviser': game_data.get('questions_a_reviser', [])
    }
    
    session['game_id'] = game_id
    
    return jsonify({
        'success': True,
        'total_questions': len(game_data['questions']),
        'current_index': game_data['current_index'],
        'score': game_data['score'],
        'matiere': matiere,
        'matiere_nom': MATIERES[matiere]['nom'],
        'matiere_emoji': MATIERES[matiere]['emoji']
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
