# Configuration pour le déploiement
import os

# Configuration de la base de données
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'votre_cle_secrete_super_complexe_a_changer_123456789'
    
    # Récupérer l'URL de la base de données
    database_url = os.environ.get('DATABASE_URL')
    
    # Render fournit une URL postgres:// mais SQLAlchemy 1.4+ nécessite postgresql://
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Utiliser PostgreSQL en production (si DATABASE_URL existe) ou SQLite en local
    SQLALCHEMY_DATABASE_URI = database_url or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'thermodynamics_game.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
