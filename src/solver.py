"""
Solver OR-Tools pour l'optimisation des plannings
"""
from typing import List, Dict, Tuple, Optional
from ortools.sat.python import cp_model
import time

from src.models import Participant, Tournament, Solution, SolverConfig
from src.constants import TEAM_SIZE, MAX_CONSECUTIVE_DAYS


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    """Collecte les solutions trouvées par OR-Tools"""
    
    def __init__(
        self,
        variables: Dict,
        tournaments: List[Tournament],
        participants: List[Participant],
        limit: int,
        progress_callback=None
    ):
        super().__init__()
        self._variables = variables
        self._tournaments = tournaments
        self._participants = participants
        self._solution_limit = limit
        self._solutions = []
        self._progress_callback = progress_callback
        self._start_time = time.time()
    
    def on_solution_callback(self):
        """Appelé à chaque solution trouvée"""
        if len(self._solutions) >= self._solution_limit:
            self.StopSearch()
            return
        
        # Notifier la progression
        if self._progress_callback:
            elapsed = time.time() - self._start_time
            self._progress_callback(
                len(self._solutions) + 1,
                self._solution_limit,
                elapsed
            )
        
        # Extraire la solution
        solution_data = {}
        
        for tournament in self._tournaments:
            solution_data[tournament.id] = {'M': [], 'F': [], 'All': []}
            
            for participant in self._participants:
                key = (participant.nom, tournament.id)
                
                if key in self._variables and self.Value(self._variables[key]):
                    if tournament.is_etape:
                        solution_data[tournament.id][participant.genre].append(participant.nom)
                    else:  # open
                        solution_data[tournament.id]['All'].append(participant.nom)
        
        # Créer l'objet Solution
        solution = Solution(
            assignments=solution_data,
            participants=self._participants,
            tournaments=self._tournaments
        )
        
        # Calculer les stats
        solution.calculate_stats()
        
        self._solutions.append(solution)
    
    def get_solutions(self) -> List[Solution]:
        """Retourne les solutions collectées"""
        return self._solutions


