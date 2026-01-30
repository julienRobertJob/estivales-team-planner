#!/bin/bash
# Script de lancement pour l'Organisateur d'Estivales de Volley

echo "🏐 Organisateur d'Estivales de Volley - Version 2.0"
echo "=================================================="
echo ""

# Vérifier que Python est installé
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

# Vérifier que pip est installé
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 n'est pas installé"
    exit 1
fi

# Installer les dépendances si nécessaire
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installation des dépendances..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo ""
echo "✅ Prêt !"
echo ""
echo "🚀 Lancement de l'application..."
echo "   L'application s'ouvrira dans votre navigateur"
echo "   (Si ce n'est pas le cas, ouvrez http://localhost:8501)"
echo ""

streamlit run app.py
