"""
Modèles de données pour l'organisateur d'Estivales
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
from src.constants import VALID_GENRES, VALID_TOURNAMENT_IDS, MAX_CONSECUTIVE_DAYS


@dataclass
class Participant:
    """Représente un participant aux tournois"""
    nom: str
    genre: str
    couple: Optional[str]
    voeux_etape: int
    voeux_open: int
    dispo_jusqu_a: str
    respect_voeux: bool
    
    def __post_init__(self):
        """Validation après initialisation"""
        errors = self.validate()
        if errors:
            raise ValueError(f"Participant {self.nom} invalide: {', '.join(errors)}")
    
    def validate(self) -> List[str]:
        """Valide les données du participant"""
        errors = []
        
        if not self.nom or not self.nom.strip():
            errors.append("Le nom ne peut pas être vide")
        
        if self.genre not in VALID_GENRES:
            errors.append(f"Genre invalide '{self.genre}', doit être 'M' ou 'F'")
        
        if self.voeux_etape < 0:
            errors.append(f"Vœux étapes négatif: {self.voeux_etape}")
        
        if self.voeux_open < 0:
            errors.append(f"Vœux opens négatif: {self.voeux_open}")
        
        if self.dispo_jusqu_a not in VALID_TOURNAMENT_IDS:
            errors.append(f"Disponibilité invalide: {self.dispo_jusqu_a}")
        
        return errors
    
    @property
    def voeux_jours_total(self) -> int:
        """Calcule le nombre total de jours souhaités"""
        return self.voeux_etape * 2 + self.voeux_open
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire"""
        return {
            'Nom': self.nom,
            'Genre': self.genre,
            'Couple': self.couple,
            'Voeux_Etape': self.voeux_etape,
            'Voeux_Open': self.voeux_open,
            'Dispo_Jusqu_a': self.dispo_jusqu_a,
            'Respect_Voeux': self.respect_voeux
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Participant':
        """Crée un participant depuis un dictionnaire"""
        return cls(
            nom=data['Nom'],
            genre=data['Genre'],
            couple=data.get('Couple'),
            voeux_etape=int(data['Voeux_Etape']),
            voeux_open=int(data['Voeux_Open']),
            dispo_jusqu_a=data['Dispo_Jusqu_a'],
            respect_voeux=bool(data['Respect_Voeux'])
        )


@dataclass
class Tournament:
    """Représente un tournoi"""
    id: str
    label: str
    lieu: str
    type: str  # 'etape' ou 'open'
    days: List[int]
    day_labels: List[str] = field(default_factory=list)
    
    @property
    def duration_days(self) -> int:
        """Nombre de jours du tournoi"""
        return len(self.days)
    
    @property
    def is_etape(self) -> bool:
        """True si c'est une étape"""
        return self.type == 'etape'
    
    @property
    def is_open(self) -> bool:
        """True si c'est un open"""
        return self.type == 'open'


@dataclass
class Solution:
    """Représente une solution calculée"""
    assignments: Dict[str, Dict[str, List[str]]]  # {tournament_id: {'M': [...], 'F': [...], 'All': [...]}}
    participants: List[Participant]
    tournaments: List[Tournament]
    
    # Statistiques calculées
    violated_wishes: Set[str] = field(default_factory=set)
    max_consecutive_days: int = 0
    fatigue_participants: List[str] = field(default_factory=list)
    total_days_played: int = 0
    
    def calculate_stats(self):
        """Calcule les statistiques de la solution"""
        self.violated_wishes = set()
        self.fatigue_participants = []
        max_cons_global = 0
        total_days = 0
        
        for participant in self.participants:
            stats = self.get_participant_stats(participant.nom)
            
            # Vérifier si vœux respectés
            if stats['etapes_jouees'] != participant.voeux_etape or \
               stats['opens_joues'] != participant.voeux_open:
                self.violated_wishes.add(participant.nom)
            
            # Vérifier la fatigue
            if stats['max_consecutifs'] > 3:
                self.fatigue_participants.append(
                    f"{participant.nom} ({stats['max_consecutifs']}j)"
                )
            
            max_cons_global = max(max_cons_global, stats['max_consecutifs'])
            total_days += stats['jours_joues']
        
        self.max_consecutive_days = max_cons_global
        self.total_days_played = total_days
    
    def get_participant_stats(self, participant_name: str) -> dict:
        """Calcule les stats pour un participant"""
        # Trouver le participant
        participant = next(
            (p for p in self.participants if p.nom == participant_name),
            None
        )
        
        if not participant:
            return {}
        
        # Calculer présence par jour
        presence = [False] * 9
        
        for tournament_id, teams in self.assignments.items():
            all_players = teams['M'] + teams['F'] + teams['All']
            
            if participant_name in all_players:
                # Trouver les jours de ce tournoi
                tournament = next(
                    (t for t in self.tournaments if t.id == tournament_id),
                    None
                )
                if tournament:
                    for day in tournament.days:
                        presence[day] = True
        
        # Compter étapes et opens
        etapes_jouees = sum(
            1 for tid, teams in self.assignments.items()
            if participant_name in (teams['M'] + teams['F'] + teams['All'])
            and any(t.id == tid and t.is_etape for t in self.tournaments)
        )
        
        opens_joues = sum(
            1 for tid, teams in self.assignments.items()
            if participant_name in (teams['M'] + teams['F'] + teams['All'])
            and any(t.id == tid and t.is_open for t in self.tournaments)
        )
        
        # Calculer jours consécutifs max
        max_consecutive = 0
        current_streak = 0
        
        for day_played in presence:
            if day_played:
                current_streak += 1
                max_consecutive = max(max_consecutive, current_streak)
            else:
                current_streak = 0
        
        jours_joues = sum(presence)
        jours_souhaites = participant.voeux_jours_total
        
        return {
            'etapes_jouees': etapes_jouees,
            'opens_joues': opens_joues,
            'jours_joues': jours_joues,
            'jours_souhaites': jours_souhaites,
            'ecart': jours_joues - jours_souhaites,
            'max_consecutifs': max_consecutive,
            'presence': presence
        }
    
    def get_quality_score(self) -> float:
        """
        Calcule un score de qualité de la solution (0-100)
        
        ALIGNÉ SUR L'OBJECTIF OR-TOOLS (v2.3.0):
        Le score reflète exactement ce que le solver optimise pour garantir
        une cohérence totale entre l'objectif OR-Tools et le score affiché.
        
        Critères (par ordre de priorité):
        1. max_shortage (lésion max individuelle): -10 pts/jour
        2. total_shortage (total jours lésés): -2.5 pts/jour
        3. fatigue (>3j consécutifs): -2 pts/personne
        4. max_consecutifs: -1 pt/jour au-dessus de 3
        
        100 = solution parfaite (tous vœux respectés)
        0 = solution très mauvaise
        """
        if not self.participants:
            return 0.0
        
        # 1. CRITÈRE DOMINANT: Lésion maximale individuelle
        max_shortage = max(
            (abs(self.get_participant_stats(p.nom)['ecart']) 
             for p in self.participants 
             if self.get_participant_stats(p.nom)['ecart'] < 0),
            default=0
        )
        
        # 2. CRITÈRE SECONDAIRE: Total jours lésés
        total_shortage = sum(
            abs(self.get_participant_stats(p.nom)['ecart'])
            for p in self.participants
            if self.get_participant_stats(p.nom)['ecart'] < 0
        )
        
        # 3. CRITÈRE TERTIAIRE: Fatigue (nombre de personnes avec >3j consécutifs)
        nb_fatigues = len(self.fatigue_participants)
        
        # 4. CRITÈRE QUATERNAIRE: Jours consécutifs max
        max_consecutifs = self.max_consecutive_days
        
        # Calcul des pénalités (mêmes pondérations relatives que OR-Tools)
        penalite_max = max_shortage * 10           # 10 points par jour max (priorité absolue)
        penalite_total = total_shortage * 2.5      # 2.5 points par jour total
        penalite_fatigue = nb_fatigues * 2         # 2 points par personne fatiguée
        penalite_consecutifs = max(0, max_consecutifs - 3) * 1  # 1 point par jour au-dessus de 3
        
        # Score final
        score = 100 - penalite_max - penalite_total - penalite_fatigue - penalite_consecutifs
        
        # Bonus pour solution parfaite
        if total_shortage == 0:
            score = 100.0
        
        return max(0.0, min(100.0, score))


@dataclass
class SolverConfig:
    """Configuration pour le solver"""
    include_o3: bool = False
    allow_incomplete: bool = False
    max_solutions: int = 50
    timeout_seconds: float = 120.0
    search_mode: str = 'unique_profiles'  # 'unique_profiles' ou 'all'
    min_quality_score: int = 0  # Score minimum pour filtrer les profils
    
    # Poids pour l'objectif multi-critères
    weight_wishes: int = 1000
    weight_fatigue: int = 500
    weight_balance: int = 100
    weight_incomplete: int = 10
