let totalQuestions = 0;
let currentMatiere = 'thermo'; // Matière par défaut
let timerInterval = null;
let timerEnabled = false;

// Vérifier l'authentification et les sauvegardes au chargement
window.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadMatieres();
    checkSavedGame();
    loadStats();
});

async function loadMatieres() {
    try {
        const response = await fetch('/api/matieres');
        const data = await response.json();
        
        const container = document.querySelector('.matiere-selector');
        if (!container) return;
        
        // Vider le conteneur
        container.innerHTML = '';
        
        // Créer les boutons pour chaque matière
        data.matieres.forEach((matiere, index) => {
            const button = document.createElement('button');
            button.className = 'btn-matiere' + (index === 0 ? ' active' : '');
            button.id = `btn-${matiere.code}`;
            button.onclick = () => selectMatiere(matiere.code);
            
            button.innerHTML = `
                <div class="matiere-emoji">${matiere.emoji}</div>
                <div class="matiere-name">${matiere.nom}</div>
                <div class="matiere-count">${matiere.nb_questions} question${matiere.nb_questions > 1 ? 's' : ''}</div>
            `;
            
            container.appendChild(button);
        });
        
        // Définir la première matière comme matière par défaut
        if (data.matieres.length > 0) {
            currentMatiere = data.matieres[0].code;
        }
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
        document.getElementById('question-text').textContent = data.question;
        document.getElementById('answer-text').textContent = data.reponse_proposee;
        document.getElementById('score').textContent = data.score;
        document.getElementById('question-counter').textContent = 
            `Question ${data.question_number}/${data.total_questions}`;
        
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
            // Recharger la question avec la nouvelle réponse
            setTimeout(() => {
                loadQuestion();
            }, 1500);
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

async function showScores() {
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
        
        const scoresList = document.getElementById('scores-list');
        
        if (scores.length === 0) {
            scoresList.innerHTML = '<p style="text-align: center; color: #6c757d;">Aucun score pour le moment</p>';
        } else {
            let html = '';
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
                
                html += `
                    <div class="score-item ${rankClass}">
                        <div>
                            <div class="score-username">${medal}${score.username}</div>
                            <div class="score-details">${score.questions_correctes}/${score.total_questions} correctes</div>
                        </div>
                        <div class="score-value">${score.score} pts</div>
                    </div>
                `;
            });
            scoresList.innerHTML = html;
        }
        
        showScreen('scores-screen');
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement des scores');
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
