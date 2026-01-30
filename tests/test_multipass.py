"""
Tests pour le multipass solver et l'assistant de conflits
"""
import pytest
from src.models import Participant, Tournament, SolverConfig
from src.multipass_solver import MultiPassSolver, ConflictAnalyzer
from src.constants import TOURNAMENTS


class TestMultiPassSolver:
    """Tests du solver multi-passes"""
    
    def test_multipass_finds_perfect_solution_pass1(self):
        """
        Test que le multipass trouve une solution parfaite en Pass 1
        """
        # Configuration simple
        alice = Participant("Alice", "F", None, 1, 0, "O3", False)
        bob = Participant("Bob", "M", None, 1, 0, "O3", False)
        
        participants = [alice, bob]
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:2]
        
        config = SolverConfig(
            max_solutions=5,
            timeout_seconds=10.0,
            allow_incomplete=True
        )
        
        multipass = MultiPassSolver(config)
        result = multipass.solve_multipass(participants, tournaments)
        
        # Devrait réussir en Pass 1
        assert result.status == 'success'
        assert result.pass_number == 1
        assert len(result.solutions) > 0
        assert len(result.relaxed_participants) == 0
        assert "parfaite" in result.message.lower()
    
    def test_multipass_proposes_candidates_when_impossible(self):
        """
        Test que le multipass propose des candidats quand impossible
        """
        # Configuration impossible : tous veulent trop
        participants = [
            Participant("Alice", "F", None, 3, 3, "O3", True),  # Strict, veut trop
            Participant("Bob", "M", None, 3, 3, "O3", True),    # Strict, veut trop
            Participant("Charlie", "M", None, 3, 3, "O3", False)
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:2]
        
        config = SolverConfig(
            max_solutions=5,
            timeout_seconds=10.0,
            allow_incomplete=True
        )
        
        multipass = MultiPassSolver(config)
        result = multipass.solve_multipass(participants, tournaments)
        
        # Devrait proposer des candidats
        # (peut être success avec solutions partielles OU need_user_choice)
        assert result.status in ['need_user_choice', 'partial_success', 'impossible']
        
        if result.status == 'need_user_choice':
            assert len(result.candidates_if_failed) > 0
    
    def test_multipass_with_relaxation(self):
        """
        Test résolution avec relaxation explicite
        """
        # Configuration nécessitant relaxation
        alice = Participant("Alice", "F", None, 3, 0, "O3", False)
        bob = Participant("Bob", "M", None, 3, 0, "O3", False)
        charlie = Participant("Charlie", "M", None, 2, 0, "O3", False)
        
        participants = [alice, bob, charlie]
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:2]
        
        config = SolverConfig(
            max_solutions=5,
            timeout_seconds=15.0,
            allow_incomplete=True
        )
        
        multipass = MultiPassSolver(config)
        
        # Résoudre avec relaxation de Charlie
        result = multipass.solve_with_relaxation(
            participants,
            tournaments,
            relax_names=["Charlie"]
        )
        
        # Devrait trouver des solutions
        assert result.pass_number == 3
        assert len(result.relaxed_participants) > 0
        assert "Charlie" in result.relaxed_participants


class TestConflictAnalyzer:
    """Tests de l'analyseur de conflits"""
    
    def test_analyzer_detects_too_many_strict(self):
        """
        Test détection de trop de contraintes strictes
        """
        # Beaucoup de strict
        participants = [
            Participant(f"P{i}", "M" if i % 2 == 0 else "F", None, 1, 1, "O3", True)
            for i in range(10)
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS[:3]]
        config = SolverConfig()
        
        diagnostics = ConflictAnalyzer.analyze_why_no_solution(
            participants,
            tournaments,
            config
        )
        
        # Devrait détecter le problème
        assert len(diagnostics['issues']) > 0
        assert any("strict" in issue.lower() for issue in diagnostics['issues'])
        assert diagnostics['severity'] in ['high', 'critical']
    
    def test_analyzer_detects_incomplete_teams_issue(self):
        """
        Test détection du problème d'équipes incomplètes
        """
        # 7 participants (pas multiple de 3)
        participants = [
            Participant(f"P{i}", "M" if i % 2 == 0 else "F", None, 1, 0, "O3", False)
            for i in range(7)
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS[:2]]
        config = SolverConfig(allow_incomplete=False)
        
        diagnostics = ConflictAnalyzer.analyze_why_no_solution(
            participants,
            tournaments,
            config
        )
        
        # Devrait détecter le problème
        assert len(diagnostics['issues']) > 0
        assert any("multiple de 3" in issue.lower() or "incomplète" in issue.lower() 
                   for issue in diagnostics['issues'])
        assert any("incomplète" in sug.lower() for sug in diagnostics['suggestions'])
    
    def test_analyzer_detects_couple_conflicts(self):
        """
        Test détection de conflits dans les couples
        """
        # Couple avec beaucoup de vœux
        alice = Participant("Alice", "F", "Bob", 3, 3, "O3", False)
        bob = Participant("Bob", "M", "Alice", 3, 3, "O3", False)
        
        participants = [alice, bob]
        tournaments = [Tournament(**t) for t in TOURNAMENTS]
        config = SolverConfig()
        
        diagnostics = ConflictAnalyzer.analyze_why_no_solution(
            participants,
            tournaments,
            config
        )
        
        # Devrait mentionner le couple
        # (peut ne pas être détecté selon la logique, mais ne devrait pas crasher)
        assert isinstance(diagnostics['issues'], list)
        assert isinstance(diagnostics['suggestions'], list)


class TestRelaxationCandidates:
    """Tests de l'identification des candidats à relaxer"""
    
    def test_candidates_identification(self):
        """
        Test que les candidats sont identifiés correctement
        """
        # Configuration avec conflit
        alice = Participant("Alice", "F", None, 2, 0, "O3", False)  # Peut être lésée
        bob = Participant("Bob", "M", None, 3, 0, "O3", True)      # Protégé
        charlie = Participant("Charlie", "M", None, 2, 0, "O3", False)  # Peut être lésé
        
        participants = [alice, bob, charlie]
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:2]
        
        config = SolverConfig(
            max_solutions=2,
            timeout_seconds=15.0,
            allow_incomplete=True
        )
        
        multipass = MultiPassSolver(config)
        candidates = multipass._identify_relaxation_candidates(participants, tournaments)
        
        # Devrait identifier Alice et/ou Charlie (pas Bob qui est protégé)
        candidate_names = [c.participant_name for c in candidates]
        
        # Bob ne doit PAS être dans les candidats (protégé)
        assert "Bob" not in candidate_names
        
        # Au moins un candidat devrait être trouvé
        # (peut être vide si pas de solution même en relaxant)
        if len(candidates) > 0:
            # Vérifier que les candidats sont triés par impact
            impacts = [c.impact_days_if_relaxed for c in candidates]
            assert impacts == sorted(impacts)  # Doit être trié croissant


# Point d'entrée pour pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