class TournamentSolver:
    """Solver principal pour l'optimisation des tournois"""
    
    def __init__(self, config: SolverConfig):
        self.config = config
    
    def solve(
        self,
        participants: List[Participant],
        tournaments: List[Tournament],
        progress_callback=None
    ) -> Tuple[List[Solution], str, Dict]:
        """
        Résout le problème d'optimisation.
        
        Args:
            participants: Liste des participants
            tournaments: Liste des tournois actifs
            progress_callback: Fonction appelée pour la progression (current, total, time)
            
        Returns:
            Tuple (solutions, status, info)
        """
        # Construire le modèle
        model, variables, auxiliary_vars = self._build_model(participants, tournaments)
        
        # Configurer le solver
        solver = cp_model.CpSolver()
        solver.parameters.enumerate_all_solutions = True
        solver.parameters.max_time_in_seconds = self.config.timeout_seconds
        
        # Collecter les solutions
        collector = SolutionCollector(
            variables,
            tournaments,
            participants,
            self.config.max_solutions,
            progress_callback
        )
        
        # Lancer la résolution
        start_time = time.time()
        status = solver.Solve(model, collector)
        elapsed_time = time.time() - start_time
        
        # Préparer les infos
        info = {
            'status': solver.StatusName(status),
            'num_solutions': len(collector.get_solutions()),
            'elapsed_time': elapsed_time,
            'num_branches': solver.NumBranches(),
            'wall_time': solver.WallTime()
        }
        
        return collector.get_solutions(), solver.StatusName(status), info
    
    def _build_model(
        self,
        participants: List[Participant],
        tournaments: List[Tournament]
    ) -> Tuple[cp_model.CpModel, Dict, Dict]:
        """
        Construit le modèle OR-Tools.
        
        Returns:
            Tuple (model, variables, auxiliary_variables)
        """
        model = cp_model.CpModel()
        
        # Variables principales: x[participant, tournament] = 1 si participe
        x = {}
        for participant in participants:
            for tournament in tournaments:
                x[(participant.nom, tournament.id)] = model.NewBoolVar(
                    f"x_{participant.nom}_{tournament.id}"
                )
        
        # Variables auxiliaires
        auxiliary_vars = {}
        
        # === CONTRAINTES ===
        
        # 1. Contrainte de couples (un seul du couple par jour)
        self._add_couple_constraints(model, x, participants, tournaments)
        
        # 2. Contrainte d'équipes (multiples de 3 ou incomplets autorisés)
        incomplete_penalties = self._add_team_constraints(
            model, x, participants, tournaments, auxiliary_vars
        )
        
        # 3. Contrainte de disponibilité
        self._add_availability_constraints(model, x, participants, tournaments)
        
        # 4. Contrainte de vœux
        self._add_wish_constraints(model, x, participants, tournaments)
        
        # === OBJECTIF ===
        
        # Calculer les variables pour l'objectif
        days_played = self._calculate_days_played(
            model, x, participants, tournaments, auxiliary_vars
        )
        
        # Calculer les écarts aux vœux
        wish_deviations = self._calculate_wish_deviations(
            model, days_played, participants, auxiliary_vars
        )
        
        # Calculer les pénalités de fatigue (>3 jours consécutifs)
        fatigue_penalties = self._calculate_fatigue_penalties(
            model, x, participants, tournaments, auxiliary_vars
        )
        
        # Fonction objectif multi-critères
        objective = (
            sum(wish_deviations) * self.config.weight_wishes +
            sum(fatigue_penalties) * self.config.weight_fatigue +
            sum(incomplete_penalties) * self.config.weight_incomplete
        )
        
        model.Minimize(objective)
        
        return model, x, auxiliary_vars
    
    def _add_couple_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict,
        participants: List[Participant],
        tournaments: List[Tournament]
    ):
        """Ajoute les contraintes de couples"""
        processed_pairs = set()
        
        for participant in participants:
            if not participant.couple:
                continue
            
            # Éviter de traiter deux fois le même couple
            pair = tuple(sorted([participant.nom, participant.couple]))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)
            
            # Pour chaque jour (0-8), un seul du couple peut jouer
            for day in range(9):
                # Trouver tous les tournois qui se jouent ce jour
                tournaments_this_day = [
                    t.id for t in tournaments
                    if day in t.days
                ]
                
                if tournaments_this_day:
                    # Au plus 1 des deux membres du couple peut jouer ce jour
                    model.Add(
                        sum(
                            x[(name, tid)]
                            for tid in tournaments_this_day
                            for name in pair
                            if (name, tid) in x
                        ) <= 1
                    )
    
    def _add_team_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict,
        participants: List[Participant],
        tournaments: List[Tournament],
        auxiliary_vars: Dict
    ) -> List:
        """Ajoute les contraintes d'équipes"""
        penalty_vars = []
        
        for tournament in tournaments:
            if tournament.is_etape:
                # Étapes: séparées par genre
                for genre in ['M', 'F']:
                    players = [
                        x[(p.nom, tournament.id)]
                        for p in participants
                        if p.genre == genre and (p.nom, tournament.id) in x
                    ]
                    
                    if not players:
                        continue
                    
                    num_teams = model.NewIntVar(
                        0, 20,
                        f"teams_{tournament.id}_{genre}"
                    )
                    remainder = model.NewIntVar(
                        0, TEAM_SIZE - 1,
                        f"remainder_{tournament.id}_{genre}"
                    )
                    
                    # Toujours autoriser les restes (sinon impossible avec peu de joueurs)
                    model.Add(sum(players) == num_teams * TEAM_SIZE + remainder)
                    
                    # Pénaliser seulement si config demande des équipes complètes
                    if not self.config.allow_incomplete:
                        # Pénalité forte pour les restes
                        penalty_vars.append(remainder * 100)
                    else:
                        # Pénalité légère
                        penalty_vars.append(remainder)
            
            else:  # Open (mixte)
                players = [
                    x[(p.nom, tournament.id)]
                    for p in participants
                    if (p.nom, tournament.id) in x
                ]
                
                if not players:
                    continue
                
                num_teams = model.NewIntVar(
                    0, 20,
                    f"teams_{tournament.id}"
                )
                remainder = model.NewIntVar(
                    0, TEAM_SIZE - 1,
                    f"remainder_{tournament.id}"
                )
                
                # Toujours autoriser les restes
                model.Add(sum(players) == num_teams * TEAM_SIZE + remainder)
                
                if not self.config.allow_incomplete:
                    penalty_vars.append(remainder * 100)
                else:
                    penalty_vars.append(remainder)
        
        return penalty_vars
    
    def _add_availability_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict,
        participants: List[Participant],
        tournaments: List[Tournament]
    ):
        """Ajoute les contraintes de disponibilité"""
        # Créer un ordre des tournois
        tournament_order = {t.id: idx for idx, t in enumerate(tournaments)}
        
        for participant in participants:
            max_tournament_idx = tournament_order.get(participant.dispo_jusqu_a)
            
            if max_tournament_idx is None:
                continue
            
            # Ne peut pas jouer après sa disponibilité
            for tournament in tournaments:
                if tournament_order[tournament.id] > max_tournament_idx:
                    if (participant.nom, tournament.id) in x:
                        model.Add(x[(participant.nom, tournament.id)] == 0)
    
    def _add_wish_constraints(
        self,
        model: cp_model.CpModel,
        x: Dict,
        participants: List[Participant],
        tournaments: List[Tournament]
    ):
        """Ajoute les contraintes de vœux"""
        for participant in participants:
            # Compter les étapes jouées
            etapes_played = sum(
                x[(participant.nom, t.id)]
                for t in tournaments
                if t.is_etape and (participant.nom, t.id) in x
            )
            
            # Compter les opens joués
            opens_played = sum(
                x[(participant.nom, t.id)]
                for t in tournaments
                if t.is_open and (participant.nom, t.id) in x
            )
            
            # Ne jamais dépasser les vœux
            model.Add(etapes_played <= participant.voeux_etape)
            model.Add(opens_played <= participant.voeux_open)
            
            # Si respect strict, égalité
            if participant.respect_voeux:
                model.Add(etapes_played == participant.voeux_etape)
                model.Add(opens_played == participant.voeux_open)
    
    def _calculate_days_played(
        self,
        model: cp_model.CpModel,
        x: Dict,
        participants: List[Participant],
        tournaments: List[Tournament],
        auxiliary_vars: Dict
    ) -> Dict[str, cp_model.IntVar]:
        """Calcule le nombre de jours joués par participant"""
        days_played = {}
        
        for participant in participants:
            # Pour chaque jour, vérifier si le participant joue
            day_vars = []
            
            for day in range(9):
                # Tournois qui se jouent ce jour
                tournaments_this_day = [
                    t.id for t in tournaments
                    if day in t.days
                ]
                
                if tournaments_this_day:
                    day_var = model.NewBoolVar(f"{participant.nom}_day_{day}")
                    
                    # day_var = 1 si au moins un tournoi ce jour
                    participations_this_day = [
                        x[(participant.nom, tid)]
                        for tid in tournaments_this_day
                        if (participant.nom, tid) in x
                    ]
                    
                    if participations_this_day:
                        model.Add(sum(participations_this_day) >= 1).OnlyEnforceIf(day_var)
                        model.Add(sum(participations_this_day) == 0).OnlyEnforceIf(day_var.Not())
                        day_vars.append(day_var)
            
            # Total de jours joués
            total_days = model.NewIntVar(0, 9, f"{participant.nom}_total_days")
            model.Add(total_days == sum(day_vars))
            
            days_played[participant.nom] = total_days
            auxiliary_vars[f"days_{participant.nom}"] = day_vars
        
        return days_played
    
    def _calculate_wish_deviations(
        self,
        model: cp_model.CpModel,
        days_played: Dict[str, cp_model.IntVar],
        participants: List[Participant],
        auxiliary_vars: Dict
    ) -> List[cp_model.IntVar]:
        """Calcule les écarts aux vœux pour chaque participant"""
        deviations = []
        
        for participant in participants:
            wished_days = participant.voeux_jours_total
            played_days = days_played[participant.nom]
            
            # Calculer l'écart (peut être négatif)
            deviation = model.NewIntVar(-9, 9, f"deviation_{participant.nom}")
            model.Add(deviation == played_days - wished_days)
            
            # Valeur absolue de l'écart
            abs_deviation = model.NewIntVar(0, 9, f"abs_deviation_{participant.nom}")
            model.AddAbsEquality(abs_deviation, deviation)
            
            deviations.append(abs_deviation)
            auxiliary_vars[f"deviation_{participant.nom}"] = deviation
            auxiliary_vars[f"abs_deviation_{participant.nom}"] = abs_deviation
        
        return deviations
    
    def _calculate_fatigue_penalties(
        self,
        model: cp_model.CpModel,
        x: Dict,
        participants: List[Participant],
        tournaments: List[Tournament],
        auxiliary_vars: Dict
    ) -> List[cp_model.IntVar]:
        """Calcule les pénalités pour fatigue (>3 jours consécutifs)"""
        penalties = []
        
        for participant in participants:
            # Récupérer les variables de jours
            day_vars = auxiliary_vars.get(f"days_{participant.nom}", [])
            
            if len(day_vars) < 4:
                continue
            
            # Pour chaque fenêtre de 4 jours consécutifs
            for start_day in range(len(day_vars) - 3):
                window_days = day_vars[start_day:start_day + 4]
                
                # Pénalité si les 4 jours sont joués
                penalty = model.NewBoolVar(
                    f"fatigue_{participant.nom}_{start_day}"
                )
                
                # penalty = 1 si tous les 4 jours sont joués
                model.Add(sum(window_days) == 4).OnlyEnforceIf(penalty)
                model.Add(sum(window_days) < 4).OnlyEnforceIf(penalty.Not())
                
                penalties.append(penalty)
        
        return penalties


def analyze_solutions(solutions: List[Solution]) -> Dict:
    """
    Analyse un ensemble de solutions.
    
    Args:
        solutions: Liste de solutions
        
    Returns:
        Statistiques agrégées
    """
    if not solutions:
        return {
            'total': 0,
            'perfect': 0,
            'one_violated': 0,
            'two_violated': 0,
            'three_plus_violated': 0,
            'avg_quality': 0.0
        }
    
    stats = {
        'total': len(solutions),
        'perfect': sum(1 for s in solutions if len(s.violated_wishes) == 0),
        'one_violated': sum(1 for s in solutions if len(s.violated_wishes) == 1),
        'two_violated': sum(1 for s in solutions if len(s.violated_wishes) == 2),
        'three_plus_violated': sum(1 for s in solutions if len(s.violated_wishes) >= 3),
        'avg_quality': sum(s.get_quality_score() for s in solutions) / len(solutions),
        'best_solution': max(solutions, key=lambda s: s.get_quality_score()),
        'max_consecutive_days': max(s.max_consecutive_days for s in solutions)
    }
    
    return stats
