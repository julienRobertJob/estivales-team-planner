# 🚀 GUIDE DE DÉMARRAGE RAPIDE

## ⚡ Installation en 3 Étapes

### 1. Prérequis
```bash
# Vérifier Python (version 3.8+)
python3 --version

# Si pas installé, installer Python 3.8+
# Ubuntu/Debian: sudo apt install python3 python3-pip
# MacOS: brew install python3
# Windows: https://python.org/downloads
```

### 2. Installation
```bash
cd estivales_volley

# Option A : Utiliser le script automatique (recommandé)
./run.sh

# Option B : Installation manuelle
pip install -r requirements.txt
streamlit run app.py
```

### 3. Utilisation
L'application s'ouvre automatiquement dans votre navigateur à `http://localhost:8501`

---

## 📖 Premier Lancement - 5 Minutes

### Étape 1 : Charger l'Exemple (10 secondes)
1. Cliquer sur "📝 Charger Exemple" (colonne de droite)
2. Les données par défaut se chargent (13 participants)

### Étape 2 : Valider (5 secondes)
1. Cliquer sur "✅ Valider Données"
2. Vérifier qu'il n'y a pas d'erreurs critiques

### Étape 3 : Configurer (10 secondes)
1. Cocher "🌅 Inclure l'Open du Dimanche (O3)" si souhaité
2. Cocher "👥 Autoriser équipes incomplètes" si besoin
3. Ajuster le nombre de solutions à chercher (par défaut 50)

### Étape 4 : Calculer (30-60 secondes)
1. Cliquer sur "🚀 Calculer les Variantes"
2. Attendre la fin du calcul (barre de progression)
3. ✅ Vous devriez voir "X solutions trouvées"

### Étape 5 : Explorer (3 minutes)
1. Regarder les **Statistiques Générales** en haut
2. Parcourir les **onglets de solutions** (Option 1, 2, 3...)
3. Pour chaque solution :
   - Voir qui est lésé
   - Voir le planning par lieu
   - Voir le tableau récapitulatif

### Étape 6 : Exporter (30 secondes)
1. Choisir la meilleure solution
2. Cliquer sur "💾 Exporter cette solution"
3. Télécharger le CSV

**🎉 Félicitations ! Vous avez créé votre premier planning !**

---

## 🎯 Cas d'Usage Typiques

### Cas 1 : Planning Simple (Tout le monde respecté)

**Situation :** 10 participants, vœux modérés, pas de contraintes strictes

**Étapes :**
1. Saisir les participants
2. Décocher "Respect_Voeux" pour tous (sauf exceptions)
3. Laisser "Équipes incomplètes" décoché
4. Calculer → Devrait trouver des solutions parfaites

**Résultat attendu :** Solutions avec tous les vœux respectés

---

### Cas 2 : Planning Contraint (Couples multiples)

**Situation :** 6 couples, beaucoup de vœux stricts

**Étapes :**
1. Vérifier que les couples sont bien bidirectionnels
2. Cocher "Respect_Voeux" pour les prioritaires uniquement (max 30%)
3. ✅ ACTIVER "Équipes incomplètes"
4. Augmenter le nombre de solutions (70-100)
5. Calculer

**Résultat attendu :** Solutions avec 1-2 vœux lésés mais équilibrées

**Si échec :**
- Vérifier les suggestions affichées
- Relâcher quelques "Respect_Voeux"
- Inclure O3 pour plus de places

---

### Cas 3 : Optimisation Fine

**Situation :** Plusieurs solutions OK, comment choisir ?

**Critères de sélection :**
1. **Score Qualité** : Prendre >85/100
2. **Vœux Lésés** : Minimiser (préférer 0 ou 1)
3. **Fatigue** : Aucun participant >3j consécutifs
4. **Équilibre** : Variance des jours joués faible

**Outil :** Utilisez le tableau récapitulatif en bas de chaque solution

---

## 🔧 Résolution de Problèmes

### ❌ Problème : "Aucune solution trouvée"

