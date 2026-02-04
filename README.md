# 🏐 Organisateur d'Équipes - Estivales de Volley

Application web pour optimiser la composition des équipes de beach-volley lors des tournois Estivales.

## 🎯 Fonctionnalités

- **Optimisation intelligente** avec algorithme multi-passes
- **Visualisations interactives** (Plotly)
- **Assistant de résolution** de conflits
- **Gestion des couples** et disponibilités
- **Export CSV** des plannings

## 📚 Documentation

### Spécifications Complètes

Pour une compréhension approfondie du projet, consultez les spécifications détaillées dans `/docs` :

- **[SPEC_FONCTIONNELLE.md](docs/SPEC_FONCTIONNELLE.md)** :
  - 📋 Vue d'ensemble et objectifs
  - 👥 Personas et cas d'usage  
  - 🎯 Exigences fonctionnelles détaillées
  - 🎨 Interface utilisateur et parcours
  - 📊 Métriques et KPI
  - 🔍 Gestion des erreurs

- **[SPEC_TECHNIQUE.md](docs/SPEC_TECHNIQUE.md)** :
  - 🏗️ Architecture système
  - 💻 Modèles de données
  - ⚙️ Algorithmes OR-Tools (détails d'implémentation)
  - 🧪 Tests et qualité
  - 🚀 Performance et optimisation
  - 📈 Points d'amélioration futurs

**Version actuelle** : 2.2.3 (3 Février 2026)

## 🚀 Démarrage Rapide

### Installation
```bash
git clone https://github.com/votre-username/estivales-team-planner.git
cd estivales-team-planner
py -m pip install -r requirements.txt
```

### Lancement
```bash
py -m streamlit run app.py
```

### Tests
```bash
py -m pytest tests/ -v
```

## 📖 Guide d'Utilisation

1. **Configurer** les participants avec leurs vœux
2. **Ajuster** les paramètres (O3, équipes incomplètes)
3. **Calculer** les variantes
4. **Analyser** avec les visualisations
5. **Exporter** le planning choisi

## 🛠️ Stack Technique

- **Streamlit** : Interface web
- **OR-Tools** : Optimisation
- **Plotly** : Visualisations
- **pytest** : Tests

## 📊 Architecture

```
├── app.py              # Application principale
├── src/
│   ├── solver.py       # Optimisation OR-Tools
│   ├── multipass_solver.py  # Assistant intelligent
│   ├── visualizations.py    # Graphiques Plotly
│   └── validation.py   # Validation des données
├── docs/               # 📚 Spécifications complètes
│   ├── SPEC_FONCTIONNELLE.md
│   └── SPEC_TECHNIQUE.md
└── tests/              # Tests automatiques
```

## 🚀 Déploiement Streamlit Cloud

1. Push sur GitHub
2. Connecter à https://share.streamlit.io/
3. Déployer (fichier : `app.py`)

## 📝 Configuration

### Planning des Tournois
- **E1** : Sam-Dim (SABLES D'OR)
- **O1** : Lun (ERQUY)
- **E2** : Mar-Mer (ERQUY)
- **O2** : Jeu (SAINT-CAST)
- **E3** : Ven-Sam (SAINT-CAST)
- **O3** : Dim (SAINT-CAST)

### Paramètres Avancés
Éditer `src/constants.py` :
```python
TEAM_SIZE = 3
MAX_CONSECUTIVE_DAYS = 3
SOLVER_TIMEOUT = 60.0
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Ajouter des tests
4. Ouvrir une Pull Request

## 📄 Licence

MIT License - voir `LICENSE`

---

**Développé pour les Estivales de Volley** 🏐
