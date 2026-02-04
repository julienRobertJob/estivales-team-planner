"""
Solver multi-passes avec assistant de résolution de conflits
"""
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import copy

from src.models import Participant, Tournament, Solution, SolverConfig
from src.solver import TournamentSolver, analyze_solutions


@dataclass
class RelaxationCandidate:
    """Candidat pour relaxer les contraintes"""
    participant_name: str
    current_wishes_etape: int
    current_wishes_open: int
    proposed_wishes_etape: int
    proposed_wishes_open: int
    impact_days_if_relaxed: int
    reason: str


@dataclass
class MultiPassResult:
    """Résultat d'une résolution multi-passes"""
    solutions: List[Solution]
    pass_number: int  # 1=strict, 2=relaxed, 3=forced_relaxation
    relaxed_participants: List[str]
    candidates_if_failed: List[RelaxationCandidate]
    status: str  # 'success', 'need_user_choice', 'impossible'
    message: str


class MultiPassSolver:
    """
    Solver en plusieurs passes pour gérer les conflits
    
    Algorithme:
    1. Pass 1: Essayer avec tous les vœux respectés
    2. Pass 2: Si échec, identifier automatiquement qui peut être lésé
    3. Pass 3: Proposer à l'utilisateur et résoudre avec choix
    """
    
    def __init__(self, config: SolverConfig):
        self.config = config
        self.base_solver = TournamentSolver(config)
    
    def solve_multipass(
        self,
        participants: List[Participant],
        tournaments: List[Tournament],
        progress_callback=None
    ) -> MultiPassResult:
        """
        Résout en plusieurs passes
        
        Args:
            participants: Liste des participants
            tournaments: Liste des tournois
            progress_callback: Callback pour la progression
            
        Returns:
            MultiPassResult avec solutions ou candidats à relaxer
        """
        
        # === PASS 1: Essayer strict ===
        if progress_callback:
            progress_callback("pass1", "Recherche solutions parfaites...")
        
        solutions, status, info = self.base_solver.solve(
            participants,
            tournaments,
            progress_callback=None  # Pas de callback interne pour l'instant
        )
        
        if solutions and len(solutions) > 0:
            # Vérifier combien sont parfaites
            perfect = [s for s in solutions if len(s.violated_wishes) == 0]
            
            if len(perfect) > 0:
                return MultiPassResult(
                    solutions=solutions,
                    pass_number=1,
                    relaxed_participants=[],
                    candidates_if_failed=[],
                    status='success',
                    message=f"✅ {len(perfect)} solution(s) parfaite(s) trouvée(s) (tous les vœux respectés)"
                )
        
        # === PASS 2: Identifier les candidats à léser ===
        if progress_callback:
            progress_callback("pass2", "Analyse des blocages...")
        
        candidates = self._identify_relaxation_candidates(
            participants,
            tournaments
        )
        
        if not candidates:
            return MultiPassResult(
                solutions=solutions if solutions else [],
                pass_number=2,
                relaxed_participants=[],
                candidates_if_failed=[],
                status='impossible' if not solutions else 'partial_success',
                message="❌ Impossible de trouver une solution même en relaxant les contraintes" if not solutions 
                        else f"⚠️ {len(solutions)} solutions trouvées mais avec des vœux non respectés"
            )
        
        # === PASS 3: Tester automatiquement les candidats ===
        if progress_callback:
            progress_callback("pass3", f"Test automatique avec {len(candidates)} candidat(s)...")
        
        # Essayer avec chaque candidat individuellement
        all_solutions = []
        tested_candidates = []
        
        for candidate in candidates:
            # Tester en lésant ce candidat (passer le candidat complet)
            result = self.solve_with_relaxation(
                participants,
                tournaments,
                [candidate],  # Passer le RelaxationCandidate complet
                progress_callback
            )
            
            if result.solutions:
                all_solutions.extend(result.solutions)
                tested_candidates.append(candidate.participant_name)
                # Ne pas tester tous si on a déjà assez de solutions
                if len(all_solutions) >= self.config.max_solutions:
                    break
        
        if all_solutions:
            # Dédupliquer les solutions (au cas où)
            unique_solutions = []
            seen_assignments = set()
            for sol in all_solutions:
                sol_key = str(sorted([(k, tuple(v.get('F', [])), tuple(v.get('M', []))) 
                                     for k, v in sol.assignments.items()]))
                if sol_key not in seen_assignments:
                    seen_assignments.add(sol_key)
                    unique_solutions.append(sol)
            
            return MultiPassResult(
                solutions=unique_solutions[:self.config.max_solutions],
                pass_number=3,
                relaxed_participants=tested_candidates,
                candidates_if_failed=candidates,  # TOUJOURS garder les candidats pour choix manuel
                status='success',
                message=f"✅ {len(unique_solutions)} solution(s) trouvée(s) en testant automatiquement les candidats"
            )
        
        # Si aucune solution trouvée même en testant automatiquement
        return MultiPassResult(
            solutions=solutions if solutions else [],
            pass_number=3,
            relaxed_participants=[],
            candidates_if_failed=candidates,
            status='need_user_choice',
            message=f"💡 Aucune solution automatique - {len(candidates)} participant(s) peuvent être lésés manuellement"
        )
    
    def solve_with_relaxation(
        self,
        participants: List[Participant],
        tournaments: List[Tournament],
        relax_candidates: List,  # List[RelaxationCandidate] ou List[str] pour rétrocompat
        progress_callback=None
    ) -> MultiPassResult:
        """
        Résout en relaxant les contraintes des participants sélectionnés
        
        IMPORTANT: Filtre pour garder SEULEMENT les solutions où les personnes
        sont effectivement lésées
        
        Args:
            participants: Liste des participants
            tournaments: Liste des tournois
            relax_candidates: Liste de RelaxationCandidate OU noms (str) pour compatibilité
            progress_callback: Callback pour progression
            
        Returns:
            MultiPassResult avec solutions
        """
        # Support des deux formats: RelaxationCandidate ou str (rétrocompatibilité)
        if relax_candidates and isinstance(relax_candidates[0], str):
            # Ancien format: liste de noms
            relax_names = relax_candidates
            relax_dict = {name: None for name in relax_names}  # Pas d'info sur comment léser
        else:
            # Nouveau format: liste de RelaxationCandidate
            relax_names = [c.participant_name for c in relax_candidates]
            relax_dict = {c.participant_name: c for c in relax_candidates}
        
        if progress_callback:
            progress_callback("pass3", f"Calcul avec {len(relax_names)} relaxation(s)...")
        
        # Sauvegarder les vœux originaux pour calculer les vraies violations
        original_wishes = {p.nom: (p.voeux_etape, p.voeux_open) for p in participants}
        
        # Créer une copie modifiée
        modified_participants = []
        for p in participants:
            p_copy = copy.copy(p)
            if p.nom in relax_names:
                candidate = relax_dict.get(p.nom)
                
                if candidate:
                    # Utiliser les vœux proposés du candidat (sait si open ou étape)
                    p_copy.voeux_etape = candidate.proposed_wishes_etape
                    p_copy.voeux_open = candidate.proposed_wishes_open
                else:
                    # Ancien comportement: réduire étape en priorité
                    if p_copy.voeux_etape > 0:
                        p_copy.voeux_etape -= 1
                    elif p_copy.voeux_open > 0:
                        p_copy.voeux_open -= 1
                
                # IMPORTANT: Activer respect_voeux pour FORCER ces nouveaux vœux
                p_copy.respect_voeux = True
            modified_participants.append(p_copy)
        
        # Résoudre avec relaxation
        solutions, status, info = self.base_solver.solve(
            modified_participants,
            tournaments,
            progress_callback=None
        )
        
        # RECALCULER TOUTES les stats avec les participants ORIGINAUX
        if solutions:
            for sol in solutions:
                # Remplacer les participants par les originaux
                sol.participants = participants
                # Recalculer TOUTES les stats avec les vœux originaux
                sol.calculate_stats()
            
            # Filtrer pour garder seulement celles où au moins un relax_name est lésé
            filtered_solutions = []
            for sol in solutions:
                # Vérifier si au moins une personne de relax_names est vraiment lésée
                is_valid = False
                for name in relax_names:
                    if name in sol.violated_wishes:
                        # Vérifier que c'est bien un déficit (pas un surplus)
                        stats = sol.get_participant_stats(name)
                        participant = next((p for p in participants if p.nom == name), None)
                        if participant:
                            deficit = participant.voeux_jours_total - stats['jours_joues']
                            if deficit > 0:  # Vraiment lésé
                                is_valid = True
                                break
                
                if is_valid:
                    filtered_solutions.append(sol)
            
            # Si aucune n'est vraiment lésée après recalcul, garder toutes quand même
            if not filtered_solutions:
                filtered_solutions = solutions
            
            return MultiPassResult(
                solutions=filtered_solutions,
                pass_number=3,
                relaxed_participants=relax_names,
                candidates_if_failed=[],
                status='success',
                message=f"✅ {len(filtered_solutions)} solution(s) trouvée(s) en lésant: {', '.join(relax_names)}"
            )
        else:
            return MultiPassResult(
                solutions=[],
                pass_number=3,
                relaxed_participants=relax_names,
                candidates_if_failed=[],
                status='impossible',
                message=f"❌ Aucune solution même avec relaxation de {', '.join(relax_names)}"
            )
    
    def _identify_relaxation_candidates(
        self,
        participants: List[Participant],
        tournaments: List[Tournament]
    ) -> List[RelaxationCandidate]:
        """
        Identifie les participants qu'on peut léser pour débloquer
        
        Stratégie AMÉLIORÉE:
        1. Pour chaque participant NON PROTÉGÉ (respect_voeux=False)
        2. Tester DEUX possibilités:
           a) Réduire 1 OPEN (impact: 1 jour) - PRIORITÉ
           b) Réduire 1 ÉTAPE (impact: 2 jours) - SECONDAIRE
        3. Trier par impact croissant (moins de jours lésés en premier)
        4. Retourner les candidats
        
        IMPORTANT: On ne teste JAMAIS les participants avec respect_voeux=True.
        Leurs vœux doivent être respectés strictement.
        """
        candidates = []
        
        # UNIQUEMENT les participants avec respect_voeux=False (non protégés)
        candidates_to_test = [
            p for p in participants
            if not p.respect_voeux and (p.voeux_etape > 0 or p.voeux_open > 0)
        ]
        
        # Pour chaque candidat, tester les DEUX possibilités
        for candidate in candidates_to_test:
            # Option 1: Réduire 1 OPEN (si possible) - IMPACT: 1 jour
            if candidate.voeux_open > 0:
                modified_participants = []
                for p in participants:
                    p_copy = copy.copy(p)
                    if p.nom == candidate.nom:
                        p_copy.voeux_open -= 1  # Réduire 1 open
                    modified_participants.append(p_copy)
                
                # Tester rapidement
                test_config = copy.copy(self.config)
                test_config.max_solutions = 1
                test_config.timeout_seconds = 5.0
                
                test_solver = TournamentSolver(test_config)
                solutions, status, info = test_solver.solve(modified_participants, tournaments)
                
                if solutions and len(solutions) > 0:
                    candidates.append(RelaxationCandidate(
                        participant_name=candidate.nom,
                        current_wishes_etape=candidate.voeux_etape,
                        current_wishes_open=candidate.voeux_open,
                        proposed_wishes_etape=candidate.voeux_etape,
                        proposed_wishes_open=candidate.voeux_open - 1,
                        impact_days_if_relaxed=1,  # 1 jour lésé
                        reason=f"Réduire 1 open ({candidate.voeux_open}→{candidate.voeux_open-1})"
                    ))
            
            # Option 2: Réduire 1 ÉTAPE (si possible) - IMPACT: 2 jours
            if candidate.voeux_etape > 0:
                modified_participants = []
                for p in participants:
                    p_copy = copy.copy(p)
                    if p.nom == candidate.nom:
                        p_copy.voeux_etape -= 1  # Réduire 1 étape
                    modified_participants.append(p_copy)
                
                # Tester rapidement
                test_config = copy.copy(self.config)
                test_config.max_solutions = 1
                test_config.timeout_seconds = 5.0
                
                test_solver = TournamentSolver(test_config)
                solutions, status, info = test_solver.solve(modified_participants, tournaments)
                
                if solutions and len(solutions) > 0:
                    candidates.append(RelaxationCandidate(
                        participant_name=candidate.nom,
                        current_wishes_etape=candidate.voeux_etape,
                        current_wishes_open=candidate.voeux_open,
                        proposed_wishes_etape=candidate.voeux_etape - 1,
                        proposed_wishes_open=candidate.voeux_open,
                        impact_days_if_relaxed=2,  # 2 jours lésés
                        reason=f"Réduire 1 étape ({candidate.voeux_etape}→{candidate.voeux_etape-1})"
                    ))
        
        # TRIER par impact CROISSANT (opens en premier, étapes ensuite)
        # Puis par nom pour déterminisme
        candidates.sort(key=lambda c: (c.impact_days_if_relaxed, c.participant_name))
        
        return candidates


