let totalQuestions = 0;
let currentMatiere = 'thermo'; // Matière par défaut
let timerInterval = null;
let timerEnabled = false;
let currentScoreTab = 'single'; // Type de score affiché: 'single' ou 'total'
let userHintsCount = 0; // Nombre d'indices de l'utilisateur
// Durée en ms entre question/réponse et chargement de la suivante
const QUESTION_TRANSITION_DELAY = 600; // réduit par rapport à 1500ms

// Vérifier l'authentification et les sauvegardes au chargement
window.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadMatieres();
    checkSavedGame();
    loadStats();
});

async function loadMatieres() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        
        const container = document.querySelector('.matiere-selector');
        if (!container) return;
        
        // Vider le conteneur
        container.innerHTML = '';
        
        let isFirst = true;
        
        // Créer les boutons pour chaque catégorie
        data.categories.forEach(categorie => {
            if (categorie.has_subcategories) {
                // Catégorie avec sous-catégories (ex: Physique)
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category-group';
                
                const categoryTitle = document.createElement('h3');
                categoryTitle.className = 'category-title';
                categoryTitle.innerHTML = `${categorie.emoji} ${categorie.nom}`;
                categoryDiv.appendChild(categoryTitle);
                
                const subcategoriesDiv = document.createElement('div');
                subcategoriesDiv.className = 'subcategories';
                
                categorie.matieres.forEach(matiere => {
                    const button = document.createElement('button');
                    button.className = 'btn-matiere' + (isFirst ? ' active' : '');
                    button.id = `btn-${matiere.id}`;
                    button.onclick = () => selectMatiere(matiere.id);
                    
                    button.innerHTML = `
                        <div class="matiere-emoji">${matiere.emoji}</div>
                        <div class="matiere-name">${matiere.nom}</div>
                    `;
                    
                    subcategoriesDiv.appendChild(button);
                    
                    if (isFirst) {
                        currentMatiere = matiere.id;
                        isFirst = false;
                    }
                });
                
                categoryDiv.appendChild(subcategoriesDiv);
                container.appendChild(categoryDiv);
            } else {
                // Catégorie directe (ex: Maths, Meca, Elec, Anglais)
                const matiere = categorie.matieres[0];
                const button = document.createElement('button');
                button.className = 'btn-matiere' + (isFirst ? ' active' : '');
                button.id = `btn-${matiere.id}`;
                button.onclick = () => selectMatiere(matiere.id);
                
                button.innerHTML = `
                    <div class="matiere-emoji">${matiere.emoji}</div>
                    <div class="matiere-name">${matiere.nom}</div>
                `;
                
                container.appendChild(button);
                
                if (isFirst) {
                    currentMatiere = matiere.id;
                    isFirst = false;
                }
            }
        });
    } catch (error) {
        console.error('Erreur lors du chargement des matières:', error);
    }
}

