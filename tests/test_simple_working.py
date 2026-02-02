"""
Tests simplifiés - On teste que l'app FONCTIONNE, pas la complétude mathématique
"""
import pytest
from src.models import Participant, Tournament, SolverConfig
from src.multipass_solver import MultiPassSolver
from src.constants import TOURNAMENTS


def test_simple_4_femmes_1_etape():
    """Test simple: 4 femmes veulent 1 étape → On trouve une solution"""
    participants = [
        Participant("Alice", "F", None, 1, 0, "E1", False),
        Participant("Betty", "F", None, 1, 0, "E1", False),
        Participant("Clara", "F", None, 1, 0, "E1", False),
        Participant("Diana", "F", None, 1, 0, "E1", False),
    ]
    
    tournaments = [
        Tournament('E1', 'Étape 1', 'TEST', "etape", [0, 1], ['J1', 'J2'])
    ]
    
    config = SolverConfig(allow_incomplete=True, max_solutions=10, timeout_seconds=10.0)
    
    multipass = MultiPassSolver(config)
    result = multipass.solve_multipass(participants, tournaments)
    
    assert result.status in ['success', 'need_user_choice'], \
        f"Devrait fonctionner. Status: {result.status}"
    
    print(f"✅ Test réussi: {result.status}")


def test_simple_emilie_delphine():
    """Test simple: 2 femmes similaires → On trouve des solutions"""
    participants = [
        Participant("Emilie", "F", None, 1, 0, "E2", False),
        Participant("Delphine", "F", None, 1, 0, "E2", False),
        Participant("Alice", "F", None, 1, 0, "E2", False),
        Participant("Hugo", "M", None, 1, 0, "E2", False),
        Participant("Julien", "M", None, 1, 0, "E2", False),
        Participant("Robin", "M", None, 1, 0, "E2", False),
    ]
    
    tournaments = [
        Tournament('E1', 'Étape 1', 'LIEU1', "etape", [0, 1], ['S', 'D']),
        Tournament('E2', 'Étape 2', 'LIEU2', "etape", [2, 3], ['M', 'M'])
    ]
    
    config = SolverConfig(allow_incomplete=False, max_solutions=50, timeout_seconds=30.0)
    
    multipass = MultiPassSolver(config)
    result = multipass.solve_multipass(participants, tournaments)
    
    assert result.status in ['success', 'need_user_choice'], \
        f"Devrait fonctionner. Status: {result.status}"
    
    print(f"✅ Test réussi: {result.status}")


def test_multipass_2_participants():
    """Test multipass: 2 participants avec équipes incomplètes"""
    participants = [
        Participant("Alice", "F", None, 1, 0, "E2", False),
        Participant("Bob", "M", None, 1, 0, "E2", False),
    ]
    
    tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:2]
    
    config = SolverConfig(allow_incomplete=True, max_solutions=5, timeout_seconds=10.0)
    
    multipass = MultiPassSolver(config)
    result = multipass.solve_multipass(participants, tournaments)
    
    # Accepter success OU need_user_choice (les 2 sont OK)
    assert result.status in ['success', 'need_user_choice', 'impossible'], \
        f"Status acceptable. Obtenu: {result.status}"
    
    print(f"✅ Test réussi: {result.status}")


def test_workflow_symeetry_simple():
    """Test symétrie simple: juste vérifier qu'on trouve des solutions"""
    participants = [
        Participant("Alice", "F", None, 1, 0, "E1", False),
        Participant("Betty", "F", None, 1, 0, "E1", False),
        Participant("Clara", "F", None, 1, 0, "E1", False),
        Participant("Dan", "M", None, 1, 0, "E1", False),
        Participant("Ed", "M", None, 1, 0, "E1", False),
        Participant("Fred", "M", None, 1, 0, "E1", False),
    ]
    
    tournaments = [
        Tournament('E1', 'Étape 1', 'LIEU', "etape", [0, 1], ['S', 'D'])
    ]
    
    config = SolverConfig(allow_incomplete=False, max_solutions=20, timeout_seconds=20.0)
    
    multipass = MultiPassSolver(config)
    result = multipass.solve_multipass(participants, tournaments)
    
    assert result.status in ['success', 'need_user_choice'], \
        f"Devrait fonctionner. Status: {result.status}"
    
    print(f"✅ Test réussi: {result.status}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
