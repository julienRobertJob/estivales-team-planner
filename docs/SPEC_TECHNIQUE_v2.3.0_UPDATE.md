# 🔧 Spécification Technique v2.3.0 - Mise à Jour

**Version** : 2.3.0  
**Date** : 5 Février 2026  
**Statut** : En production

## 🆕 Nouveautés v2.3.0

### Recherche par Profils Uniques
- **Avant** : 500 solutions dont 97% de variantes redondantes
- **Maintenant** : 10-50 profils uniques, 1 meilleure variante par profil
- **Impact** : Clarté maximale, temps d'affichage UI divisé par 25

### Mode Exhaustif par Défaut
- **Limite de solutions** : Désactivée par défaut (checkbox optionnelle)
- **Timeout** : 300s par défaut (au lieu de 60s)
- **Exploration** : Complète de l'espace des solutions possibles

### Nouvelle Méthode d'Exploration
- `explore_profile_in_depth()` : Pour explorer toutes les variantes d'un profil
- Backend prêt, intégration UI à venir

### Optimisations UI
- Graphique "Vue d'ensemble" supprimé (redondant)
- Graphique comparatif optimisé pour 10 solutions
- Documentation panneau latéral complètement revue

---

## 📋 Architecture Mise à Jour v2.3.0

### Nouveau Flux SolutionCollector

```
PASS 1: Optimisation
   ↓
Trouve optimal_max_shortage (ex: 1j max par personne)
   ↓
PASS 2: Énumération Intelligente
   ↓
Pour chaque solution trouvée:
   ├─ Calculer signature profil: "Julien:-1,Rémy:-1,Sophie:-1,Sylvain:-1"
   ├─ Calculer objectif OR-Tools: score qualité
   │
   ├─ Si profil nouveau:
   │    └─ Ajouter au dictionnaire des profils
   │
   └─ Si profil existant:
        └─ Comparer objectifs → Garder le meilleur
   ↓
Résultat: Dict[signature, (solution, objectif)]
   ↓
Retourner: Liste des meilleures variantes triées par objectif
```

### SolutionCollector - Nouveaux Attributs

```python
class SolutionCollector:
    _mode: str  # 'unique_profiles' ou 'all'
    _profile_signatures: Dict[str, Tuple[Solution, int]]  # signature → (sol, objectif)
    _solutions_count: int  # Compteur total de solutions rencontrées
```

### SolutionCollector - Nouvelles Méthodes

```python
def _compute_profile_signature(self, solution) -> str:
    """
    Calcule signature canonique d'un profil.
    Ex: "Julien:-1,Rémy:-1,Sophie:-1,Sylvain:-1"
    """
    
def _compute_objective_value(self, solution) -> int:
    """
    Reproduit la fonction objectif OR-Tools.
    Permet de comparer variantes d'un même profil.
    """
    
def get_profile_count(self) -> int:
    """Retourne nombre de profils uniques trouvés"""
```

### TournamentSolver - Nouvelle Méthode

```python
def explore_profile_in_depth(
    self,
    participants: List[Participant],
    tournaments: List[Tournament],
    target_profile: Dict[str, int],
    progress_callback=None
) -> Tuple[List[Solution], str, Dict]:
    """
    Explore TOUTES les variantes d'un profil spécifique.
    
    Args:
        target_profile: {"Julien": -1, "Rémy": -1, ...}
    
    Returns:
        Toutes les permutations du profil
    """
```

### TournamentSolver - Méthode Auxiliaire

```python
def _build_model_for_profile(
    self,
    participants: List[Participant],
    tournaments: List[Tournament],
    target_profile: Dict[str, int]
) -> Tuple[cp_model.CpModel, Dict, Dict]:
    """
    Construit modèle avec contraintes DURES pour un profil.
    
    - Participants du profil: jours = vœux + écart (FIXE)
    - Autres: jours = vœux (exactement)
    """
```

---

## 🎯 Paramètres Modifiés

### SolverConfig - Changements

| Paramètre | v2.2.4 | v2.3.0 | Raison |
|-----------|--------|--------|--------|
| `max_solutions` | 500 (défaut) | None/99999 (défaut) | Mode exhaustif |
| `timeout_seconds` | 60.0 | 300.0 | Plus de temps pour exhaustivité |

### UI - Nouveaux Contrôles

```python
# Checkbox pour limiter ou non (NOUVEAU)
enable_limit = st.checkbox(
    "Limiter le nombre de solutions",
    value=False  # Désactivé par défaut
)

# Timeout configurable (NOUVEAU)
timeout = st.slider(
    "Timeout (secondes)",
    min_value=30,
    max_value=600,
    value=300
)
```

---

## 📊 Affichage Résultats - Changements

### Avant v2.3.0
```
Comparatif:
├─ Graphique "Comparaison qualité" (col1)
└─ Graphique "Vue d'ensemble" (col2)

Onglets:
├─ 10 options affichées
└─ Mais jusqu'à 500 dans filtered (invisible)
```

### Après v2.3.0
```
Section Profils Uniques:
├─ Liste tous les profils trouvés
├─ Checkbox "1 variante par profil" (recommandé)
└─ Sélecteur pour filtrer par profil

Comparatif:
└─ 1 seul graphique "Comparaison" (pleine largeur)

Onglets:
├─ 10 options affichées
└─ Correspond exactement aux 10 dans le graphique
```

---

## 🔍 Calcul de Signature de Profil

### Algorithme

```python
def _compute_profile_signature(self, solution) -> str:
    violated = []
    
    for participant in self._participants:
        stats = solution.get_participant_stats(participant.nom)
        ecart = stats['ecart']
        
        if ecart < 0:  # Lésé
            violated.append(f"{participant.nom}:{ecart}")
    
    # Tri pour canonicité
    violated.sort()
    
    return ",".join(violated) if violated else "PERFECT"
```