function selectMatiere(matiere) {
    currentMatiere = matiere;
    
    // Mettre à jour l'interface
    document.querySelectorAll('.btn-matiere').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`btn-${matiere}`).classList.add('active');
    
    // Recharger les sauvegardes et stats pour cette matière
    checkSavedGame();
    loadStats();
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ matiere: currentMatiere })
        });
        const data = await response.json();
        
        // Mettre à jour les stats dans l'interface si l'élément existe
        const statsContainer = document.getElementById('stats-container');
        if (statsContainer && data) {
            statsContainer.innerHTML = `
                <div class="stats-card">
                    <div class="stat-item success">
                        <span class="stat-label">✅ Réussies</span>
                        <span class="stat-value">${data.success_count}</span>
                    </div>
                    <div class="stat-item failed">
                        <span class="stat-label">❌ Ratées</span>
                        <span class="stat-value">${data.failed_count}</span>
                    </div>
                    <div class="stat-item unseen">
                        <span class="stat-label">👁️ Non vues</span>
                        <span class="stat-value">${data.never_seen_count}</span>
                    </div>
                    <div class="stat-item completion">
                        <span class="stat-label">📊 Complétion</span>
                        <span class="stat-value">${data.completion_percent}%</span>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur lors du chargement des stats:', error);
    }
}

async function checkAuth() {
    try {
        const response = await fetch('/api/current_user');
        const data = await response.json();
        
        if (!data.authenticated) {
            // Non connecté, rediriger vers la page de connexion
            window.location.href = '/auth';
            return;
        }
        
        // Afficher le nom d'utilisateur
        document.getElementById('username-display').textContent = `👤 ${data.username}`;
    } catch (error) {
        console.error('Erreur:', error);
        window.location.href = '/auth';
    }
}

async function handleLogout() {
    if (!confirm('Voulez-vous vraiment vous déconnecter ?')) {
        return;
    }
    
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/auth';
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la déconnexion');
    }
}

async function checkSavedGame() {
    try {
        const response = await fetch('/api/check_saved', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ matiere: currentMatiere })
        });
        const data = await response.json();
        
        if (data.has_saved_game) {
            document.getElementById('resume-btn').style.display = 'block';
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function startGame(matiere = null, timerMinutes = 0) {
    try {
        // Si une matière est fournie, la définir comme matière actuelle
        if (matiere) {
            currentMatiere = matiere;
        }
        
        // Vérifier s'il y a une sauvegarde
        const checkResponse = await fetch('/api/check_saved', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ matiere: currentMatiere })
        });
        const checkData = await checkResponse.json();
        
        if (checkData.has_saved_game) {
            if (!confirm('Vous avez une partie en cours. Voulez-vous vraiment commencer une nouvelle partie ? (La sauvegarde sera effacée)')) {
                return;
            }
        }
        
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                matiere: currentMatiere,
                timer_minutes: timerMinutes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            totalQuestions = data.total_questions;
            timerEnabled = data.timer_minutes > 0;
            
            // Afficher la matière dans l'interface
            if (data.matiere_emoji && data.matiere_nom) {
                document.getElementById('question-text').textContent = `${data.matiere_emoji} ${data.matiere_nom}`;
            }
            
            // Démarrer le chronomètre si activé
            if (timerEnabled) {
                startTimer();
            } else {
                // Masquer le chronomètre en mode classique
                const timerDisplay = document.getElementById('timer-display');
                if (timerDisplay) {
                    timerDisplay.style.display = 'none';
                }
            }
            
            showScreen('game-screen');
            loadQuestion();
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du démarrage du jeu');
    }
}

function startTimer() {
    const timerDisplay = document.getElementById('timer-display');
    if (timerDisplay) {
        timerDisplay.style.display = 'block';
    }
    
    // Arrêter l'ancien timer si existe
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    
    // Mettre à jour toutes les secondes
    timerInterval = setInterval(updateTimer, 1000);
    updateTimer(); // Mise à jour immédiate
}

async function updateTimer() {
    try {
        const response = await fetch('/api/time_remaining');
        const data = await response.json();
        
        if (!data.timer_enabled) {
            stopTimer();
            return;
        }
        
        const minutes = Math.floor(data.remaining_seconds / 60);
        const seconds = data.remaining_seconds % 60;
        
        const timerElement = document.getElementById('timer');
        if (timerElement) {
            timerElement.textContent = `⏱️ ${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            // Changer la couleur si moins d'une minute
            if (data.remaining_seconds < 60) {
                timerElement.style.color = '#e74c3c';
            } else {
                timerElement.style.color = '#2ecc71';
            }
        }
        
        // Terminer la partie si le temps est écoulé
        if (data.is_expired) {
            stopTimer();
            alert('⏰ Temps écoulé ! La partie se termine.');
            showTimedGameEnd();
        }
    } catch (error) {
        console.error('Erreur lors de la mise à jour du timer:', error);
    }
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

async function showTimedGameEnd() {
    try {
        // Récupérer les statistiques finales
        const response = await fetch('/api/question');
        const data = await response.json();
        
        showEndScreen(data.score || 0, false, 0);
    } catch (error) {
        console.error('Erreur:', error);
        showEndScreen(0, false, 0);
    }
}

async function loadQuestion() {
    try {
        const response = await fetch('/api/question');
        const data = await response.json();
        
        if (data.finished) {
            showEndScreen(data.score, data.has_revision, data.revision_count);
            return;
        }
        
        // Mettre à jour l'interface
        document.getElementById('question-text').innerHTML = data.question;
        document.getElementById('answer-text').innerHTML = data.reponse_proposee;
        document.getElementById('score').textContent = data.score;
        document.getElementById('question-counter').textContent = 
            `Question ${data.question_number}/${data.total_questions}`;
        
        // Rendre les formules LaTeX avec MathJax
        if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
            MathJax.typesetPromise([
                document.getElementById('question-text'),
                document.getElementById('answer-text')
            ]).catch((err) => console.error('Erreur MathJax:', err));
        }
        
        // Afficher le nombre de réponses restantes
        const remainingDiv = document.getElementById('remaining-answers');
        if (data.reponses_restantes > 1) {
            remainingDiv.textContent = `(${data.reponses_restantes} réponses restantes)`;
        } else {
            remainingDiv.textContent = '(Dernière réponse!)';
        }
        
        // Réinitialiser l'affichage
        document.getElementById('message').className = 'message';
        document.getElementById('message').textContent = '';
        document.getElementById('buttons').style.display = 'flex';
        document.getElementById('next-btn').style.display = 'none';
        
        // Réinitialiser l'affichage de l'indice
        const hintResult = document.getElementById('hint-result');
        if (hintResult) {
            hintResult.classList.remove('show');
        }
        
        // Charger le nombre d'indices et afficher le bouton si nécessaire
        await loadHintsCount();
        
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement de la question');
    }
}

async function submitAnswer(answer) {
    try {
        const response = await fetch('/api/answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ answer: answer })
        });
        
        const data = await response.json();
        
        // Mettre à jour le score
        document.getElementById('score').textContent = data.score;
        
        // Afficher le message
        const messageDiv = document.getElementById('message');
        messageDiv.textContent = data.message;
        messageDiv.className = 'message show';
        
        if (data.correct) {
            messageDiv.classList.add('success');
        } else if (data.points < 0) {
            messageDiv.classList.add('error');
            messageDiv.textContent += `\n\nLa bonne réponse était: ${data.bonne_reponse}`;
        } else {
            messageDiv.classList.add('info');
        }
        
        if (data.next_question) {
            // Masquer les boutons OUI/NON et afficher le bouton Suivant
            document.getElementById('buttons').style.display = 'none';
            document.getElementById('next-btn').style.display = 'block';
        } else {
            // Recharger la question avec la nouvelle réponse (délais réduit pour UX plus fluide)
            setTimeout(() => {
                loadQuestion();
            }, QUESTION_TRANSITION_DELAY);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la soumission de la réponse');
    }
}

