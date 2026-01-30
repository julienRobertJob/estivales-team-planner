"""
Constantes pour l'organisateur d'Estivales de Volley
"""

# Configuration des équipes
TEAM_SIZE = 3
MAX_CONSECUTIVE_DAYS = 3

# Limites de solutions
MAX_SOLUTIONS_TO_FIND = 50
MAX_SOLUTIONS_TO_DISPLAY = 10

# Timeout du solver (en secondes)
SOLVER_TIMEOUT = 120.0

# Poids pour la fonction objectif multi-critères
WEIGHT_RESPECT_WISHES = 1000  # Priorité maximale : respecter les vœux
WEIGHT_AVOID_FATIGUE = 500    # Priorité haute : éviter >3j consécutifs
WEIGHT_BALANCE = 100          # Priorité moyenne : équilibrer les charges
WEIGHT_COMPLETE_TEAMS = 10    # Priorité basse : éviter équipes incomplètes

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
    {
        'id': 'O1',
        'label': 'Open 1',
        'lieu': 'ERQUY',
        'type': 'open',
        'days': [2],
        'day_labels': ['Lundi']
    },
    {
        'id': 'E2',
        'label': 'Étape 2',
        'lieu': 'ERQUY',
        'type': 'etape',
        'days': [3, 4],
        'day_labels': ['Mardi', 'Mercredi']
    },
    {
        'id': 'O2',
        'label': 'Open 2',
        'lieu': 'SAINT-CAST',
        'type': 'open',
        'days': [5],
        'day_labels': ['Jeudi']
    },
    {
        'id': 'E3',
        'label': 'Étape 3',
        'lieu': 'SAINT-CAST',
        'type': 'etape',
        'days': [6, 7],
        'day_labels': ['Vendredi', 'Samedi']
    },
    {
        'id': 'O3',
        'label': 'Open 3',
        'lieu': 'SAINT-CAST',
        'type': 'open',
        'days': [8],
        'day_labels': ['Dimanche']
    },
]

# Données par défaut
DEFAULT_PARTICIPANTS = [
    ['Julien', 'M', 'Emilie', 1, 1, 'O3', False],
    ['Hugo', 'M', None, 1, 1, 'E3', False],
    ['Sébastien A', 'M', 'Kathleen', 0, 1, 'O3', False],
    ['Emilie', 'F', 'Julien', 2, 0, 'O3', False],
    ['Kathleen', 'F', 'Sébastien A', 2, 0, 'O3', False],
    ['Delphine', 'F', None, 2, 0, 'E2', False],  # Plus de couple, pas strict
    ['Sylvain', 'M', 'Sophie L', 2, 1, 'E3', False],
    ['Robin', 'M', None, 2, 1, 'E3', False],  # Plus de couple avec Delphine
    ['Rémy', 'M', 'Lise', 2, 1, 'O3', False],
    ['Sophie S', 'F', 'Sébastien S', 2, 1, 'O3', False],
    ['Lise', 'F', 'Rémy', 1, 2, 'O3', False],
    ['Sébastien S', 'M', 'Sophie S', 1, 2, 'O3', False],
    ['Sophie L', 'F', 'Sylvain', 1, 2, 'E3', False],
]

# Colonnes du DataFrame participants
PARTICIPANT_COLUMNS = [
    'Nom',
    'Genre',
    'Couple',
    'Voeux_Etape',
    'Voeux_Open',
    'Dispo_Jusqu_a',
    'Respect_Voeux'
]

# Genres valides
VALID_GENRES = ['M', 'F']

# IDs de tournois valides
VALID_TOURNAMENT_IDS = [t['id'] for t in TOURNAMENTS]
