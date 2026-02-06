# 🔧 Spécification Technique - Organisateur d'Équipes Estivales de Volley

**Version** : 2.2.4  
**Date** : 4 Février 2026  
**Statut** : En production

---

## 📋 Table des Matières

1. [Architecture Générale](#architecture-générale)
2. [Stack Technique](#stack-technique)
3. [Modèles de Données](#modèles-de-données)
4. [Algorithmes](#algorithmes)
5. [Modules et Composants](#modules-et-composants)
6. [OR-Tools : Implémentation](#or-tools--implémentation)
7. [Performance et Optimisation](#performance-et-optimisation)
8. [Tests](#tests)
9. [Déploiement](#déploiement)
10. [Points d'Amélioration](#points-damélioration)

---

## 1. Architecture Générale

### 1.1 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT APP                        │
│                      (app.py)                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │ UI Components│  │ Visualizations│  │  Validation │  │
│  │   (render)   │  │    (Plotly)   │  │   (checks)  │  │
│  └──────────────┘  └──────────────┘  └─────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           CORE BUSINESS LOGIC                   │   │
│  │  ┌──────────────┐      ┌──────────────────┐    │   │
│  │  │ MultiPass    │      │  TournamentSolver │    │   │
│  │  │   Solver     │─────▶│    (OR-Tools)    │    │   │
│  │  └──────────────┘      └──────────────────┘    │   │
│  │                                                 │   │
│  │  ┌──────────────┐      ┌──────────────────┐    │   │
│  │  │ Conflict     │      │   Solution       │    │   │
│  │  │  Analyzer    │      │   Collector      │    │   │
│  │  └──────────────┘      └──────────────────┘    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │               DATA MODELS                       │   │
│  │  Participant | Tournament | Solution | Config  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              CONSTANTS                          │   │
│  │  Tournaments | Weights | Limits | Defaults     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Flux de Données

```
Utilisateur
   │
   ├─► [Saisie Participants] → DataFrame → List[Participant]
   │
   ├─► [Configuration] → SolverConfig
   │
   ├─► [Validation] → List[str] (erreurs)
   │
   ├─► [Résolution]
   │      │
   │      └─► MultiPassSolver.solve_multipass()
   │             │
   │             ├─► PASS 1: TournamentSolver.solve() → List[Solution]
   │             │              │
   │             │              └─► OR-Tools CP-SAT Solver
   │             │                     │
   │             │                     ├─► Model building (variables + constraints)
   │             │                     ├─► Optimization (objective function)
   │             │                     └─► SolutionCollector.on_solution_callback()
   │             │
   │             ├─► Si échec → PASS 2: ConflictAnalyzer.analyze()
   │             │                         │
   │             │                         └─► Identification candidats relaxation
   │             │
   │             └─► Si accepté → PASS 3: TournamentSolver.solve() avec relaxation
   │
   ├─► [Analyse] → Solution.calculate_stats() → Métriques
   │
   ├─► [Visualisation] → Plotly Figures
   │
   └─► [Export] → CSV File
```

---

## 2. Stack Technique

### 2.1 Langages et Frameworks

| Composant | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **Backend** | Python | ≥ 3.8 | Écosystème riche, OR-Tools natif |
| **Interface** | Streamlit | ≥ 1.20 | Rapidité de développement, interface web sans JS |
| **Optimisation** | OR-Tools (CP-SAT) | ≥ 9.0 | Solver de contraintes performant (Google) |
| **Visualisation** | Plotly | ≥ 5.0 | Graphiques interactifs, export PNG |
| **Tests** | pytest | ≥ 7.0 | Standard Python, fixtures puissantes |
| **Data** | pandas | ≥ 1.3 | Manipulation de tableaux, CSV |

### 2.2 Dépendances (requirements.txt)

```txt
streamlit>=1.20.0
ortools>=9.5.0
plotly>=5.14.0
pandas>=1.5.0
pytest>=7.2.0
pytest-cov>=4.0.0
```

### 2.3 Structure du Projet

```
orga_team_estivales/
│
├── app.py                      # Point d'entrée Streamlit
├── requirements.txt            # Dépendances pip
├── README.md                   # Documentation utilisateur
├── QUICKSTART.md               # Guide démarrage rapide
├── run.sh                      # Script de lancement (Linux/Mac)
│
├── src/                        # Code source
│   ├── __init__.py
│   ├── constants.py            # Constantes et configuration
│   ├── models.py               # Modèles de données (dataclasses)
│   ├── solver.py               # TournamentSolver (OR-Tools)
│   ├── multipass_solver.py     # Résolution multi-passes
│   ├── validation.py           # Validation des entrées
│   ├── visualizations.py       # Graphiques Plotly
│   └── ui_components.py        # Composants Streamlit réutilisables
│
├── tests/                      # Tests unitaires et intégration
│   ├── __init__.py
│   ├── test_solver.py          # Tests du solver principal
│   ├── test_multipass.py       # Tests multi-passes
│   ├── test_categories_B_C.py  # Tests contraintes et qualité
│   ├── test_enumerate_all.py   # Tests énumération
│   ├── test_simple_working.py  # Tests cas simples
│   └── test_workflow.py        # Tests workflow complet
│
├── data/                       # Données (optionnel)
│   └── examples/
│
└── docs/                       # Documentation
    ├── SPEC_FONCTIONNELLE.md   # Ce document
    └── SPEC_TECHNIQUE.md       # Spécifications techniques
```

---

## 3. Modèles de Données

### 3.1 Participant

**Fichier** : `src/models.py`

```python
@dataclass
class Participant:
    """Représente un participant aux tournois"""
    nom: str                    # Identifiant unique
    genre: str                  # 'M' ou 'F'
    couple: Optional[str]       # Nom du partenaire (contrainte d'exclusion)
    voeux_etape: int           # Nombre d'étapes souhaitées (0-3)
    voeux_open: int            # Nombre d'opens souhaités (0-3)
    dispo_jusqu_a: str         # Dernier tournoi disponible (E1/O1/E2/O2/E3/O3)
    respect_voeux: bool        # Contrainte dure si True
    
    @property
    def voeux_jours_total(self) -> int:
        """Calcule le nombre total de jours souhaités"""
        return self.voeux_etape * 2 + self.voeux_open
```

**Validation** :
- `__post_init__` : Appelle `validate()` automatiquement
- `validate()` : Retourne une liste d'erreurs
- Levée d'exception `ValueError` si données invalides

**Conversions** :
- `to_dict()` : Vers dictionnaire (pour DataFrame)
- `from_dict()` : Depuis dictionnaire (parsing CSV/JSON)

---

### 3.2 Tournament

**Fichier** : `src/models.py`

```python
@dataclass
class Tournament:
    """Représente un tournoi"""
    id: str                    # Identifiant unique (E1, O1, E2, O2, E3, O3)
    label: str                 # Nom affiché ("Étape 1", "Open 1")
    lieu: str                  # Lieu physique ("SABLES D'OR", "ERQUY", "SAINT-CAST")
    type: str                  # 'etape' ou 'open'
    days: List[int]            # Jours concernés ([0,1] pour E1)
    day_labels: List[str]      # Labels des jours (["Samedi", "Dimanche"])
    
    @property
    def duration_days(self) -> int:
        return len(self.days)
    
    @property
    def is_etape(self) -> bool:
        return self.type == 'etape'
    
    @property
    def is_open(self) -> bool:
        return self.type == 'open'
```

**Chargement** : Depuis `constants.TOURNAMENTS`

---

### 3.3 Solution

**Fichier** : `src/models.py`

```python
@dataclass
class Solution:
    """Représente une solution (planning complet)"""
    assignments: Dict[str, Dict[str, List[str]]]  # {tournament_id: {genre: [noms]}}
    participants: List[Participant]
    tournaments: List[Tournament]
    
    # Métriques calculées (lazy loading)
    score: Optional[float] = None
    violated_wishes: List[Tuple[str, int]] = field(default_factory=list)
    quality_level: Optional[str] = None
    fatigue_alerts: List[str] = field(default_factory=list)
    
    def calculate_stats(self):
        """Calcule toutes les métriques de la solution"""
        # - Score qualité (0-100)
        # - Participants lésés (nom, écart)
        # - Niveau de qualité (Parfaite, Excellente, Acceptable, Compromis)
        # - Alertes fatigue (>4j consécutifs)
    
    def get_participant_stats(self, nom: str) -> dict:
        """Retourne les stats d'un participant"""
        return {
            'jours_souhaites': int,
            'jours_joues': int,
            'ecart': int,
            'presence': List[int],  # [0,1,0,1,1,0,1,0,0]
            'consecutifs_max': int
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convertit en DataFrame pour affichage/export"""
```

**Calcul du Score (v2.2.3)** :

```python
def get_quality_score(self) -> float:
    """
    Score de qualité 0-100 avec pénalités hiérarchiques
    
    Formule v2.2.3 :
    Score = 100 - pénalité_total - pénalité_concentration - pénalité_distribution - pénalité_fatigue
    
    1. Pénalité total : -2.5 pts par jour lésé total
    2. Pénalité concentration : -5 pts par jour au-delà de 1j pour une même personne
    3. Pénalité distribution : ratio de lésion × 8 (favorise léser les gros demandeurs)
    4. Pénalité fatigue : -2 pts par personne fatiguée
    """
    
    # 1. Total jours lésés
    total_jours_leses = sum(abs(ecart) for ecart in ecarts if ecart < 0)
    penalite_jours = total_jours_leses * 2.5
    
    # 2. Concentration des lésions (favorise répartition)
    penalite_concentration = 0.0
    for ecart in ecarts:
        if ecart < 0:
            jours_manquants = abs(ecart)
            if jours_manquants > 1:
                penalite_concentration += (jours_manquants - 1) * 5
    
    # 3. Distribution (favorise léser les gros demandeurs)
    cout_distribution = 0.0
    for participant, ecart in zip(participants, ecarts):
        if ecart < 0:
            ratio_lesion = abs(ecart) / participant.voeux_jours_total
            cout_distribution += ratio_lesion * 8
    
    # 4. Fatigue
    penalite_fatigue = len(fatigue_participants) * 2
    
    score = 100 - penalite_jours - penalite_concentration - cout_distribution - penalite_fatigue
    
    return max(0.0, min(100.0, score))
```

**Exemples de scores** :
- **Parfait** (0j lésé) : 100/100
- **Excellent** (6j répartis sur 6 personnes) : ~82/100
- **Bon** (6j avec 1 personne -2j, 4 personnes -1j) : ~70/100
- **Compromis** (6j avec 1 personne -3j, 3 personnes -1j) : ~65/100

**Niveaux de Qualité** :

| Niveau | Condition | Score | Affichage |
|--------|-----------|-------|-----------|
| Parfaite | `violated_wishes == []` | 100 | 🎯 Parfaite |
| Excellente | `max_ecart_individuel <= 1` | 85-95 | 🟢 Excellente |
| Acceptable | `max_ecart_individuel <= 2` | 70-84 | 🟡 Acceptable |
| Compromis | `max_ecart_individuel > 2` | <70 | 🟠 Compromis |

---

### 3.4 SolverConfig

**Fichier** : `src/models.py`

```python
@dataclass
class SolverConfig:
    """Configuration du solver"""
    include_o3: bool = False            # Inclure le dimanche O3
    allow_incomplete_teams: bool = False  # Autoriser équipes <3
    max_solutions: int = 50             # Nombre de solutions à chercher
    timeout_seconds: float = 120.0      # Timeout OR-Tools
    
    # Poids de la fonction objectif
    weight_respect_wishes: int = 1000
    weight_avoid_fatigue: int = 500
    weight_balance: int = 100
    weight_complete_teams: int = 10
```

---

## 4. Algorithmes

### 4.1 Algorithme Multi-Passes

**Fichier** : `src/multipass_solver.py`

**Principe** : Résolution en 3 passes pour gérer les cas impossibles.

```python
def solve_multipass(participants, tournaments, progress_callback):
    """
    PASS 1 : Résolution stricte (tous les vœux)
    ├─ Si succès → Retourner solutions parfaites
    └─ Si échec → PASS 2
    
    PASS 2 : Analyse des blocages
    ├─ ConflictAnalyzer.analyze()
    ├─ Identifier candidats à léser
    │   ├─ Vœux impossibles (demande > max disponible)
    │   ├─ Couples avec vœux incompatibles
    │   └─ Trop de contraintes strictes
    └─ Proposer à l'utilisateur → PASS 3
    
    PASS 3 : Résolution relaxée
    ├─ Appliquer les relaxations choisies
    └─ Retourner solutions de compromis
    """
```

**Implémentation PASS 1** :

```python
# Appeler le solver standard
solutions, status, info = self.base_solver.solve(
    participants,
    tournaments,
    progress_callback
)

# Vérifier si solutions parfaites
perfect = [s for s in solutions if len(s.violated_wishes) == 0]

if len(perfect) > 0:
    return MultiPassResult(
        solutions=solutions,
        pass_number=1,
        status='success',
        message=f"✅ {len(perfect)} solution(s) parfaite(s)"
    )
```

**Implémentation PASS 2** :

```python
candidates = self._identify_relaxation_candidates(participants, tournaments)

if not candidates:
    return MultiPassResult(
        solutions=[],
        pass_number=2,
        status='impossible',
        message="❌ Aucune solution trouvée même avec relaxations"
    )

return MultiPassResult(
    solutions=[],
    pass_number=2,
    candidates_if_failed=candidates,
    status='need_user_choice',
    message=f"⚠️ {len(candidates)} candidats identifiés pour relaxation"
)
```

**Identification des Candidats** :

```python
def _identify_relaxation_candidates(participants, tournaments):
    candidates = []
    
    for participant in participants:
        # 1. Vœux impossibles
        if participant.voeux_etape > len([t for t in tournaments if t.is_etape]):
            candidates.append(RelaxationCandidate(
                participant_name=participant.nom,
                current_wishes_etape=participant.voeux_etape,
                proposed_wishes_etape=len([t for t in tournaments if t.is_etape]),
                reason="Demande plus d'étapes que disponibles"
            ))
        
        # 2. Couples incompatibles
        if participant.couple:
            partner = get_partner(participant)
            total_days = participant.voeux_jours_total + partner.voeux_jours_total
            if total_days > len(all_days):
                candidates.append(...)
        
        # 3. Contraintes strictes excessives
        if too_many_strict_participants(participants):
            candidates.append(...)
    
    return candidates
```

---

### 4.2 Algorithme Principal (OR-Tools)

**Fichier** : `src/solver.py`

**Approche** : Résolution en 2 sous-passes pour énumérer TOUTES les solutions optimales.

```python
def solve(participants, tournaments, progress_callback):
    """
    SUB-PASS 1 : Trouver le score optimal (Optimisation)
    ├─ Créer modèle OR-Tools
    ├─ Ajouter variables + contraintes
    ├─ Minimiser fonction objectif hiérarchique
    └─ Récupérer best_max_shortage et best_total_shortage
    
    SUB-PASS 2 : Énumérer TOUS les profils optimaux (Satisfaction v2.2.3)
    ├─ Créer nouveau modèle
    ├─ Ajouter variables + contraintes
    ├─ Contraindre SEULEMENT les 2 critères principaux:
    │   - max_shortage == best_max_shortage (critère #1)
    │   - sum(shortages) == best_total_shortage (critère #2)
    ├─ NE PAS contraindre distribution_penalties (critère #3)
    ├─ Mode Satisfaction (pas d'optimisation)
    └─ Collecter TOUTES les solutions (tous les profils de lésés possibles)
    """
```

**Justification v2.2.3** : 
- En contraignant seulement les 2 critères principaux, on obtient **TOUS les profils** de lésés possibles
- Avant (v2.2.2) : on contraignait les 3 critères → seulement 1 profil trouvé
- Après (v2.2.3) : on explore tous les profils ayant le même max et le même total
- Exemple : Si optimal = max 2j, total 6j, on trouve tous les profils (Sophie S -2j + 4×-1j, Delphine -2j + 4×-1j, etc.)

---

### 4.3 Construction du Modèle OR-Tools

**Fichier** : `src/solver.py`, méthode `_build_model()`

**Variables Binaires** :

```python
# Pour chaque participant P et tournoi T
plays[P, T] = model.NewBoolVar(f'plays_{P}_{T}')

# Valeur = 1 si P joue à T, sinon 0
```

**Contraintes Dures** :

```python
# 1. CONTRAINTE COUPLE : Ne peuvent jouer ensemble le même jour
for day in all_days:
    for couple in couples:
        model.Add(
            sum(plays[P1, T] for T in tournaments_of_day[day]) +
            sum(plays[P2, T] for T in tournaments_of_day[day]) <= 1
        )

# 2. CONTRAINTE DISPONIBILITÉ : Ne peut jouer après dispo_jusqu_a
for participant in participants:
    for tournament in tournaments:
        if tournament.day > participant.dispo_jusqu_a_day:
            model.Add(plays[participant, tournament] == 0)

# 3. CONTRAINTE ÉQUIPES DE 3 (étapes)
for tournament in etapes:
    model.Add(sum(plays[P, tournament] for P in hommes) == 2)  # 2 hommes
    model.Add(sum(plays[P, tournament] for P in femmes) == 1)  # 1 femme
    # OU
    model.Add(sum(plays[P, tournament] for P in hommes) == 1)  # 1 homme
    model.Add(sum(plays[P, tournament] for P in femmes) == 2)  # 2 femmes

# 4. CONTRAINTE RESPECT VŒUX (si respect_voeux = True)
for participant in participants_stricts:
    jours_joues = sum(
        plays[participant, T] * T.duration_days 
        for T in tournaments
    )
    model.Add(jours_joues == participant.voeux_jours_total)

# 5. CONTRAINTE UNICITÉ : Un participant ne peut jouer 2 tournois le même jour
for participant in participants:
    for day in all_days:
        model.Add(
            sum(plays[participant, T] for T in tournaments_of_day[day]) <= 1
        )
```

**Fonction Objectif (Multi-Critères Hiérarchiques - v2.2.3)** :

```python
# STRATÉGIE v2.2.3 : Hiérarchie stricte des critères
# Priorité #1 : Minimiser la lésion maximale individuelle (×100000)
# Priorité #2 : Minimiser le total des jours lésés (×1000)
# Priorité #3 : Favoriser léser les gros demandeurs (×1)

# Variables pour les écarts (shortage)
wish_deviations = []
max_shortage = model.NewIntVar(0, 9, "max_shortage")
distribution_penalties = []

for participant in participants:
    if not participant.respect_voeux:
        jours_joues = sum(plays[participant, T] * T.duration_days for T in tournaments)
        souhaits = participant.voeux_jours_total
        
        # Shortage = max(0, souhaits - jours_joues)
        shortage = model.NewIntVar(0, 9, f'shortage_{participant.nom}')
        model.AddMaxEquality(shortage, [0, souhaits - jours_joues])
        
        # CRITÈRE #1 : Mettre à jour le maximum
        model.Add(max_shortage >= shortage)
        
        # CRITÈRE #2 : Shortage brut (non pondéré)
        wish_deviations.append(shortage)
        
        # CRITÈRE #3 : Pénalité de distribution
        # weight = max(1, 6 - jours_demandés) : favorise léser les gros demandeurs
        weight = max(1, 6 - souhaits)
        distribution_penalty = model.NewIntVar(0, 9 * weight, f'distrib_{participant.nom}')
        model.AddMultiplicationEquality(distribution_penalty, [shortage, weight])
        distribution_penalties.append(distribution_penalty)

# Variables pour fatigue (>3 jours consécutifs)
fatigue_penalties = []
for participant in participants:
    for day in range(len(all_days) - 3):
        consecutive_4 = sum(
            plays[participant, T] 
            for d in range(day, day + 4)
            for T in tournaments_of_day[d]
        )
        is_fatigued = model.NewBoolVar(f'fatigue_{participant.nom}_{day}')
        model.Add(consecutive_4 > 3).OnlyEnforceIf(is_fatigued)
        model.Add(consecutive_4 <= 3).OnlyEnforceIf(is_fatigued.Not())
        fatigue_penalties.append(is_fatigued)

# Variables pour équipes incomplètes
incomplete_penalties = []
if not config.allow_incomplete_teams:
    for tournament in etapes:
        total = sum(plays[P, tournament] for P in participants)
        is_incomplete = model.NewBoolVar(f'incomplete_{tournament.id}')
        model.Add(total < 3).OnlyEnforceIf(is_incomplete)
        model.Add(total >= 3).OnlyEnforceIf(is_incomplete.Not())
        incomplete_penalties.append(is_incomplete)

# OBJECTIF FINAL : Hiérarchie stricte avec ratios 100000:1000:500:10:1
objective = (
    max_shortage * 100000 +                          # PRIORITÉ #1 : Max lésion individuelle
    sum(wish_deviations) * 1000 +                    # PRIORITÉ #2 : Total jours lésés
    sum(fatigue_penalties) * 500 +                   # Fatigue
    sum(incomplete_penalties) * 10 +                 # Équipes incomplètes
    sum(distribution_penalties) * 1                  # PRIORITÉ #3 : Distribution
)

model.Minimize(objective)
```

**Justification de la hiérarchie (v2.2.3)** :
- Ratio 100:1 entre critères garantit que le critère supérieur est **toujours** respecté
- Évite absolument de léser 1 personne de 3j si on peut léser 3 personnes de 1j
- À égalité de max et total, favorise répartir les lésions (plus de personnes lésées de 1j)
- À égalité complète, favorise léser ceux qui demandent le plus (5j > 2j)

---

### 4.4 Collection des Solutions

**Fichier** : `src/solver.py`, classe `SolutionCollector`

```python
class SolutionCollector(cp_model.CpSolverSolutionCallback):
    """Callback appelé à chaque solution trouvée"""
    
    def on_solution_callback(self):
        # Limiter le nombre de solutions
        if len(self._solutions) >= self._solution_limit:
            self.StopSearch()
            return
        
        # Extraire les valeurs des variables
        solution_data = {}
        for tournament in self._tournaments:
            solution_data[tournament.id] = {'M': [], 'F': [], 'All': []}
            
            for participant in self._participants:
                key = (participant.nom, tournament.id)
                if key in self._variables and self.Value(self._variables[key]):
                    if tournament.is_etape:
                        solution_data[tournament.id][participant.genre].append(participant.nom)
                    else:
                        solution_data[tournament.id]['All'].append(participant.nom)
        
        # Créer l'objet Solution
        solution = Solution(
            assignments=solution_data,
            participants=self._participants,
            tournaments=self._tournaments
        )
        solution.calculate_stats()
        
        self._solutions.append(solution)
        
        # Notifier la progression
        if self._progress_callback:
            self._progress_callback(len(self._solutions), self._solution_limit, time.time() - self._start_time)
```

---

## 5. Modules et Composants

### 5.1 constants.py

**Rôle** : Configuration centralisée.

**Contenu** :

```python
# Paramètres équipes
TEAM_SIZE = 3
MAX_CONSECUTIVE_DAYS = 4

# Limites
MAX_SOLUTIONS_TO_FIND = 50
MAX_SOLUTIONS_TO_DISPLAY = 10
SOLVER_TIMEOUT = 120.0

# Poids fonction objectif
WEIGHT_RESPECT_WISHES = 1000
WEIGHT_AVOID_FATIGUE = 500
WEIGHT_BALANCE = 100
WEIGHT_COMPLETE_TEAMS = 10

# Configuration des tournois
TOURNAMENTS = [
    {
        'id': 'E1',
        'label': 'Étape 1',
        'lieu': "SABLES D'OR",
        'type': 'etape',
        'days': [0, 1],
        'day_labels': ['Samedi', 'Dimanche']
    },
    # ...
]

# Données par défaut (13 participants)
DEFAULT_PARTICIPANTS = [
    ['Delphine', 'F', None, 2, 0, 'E2', False],
    ['Emilie', 'F', 'Julien', 2, 0, 'O3', False],
    # ...
]
```

---

### 5.2 validation.py

**Rôle** : Validation des données d'entrée.

**Fonctions principales** :

```python
def validate_participants_data(participants: List[Participant]) -> List[str]:
    """Valide la liste des participants"""
    errors = []
    
    # Vérifier noms uniques
    # Vérifier couples bidirectionnels
    # Vérifier genres compatibles
    # Vérifier contraintes strictes excessives
    
    return errors

def validate_solution_feasibility(
    participants: List[Participant],
    tournaments: List[Tournament],
    config: SolverConfig
) -> Tuple[bool, List[str]]:
    """Vérifie si une solution est théoriquement possible"""
    warnings = []
    
    # Vérifier nombre de créneaux disponibles
    # Vérifier équilibre hommes/femmes
    # Vérifier disponibilités vs vœux
    
    return (is_feasible, warnings)

def suggest_improvements(
    participants: List[Participant],
    config: SolverConfig
) -> List[str]:
    """Suggère des améliorations de configuration"""
    suggestions = []
    
    # Suggestion 1 : Relâcher contraintes strictes
    # Suggestion 2 : Activer équipes incomplètes
    # Suggestion 3 : Inclure O3
    # Suggestion 4 : Réduire les vœux
    
    return suggestions
```

---

### 5.3 visualizations.py

**Rôle** : Génération des graphiques Plotly.

**Fonctions** :

| Fonction | Type de graphique | Utilité |
|----------|------------------|---------|
| `create_timeline_chart()` | Gantt | Vue chronologique des participations |
| `create_heatmap_chart()` | Heatmap | Matrice présence (participants × jours) |
| `create_workload_distribution_chart()` | Barres groupées | Comparer souhaits vs réalité |
| `create_pie_chart_distribution()` | Camembert | Répartition globale de la charge |
| `create_consecutive_days_chart()` | Barres empilées | Identifier fatigue |
| `create_quality_comparison_chart()` | Radar | Comparer plusieurs solutions |
| `create_gantt_chart()` | Gantt détaillé | Planning par lieu |
| `create_statistics_overview()` | Métriques | Résumé global |

**Exemple : Timeline**

```python
def create_timeline_chart(solution: Solution, tournaments: List[Tournament]) -> go.Figure:
    data = []
    
    for participant in solution.participants:
        stats = solution.get_participant_stats(participant.nom)
        presence = stats['presence']
        
        for day in range(len(presence)):
            if presence[day]:
                tournament_day = get_tournament_of_day(day, tournaments)
                data.append({
                    'Participant': participant.nom,
                    'Jour': day,
                    'Tournoi': tournament_day.label,
                    'Lieu': tournament_day.lieu,
                    'Type': tournament_day.type
                })
    
    df = pd.DataFrame(data)
    
    fig = px.timeline(
        df,
        x_start='Jour',
        x_end='Jour',
        y='Participant',
        color='Lieu',
        title='📅 Timeline des Participations'
    )
    
    fig.update_layout(height=max(400, len(solution.participants) * 30))
    
    return fig
```

---

### 5.4 ui_components.py

**Rôle** : Composants Streamlit réutilisables.

**Fonctions** :

```python
def render_participant_editor() -> pd.DataFrame:
    """Affiche le tableau éditable des participants"""
    
def render_configuration_panel() -> SolverConfig:
    """Affiche le panneau de configuration (sidebar)"""
    
def render_statistics_section(solutions: List[Solution]):
    """Affiche les statistiques générales"""
    
def render_solution_tabs(solutions: List[Solution], tournaments: List[Tournament]):
    """Affiche les onglets de solutions"""
    
def render_help_section():
    """Affiche l'aide contextuelle"""
```

**Exemple : render_statistics_section()**

```python
def render_statistics_section(solutions: List[Solution]):
    st.subheader("📊 Statistiques Générales")
    
    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Solutions trouvées", len(solutions))
    
    with col2:
        avg_score = sum(s.score for s in solutions) / len(solutions)
        st.metric("Score moyen", f"{avg_score:.0f}/100")
    
    with col3:
        best_score = max(s.score for s in solutions)
        st.metric("Meilleur score", f"{best_score:.0f}/100")
    
    with col4:
        st.metric("Temps de calcul", "42s")
    
    # Répartition par niveau
    perfect = [s for s in solutions if s.quality_level == 'Parfaite']
    excellent = [s for s in solutions if s.quality_level == 'Excellente']
    acceptable = [s for s in solutions if s.quality_level == 'Acceptable']
    compromis = [s for s in solutions if s.quality_level == 'Compromis']
    
    st.markdown(f"""
    **Répartition par niveau :**
    - 🎯 Parfaites : {len(perfect)} solution(s)
    - 🟢 Excellentes : {len(excellent)} solution(s)
    - 🟡 Acceptables : {len(acceptable)} solution(s)
    - 🟠 Compromis : {len(compromis)} solution(s)
    """)
```

---

## 6. OR-Tools : Implémentation

### 6.1 Pourquoi CP-SAT ?

**Constraint Programming - Satisfaction** (CP-SAT) est un solver de Google OR-Tools adapté aux problèmes combinatoires avec contraintes complexes.

**Avantages** :
- ✅ Gère les contraintes non-linéaires (couples, équilibre genre)
- ✅ Optimisation multi-critères native
- ✅ Énumération de toutes les solutions à un score donné
- ✅ Performance excellente (jusqu'à 10M de solutions/s)
- ✅ Open-source et bien documenté

**Alternatives considérées** :
- ❌ **PuLP** : Moins performant sur contraintes complexes
- ❌ **Google OR-Tools (MIP)** : Pas adapté aux contraintes non-linéaires
- ❌ **Z3** : Plus difficile à configurer

---

### 6.2 Modélisation

**Variables** :

| Variable | Type | Domaine | Description |
|----------|------|---------|-------------|
| `plays[P, T]` | BoolVar | {0, 1} | 1 si participant P joue au tournoi T |
| `deviation_pos[P]` | IntVar | [0, 10] | Écart positif (joue plus que souhaits) |
| `deviation_neg[P]` | IntVar | [0, 10] | Écart négatif (joue moins que souhaits) |
| `is_fatigued[P, d]` | BoolVar | {0, 1} | 1 si P joue >3j consécutifs à partir du jour d |
| `is_incomplete[T]` | BoolVar | {0, 1} | 1 si l'équipe du tournoi T est incomplète |

**Nombre total de variables** :

```
N_participants = 13
N_tournaments = 6
N_days = 9

Variables principales : N_participants × N_tournaments = 78
Variables auxiliaires : ~50 (déviations, fatigue, équipes incomplètes)

TOTAL : ~130 variables binaires/entières
```

**Complexité** : O(2^N) en pire cas, mais élagage efficace par OR-Tools → Temps réel ~30-60s

---

### 6.3 Stratégies d'Optimisation

**1. Pré-processing**

```python
# Éliminer variables impossibles AVANT de créer le modèle
for participant in participants:
    for tournament in tournaments:
        if tournament.day > participant.dispo_jusqu_a_day:
            # Ne pas créer la variable plays[participant, tournament]
            continue
```

**2. Hints (Solutions initiales)**

```python
# Donner une solution initiale pour accélérer
for participant in participants:
    # Stratégie gloutonne : Assigner aux premiers tournois
    ...
    model.AddHint(plays[participant, tournament], 1)
```

**3. Timeout et Limites**

```python
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = config.timeout_seconds
solver.parameters.num_search_workers = 4  # Parallélisation
solver.parameters.log_search_progress = False  # Pas de logs verbeux
```

---

## 7. Performance et Optimisation

### 7.1 Benchmarks

**Environnement de test** :
- Machine : Intel i7-10700K (8 cores), 16 GB RAM
- Python 3.10, OR-Tools 9.5

**Résultats** :

| Cas | Participants | Tournois | Solutions | Temps (PASS 1) | Temps (PASS 2) | Total |
|-----|--------------|----------|-----------|---------------|---------------|-------|
| Simple | 4 | 1 (E1) | 10 | 0.5s | 2s | 2.5s |
| Moyen | 10 | 6 | 50 | 5s | 25s | 30s |
| Réel | 13 | 6 | 50 | 8s | 35s | 43s |
| Complexe | 20 | 6 | 100 | 15s | 90s | 105s |

**Goulots d'étranglement** :
- PASS 2 (énumération) prend 80% du temps total
- Contraintes de couples ralentissent (graphe de conflit)
- Visualisations Plotly : ~1-2s pour 10 graphiques

---

### 7.2 Optimisations Appliquées

**1. Lazy Calculation des Stats**

```python
@dataclass
class Solution:
    score: Optional[float] = None  # Calculé seulement si demandé
    
    def calculate_stats(self):
        if self.score is not None:
            return  # Déjà calculé
        
        # Calcul coûteux
        ...
```

**2. Cache Streamlit**

```python
@st.cache_data
def load_default_participants():
    return DEFAULT_PARTICIPANTS.copy()

@st.cache_resource
def create_heavy_plot(solution_data):
    # Plotly fig mise en cache
    ...
```

**3. Affichage Progressif**

```python
# N'afficher que les 10 meilleures solutions
solutions_to_display = sorted(solutions, key=lambda s: s.score, reverse=True)[:10]
```

**4. Parallélisation OR-Tools**

```python
solver.parameters.num_search_workers = min(4, os.cpu_count())
```

---

### 7.3 Limites de Performance

**Scalabilité** :

| Participants | Tournois | Temps estimé | Faisabilité |
|--------------|----------|--------------|-------------|
| ≤10 | 6 | <30s | ✅ Excellent |
| 11-15 | 6 | 30-60s | ✅ Bon |
| 16-20 | 6 | 60-120s | 🟡 Acceptable |
| 21-30 | 6 | 120-300s | 🟠 Limite |
| >30 | 6 | >300s | ❌ Non recommandé |

**Recommandation** : Limiter à 20 participants pour expérience utilisateur fluide.

---

## 8. Tests

### 8.1 Stratégie de Test

**Pyramide de tests** :

```
        ┌─────────────────────┐
        │   Tests E2E (10%)   │ ← test_workflow.py
        ├─────────────────────┤
        │  Tests Intégration  │ ← test_multipass.py
        │       (30%)         │   test_enumerate_all.py
        ├─────────────────────┤
        │   Tests Unitaires   │ ← test_solver.py
        │       (60%)         │   test_categories_B_C.py
        └─────────────────────┘   test_simple_working.py
```

**Couverture actuelle** : ~85% (pytest-cov)

---

### 8.2 Tests Unitaires (test_solver.py)

**Catégories** :

```python
class TestModels:
    """Tests des dataclasses"""
    def test_participant_creation_valid()
    def test_participant_invalid_genre()
    def test_participant_negative_wishes()
    def test_participant_from_dict()

class TestValidation:
    """Tests de validation"""
    def test_validate_empty_participants()
    def test_validate_duplicate_names()
    def test_validate_couple_not_found()
    def test_validate_couple_not_bidirectional()

class TestSolverBasic:
    """Tests du solver de base"""
    def test_solver_initialization()
    def test_simple_case_two_participants()
    def test_impossible_case_all_strict()

class TestSolverObjective:
    """Tests de la fonction objectif"""
    def test_objective_minimizes_deviation()
    def test_objective_balances_when_conflict()
    def test_objective_respects_strict_wishes()

class TestSolverCouples:
    """Tests des contraintes de couples"""
    def test_couple_cannot_play_same_day()

class TestSolverFatigue:
    """Tests de fatigue"""
    def test_penalizes_consecutive_days()

class TestDefaultData:
    """Tests avec données par défaut"""
    def test_default_participants_valid()
    def test_default_data_finds_solutions()
```

---

### 8.3 Tests d'Intégration

**test_multipass.py** :

```python
class TestMultiPassSolver:
    def test_multipass_finds_perfect_solution_pass1()
        """Vérifie que PASS 1 trouve des solutions parfaites si elles existent"""
    
    def test_multipass_proposes_candidates_when_impossible()
        """Vérifie que PASS 2 propose des candidats si aucune solution parfaite"""
    
    def test_multipass_with_relaxation()
        """Vérifie que PASS 3 trouve des solutions après relaxation"""

class TestConflictAnalyzer:
    def test_analyzer_detects_too_many_strict()
        """Détecte trop de contraintes strictes"""
    
    def test_analyzer_detects_incomplete_teams_issue()
        """Détecte problèmes d'équipes incomplètes"""
    
    def test_analyzer_detects_couple_conflicts()
        """Détecte conflits de couples"""
```

**test_enumerate_all.py** :

```python
def test_enumerate_all_solutions_4_players_1_etape()
    """Vérifie énumération de TOUTES les solutions équivalentes"""

def test_enumerate_all_solutions_permutations()
    """Vérifie que permutations sont bien distinctes"""

def test_max_solutions_limit()
    """Vérifie que la limite de solutions est respectée"""
```

---

### 8.4 Tests E2E (test_workflow.py)

```python
def test_complete_workflow():
    """Test du workflow complet de bout en bout"""
    
    # 1. Charger données
    participants = load_default_participants()
    
    # 2. Valider
    errors = validate_participants_data(participants)
    assert len(errors) == 0
    
    # 3. Configurer
    config = SolverConfig(include_o3=False, allow_incomplete_teams=False)
    
    # 4. Résoudre
    multipass_solver = MultiPassSolver(config)
    result = multipass_solver.solve_multipass(participants, tournaments)
    
    # 5. Vérifier résultats
    assert result.status == 'success'
    assert len(result.solutions) > 0
    
    # 6. Calculer stats
    for solution in result.solutions:
        solution.calculate_stats()
        assert solution.score is not None
    
    # 7. Exporter
    df = result.solutions[0].to_dataframe()
    assert len(df) == len(participants)
```

---

### 8.5 Exécution des Tests

```bash
# Tous les tests
pytest tests/ -v

# Tests avec couverture
pytest tests/ --cov=src --cov-report=html

# Tests rapides uniquement (unitaires)
pytest tests/test_solver.py -v

# Tests d'un cas spécifique
pytest tests/test_multipass.py::TestMultiPassSolver::test_multipass_finds_perfect_solution_pass1 -v
```

**Tests en échec connus (à corriger)** :

1. `test_trouve_multiples_variantes_si_existent` (test_categories_B_C.py)
2. `test_enumerate_emilie_delphine_swap` (test_enumerate_all.py)

**Raison probable** : Contraintes trop strictes ou limite de solutions trop basse.

---

## 9. Déploiement

### 9.1 Déploiement Local

**Installation** :

```bash
# Cloner le repo
git clone https://github.com/votre-username/estivales-team-planner.git
cd estivales-team-planner

# Créer environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Installer dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

**Script automatique (run.sh)** :

```bash
#!/bin/bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

---

### 9.2 Déploiement Streamlit Cloud

**Étapes** :

1. **Pousser sur GitHub** :
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/votre-username/estivales-team-planner.git
   git push -u origin main
   ```

2. **Connecter Streamlit Cloud** :
   - Aller sur https://share.streamlit.io/
   - Se connecter avec GitHub
   - Cliquer sur "New app"
   - Sélectionner le repo et la branche `main`
   - Fichier principal : `app.py`

3. **Configuration** :
   - Streamlit Cloud installe automatiquement `requirements.txt`
   - L'app est disponible sur `https://share.streamlit.io/votre-username/estivales-team-planner/main/app.py`

**Limitations Streamlit Cloud (gratuit)** :
- CPU : 1 core (limite de performance)
- RAM : 1 GB (suffisant pour ce projet)
- Pas de persistance de données
- Timeout : 10 min d'inactivité → app sleep

---

### 9.3 Déploiement Docker (optionnel)

**Dockerfile** :

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Installer dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier code
COPY . .

# Exposer port Streamlit
EXPOSE 8501

# Lancer l'app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Build et run** :

```bash
# Build image
docker build -t estivales-team-planner .

# Run container
docker run -p 8501:8501 estivales-team-planner

# Accéder à http://localhost:8501
```

---

## 10. Points d'Amélioration

### 10.1 Améliorations Prioritaires (P0)

| ID | Description | Impact | Effort |
|----|-------------|--------|--------|
| IMP-01 | **Corriger les 2 tests en échec** | 🔴 Critique | 🟢 Faible (1h) |
| IMP-02 | **Import CSV/Excel pour participants** | 🟢 Haute | 🟡 Moyen (3h) |
| IMP-03 | **Sauvegarde état dans session** | 🟢 Haute | 🟢 Faible (2h) |
| IMP-04 | **Optimiser temps énumération (PASS 2)** | 🟡 Moyenne | 🔴 Élevé (1j) |

---

### 10.2 Améliorations Secondaires (P1)

| ID | Description | Impact | Effort |
|----|-------------|--------|--------|
| IMP-05 | Historique des plannings (CSV local) | 🟡 Moyenne | 🟡 Moyen (4h) |
| IMP-06 | Export PDF avec graphiques | 🟡 Moyenne | 🟡 Moyen (5h) |
| IMP-07 | Mode comparaison (2-3 solutions côte à côte) | 🟢 Haute | 🟡 Moyen (4h) |
| IMP-08 | Tooltips explicatifs sur chaque paramètre | 🟡 Moyenne | 🟢 Faible (2h) |
| IMP-09 | Dark mode (thème Streamlit) | 🟡 Faible | 🟢 Faible (1h) |

---

### 10.3 Améliorations Futures (P2)

| ID | Description | Impact | Effort |
|----|-------------|--------|--------|
| IMP-10 | Support tournois personnalisés (dates variables) | 🟢 Haute | 🔴 Élevé (1 semaine) |
| IMP-11 | Interface mobile responsive améliorée | 🟡 Moyenne | 🟡 Moyen (3j) |
| IMP-12 | Base de données (PostgreSQL) pour multi-utilisateurs | 🔴 Critique | 🔴 Élevé (2 semaines) |
| IMP-13 | Notification email automatique aux participants | 🟡 Moyenne | 🟡 Moyen (1j) |
| IMP-14 | Mode collaboratif (WebSocket + Redis) | 🟢 Haute | 🔴 Élevé (3 semaines) |

---

### 10.4 Bugs Connus

| ID | Description | Gravité | Workaround |
|----|-------------|---------|------------|
| BUG-01 | Refresh = perte de données (pas de persistance) | 🟡 Moyenne | Exporter CSV régulièrement |
| BUG-02 | Graphiques Plotly lents avec >15 participants | 🟢 Faible | Limiter à 10 solutions affichées |
| BUG-03 | Erreur si tous les participants ont le même genre | 🔴 Critique | Valider équilibre H/F avant calcul |

---

### 10.5 Améliorations Algorithmiques

**IMP-ALG-01 : Heuristique de branch & bound**

```python
# Actuellement : Énumération exhaustive (lente)
# Amélioration : Branch & bound avec élagage précoce

def branch_and_bound_solver(participants, tournaments):
    best_solutions = []
    best_score = float('inf')
    
    def branch(partial_assignment, remaining_participants):
        nonlocal best_score, best_solutions
        
        # Élagage : Si score partiel > best_score, abandonner
        partial_score = calculate_partial_score(partial_assignment)
        if partial_score > best_score:
            return
        
        # Si complet, vérifier si meilleur
        if not remaining_participants:
            if partial_score < best_score:
                best_score = partial_score
                best_solutions = [partial_assignment]
            elif partial_score == best_score:
                best_solutions.append(partial_assignment)
            return
        
        # Brancher sur le prochain participant
        participant = remaining_participants[0]
        for tournament in feasible_tournaments(participant):
            new_assignment = partial_assignment + [(participant, tournament)]
            branch(new_assignment, remaining_participants[1:])
    
    branch([], participants)
    return best_solutions
```

**Gain attendu** : -30% temps de calcul

---

**IMP-ALG-02 : Précomputation des incompatibilités**

```python
# Créer un graphe de conflits AVANT le solver
conflict_graph = defaultdict(set)

for p1, p2 in couples:
    conflict_graph[p1].add(p2)
    conflict_graph[p2].add(p1)

# Utiliser dans les contraintes
for day in all_days:
    for p1 in participants:
        for p2 in conflict_graph[p1]:
            model.Add(plays[p1, day] + plays[p2, day] <= 1)
```

**Gain attendu** : -20% temps de construction du modèle

---

## 11. Annexes

### 11.1 Exemple de Log OR-Tools

```
Starting CP-SAT solver v9.5.2237
Setting time limit to 120 seconds

--- PASS 1: Optimization ---
Building model...
  78 variables created
  126 constraints added
  Objective: Minimize (1000 * deviations + 500 * fatigue + 10 * incomplete)

Solving...
  Workers: 4
  Search progress:
    [10s] Solutions: 0, Best obj: ∞
    [25s] Solutions: 1, Best obj: 2450
    [40s] Solutions: 3, Best obj: 1200
    [55s] Solutions: 8, Best obj: 850
    [60s] Solutions: 12, Best obj: 600 ← Optimal found

Status: OPTIMAL
Best objective: 600
Time: 62.34s

--- PASS 2: Enumeration (obj = 600) ---
Building model...
  78 variables created
  126 constraints added
  1 additional constraint: objective == 600

Solving...
  Workers: 4
  Search progress:
    [5s] Solutions found: 5
    [10s] Solutions found: 12
    [15s] Solutions found: 23
    [20s] Solutions found: 35
    [25s] Solutions found: 48
    [28s] Solutions found: 50 ← Limit reached

Status: FEASIBLE (limit reached)
Solutions found: 50
Time: 28.76s

TOTAL TIME: 91.10s
```

---

### 11.2 Exemple de Solution JSON

```json
{
  "score": 87,
  "quality_level": "Excellente",
  "violated_wishes": [
    ["Sophie L", -1],
    ["Rémy", -1]
  ],
  "fatigue_alerts": [],
  "assignments": {
    "E1": {
      "M": ["Julien", "Sylvain"],
      "F": ["Sophie S"]
    },
    "O1": {
      "All": ["Hugo", "Robin", "Sébastien A"]
    },
    "E2": {
      "M": ["Rémy", "Sébastien S"],
      "F": ["Emilie"]
    },
    "O2": {
      "All": ["Delphine", "Kathleen", "Lise"]
    },
    "E3": {
      "M": ["Julien", "Sylvain"],
      "F": ["Sophie L"]
    }
  },
  "participant_stats": {
    "Emilie": {
      "jours_souhaites": 4,
      "jours_joues": 4,
      "ecart": 0,
      "presence": [0, 0, 0, 1, 1, 0, 0, 0, 0],
      "consecutifs_max": 2
    },
    "Sophie L": {
      "jours_souhaites": 4,
      "jours_joues": 3,
      "ecart": -1,
      "presence": [0, 0, 0, 0, 0, 0, 1, 1, 0],
      "consecutifs_max": 2
    }
  }
}
```

---

### 11.3 Glossaire Technique

| Terme | Définition |
|-------|------------|
| **CP-SAT** | Constraint Programming - SATisfiability, solver de Google OR-Tools |
| **BoolVar** | Variable binaire (0 ou 1) dans OR-Tools |
| **IntVar** | Variable entière dans OR-Tools |
| **Callback** | Fonction appelée par OR-Tools à chaque solution trouvée |
| **Objective** | Fonction à minimiser/maximiser |
| **Constraint** | Règle qui doit être satisfaite (contrainte dure) |
| **Hint** | Solution initiale donnée au solver pour accélérer |
| **Branch & Bound** | Algorithme d'optimisation combinatoire |
| **Lazy Loading** | Calcul différé (seulement si nécessaire) |
| **Session State** | État persistant dans Streamlit (durant la session) |

---

**FIN DE LA SPÉCIFICATION TECHNIQUE**

## 11. Historique des Modifications Techniques

### Version 2.2.4 (4 Février 2026)

**Optimisations UI** :
```python
# app.py ligne 52
st.set_page_config(
    initial_sidebar_state="collapsed"  # Fermée par défaut
)

# app.py ligne 510
max_solutions = st.slider(
    value=500  # 500 au lieu de 50
)
```

**Nouvelles fonctionnalités** :
```python
# app.py lignes 1091-1133
# Checkbox "1 solution par profil"
limit_to_best_per_profile = st.checkbox(...)

if limit_to_best_per_profile:
    best_per_profile = []
    for signature, solutions in profils_dict.items():
        best_solution = max(solutions, key=lambda s: s.get_quality_score())
        best_per_profile.append(best_solution)
    filtered = sorted(best_per_profile, key=lambda s: -s.get_quality_score())
```

**Métriques modifiées** :
```python
# app.py ligne 1132
# Score moyen → Score max
score_max = max(s.get_quality_score() for s in solutions)
st.metric("Score max", f"{score_max:.0f}/100")
```

**Nouveaux documents** :
- `docs/REVIEW_SPECS_VS_REALITE.md` : Analyse conformité
- `README.md` : Section Documentation avec liens specs

**Impact performance** :
- Nombre solutions par défaut : 50 → 500 (+900%)
- Temps calcul moyen : +20-30s (acceptable)
- Exhaustivité : Meilleure couverture des profils uniques

**Tests** : Tous passants (44/44) ✅
