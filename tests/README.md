# 🧪 Tests - Organisateur d'Équipes Estivales

## Structure

```
tests/
├── README.md                    # Ce fichier
├── __init__.py
│
├── algorithm/                   # Tests de l'algorithme d'optimisation (v2.2.3)
│   ├── test_algorithme_ameliore.py   # Tests du système hiérarchique
│   ├── test_cas_utilisateur.py       # Tests de cas réels utilisateur
│   └── test_critere_principal.py     # Tests du critère principal (max lésion)
│
├── scoring/                     # Tests du système de scoring (v2.2.3)
│   ├── test_scoring.py               # Tests du scoring de base
│   ├── test_poids_distribution.py    # Tests du poids de distribution
│   ├── test_score_concentration.py   # Tests de la pénalité de concentration
│   └── validate_new_scoring.py       # Validation de la formule de scoring
│
├── test_categories_B_C.py       # Tests des catégories B et C
├── test_enumerate_all.py        # Tests d'énumération de solutions
├── test_multipass.py            # Tests du solver multi-passes
├── test_simple_working.py       # Tests de base de fonctionnement
├── test_solver.py               # Tests du solver principal
└── test_workflow.py             # Tests du workflow complet

```

## Lancer les tests

### Tous les tests
```bash
pytest tests/
```

### Tests d'algorithme uniquement
```bash
pytest tests/algorithm/
```

### Tests de scoring uniquement
```bash
pytest tests/scoring/
```

### Test spécifique
```bash
pytest tests/algorithm/test_critere_principal.py -v
```

## Description des tests

### 📊 Tests d'algorithme (algorithm/)

**test_critere_principal.py**
- Vérifie que l'algorithme minimise d'abord la lésion maximale individuelle
- Teste la hiérarchie des critères (max → total → distribution)
- Vérifie que 1 personne -3j est évité au profit de 3 personnes -1j

**test_algorithme_ameliore.py**
- Teste le système hiérarchique v2.2.3
- Vérifie les ratios de poids (100000:1000:1)
- Teste les différents profils de lésions

**test_cas_utilisateur.py**
- Tests basés sur des cas réels utilisateur
- Vérifie les comportements spécifiques demandés

### 📈 Tests de scoring (scoring/)

**test_scoring.py**
- Tests de la formule de scoring v2.2.3
- Vérifie les pénalités (total, concentration, distribution, fatigue)

**test_poids_distribution.py**
- Teste le poids de distribution (×8)
- Vérifie que léser un gros demandeur coûte moins cher

**test_score_concentration.py**
- Teste la pénalité de concentration (×5)
- Vérifie que 1×-3j est pire que 3×-1j dans le score

**validate_new_scoring.py**
- Script de validation complète de la formule
- Exemples et cas limites

### 🔧 Tests fonctionnels (racine)

**test_solver.py**
- Tests unitaires du solver OR-Tools
- Contraintes, variables, objectif

**test_multipass.py**
- Tests du système multi-passes
- Détection de conflits et propositions

**test_enumerate_all.py**
- Tests de l'énumération de toutes les solutions
- Vérifie que tous les profils sont trouvés

**test_workflow.py**
- Tests end-to-end du workflow complet
- De la saisie à l'export

## Versions

- **v2.2.3** : Hiérarchie stricte des critères + énumération de tous les profils
- **v2.2.2** : Première tentative de hiérarchie (trop restrictive)
- **v2.2.1** : Pondération intégrée (éliminait les solutions)
- **v2.2** : Formule de scoring soustractive
- **v2.1** : Formule de scoring additive (donnait 0/100)
