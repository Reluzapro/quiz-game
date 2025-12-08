#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration: Ajouter la colonne is_public à la table Battle
"""

import os
from sqlalchemy import create_engine, text

# Récupérer l'URL de la base de données depuis les variables d'environnement
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ Erreur: DATABASE_URL non définie")
    exit(1)

# Fix pour PostgreSQL (Render utilise postgres:// mais SQLAlchemy 1.4+ requiert postgresql://)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print(f"🔗 Connexion à la base de données...")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        # Vérifier si la colonne existe déjà
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='battle' AND column_name='is_public'
        """))
        
        if result.fetchone():
            print("✅ La colonne 'is_public' existe déjà")
        else:
            # Ajouter la colonne is_public
            print("🔨 Ajout de la colonne 'is_public'...")
            conn.execute(text("""
                ALTER TABLE battle 
                ADD COLUMN is_public BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("✅ Colonne 'is_public' ajoutée avec succès")
        
        # Mettre à jour les battles existantes pour être privées par défaut
        print("🔄 Mise à jour des battles existantes...")
        conn.execute(text("""
            UPDATE battle 
            SET is_public = FALSE 
            WHERE is_public IS NULL
        """))
        conn.commit()
        print("✅ Migration terminée avec succès!")
        
except Exception as e:
    print(f"❌ Erreur lors de la migration: {e}")
    exit(1)