**Solutions (dans l'ordre) :**

1. **Activer "Équipes incomplètes"**
   - Impact : Permet des équipes de 1-2 joueurs
   - Quand : Nombre de participants pas multiple de 3

2. **Décocher quelques "Respect_Voeux"**
   - Impact : Plus de flexibilité
   - Quand : Trop de vœux stricts (>50%)

3. **Inclure O3**
   - Impact : 1 jour supplémentaire = plus de places
   - Quand : Beaucoup de demande totale

4. **Réduire les vœux de quelqu'un**
   - Impact : Moins de contraintes
   - Quand : Un participant demande beaucoup

5. **Vérifier les disponibilités**
   - Impact : Libère des créneaux
   - Quand : Beaucoup de fin de dispo à E2 ou avant

---

### ⚠️ Problème : "Trop de solutions trouvées" (>100)

**Solutions :**

1. **Ajouter des "Respect_Voeux"** pour les prioritaires
   - Réduit les combinaisons possibles

2. **Limiter le nombre de solutions cherchées**
   - Slider en haut : réduire à 30-50

3. **Filtrer avec "Qui acceptez-vous de léser"**
   - Sélectionner seulement les personnes flexibles

---

### 🐛 Problème : Tests Échouent

**Solutions :**

1. Vérifier les dépendances :
```bash
pip install -r requirements.txt --upgrade
```

2. Vérifier la version d'OR-Tools :
```bash
pip show ortools
# Doit être >= 9.7.0
```

3. Lancer un test spécifique pour identifier :
```bash
pytest tests/test_solver.py::TestSolverObjective::test_objective_minimizes_deviation -v
```

4. Si un test critique échoue :
   - C'est une régression !
   - Vérifier les modifications récentes du code
   - Revenir à la version précédente si besoin

---

## 📊 Interpréter les Résultats

### Statistiques Générales

```
Total Solutions : 18
✅ Parfaites    : 5   (28%)   ← Tous les vœux respectés
⚠️ 1 Vœu       : 10  (56%)   ← 1 seul vœu non respecté
⚠️⚠️ 2 Vœux     : 3   (17%)   ← 2 vœux non respectés
```

**Interprétation :**
- Si **>50% Parfaites** : Excellent ! Choisir parmi les parfaites
- Si **>50% avec 1 Vœu** : Bon, identifier qui léser
- Si **>50% avec 2+ Vœux** : Difficile, relâcher contraintes

---

### Score Qualité

```
Score : 95/100
```

**Échelle :**
- **90-100** : Excellent (vœux respectés, pas de fatigue)
- **75-89** : Bon (quelques compromis mineurs)
- **60-74** : Acceptable (compromis notables)
- **<60** : Problématique (beaucoup de compromis)

---

### Tableau Récapitulatif

```
Nom      | Souhait | Joué | Écart | Consécutifs
---------|---------|------|-------|-------------
Alice    | 4j      | 4j   | 0     | 2
Bob      | 6j      | 5j   | -1    | 3
Charlie  | 2j      | 3j   | +1    | 2
```

**À regarder :**
- **Écart** : 0 = parfait, ±1 = bon, ±2+ = compromis
- **Consécutifs** : ≤3 = OK, 4 = attention, 5+ = fatigue

---

## 💡 Astuces d'Expert

### 1. Utiliser les Valeurs par Défaut au Début
Ne personnalisez pas tout tout de suite :
- Laissez "Respect_Voeux" décoché pour la plupart
- Commencez sans O3
- Activez "Équipes incomplètes" seulement si bloqué

### 2. Itérer Progressivement
1. Premier calcul : Configuration minimale
2. Si échec : Ajouter O3
3. Si encore échec : Équipes incomplètes
4. En dernier recours : Réduire vœux

### 3. Prioriser les Contraintes Importantes
- Cocher "Respect_Voeux" seulement pour :
  - Les organisateurs
  - Les joueurs clés
  - Les cas particuliers (blessure, etc.)

### 4. Lire les Suggestions
L'application affiche des suggestions intelligentes :
```
💡 Suggestions d'amélioration
   • Décocher 'Respect_Voeux' pour...
   • Activer 'Équipes incomplètes'...
   • Inclure O3 pour plus de places...
```
Suivez-les !

### 5. Exporter Plusieurs Solutions
Ne vous limitez pas à la première :
- Exportez les 3 meilleures
- Comparez-les hors ligne
- Consultez l'équipe avant de choisir

---

## 🎓 Pour Aller Plus Loin

### Lancer les Tests
```bash
# Tous les tests
pytest tests/ -v

# Tests spécifiques
pytest tests/test_solver.py::TestSolverObjective -v

# Avec couverture
pytest tests/ --cov=src --cov-report=html
```

### Modifier le Code

**Structure importante :**
```
src/
├── constants.py    ← Modifier les constantes ici
├── models.py       ← Ajouter champs aux participants
├── solver.py       ← Modifier l'algorithme
└── validation.py   ← Ajouter validations
```

**Exemple : Ajouter un champ "Niveau" :**

1. Dans `models.py` :
```python
@dataclass
class Participant:
    # ... champs existants
    niveau: int = 3  # 1-5
```

2. Dans `constants.py` :
```python
PARTICIPANT_COLUMNS = [
    'Nom', 'Genre', 'Couple',
    'Voeux_Etape', 'Voeux_Open',
    'Dispo_Jusqu_a', 'Respect_Voeux',
    'Niveau'  # Nouveau
]
```

3. Dans `app.py`, ajouter la colonne :
```python
column_config={
    # ... autres colonnes
    "Niveau": st.column_config.NumberColumn(
        "Niveau (1-5)",
        min_value=1,
        max_value=5
    )
}
```

---

## 🆘 Aide

### Documentation
- README.md : Vue d'ensemble
- RECOMMENDATIONS.md : Améliorations futures
- Ce fichier : Guide pratique

### Support
- Tests qui échouent : Voir les messages d'erreur détaillés
- Erreurs Python : Vérifier requirements.txt
- Questions : Lire les docstrings dans le code

---

## ✅ Checklist de Validation

Avant de partager un planning, vérifier :

- [ ] Tous les couples sont bidirectionnels
- [ ] Aucun couple ne joue le même jour
- [ ] Les disponibilités sont respectées
- [ ] Les vœux stricts sont respectés
- [ ] Pas de participant >3j consécutifs (sauf accepté)
- [ ] Les équipes sont de 3 (ou incomplet autorisé)
- [ ] Score qualité >75
- [ ] Export CSV fonctionne

---

**🎉 Vous êtes prêt ! Bon planning !**
