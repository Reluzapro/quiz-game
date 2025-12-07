function showLogin() {
    document.getElementById('login-form').classList.add('active');
    document.getElementById('register-form').classList.remove('active');
    clearErrors();
}

function showRegister() {
    document.getElementById('login-form').classList.remove('active');
    document.getElementById('register-form').classList.add('active');
    clearErrors();
}

function clearErrors() {
    document.getElementById('login-error').classList.remove('show');
    document.getElementById('register-error').classList.remove('show');
}

function showError(formType, message) {
    const errorDiv = document.getElementById(formType + '-error');
    errorDiv.textContent = message;
    errorDiv.classList.add('show');
}

async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError('login', data.error);
        } else {
            // Connexion réussie, rediriger vers le jeu
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('login', 'Erreur de connexion au serveur');
    }
}

async function handleRegister(event) {
    event.preventDefault();
    
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const passwordConfirm = document.getElementById('register-password-confirm').value;
    
    if (password !== passwordConfirm) {
        showError('register', 'Les mots de passe ne correspondent pas');
        return;
    }
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError('register', data.error);
        } else {
            // Inscription réussie, rediriger vers le jeu
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('register', 'Erreur de connexion au serveur');
    }
}
