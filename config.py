# Configuration pour le déploiement
import os

# Configuration de la base de données
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'votre_cle_secrete_super_complexe_a_changer_123456789'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'thermodynamics_game.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