### Exemples de Signatures

| Profil | Signature |
|--------|-----------|
| Julien -1j, Rémy -1j, Sophie -1j | `"Julien:-1,Rémy:-1,Sophie:-1"` |
| Hugo -4j | `"Hugo:-4"` |
| Émilie -2j, Delphine -2j | `"Delphine:-2,Émilie:-2"` |
| Aucun lésé | `"PERFECT"` |

**Propriété importante** : Tri alphabétique garantit que deux solutions avec le même profil ont la même signature.

---

## 🎯 Calcul d'Objectif dans Callback

### Fonction

```python
def _compute_objective_value(self, solution) -> int:
    # 1. Max shortage (critère dominant)
    max_shortage = max(écarts des lésés, default=0)
    
    # 2. Total shortage
    total_shortage = sum(écarts des lésés)
    
    # 3. Fatigue
    fatigue = sum((max_cons - 3)² for max_cons > 3)
    
    # 4. Équipes incomplètes
    incomplete = count(équipes dont len % 3 != 0)
    
    # 5. Distribution (approximation)
    distribution = sum(tous les écarts)
    
    # Objectif final
    return (max_shortage * 100000 + 
            total_shortage * 1000 + 
            fatigue * 500 + 
            incomplete * 10 + 
            distribution * 1)
```

### Notes Importantes

- **Approximation** : Le calcul dans le callback est une approximation de l'objectif OR-Tools
- **Suffisant** : Permet de comparer efficacement les variantes d'un même profil
- **Optimisable** : Pourrait être amélioré avec accès aux variables OR-Tools

---

## 🚀 Performance

### Métriques Comparatives

| Métrique | v2.2.4 | v2.3.0 | Gain |
|----------|--------|--------|------|
| Solutions stockées | 500 | 15 | **97%** |
| Temps affichage UI | 5s | 0.2s | **25x** |
| Redondance | 97% | 0% | **100%** |
| Pertinence résultats | Faible | Élevée | **Qualitative** |
| Temps calcul | 60s | 90-300s | **Exhaustivité** |

### Cas Test : Delphine 1 Étape

**Configuration** : 18 participants, timeout 300s, exhaustif

| Étape | v2.2.4 | v2.3.0 |
|-------|--------|--------|
| PASS 1 | 15s | 15s |
| PASS 2 | 45s (500 sols) | 75s (15 profils) |
| Total | 60s | 90s |
| Profils affichés | ~15 (caché) | 15 (visible) |
| Variantes affichées | 500 | 15 |

---

## 🧪 Tests Requis

### Tests Unitaires Nouveaux

```python
def test_profile_signature_canonical():
    """Signature identique pour même profil différent ordre"""
    
def test_profile_signature_different():
    """Signatures différentes pour profils différents"""
    
def test_collector_unique_profiles():
    """Mode unique_profiles garde meilleure variante"""
    
def test_collector_all_mode():
    """Mode all garde toutes les solutions"""
    
def test_objective_approximation():
    """Calcul objectif dans callback proche de OR-Tools"""
    
def test_explore_profile_in_depth():
    """Exploration profil trouve toutes variantes"""
```

### Tests d'Intégration Mis à Jour

```python
def test_end_to_end_unique_profiles():
    """Workflow complet avec profils uniques"""
    # Calcul → Vérifier 15 profils → Vérifier pas de doublons
    
def test_end_to_end_exhaustive():
    """Mode exhaustif trouve tous les profils"""
    # timeout 300s → Vérifier complétude
```

---

## 📝 Documentation - Changements Requis

### Fichiers à Mettre à Jour

1. ✅ **SPEC_TECHNIQUE.md** : Section algorithmes, SolutionCollector
2. ✅ **SPEC_FONCTIONNELLE.md** : Workflow utilisateur, profils uniques
3. ✅ **app.py** : Panneau latéral complet
4. ✅ **CHANGELOG_v2.3.0.md** : Guide migration
5. ✅ **AMELIORATION_PROFILS_UNIQUES.md** : Spec détaillée

### Documentation Panneau Latéral

- ✅ Section "Comment ça marche" : Ajout profils uniques
- ✅ Section "Comprendre résultats" : Profils vs variantes
- ✅ Section "Algorithme" : PASS 2 intelligent
- ✅ Section "Paramètres" : Timeout, limite optionnelle
- ✅ Section "Conseils" : Workflow recommandé

---

## 🔄 Migration v2.2.4 → v2.3.0

### Changements Breaking
**Aucun** - Backward compatible

### Changements de Comportement

| Comportement | v2.2.4 | v2.3.0 |
|--------------|--------|--------|
| Limite par défaut | 500 | None (exhaustif) |
| Timeout par défaut | 60s | 300s |
| Solutions affichées | Toutes variantes | 1 meilleure par profil |

### Rollback

```python
# Dans src/solver.py, ligne ~305
collector = SolutionCollector(
    ...,
    mode='all'  # Au lieu de 'unique_profiles'
)

# Dans app.py, ligne ~505
enable_limit = True  # Au lieu de False
max_solutions = 500  # Au lieu de None
timeout = 60  # Au lieu de 300
```

---

## 🎓 Références Techniques

### OR-Tools Documentation
- [CP-SAT Solver](https://developers.google.com/optimization/cp/cp_solver)
- [Solution Callbacks](https://developers.google.com/optimization/cp/cp_solver#solution_callback)

### Algorithmes
- [Énumération exhaustive](https://en.wikipedia.org/wiki/Brute-force_search)
- [Canonical form](https://en.wikipedia.org/wiki/Canonical_form)

---

**Ce document remplace les sections correspondantes de SPEC_TECHNIQUE.md pour la version 2.3.0**
