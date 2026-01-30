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
        
        # Proposer les candidats
        return MultiPassResult(
            solutions=solutions if solutions else [],
            pass_number=2,
            relaxed_participants=[],
            candidates_if_failed=candidates,
            status='need_user_choice',
            message=f"💡 {len(candidates)} participant(s) peuvent être lésés pour débloquer la situation"
        )
    
    def solve_with_relaxation(
        self,
        participants: List[Participant],
        tournaments: List[Tournament],
        relax_names: List[str],
        progress_callback=None
    ) -> MultiPassResult:
        """
        Résout en relaxant les contraintes des participants sélectionnés
        
        Args:
            participants: Liste des participants
            tournaments: Liste des tournois
            relax_names: Noms des participants à léser
            progress_callback: Callback pour progression
            
        Returns:
            MultiPassResult avec solutions
        """
        if progress_callback:
            progress_callback("pass3", f"Calcul avec {len(relax_names)} relaxation(s)...")
        
        # Créer une copie modifiée
        modified_participants = []
        for p in participants:
            p_copy = copy.copy(p)
            if p.nom in relax_names:
                # Relâcher la contrainte stricte
                p_copy.respect_voeux = False
            modified_participants.append(p_copy)
        
        # Résoudre avec relaxation
        solutions, status, info = self.base_solver.solve(
            modified_participants,
            tournaments,
            progress_callback=None
        )
        
        if solutions and len(solutions) > 0:
            return MultiPassResult(
                solutions=solutions,
                pass_number=3,
                relaxed_participants=relax_names,
                candidates_if_failed=[],
                status='success',
                message=f"✅ {len(solutions)} solution(s) trouvée(s) en lésant: {', '.join(relax_names)}"
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
        
        Stratégie:
        1. Tester en réduisant 1 vœu à chaque participant non protégé
        2. Voir si ça débloque la situation
        3. Retourner les candidats
        """
        candidates = []
        
        # Participants non protégés avec des vœux
        non_protected = [
            p for p in participants
            if not p.respect_voeux and (p.voeux_etape > 0 or p.voeux_open > 0)
        ]
        
        for candidate in non_protected:
            # Créer une version modifiée
            modified_participants = []
            for p in participants:
                p_copy = copy.copy(p)
                if p.nom == candidate.nom:
                    # Réduire les vœux de 1
                    if p_copy.voeux_etape > 0:
                        p_copy.voeux_etape -= 1
                    elif p_copy.voeux_open > 0:
                        p_copy.voeux_open -= 1
                modified_participants.append(p_copy)
            
            # Tester rapidement (timeout court)
            test_config = copy.copy(self.config)
            test_config.max_solutions = 1  # Juste vérifier si possible
            test_config.timeout_seconds = 5.0  # Court
            
            test_solver = TournamentSolver(test_config)
            solutions, status, info = test_solver.solve(modified_participants, tournaments)
            
            if solutions and len(solutions) > 0:
                # Calculer l'impact
                solution = solutions[0]
                stats = solution.get_participant_stats(candidate.nom)
                
                proposed_etape = candidate.voeux_etape - 1 if candidate.voeux_etape > 0 else candidate.voeux_etape
                proposed_open = candidate.voeux_open - 1 if candidate.voeux_open > 0 else candidate.voeux_open
                
                reason = "Réduire 1 étape" if candidate.voeux_etape > 0 else "Réduire 1 open"
                
                candidates.append(RelaxationCandidate(
                    participant_name=candidate.nom,
                    current_wishes_etape=candidate.voeux_etape,
                    current_wishes_open=candidate.voeux_open,
                    proposed_wishes_etape=proposed_etape,
                    proposed_wishes_open=proposed_open,
                    impact_days_if_relaxed=stats['jours_joues'],
                    reason=reason
                ))
        
        # Trier par impact (privilégier ceux qui joueraient le moins si lésés)
        candidates.sort(key=lambda c: c.impact_days_if_relaxed)
        
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
        
        # 4. Vérifier si équipes incomplètes est activé
        if not config.allow_incomplete:
            nb_participants = len(participants)
            if nb_participants % 3 != 0:
                diagnostics['issues'].append(
                    f"Nombre de participants ({nb_participants}) n'est pas multiple de 3"
                )
                diagnostics['suggestions'].append(
                    "Activer 'Autoriser équipes incomplètes'"
                )
                diagnostics['severity'] = 'medium' if diagnostics['severity'] == 'unknown' else diagnostics['severity']
        
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