class ConflictAnalyzer:
    """Analyse les conflits et propose des solutions"""
    
    @staticmethod
    def analyze_why_no_solution(
        participants: List[Participant],
        tournaments: List[Tournament],
        config: SolverConfig
    ) -> Dict[str, any]:
        """
        Analyse pourquoi aucune solution n'a été trouvée
        
        Returns:
            Dict avec diagnostics et suggestions
        """
        diagnostics = {
            'issues': [],
            'suggestions': [],
            'severity': 'unknown'
        }
        
        # 1. Vérifier les vœux stricts vs ressources
        strict_participants = [p for p in participants if p.respect_voeux]
        
        if len(strict_participants) > len(participants) * 0.7:
            diagnostics['issues'].append(
                f"Trop de contraintes strictes: {len(strict_participants)}/{len(participants)} participants"
            )
            diagnostics['suggestions'].append(
                "Décocher 'Respect_Voeux' pour certains participants (garder <50%)"
            )
            diagnostics['severity'] = 'high'
        
        # 2. Vérifier la demande totale vs places disponibles
        etapes = [t for t in tournaments if t.is_etape]
        opens = [t for t in tournaments if t.is_open]
        
        total_etape_wishes = sum(p.voeux_etape for p in participants)
        total_open_wishes = sum(p.voeux_open for p in participants)
        
        # Estimation grossière des places
        max_etape_slots = len(etapes) * 10  # Arbitraire
        max_open_slots = len(opens) * 10
        
        if total_etape_wishes > max_etape_slots:
            diagnostics['issues'].append(
                f"Trop de demandes d'étapes: {total_etape_wishes} demandées, ~{max_etape_slots} places"
            )
            diagnostics['suggestions'].append(
                "Réduire les vœux d'étapes ou inclure plus de tournois"
            )
            diagnostics['severity'] = 'critical'
        
        if total_open_wishes > max_open_slots:
            diagnostics['issues'].append(
                f"Trop de demandes d'opens: {total_open_wishes} demandées, ~{max_open_slots} places"
            )
        
        # 3. Vérifier les couples avec vœux incompatibles
        participants_map = {p.nom: p for p in participants}
        
        for p in participants:
            if p.couple:
                partner = participants_map.get(p.couple)
                if partner:
                    combined_wishes = (p.voeux_etape + partner.voeux_etape) * 2 + (p.voeux_open + partner.voeux_open)
                    
                    # Si le couple veut beaucoup jouer mais ne peut pas le même jour
                    if combined_wishes > 12:  # Plus de 12 jours combinés
                        diagnostics['issues'].append(
                            f"Couple {p.nom}/{partner.nom} veut {combined_wishes}j combinés "
                            f"mais ne peut jouer ensemble"
                        )
                        diagnostics['suggestions'].append(
                            f"Réduire les vœux de {p.nom} ou {partner.nom}"
                        )
        
        # 4. Vérifier si équipes incomplètes et multiples de 3 par genre
        if not config.allow_incomplete:
            # Analyser par étape et par genre
            etapes = [t for t in tournaments if t.is_etape]
            
            for genre in ['M', 'F']:
                participants_genre = [p for p in participants if p.genre == genre]
                # Compter combien ont des vœux étape >= 1 (veulent jouer des étapes)
                nb_wants_etape = sum(1 for p in participants_genre if p.voeux_etape >= 1)
                
                if nb_wants_etape > 0 and nb_wants_etape % 3 != 0:
                    diagnostics['issues'].append(
                        f"🚫 BLOCAGE CRITIQUE: {nb_wants_etape} {genre} veulent jouer des étapes, "
                        f"mais {nb_wants_etape} n'est pas un multiple de 3"
                    )
                    diagnostics['suggestions'].append(
                        f"✅ Solution 1 (RECOMMANDÉE): Activer 'Autoriser équipes incomplètes'"
                    )
                    
                    # Calculer le nombre optimal
                    lower_multiple = (nb_wants_etape // 3) * 3
                    upper_multiple = ((nb_wants_etape // 3) + 1) * 3
                    
                    diagnostics['suggestions'].append(
                        f"✅ Solution 2: Ajuster à {lower_multiple} ou {upper_multiple} {genre} "
                        f"({abs(nb_wants_etape - lower_multiple)} ou {abs(upper_multiple - nb_wants_etape)} personnes à modifier)"
                    )
                    
                    if lower_multiple > 0:
                        nb_to_remove = nb_wants_etape - lower_multiple
                        diagnostics['suggestions'].append(
                            f"✅ Solution 3: {nb_to_remove} {genre} ne jouent AUCUNE étape (mettre vœux_etape = 0)"
                        )
                    
                    diagnostics['severity'] = 'critical'
            
            # Vérifier aussi globalement si pas encore de problème détecté
            if diagnostics['severity'] == 'unknown':
                nb_participants = len(participants)
                if nb_participants % 3 != 0:
                    diagnostics['issues'].append(
                        f"Nombre total de participants ({nb_participants}) n'est pas multiple de 3"
                    )
                    diagnostics['suggestions'].append(
                        "Activer 'Autoriser équipes incomplètes'"
                    )
                    diagnostics['severity'] = 'high'
        
        return diagnostics


def format_diagnostic_message(diagnostics: Dict[str, any]) -> str:
    """Formate le diagnostic en message lisible"""
    
    if not diagnostics['issues']:
        return "Aucun problème détecté (mais solution impossible quand même)"
    
    message = "🔍 **Diagnostic des Blocages:**\n\n"
    
    for i, issue in enumerate(diagnostics['issues'], 1):
        message += f"{i}. ❌ {issue}\n"
    
    message += "\n💡 **Suggestions:**\n\n"
    
    for i, suggestion in enumerate(diagnostics['suggestions'], 1):
        message += f"{i}. ✅ {suggestion}\n"
    
    # Indicateur de sévérité
    severity_emoji = {
        'critical': '🚨',
        'high': '⚠️',
        'medium': '⚡',
        'low': 'ℹ️',
        'unknown': '❓'
    }
    
    emoji = severity_emoji.get(diagnostics['severity'], '❓')
    message += f"\n{emoji} Sévérité: **{diagnostics['severity'].upper()}**"
    
    return message
