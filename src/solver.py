"""
Solver OR-Tools pour l'optimisation des plannings
"""
from typing import List, Dict, Tuple, Optional
from ortools.sat.python import cp_model
import time

from src.models import Participant, Tournament, Solution, SolverConfig
from src.constants import TEAM_SIZE, MAX_CONSECUTIVE_DAYS


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    """Collecte les solutions trouvées par OR-Tools
    
    Modes de fonctionnement:
    - mode='all': Collecte toutes les solutions (ancien comportement)
    - mode='unique_profiles': Ne garde que la meilleure variante de chaque profil unique
    """
    
    def __init__(
        self,
        variables: Dict,
        tournaments: List[Tournament],
        participants: List[Participant],
        limit: int,
        progress_callback=None,
        mode: str = 'unique_profiles',
        min_quality_score: int = 0
    ):
        super().__init__()
        self._variables = variables
        self._tournaments = tournaments
        self._participants = participants
        self._solution_limit = limit
        self._solutions = []
        self._progress_callback = progress_callback
        self._start_time = time.time()
        self._mode = mode
        self._min_quality_score = min_quality_score
        
        # Pour mode 'unique_profiles': tracker profils et leurs meilleures solutions
        self._profile_signatures = {}  # signature -> (solution, objective_value)
        self._solutions_count = 0  # Compte total de solutions rencontrées
        self._solutions_rejected_score = 0  # Compte solutions rejetées pour score
    
    def _compute_profile_signature(self, solution) -> str:
        """Calcule une signature unique pour identifier un profil de lésés
        
        Signature = liste triée des (nom, écart) pour les participants lésés
        Ex: "Hugo:-4" ou "Julien:-1,Rémy:-1,Sophie:-1,Sylvain:-1"
        """
        violated = []
        for p in self._participants:
            stats = solution.get_participant_stats(p.nom)
            ecart = stats['ecart']
            if ecart < 0:  # Participant lésé
                violated.append(f"{p.nom}:{ecart}")
        
        # Trier pour avoir une signature canonique
        violated.sort()
        return ",".join(violated) if violated else "PERFECT"
    
    def _compute_objective_value(self, solution) -> int:
        """Calcule la valeur d'objectif OR-Tools pour une solution
        
        Reproduit la fonction objectif de _build_model:
        - max_shortage * 100000 (priorité absolue)
        - total_shortage * 1000
        - fatigue_penalties * 500
        - incomplete_penalties * 10
        - distribution_penalties * 1
        """
        # Max shortage (critère dominant)
        max_shortage = max(
            (abs(solution.get_participant_stats(p.nom)['ecart']) 
             for p in self._participants if solution.get_participant_stats(p.nom)['ecart'] < 0),
            default=0
        )
        
        # Total shortage
        total_shortage = sum(
            abs(solution.get_participant_stats(p.nom)['ecart'])
            for p in self._participants
            if solution.get_participant_stats(p.nom)['ecart'] < 0
        )
        
        # Fatigue (calculée à partir de max_consecutive_days)
        # Pénalité : si >3j consécutifs, (jours - 3) au carré
        fatigue = 0
        for p in self._participants:
            stats = solution.get_participant_stats(p.nom)
            max_cons = stats.get('max_consecutifs', 0)
            if max_cons > 3:
                fatigue += (max_cons - 3) ** 2
        
        # Équipes incomplètes (approximation)
        incomplete = 0
        for t in self._tournaments:
            tournament_data = solution.assignments.get(t.id, {})
            if t.is_etape:
                # Vérifier séparément M et F
                for genre in ['M', 'F']:
                    players = tournament_data.get(genre, [])
                    if len(players) > 0 and len(players) % 3 != 0:
                        incomplete += 1
            else:
                # Open : tous ensemble
                players = tournament_data.get('All', [])
                if len(players) > 0 and len(players) % 3 != 0:
                    incomplete += 1
        
        # Distribution (variance des écarts - approximation simple)
        ecarts = [abs(solution.get_participant_stats(p.nom)['ecart']) 
                 for p in self._participants]
        distribution = sum(ecarts)  # Simplification
        
        # Calcul final (même pondération que dans _build_model)
        objective = (max_shortage * 100000 + 
                    total_shortage * 1000 + 
                    fatigue * 500 + 
                    incomplete * 10 + 
                    distribution * 1)
        
        return objective
    
    def on_solution_callback(self):
        """Appelé à chaque solution trouvée"""
        self._solutions_count += 1
        
        # Vérifier la limite TOTALE de solutions rencontrées (pas juste gardées)
        if self._solution_limit and self._solutions_count >= self._solution_limit:
            self.StopSearch()
            return
        
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
        
        # NOTE IMPORTANTE: On ne filtre PAS par score qualité ici !
        # Le score qualité (0-100) est différent de l'objectif OR-Tools.
        # Le filtrage par score se fait APRÈS dans app.py pour ne pas
        # manquer des solutions que OR-Tools considère optimales.
        # Exemple: une solution avec score 70 peut avoir un max_shortage
        # plus élevé qu'une solution score 69, donc OR-Tools la rejette,
        # mais pour l'utilisateur elle est meilleure !
        
        # Traitement selon le mode
        if self._mode == 'all':
            # Mode classique: garder toutes les solutions
            self._solutions.append(solution)
        
        elif self._mode == 'unique_profiles':
            # Mode profils uniques: ne garder que la meilleure de chaque profil
            signature = self._compute_profile_signature(solution)
            objective = self._compute_objective_value(solution)
            
            if signature not in self._profile_signatures:
                # Nouveau profil découvert
                self._profile_signatures[signature] = (solution, objective)
            else:
                # Profil déjà connu: garder le meilleur
                prev_solution, prev_objective = self._profile_signatures[signature]
                if objective < prev_objective:  # Meilleur score (minimisation)
                    self._profile_signatures[signature] = (solution, objective)
        
        # Notifier la progression
        if self._progress_callback:
            elapsed = time.time() - self._start_time
            if self._mode == 'unique_profiles':
                current = len(self._profile_signatures)
            else:
                current = len(self._solutions)
            
            self._progress_callback(
                current,
                self._solution_limit if self._solution_limit else current,
                elapsed
            )
    
    def get_solutions(self) -> List[Solution]:
        """Retourne les solutions collectées, triées par score qualité"""
        if self._mode == 'unique_profiles':
            # Extraire les solutions des profils uniques
            profile_solutions = [
                (sig, sol, obj) 
                for sig, (sol, obj) in self._profile_signatures.items()
            ]
            # Trier par SCORE QUALITÉ (meilleur d'abord)
            # Note: Le score est maintenant aligné sur l'objectif OR-Tools
            profile_solutions.sort(key=lambda x: -x[1].get_quality_score())
            return [sol for _, sol, _ in profile_solutions]
        else:
            # Mode 'all': trier aussi par score qualité
            return sorted(self._solutions, key=lambda s: -s.get_quality_score())
    
    def get_profile_count(self) -> int:
        """Retourne le nombre de profils uniques trouvés"""
        if self._mode == 'unique_profiles':
            return len(self._profile_signatures)
        return len(self._solutions)


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
        Résout le problème en 2 PASSES pour trouver TOUTES les solutions optimales.
        
        PASS 1: Trouve le score optimal (optimisation)
        PASS 2: Énumère TOUTES les solutions ayant ce score (satisfaction)
        
        Args:
            participants: Liste des participants
            tournaments: Liste des tournois actifs
            progress_callback: Fonction appelée pour la progression (current, total, time)
            
        Returns:
            Tuple (solutions, status, info)
        """
        start_time = time.time()
        
        # ================================================================
        # PASS 1: TROUVER LE SCORE OPTIMAL
        # ================================================================
        if progress_callback:
            progress_callback(0, 1, 0)
        
        model_pass1, variables_pass1, auxiliary_vars_pass1 = self._build_model(
            participants, tournaments
        )
        
        solver_pass1 = cp_model.CpSolver()
        solver_pass1.parameters.max_time_in_seconds = min(30.0, self.config.timeout_seconds / 3)
        solver_pass1.parameters.log_search_progress = False
        solver_pass1.parameters.num_search_workers = 8
        
        # Paramètres pour exploration plus large et meilleure optimisation
        solver_pass1.parameters.linearization_level = 0
        solver_pass1.parameters.cp_model_presolve = True
        solver_pass1.parameters.cp_model_probing_level = 2
        
        # Stratégies de recherche pour éviter les blocages locaux
        solver_pass1.parameters.search_branching = cp_model.FIXED_SEARCH
        solver_pass1.parameters.optimize_with_core = True  # Utilise le core pour l'optimisation
        
        # Pas de hints restrictifs - laisser le solver explorer librement
        # (on retire les hints qui forçaient 50% de non-participation)
        
        status_pass1 = solver_pass1.Solve(model_pass1)
        
        if status_pass1 not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            # Pas de solution trouvée
            elapsed = time.time() - start_time
            
            # Message plus détaillé selon le statut
            status_name = solver_pass1.StatusName(status_pass1)
            if status_pass1 == cp_model.INFEASIBLE:
                status_name = "INFEASIBLE - Le modèle n'a aucune solution valide. " \
                              "Vérifiez : équipes incomplètes, nombre de participants, vœux stricts."
            elif status_pass1 == cp_model.MODEL_INVALID:
                status_name = "MODEL_INVALID - Le modèle contient des erreurs"
            
            return [], status_name, {
                'status': status_name,
                'num_solutions': 0,
                'elapsed_time': elapsed,
                'num_branches': solver_pass1.NumBranches(),
                'wall_time': solver_pass1.WallTime(),
                'num_conflicts': solver_pass1.NumConflicts(),
                'pass': 1
            }
        
        # Récupérer le score optimal trouvé
        optimal_score = int(solver_pass1.ObjectiveValue())
        
        # EXTRAIRE la valeur optimale du CRITÈRE DOMINANT : lésion max individuelle
        # C'est le SEUL critère qu'on va contraindre en PASS 2
        # pour trouver TOUS les profils possibles ayant ce même max
        
        optimal_max_shortage = int(solver_pass1.Value(auxiliary_vars_pass1.get("max_shortage", 0)))
        
        # ================================================================
        # PASS 2: ÉNUMÉRER TOUTES LES SOLUTIONS AVEC CE MAX_SHORTAGE
        # ================================================================
        if progress_callback:
            elapsed = time.time() - start_time
            progress_callback(1, 2, elapsed)
        
        # Reconstruire le modèle pour énumération avec SEULE contrainte : max_shortage
        model_pass2, variables_pass2, auxiliary_vars_pass2 = self._build_model_for_enumeration(
            participants, tournaments, optimal_max_shortage
        )
        
        # Collecter les solutions selon le mode configuré
        collector = SolutionCollector(
            variables_pass2,
            tournaments,
            participants,
            self.config.max_solutions,
            progress_callback,
            mode=self.config.search_mode,
            min_quality_score=self.config.min_quality_score
        )
        
        solver_pass2 = cp_model.CpSolver()
        remaining_time = self.config.timeout_seconds - (time.time() - start_time)
        solver_pass2.parameters.max_time_in_seconds = max(10.0, remaining_time)
        solver_pass2.parameters.log_search_progress = False
        
        # CLEF: Maintenant qu'on n'a PAS d'objectif à minimiser,
        # on peut utiliser SearchForAllSolutions !
        status_pass2 = solver_pass2.SearchForAllSolutions(model_pass2, collector)
        
        elapsed_time = time.time() - start_time
        
        # Préparer les infos
        info = {
            'status': solver_pass2.StatusName(status_pass2),
            'num_solutions': len(collector.get_solutions()),
            'elapsed_time': elapsed_time,
            'num_branches': solver_pass1.NumBranches() + solver_pass2.NumBranches(),
            'wall_time': solver_pass1.WallTime() + solver_pass2.WallTime(),
            'optimal_score': optimal_score,
            'pass': 2
        }
        
        if progress_callback:
            progress_callback(len(collector.get_solutions()), len(collector.get_solutions()), elapsed_time)
        
        return collector.get_solutions(), solver_pass2.StatusName(status_pass2), info
    
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
        # Calculer les écarts aux vœux (shortage brut pour critère principal)
        wish_deviations = self._calculate_wish_deviations(
            model, days_played, participants, auxiliary_vars
        )
        
        # Calculer les pénalités de fatigue (>3 jours consécutifs)
        fatigue_penalties = self._calculate_fatigue_penalties(
            model, x, participants, tournaments, auxiliary_vars
        )
        
        # CRITÈRE SECONDAIRE : Distribution (qui est lésé)
        # Récupérer les pénalités de distribution calculées
        distribution_penalties = [
            auxiliary_vars[f"distribution_penalty_{p.nom}"]
            for p in participants
            if f"distribution_penalty_{p.nom}" in auxiliary_vars
        ]
        
        # CRITÈRE PRINCIPAL : Lésion maximale individuelle
        max_shortage = auxiliary_vars.get("max_shortage", 0)
        
        # Fonction objectif multi-critères HIÉRARCHIQUES
        # Poids: 100000 (max lésion) >> 1000 (total lésé) >> 500 (fatigue) >> 10 (incomplet) >> 1 (distribution)
        objective = (
            max_shortage * 100000 +                                      # 100000 - ÉVITER GROSSE LÉSION
            sum(wish_deviations) * self.config.weight_wishes +           # 1000 - TOTAL LÉSÉ
            sum(fatigue_penalties) * self.config.weight_fatigue +        # 500
            sum(incomplete_penalties) * self.config.weight_incomplete +  # 10
            sum(distribution_penalties) * 1                              # 1 - départage à égalité
        )
        
        model.Minimize(objective)
        
        return model, x, auxiliary_vars
    
    def _build_model_for_enumeration(
        self,
        participants: List[Participant],
        tournaments: List[Tournament],
        target_max_shortage: int
    ) -> Tuple[cp_model.CpModel, Dict, Dict]:
        """
        Construit un modèle de SATISFACTION (sans objectif à minimiser)
        pour énumérer toutes les solutions ayant le même critère principal.
        
        STRATÉGIE v2.2.4 : On contraint SEULEMENT le critère dominant
        - Lésion maximale individuelle = target_max_shortage
        
        On IGNORE le total et la distribution pour obtenir TOUS les profils possibles.
        
        Cette méthode est utilisée en PASS 2 après avoir trouvé la valeur optimale.
        
        Args:
            participants: Liste des participants
            tournaments: Liste des tournois
            target_max_shortage: Lésion maximale individuelle optimale (critère unique)
            
        Returns:
            Tuple (model, variables, auxiliary_vars)
        """
        model = cp_model.CpModel()
        
        # === VARIABLES ===
        # Variables principales: x[participant, tournament] = 1 si participe
        x = {}
        for participant in participants:
            for tournament in tournaments:
                x[(participant.nom, tournament.id)] = model.NewBoolVar(
                    f"x_{participant.nom}_{tournament.id}"
                )
        
        # Variables auxiliaires
        auxiliary_vars = {}
        
        # === CONTRAINTES (MÊMES QUE PASS 1) ===
        
        # 1. Contrainte de couples
        self._add_couple_constraints(model, x, participants, tournaments)
        
        # 2. Contrainte d'équipes
        incomplete_penalties = self._add_team_constraints(
            model, x, participants, tournaments, auxiliary_vars
        )
        
        # 3. Contrainte de disponibilité
        self._add_availability_constraints(model, x, participants, tournaments)
        
        # 4. Contrainte de vœux (ne jamais dépasser + strict si demandé)
        self._add_wish_constraints(model, x, participants, tournaments)
        # 5. Calculer les jours joués
        days_played = self._calculate_days_played(
            model, x, participants, tournaments, auxiliary_vars
        )
        
        # 6. Calculer les écarts aux vœux (pour contrainte de score)
        wish_deviations = self._calculate_wish_deviations(
            model, days_played, participants, auxiliary_vars
        )
        
        # 7. Calculer les pénalités de fatigue
        fatigue_penalties = self._calculate_fatigue_penalties(
            model, x, participants, tournaments, auxiliary_vars
        )
        
        # 8. Récupérer la lésion max et les shortages individuels
        max_shortage = auxiliary_vars.get("max_shortage", 0)
        
        # Calculer le total des shortages
        total_shortage = model.NewIntVar(0, 9 * len(participants), "total_shortage")
        model.Add(total_shortage == sum(wish_deviations))
        
        # === CONTRAINTES DES CRITÈRES PRINCIPAUX SEULEMENT ===
        # CORRECTION v2.2.4 : On contraint SEULEMENT le critère dominant (max_shortage)
        # pour trouver TOUS les profils de lésés possibles
        
        # CONTRAINTE #1 : Lésion maximale individuelle (SEULE contrainte !)
        model.Add(max_shortage == target_max_shortage)
        
        # CONTRAINTE #2 RETIRÉE : Total de jours lésés
        # ANCIEN: model.Add(total_shortage == target_total_shortage)
        # NOUVEAU: On NE contraint PAS le total, seulement le max
        # 
        # Pourquoi ? Pour trouver TOUS les profils possibles :
        # - Avec max=4 : Hugo -4j (total=4) OU 4 personnes -1j (total=4) OU autres combinaisons
        # - Sans cette contrainte, on explore toutes les distributions ayant le même max
        
        # NOTE : On NE contraint PAS non plus distribution_penalties ni fatigue_penalties
        # Cela permet d'énumérer TOUS les profils de lésés différents
        
        # PAS de model.Minimize() ici ! C'est maintenant un problème de satisfaction.
        
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
                    
                    # Contrainte d'équipes
                    model.Add(sum(players) == num_teams * TEAM_SIZE + remainder)
                    
                    if not self.config.allow_incomplete:
                        # FORCER remainder = 0 (équipes complètes obligatoires)
                        model.Add(remainder == 0)
                    else:
                        # Pénaliser légèrement les restes
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
                
                # Contrainte d'équipes
                model.Add(sum(players) == num_teams * TEAM_SIZE + remainder)
                
                if not self.config.allow_incomplete:
                    # FORCER remainder = 0 (équipes complètes obligatoires)
                    model.Add(remainder == 0)
                else:
                    # Pénaliser légèrement les restes
                    penalty_vars.append(remainder)
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
        """
        Calcule les écarts aux vœux pour chaque participant.
        
        STRATÉGIE CORRIGÉE (v2.2.3):
        1. CRITÈRE PRINCIPAL : Minimiser la LÉSION MAXIMALE INDIVIDUELLE
        2. CRITÈRE SECONDAIRE : Minimiser le TOTAL des jours lésés
        3. CRITÈRE TERTIAIRE : À égalité, favoriser léser les gros demandeurs
        
        On retourne shortage NON pondéré pour le critère secondaire.
        Le critère principal (max) et tertiaire (distribution) seront dans l'objectif.
        
        Exemples attendus :
        - 1 pers -3j vs 3 pers -1j → on PRÉFÈRE le second (éviter grosse lésion)
        - À total égal, 2j répartis sur 2 pers > 2j sur 1 pers
        - À égalité, léser qq qui demande 5j > léser qq qui demande 2j
        """
        deviations = []
        
        # Variable pour la lésion maximale individuelle (CRITÈRE PRINCIPAL)
        max_shortage = model.NewIntVar(0, 9, "max_shortage")
        
        for participant in participants:
            wished_days = participant.voeux_jours_total
            played_days = days_played[participant.nom]
            
            # Calculer l'écart (peut être négatif)
            deviation = model.NewIntVar(-9, 9, f"deviation_{participant.nom}")
            model.Add(deviation == played_days - wished_days)
            
            # shortage = max(0, -deviation) = nombre de jours en moins
            shortage = model.NewIntVar(0, 9, f"shortage_{participant.nom}")
            model.AddMaxEquality(shortage, [0, -deviation])
            
            # CRITÈRE PRINCIPAL : mettre à jour le max
            model.Add(max_shortage >= shortage)
            
            # CRITÈRE SECONDAIRE : shortage brut (non pondéré)
            deviations.append(shortage)
            
            # CRITÈRE TERTIAIRE : pondération pour départager à égalité
            # Plus tu demandes, moins c'est grave d'être lésé
            # poids = max(1, 6 - demandes)
            weight = max(1, 6 - wished_days)
            
            # Pénalité de distribution (utilisée avec poids faible dans objectif)
            distribution_penalty = model.NewIntVar(0, 9 * weight, f"distrib_{participant.nom}")
            model.AddMultiplicationEquality(distribution_penalty, [shortage, weight])
            
            # Stocker pour utilisation dans l'objectif
            auxiliary_vars[f"deviation_{participant.nom}"] = deviation
            auxiliary_vars[f"shortage_{participant.nom}"] = shortage
            auxiliary_vars[f"weight_{participant.nom}"] = weight
            auxiliary_vars[f"distribution_penalty_{participant.nom}"] = distribution_penalty
        
        # Stocker la lésion maximale
        auxiliary_vars["max_shortage"] = max_shortage
        
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


    def explore_profile_in_depth(
        self,
        participants: List[Participant],
        tournaments: List[Tournament],
        target_profile: Dict[str, int],
        progress_callback=None
    ) -> Tuple[List[Solution], str, Dict]:
        """
        Explore en profondeur TOUTES les variantes d'un profil spécifique.
        
        Args:
            participants: Liste des participants
            tournaments: Liste des tournois actifs
            target_profile: Dict {nom: écart_voulu} pour le profil cible
                           Ex: {"Julien": -1, "Rémy": -1, "Sophie": -1, "Sylvain": -1}
            progress_callback: Fonction appelée pour la progression
            
        Returns:
            Tuple (solutions, status, info)
        """
        start_time = time.time()
        
        if progress_callback:
            progress_callback(0, 1, 0)
        
        # Construire le modèle avec contraintes dures pour forcer le profil
        model, variables, auxiliary_vars = self._build_model_for_profile(
            participants, tournaments, target_profile
        )
        
        # Collecter TOUTES les variantes de ce profil
        collector = SolutionCollector(
            variables,
            tournaments,
            participants,
            self.config.max_solutions,
            progress_callback,
            mode='all'  # Mode exhaustif: toutes les variantes
        )
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.timeout_seconds
        solver.parameters.log_search_progress = False
        solver.parameters.num_search_workers = 8
        
        # Énumérer TOUTES les solutions
        status = solver.SearchForAllSolutions(model, collector)
        
        elapsed_time = time.time() - start_time
        
        info = {
            'status': solver.StatusName(status),
            'num_solutions': len(collector.get_solutions()),
            'elapsed_time': elapsed_time,
            'num_branches': solver.NumBranches(),
            'wall_time': solver.WallTime(),
            'mode': 'profile_depth_exploration'
        }
        
        if progress_callback:
            progress_callback(
                len(collector.get_solutions()), 
                len(collector.get_solutions()), 
                elapsed_time
            )
        
        return collector.get_solutions(), solver.StatusName(status), info
    
    def _build_model_for_profile(
        self,
        participants: List[Participant],
        tournaments: List[Tournament],
        target_profile: Dict[str, int]
    ) -> Tuple[cp_model.CpModel, Dict, Dict]:
        """
        Construit un modèle OR-Tools avec contraintes DURES pour un profil spécifique.
        
        Le profil fixe exactement combien de jours chaque participant doit jouer.
        
        Args:
            participants: Liste des participants
            tournaments: Liste des tournois
            target_profile: Dict {nom: écart} - ex: {"Julien": -1} = joue 1j de moins
            
        Returns:
            Tuple (model, variables, auxiliary_vars)
        """
        model = cp_model.CpModel()
        
        # Variables principales
        x = {}
        for participant in participants:
            for tournament in tournaments:
                x[(participant.nom, tournament.id)] = model.NewBoolVar(
                    f"x_{participant.nom}_{tournament.id}"
                )
        
        auxiliary_vars = {}
        
        # === CONTRAINTES NORMALES ===
        self._add_couple_constraints(model, x, participants, tournaments)
        self._add_team_constraints(model, x, participants, tournaments, auxiliary_vars)
        self._add_availability_constraints(model, x, participants, tournaments)
        
        # === CONTRAINTES DURES POUR LE PROFIL ===
        days_played = self._calculate_days_played(
            model, x, participants, tournaments, auxiliary_vars
        )
        
        for participant in participants:
            total_voeux = participant.voeux_etape + participant.voeux_open
            
            if participant.nom in target_profile:
                # Ce participant fait partie du profil: contrainte DURE
                ecart = target_profile[participant.nom]
                jours_cibles = total_voeux + ecart  # Ex: 6 + (-1) = 5
                model.Add(days_played[participant.nom] == jours_cibles)
            else:
                # Participant pas dans le profil: doit respecter exactement ses vœux
                model.Add(days_played[participant.nom] == total_voeux)
        
        return model, x, auxiliary_vars