function nextQuestion() {
    loadQuestion();
}

function showEndScreen(score, hasRevision = false, revisionCount = 0) {
    // Marquer la partie comme terminée
    markGameCompleted();
    checkSavedGame();
    
    document.getElementById('final-score').textContent = score;
    document.getElementById('total-questions').textContent = 
        `Sur ${totalQuestions} questions`;
    
    // Message personnalisé selon le score
    const maxScore = totalQuestions * 10;
    const messageDiv = document.getElementById('final-message');
    
    if (score === maxScore) {
        messageDiv.textContent = '🏆 PARFAIT! Vous avez répondu correctement à toutes les questions!';
    } else if (score >= maxScore * 0.7) {
        messageDiv.textContent = '⭐ Excellent! Très bon score!';
    } else if (score >= maxScore * 0.4) {
        messageDiv.textContent = '👍 Bien joué! Continuez à vous améliorer!';
    } else if (score >= 0) {
        messageDiv.textContent = '💪 Pas mal! Continuez à étudier!';
    } else {
        messageDiv.textContent = '📚 Continuez à étudier, vous ferez mieux la prochaine fois!';
    }
    
    // Afficher la section révision si nécessaire
    const revisionSection = document.getElementById('revision-section');
    if (hasRevision && revisionCount > 0) {
        document.getElementById('revision-count').textContent = revisionCount;
        revisionSection.style.display = 'block';
    } else {
        revisionSection.style.display = 'none';
    }
    
    showScreen('end-screen');
}

async function markGameCompleted() {
    try {
        await fetch('/api/complete_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    } catch (error) {
        console.error('Erreur:', error);
    }
}

function restartGame() {
    showScreen('home-screen');
}

async function startRevision() {
    try {
        const response = await fetch('/api/start_revision', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            totalQuestions = data.total_questions;
            showScreen('game-screen');
            loadQuestion();
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du démarrage de la révision');
    }
}

function showScoreTab(tab) {
    currentScoreTab = tab;
    
    // Mettre à jour l'apparence des onglets
    document.querySelectorAll('.score-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Charger les scores correspondants
    if (tab === 'single') {
        loadSingleScores();
    } else {
        loadTotalScores();
    }
}

async function loadSingleScores() {
    try {
        const response = await fetch('/api/scores', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ matiere: currentMatiere })
        });
        const data = await response.json();
        const scores = data.scores || [];
        
        // Mettre à jour le titre avec la matière
        const scoresTitle = document.querySelector('#scores-screen h1');
        if (scoresTitle && data.matiere_nom) {
            scoresTitle.textContent = `🏆 Classement - ${data.matiere_nom}`;
        }
        
        displayScores(scores, 'score');
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement des scores');
    }
}

async function loadTotalScores() {
    try {
        const response = await fetch('/api/scores/total', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        const scores = data.scores || [];
        
        // Mettre à jour le titre
        const scoresTitle = document.querySelector('#scores-screen h1');
        if (scoresTitle) {
            scoresTitle.textContent = `🏆 Classement Général`;
        }
        
        // Afficher le score total de l'utilisateur actuel
        displayScores(scores, 'total_score', data.current_user_score);
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement des scores totaux');
    }
}

function displayScores(scores, scoreField, currentUserScore = null) {
    const scoresList = document.getElementById('scores-list');
    
    if (scores.length === 0) {
        scoresList.innerHTML = '<p style="text-align: center; color: #6c757d;">Aucun score pour le moment</p>';
    } else {
        let html = '';
        
        // Afficher le score de l'utilisateur actuel si on est dans l'onglet total
        if (currentUserScore !== null && scoreField === 'total_score') {
            html += `
                <div class="score-item" style="background: #e7f3ff; border-left-color: #007bff; margin-bottom: 20px;">
                    <div>
                        <div class="score-username">👤 Votre score total</div>
                    </div>
                    <div class="score-value">${currentUserScore} pts</div>
                </div>
            `;
        }
        
        scores.forEach((score, index) => {
            let rankClass = '';
            let medal = '';
            if (index === 0) {
                rankClass = 'first';
                medal = '🥇 ';
            } else if (index === 1) {
                rankClass = 'second';
                medal = '🥈 ';
            } else if (index === 2) {
                rankClass = 'third';
                medal = '🥉 ';
            }
            
            const scoreValue = scoreField === 'total_score' ? score.total_score : score.score;
            const extraInfo = scoreField === 'total_score' ? `<div class="score-details">${score.games_played} parties jouées</div>` : '';
            
            html += `
                <div class="score-item ${rankClass}">
                    <div>
                        <div class="score-username">${medal}${score.username}</div>
                        ${extraInfo}
                    </div>
                    <div class="score-value">${scoreValue} pts</div>
                </div>
            `;
        });
        scoresList.innerHTML = html;
    }
}

async function showScores() {
    // Afficher l'écran et charger les scores selon l'onglet actif
    showScreen('scores-screen');
    
    if (currentScoreTab === 'single') {
        await loadSingleScores();
    } else {
        await loadTotalScores();
    }
}

async function saveAndQuit() {
    if (!confirm('Voulez-vous sauvegarder votre partie et quitter ?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert('Erreur lors de la sauvegarde');
            return;
        }
        
        alert('✅ Partie sauvegardée avec succès!\n\nVous pourrez reprendre votre partie depuis n\'importe quel appareil en vous connectant avec votre compte.');
        
        // Retourner à l'écran d'accueil
        showScreen('home-screen');
        checkSavedGame();
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la sauvegarde');
    }
}

async function resumeGame() {
    try {
        const response = await fetch('/api/restore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ matiere: currentMatiere })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error || 'Erreur lors de la restauration');
            return;
        }
        
        if (data.success) {
            totalQuestions = data.total_questions;
            if (data.matiere) {
                currentMatiere = data.matiere;
            }
            
            // Relancer le timer si c'était une partie chronométrée
            if (data.timer_minutes && data.timer_minutes > 0) {
                timerEnabled = true;
                startTimer();
            }
            
            showScreen('game-screen');
            loadQuestion();
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la restauration de la partie');
    }
}

function showScreen(screenId) {
    // Masquer tous les écrans
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    
    // Afficher l'écran demandé
    document.getElementById(screenId).classList.add('active');
}

// ==================== MODE BATTLE ====================

let socket = null;
let currentBattle = null;
let battleQuestions = [];
let battleCurrentIndex = 0;
let battleReponses = [];
let battleTimer = null;

function initSocket() {
    if (!socket) {
        socket = io();
        
        socket.on('connect', () => {
            console.log('Connecté au serveur');
        });
        
        socket.on('player_joined', (data) => {
            document.getElementById('player2-name').textContent = data.player2_name;
            document.getElementById('player2-status').textContent = '⏳';
            document.getElementById('ready-btn').disabled = false;
        });
        
        socket.on('player_ready', (data) => {
            if (data.both_ready) {
                // Les deux sont prêts, attendre le démarrage
            }
        });
        
        socket.on('battle_start', (data) => {
            startBattleGame();
        });
        
        socket.on('scores_update', (data) => {
            document.getElementById('battle-player1-score').textContent = data.player1_score;
            document.getElementById('battle-player2-score').textContent = data.player2_score;
        });
        
        socket.on('battle_finished', (data) => {
            showBattleResults(data);
        });
    }
}

function showBattleMenu() {
    initSocket();
    showScreen('battle-menu-screen');
}

async function createBattle() {
    try {
        const response = await fetch('/api/battle/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ matiere: currentMatiere })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentBattle = {
                id: data.battle_id,
                code: data.code
            };
            currentBattleId = data.battle_id;
            
            document.getElementById('battle-code-display').textContent = data.code;
            document.getElementById('player1-name').textContent = document.getElementById('username-display').textContent.replace('👤 ', '');
            
            socket.emit('join_battle', { battle_id: data.battle_id });
            showScreen('battle-waiting-screen');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la création de la battle');
    }
}

async function joinBattle() {
    const code = document.getElementById('battle-code-input').value.trim().toUpperCase();
    
    if (!code || code.length !== 6) {
        alert('Veuillez entrer un code valide à 6 caractères');
        return;
    }
    
    try {
        const response = await fetch(`/api/battle/join/${code}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        if (data.success) {
            currentBattle = {
                id: data.battle_id,
                code: code
            };
            currentBattleId = data.battle_id;
            
            socket.emit('join_battle', { battle_id: data.battle_id });
            
            // Charger les infos de la battle
            await loadBattleInfo(data.battle_id);
            showScreen('battle-waiting-screen');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de la connexion à la battle');
    }
}

async function loadBattleInfo(battleId) {
    try {
        const response = await fetch(`/api/battle/${battleId}`);
        const data = await response.json();
        
        document.getElementById('battle-code-display').textContent = data.code;
        document.getElementById('player1-name').textContent = data.player1_name;
        if (data.player2_name) {
            document.getElementById('player2-name').textContent = data.player2_name;
            document.getElementById('player2-status').textContent = '⏳';
            document.getElementById('ready-btn').disabled = false;
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}

function markReady() {
    socket.emit('ready', { battle_id: currentBattle.id });
    document.getElementById('ready-btn').disabled = true;
    document.getElementById('ready-btn').textContent = '✅ Prêt !';
}

function cancelBattle() {
    currentBattle = null;
    restartGame();
}

// ==================== MATCHMAKING ====================

let matchmakingInterval = null;

async function startMatchmaking() {
    try {
        // Créer une battle publique (matchmaking)
        const response = await fetch('/api/battle/matchmaking', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ matiere: currentMatiere })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        if (data.matched) {
            // Match trouvé immédiatement - Les deux joueurs sont prêts automatiquement
            currentBattle = {
                id: data.battle_id,
                code: data.code
            };
            currentBattleId = data.battle_id;
            
            socket.emit('join_battle', { battle_id: data.battle_id });
            
            // Attendre un peu pour la synchronisation Socket.IO puis lancer directement
            setTimeout(() => {
                startBattleGame();
            }, 1000);
        } else if (data.waiting) {
            // En attente d'un match
            currentBattle = {
                id: data.battle_id,
                code: data.code
            };
            currentBattleId = data.battle_id;
            
            socket.emit('join_battle', { battle_id: data.battle_id });
            showScreen('matchmaking-screen');
            
            // Polling pour vérifier si quelqu'un a rejoint
            matchmakingInterval = setInterval(async () => {
                try {
                    const checkResponse = await fetch(`/api/battle/${data.battle_id}`);
                    const checkData = await checkResponse.json();
                    
                    if (checkData.player2_name && checkData.player1_ready && checkData.player2_ready) {
                        clearInterval(matchmakingInterval);
                        // Les deux sont prêts, lancer directement la battle
                        setTimeout(() => {
                            startBattleGame();
                        }, 1000);
                    }
                } catch (error) {
                    console.error('Erreur matchmaking:', error);
                }
            }, 2000); // Vérifier toutes les 2 secondes
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du matchmaking');
    }
}

function cancelMatchmaking() {
    if (matchmakingInterval) {
        clearInterval(matchmakingInterval);
        matchmakingInterval = null;
    }
    
    // Supprimer la battle en attente
    if (currentBattle) {
        fetch(`/api/battle/cancel/${currentBattle.id}`, {
            method: 'POST'
        }).catch(err => console.error(err));
    }
    
    currentBattle = null;
    restartGame();
}

async function startBattleGame() {
    // Charger les infos de la battle
    const response = await fetch(`/api/battle/${currentBattle.id}`);
    const data = await response.json();
    
    document.getElementById('battle-player1-name').textContent = data.player1_name;
    document.getElementById('battle-player2-name').textContent = data.player2_name;
    document.getElementById('battle-player1-score').textContent = data.player1_score;
    document.getElementById('battle-player2-score').textContent = data.player2_score;
    
    // Charger les questions
    const gameResponse = await fetch('/api/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            matiere: currentMatiere,
            timer_minutes: 5
        })
    });
    
    const gameData = await gameResponse.json();
    totalQuestions = gameData.total_questions;
    
    showScreen('battle-game-screen');
    startBattleTimer();
    loadBattleQuestion();
}

function startBattleTimer() {
    const startTime = Date.now();
    const duration = 5 * 60 * 1000; // 5 minutes
    
    battleTimer = setInterval(() => {
        const elapsed = Date.now() - startTime;
        const remaining = Math.max(0, duration - elapsed);
        
        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        
        const timerDisplay = document.getElementById('battle-timer-display');
        timerDisplay.textContent = `⏱️ ${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        if (remaining < 60000) {
            timerDisplay.style.color = '#e74c3c';
        }
        
        if (remaining === 0) {
            clearInterval(battleTimer);
            socket.emit('battle_end', { battle_id: currentBattle.id });
        }
    }, 1000);
}

async function loadBattleQuestion() {
    try {
        const response = await fetch('/api/question');
        const data = await response.json();
        
        if (data.finished) {
            clearInterval(battleTimer);
            socket.emit('battle_end', { battle_id: currentBattle.id });
            return;
        }
        
        document.getElementById('battle-question-text').innerHTML = data.question;
        document.getElementById('battle-answer-text').innerHTML = data.reponse_proposee;
        
        // Rendre les formules LaTeX avec MathJax
        if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
            MathJax.typesetPromise([
                document.getElementById('battle-question-text'),
                document.getElementById('battle-answer-text')
            ]).catch((err) => console.error('Erreur MathJax:', err));
        }
        
        const remainingDiv = document.getElementById('battle-remaining-answers');
        if (data.reponses_restantes > 1) {
            remainingDiv.textContent = `(${data.reponses_restantes} réponses restantes)`;
        } else {
            remainingDiv.textContent = '(Dernière réponse!)';
        }
        
        document.getElementById('battle-message').className = 'message';
        document.getElementById('battle-message').textContent = '';
        document.getElementById('battle-buttons').style.display = 'flex';
        document.getElementById('battle-next-btn').style.display = 'none';
        
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function submitBattleAnswer(answer) {
    try {
        const response = await fetch('/api/answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ answer: answer })
        });
        
        const data = await response.json();
        
        const messageDiv = document.getElementById('battle-message');
        messageDiv.textContent = data.message;
        messageDiv.className = 'message show';
        
        if (data.correct) {
            messageDiv.classList.add('success');
        } else if (data.points < 0) {
            messageDiv.classList.add('error');
        } else {
            messageDiv.classList.add('info');
        }
        
        // Envoyer via SocketIO
        socket.emit('answer', {
            battle_id: currentBattle.id,
            is_correct: data.correct,
            points: data.points
        });
        
        if (data.next_question) {
            document.getElementById('battle-buttons').style.display = 'none';
            document.getElementById('battle-next-btn').style.display = 'block';
        } else {
            setTimeout(() => {
                loadBattleQuestion();
            }, 1500);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
    }
}

function nextBattleQuestion() {
    loadBattleQuestion();
}

function showBattleResults(data) {
    clearInterval(battleTimer);
    
    document.getElementById('result-player1-name').textContent = data.player1_name;
    document.getElementById('result-player2-name').textContent = data.player2_name;
    document.getElementById('result-player1-score').textContent = `${data.player1_score} pts`;
    document.getElementById('result-player2-score').textContent = `${data.player2_score} pts`;
    
    const winnerDiv = document.getElementById('winner-announcement');
    if (data.winner === 'Égalité') {
        winnerDiv.textContent = '🤝 Égalité !';
        winnerDiv.style.color = '#f39c12';
    } else {
        winnerDiv.textContent = `🏆 Gagnant : ${data.winner}`;
        winnerDiv.style.color = '#2ecc71';
    }
    
    showScreen('battle-result-screen');
}

// ==================== INDICES ====================

async function loadHintsCount() {
    try {
        const response = await fetch('/api/user/hints');
        const data = await response.json();
        userHintsCount = data.hints_count;
        
        // Mettre à jour l'affichage
        const hintsDisplay = document.getElementById('user-hints-display');
        if (hintsDisplay) {
            hintsDisplay.textContent = userHintsCount;
        }
        
        const hintsCountSpan = document.getElementById('hints-count');
        if (hintsCountSpan) {
            hintsCountSpan.textContent = userHintsCount;
        }
        
        // Afficher/masquer le bouton indice dans le jeu
        const hintButton = document.getElementById('hint-button');
        if (hintButton) {
            if (userHintsCount > 0) {
                hintButton.style.display = 'block';
                hintButton.disabled = false;
            } else {
                hintButton.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Erreur lors du chargement des indices:', error);
    }
}

async function buyHints(quantity) {
    const userPoints = parseInt(document.getElementById('user-points-display').textContent);
    const price = quantity * 25;
    
    if (userPoints < price) {
        alert(`Pas assez de points ! Il vous faut ${price} points (vous avez ${userPoints} pts)`);
        return;
    }
    
    if (!confirm(`Voulez-vous acheter ${quantity} indice${quantity > 1 ? 's' : ''} pour ${price} points ?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/shop/buy_hints', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity: quantity })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message);
            // Recharger la boutique
            showShop();
        } else {
            alert(data.error || 'Erreur lors de l\'achat');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'achat des indices');
    }
}

async function useHint() {
    if (userHintsCount <= 0) {
        alert('Vous n\'avez plus d\'indices ! Achetez-en dans la boutique.');
        return;
    }
    
    if (!confirm('Utiliser un indice pour révéler si cette réponse est bonne ? (1 indice)')) {
        return;
    }
    
    try {
        const response = await fetch('/api/game/use_hint', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Mettre à jour le nombre d'indices
            userHintsCount = data.hints_remaining;
            document.getElementById('hints-count').textContent = userHintsCount;
            
            // Afficher le résultat de l'indice
            const hintResult = document.getElementById('hint-result');
            hintResult.textContent = data.message;
            hintResult.className = 'hint-result show ' + (data.is_correct ? 'correct' : 'incorrect');
            
            // Masquer le bouton si plus d'indices
            if (userHintsCount <= 0) {
                document.getElementById('hint-button').style.display = 'none';
            }
            
            // Cacher le résultat après 3 secondes
            setTimeout(() => {
                hintResult.classList.remove('show');
            }, 5000);
        } else {
            alert(data.error || 'Erreur lors de l\'utilisation de l\'indice');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'utilisation de l\'indice');
    }
}

// ==================== BOUTIQUE ====================

async function showShop() {
    try {
        const response = await fetch('/api/shop/themes', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        // Afficher les points de l'utilisateur
        document.getElementById('user-points-display').textContent = data.user_score;
        
        // Charger et afficher le nombre d'indices
        await loadHintsCount();
        
        // Afficher les thèmes
        const themesGrid = document.getElementById('themes-grid');
        themesGrid.innerHTML = '';
        
        data.themes.forEach(theme => {
            const themeCard = document.createElement('div');
            themeCard.className = 'theme-card';
            
            if (theme.owned) {
                themeCard.classList.add('owned');
            }
            if (theme.equipped) {
                themeCard.classList.add('equipped');
            }
            
            let badge = '';
            if (theme.equipped) {
                badge = '<span class="theme-badge equipped">✓ Équipé</span>';
            } else if (theme.owned) {
                badge = '<span class="theme-badge owned">✓ Possédé</span>';
            }
            
            let actionButtons = '';
            if (theme.equipped) {
                actionButtons = '<button class="btn btn-secondary" disabled>Actuellement équipé</button>';
            } else if (theme.owned) {
                actionButtons = `<button class="btn btn-primary" onclick="equipTheme('${theme.id}')">Équiper</button>`;
            } else {
                actionButtons = `<button class="btn btn-success" onclick="buyTheme('${theme.id}', ${theme.prix})">Acheter (${theme.prix} pts)</button>`;
            }
            
            themeCard.innerHTML = `
                <div class="theme-preview" style="background: ${theme.gradient};">
                    ${badge}
                </div>
                <div class="theme-name">${theme.nom}</div>
                <div class="theme-description">${theme.description}</div>
                <div class="theme-actions">
                    ${actionButtons}
                </div>
            `;
            
            themesGrid.appendChild(themeCard);
        });
        
        showScreen('shop-screen');
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement de la boutique');
    }
}

async function buyTheme(themeId, prix) {
    // Vérifier si l'utilisateur a assez de points
    const userPoints = parseInt(document.getElementById('user-points-display').textContent);
    if (userPoints < prix) {
        alert(`Pas assez de points ! Il vous faut ${prix} points (vous avez ${userPoints} pts)`);
        return;
    }
    
    if (!confirm(`Voulez-vous acheter ce thème pour ${prix} points ?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/shop/buy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ theme_id: themeId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message);
            // Recharger la boutique
            showShop();
        } else {
            alert(data.error || 'Erreur lors de l\'achat');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'achat du thème');
    }
}

async function equipTheme(themeId) {
    try {
        const response = await fetch('/api/shop/equip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ theme_id: themeId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Appliquer le nouveau gradient
            document.body.style.background = data.gradient;
            alert(data.message);
            // Recharger la boutique
            showShop();
        } else {
            alert(data.error || 'Erreur lors de l\'équipement');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'équipement du thème');
    }
}

// Charger le thème de l'utilisateur au démarrage
async function loadUserTheme() {
    try {
        const response = await fetch('/api/shop/themes', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        // Trouver le thème équipé
        const equippedTheme = data.themes.find(t => t.equipped);
        if (equippedTheme) {
            document.body.style.background = equippedTheme.gradient;
        }
    } catch (error) {
        console.error('Erreur lors du chargement du thème:', error);
    }
}

// Charger le thème au démarrage de la page
window.addEventListener('DOMContentLoaded', () => {
    loadUserTheme();
    loadUserButtonColor();
});

// ==================== COULEURS DE BOUTONS ====================

async function loadUserButtonColor() {
    try {
        const response = await fetch('/api/user/button_color', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        if (data.couleur) {
            applyButtonColor(data.couleur, data.couleur_hover);
        }
    } catch (error) {
        console.error('Erreur lors du chargement de la couleur des boutons:', error);
    }
}

function applyButtonColor(couleur, couleurHover) {
    // Créer ou mettre à jour le style personnalisé pour les boutons
    let styleElement = document.getElementById('custom-button-style');
    if (!styleElement) {
        styleElement = document.createElement('style');
        styleElement.id = 'custom-button-style';
        document.head.appendChild(styleElement);
    }
    
    styleElement.textContent = `
        .btn-success {
            background: ${couleur} !important;
        }
        .btn-success:hover {
            background: ${couleurHover} !important;
        }
    `;
}

async function loadButtonColors() {
    try {
        const response = await fetch('/api/shop/button_colors', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        const colorsGrid = document.getElementById('button-colors-grid');
        colorsGrid.innerHTML = '';
        
        data.colors.forEach(color => {
            const colorCard = document.createElement('div');
            colorCard.className = 'theme-card';
            
            if (color.owned) {
                colorCard.classList.add('owned');
            }
            if (color.equipped) {
                colorCard.classList.add('equipped');
            }
            
            let badge = '';
            if (color.equipped) {
                badge = '<span class="theme-badge equipped">✓ Équipé</span>';
            } else if (color.owned) {
                badge = '<span class="theme-badge owned">✓ Possédé</span>';
            }
            
            let actionButtons = '';
            if (color.equipped) {
                actionButtons = '<button class="btn btn-secondary" disabled>Actuellement équipé</button>';
            } else if (color.owned) {
                actionButtons = `<button class="btn btn-primary" onclick="equipButtonColor('${color.id}')">Équiper</button>`;
            } else {
                actionButtons = `<button class="btn btn-success" onclick="buyButtonColor('${color.id}', ${color.prix})">Acheter (${color.prix} pts)</button>`;
            }
            
            colorCard.innerHTML = `
                <div class="theme-preview" style="background: ${color.couleur}; display:flex; align-items:center; justify-content:center;">
                    ${badge}
                    <button class="sample-btn" style="background:${color.couleur};">Aperçu</button>
                </div>
                <div class="theme-name">${color.nom}</div>
                <div class="theme-description">${color.description}</div>
                <div class="theme-actions">
                    ${actionButtons}
                </div>
            `;
            
            colorsGrid.appendChild(colorCard);
        });
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function buyButtonColor(colorId, prix) {
    const userPoints = parseInt(document.getElementById('user-points-display').textContent);
    if (userPoints < prix) {
        alert(`Pas assez de points ! Il vous faut ${prix} points (vous avez ${userPoints} pts)`);
        return;
    }
    
    if (!confirm(`Voulez-vous acheter cette couleur pour ${prix} points ?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/shop/buy_button_color', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ color_id: colorId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message);
            showShop();
        } else {
            alert(data.error || 'Erreur lors de l\'achat');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'achat de la couleur');
    }
}

async function equipButtonColor(colorId) {
    try {
        const response = await fetch('/api/shop/equip_button_color', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ color_id: colorId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            applyButtonColor(data.couleur, data.couleur_hover);
            alert(data.message);
            showShop();
        } else {
            alert(data.error || 'Erreur lors de l\'équipement');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'équipement de la couleur');
    }
}

// ==================== ÉMOTES ====================

async function loadEmotes() {
    try {
        const response = await fetch('/api/shop/emotes', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        const emotesGrid = document.getElementById('emotes-grid');
        emotesGrid.innerHTML = '';
        
        data.emotes.forEach(emote => {
            const emoteCard = document.createElement('div');
            emoteCard.className = 'emote-card';
            
            if (emote.owned) {
                emoteCard.classList.add('owned');
            }
            
            let badge = emote.owned ? '<span class="theme-badge owned">✓ Possédé</span>' : '';
            
            let actionButton = '';
            if (emote.owned) {
                actionButton = '<button class="btn btn-secondary" disabled>Possédé</button>';
            } else {
                actionButton = `<button class="btn btn-success" onclick="buyEmote('${emote.id}', ${emote.prix})">Acheter (${emote.prix} pts)</button>`;
            }
            
            emoteCard.innerHTML = `
                <div class="emote-preview">
                    <span class="emote-emoji">${emote.emoji}</span>
                    ${badge}
                </div>
                <div class="emote-name">${emote.nom}</div>
                <div class="emote-description">${emote.description}</div>
                <div class="emote-actions">
                    ${actionButton}
                </div>
            `;
            
            emotesGrid.appendChild(emoteCard);
        });
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function buyEmote(emoteId, prix) {
    const userPoints = parseInt(document.getElementById('user-points-display').textContent);
    if (userPoints < prix) {
        alert(`Pas assez de points ! Il vous faut ${prix} points (vous avez ${userPoints} pts)`);
        return;
    }
    
    if (!confirm(`Voulez-vous acheter cette émote pour ${prix} points ?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/shop/buy_emote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ emote_id: emoteId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message);
            showShop();
        } else {
            alert(data.error || 'Erreur lors de l\'achat');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'achat de l\'émote');
    }
}

// Mettre à jour la fonction showShop pour charger toutes les sections
const originalShowShop = showShop;
showShop = async function() {
    await originalShowShop();
    await loadButtonColors();
    await loadEmotes();
};

// ==================== ÉMOTES EN BATTLE ====================

let currentBattleId = null;

function toggleEmotePicker() {
    const picker = document.getElementById('emote-picker');
    if (picker.style.display === 'none') {
        loadBattleEmotes();
        picker.style.display = 'grid';
    } else {
        picker.style.display = 'none';
    }
}

async function loadBattleEmotes() {
    try {
        const response = await fetch('/api/shop/emotes');
        const data = await response.json();
        
        const picker = document.getElementById('emote-picker');
        picker.innerHTML = '';
        
        const ownedEmotes = data.emotes.filter(e => e.owned);
        
        if (ownedEmotes.length === 0) {
            picker.innerHTML = '<p style="grid-column: 1/-1; text-align: center;">Aucune émote possédée. Achetez-en dans la boutique !</p>';
            return;
        }
        
        ownedEmotes.forEach(emote => {
            const emoteBtn = document.createElement('button');
            emoteBtn.className = 'emote-btn';
            emoteBtn.textContent = emote.emoji;
            emoteBtn.title = emote.nom;
            emoteBtn.onclick = () => sendEmote(emote.id);
            picker.appendChild(emoteBtn);
        });
    } catch (error) {
        console.error('Erreur lors du chargement des émotes:', error);
    }
}

function sendEmote(emoteId) {
    if (currentBattleId && socket) {
        socket.emit('send_emote', {
            battle_id: currentBattleId,
            emote_id: emoteId
        });
        // Fermer le picker après l'envoi
        document.getElementById('emote-picker').style.display = 'none';
    }
}

function displayReceivedEmote(data) {
    const display = document.getElementById('emote-display');
    const emoteElement = document.createElement('div');
    emoteElement.className = 'received-emote';
    emoteElement.innerHTML = `
        <span class="emote-sender">${data.sender}</span>
        <span class="emote-big">${data.emoji}</span>
    `;
    display.appendChild(emoteElement);
    
    // Supprimer après 3 secondes
    setTimeout(() => {
        emoteElement.remove();
    }, 3000);
}

// Ajouter le listener Socket.IO pour recevoir les émotes
if (typeof socket !== 'undefined') {
    socket.on('emote_received', displayReceivedEmote);
}

// ==================== PANNEAU DÉVELOPPEUR ====================

function showDevPanel() {
    const password = prompt('🔧 Mode Développeur\nMot de passe :');
    
    if (password === null) return; // Annulé
    
    if (password !== '          ') {
        alert('❌ Mot de passe incorrect');
        return;
    }
    
    const points = prompt('💰 Combien de points voulez-vous ajouter ?\n(Max: 10000)');
    
    if (points === null) return; // Annulé
    
    addDevPoints(parseInt(points));
}

async function addDevPoints(points) {
    if (isNaN(points) || points < 0 || points > 10000) {
        alert('❌ Nombre de points invalide (0-10000)');
        return;
    }
    
    try {
        const response = await fetch('/api/dev/add_points', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                password: '          ',
                points: points 
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`✅ ${data.message}\nNouveau score total : ${data.new_score} pts`);
            // Recharger les stats si on est sur l'écran d'accueil
            const homeScreen = document.getElementById('home-screen');
            if (homeScreen && homeScreen.classList.contains('active')) {
                loadStats();
            }
        } else {
            alert('❌ ' + (data.error || 'Erreur lors de l\'ajout des points'));
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('❌ Erreur lors de l\'ajout des points');
    }
}
