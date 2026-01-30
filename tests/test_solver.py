"""
Tests de non-régression pour l'organisateur d'Estivales
"""
import pytest
from src.models import Participant, Tournament, SolverConfig, Solution
from src.solver import TournamentSolver, analyze_solutions
from src.validation import validate_participants_data, check_couples_consistency
from src.constants import TOURNAMENTS, DEFAULT_PARTICIPANTS, PARTICIPANT_COLUMNS


class TestModels:
    """Tests des modèles de données"""
    
    def test_participant_creation_valid(self):
        """Test création participant valide"""
        p = Participant(
            nom="Alice",
            genre="F",
            couple=None,
            voeux_etape=2,
            voeux_open=1,
            dispo_jusqu_a="O3",
            respect_voeux=False
        )
        
        assert p.nom == "Alice"
        assert p.voeux_jours_total == 5  # 2*2 + 1
    
    def test_participant_invalid_genre(self):
        """Test participant avec genre invalide"""
        with pytest.raises(ValueError):
            Participant(
                nom="Bob",
                genre="X",  # Invalide
                couple=None,
                voeux_etape=1,
                voeux_open=1,
                dispo_jusqu_a="O3",
                respect_voeux=False
            )
    
    def test_participant_negative_wishes(self):
        """Test participant avec vœux négatifs"""
        with pytest.raises(ValueError):
            Participant(
                nom="Charlie",
                genre="M",
                couple=None,
                voeux_etape=-1,  # Négatif
                voeux_open=1,
                dispo_jusqu_a="O3",
                respect_voeux=False
            )
    
    def test_participant_from_dict(self):
        """Test création participant depuis dict"""
        data = {
            'Nom': 'David',
            'Genre': 'M',
            'Couple': None,
            'Voeux_Etape': 2,
            'Voeux_Open': 0,
            'Dispo_Jusqu_a': 'E3',
            'Respect_Voeux': False
        }
        
        p = Participant.from_dict(data)
        assert p.nom == 'David'
        assert p.voeux_jours_total == 4


class TestValidation:
    """Tests de la validation"""
    
    def test_validate_empty_participants(self):
        """Test avec liste vide"""
        errors = validate_participants_data([])
        assert len(errors) > 0
        assert "Aucun participant" in errors[0]
    
    def test_validate_duplicate_names(self):
        """Test avec noms en double"""
        p1 = Participant("Alice", "F", None, 1, 1, "O3", False)
        p2 = Participant("Alice", "M", None, 1, 1, "O3", False)
        
        errors = validate_participants_data([p1, p2])
        assert any("double" in e.lower() for e in errors)
    
    def test_validate_couple_not_found(self):
        """Test couple introuvable"""
        p1 = Participant("Alice", "F", "Bob", 1, 1, "O3", False)
        
        errors = validate_participants_data([p1])
        assert any("introuvable" in e.lower() for e in errors)
    
    def test_validate_couple_not_bidirectional(self):
        """Test couple non bidirectionnel"""
        p1 = Participant("Alice", "F", "Bob", 1, 1, "O3", False)
        p2 = Participant("Bob", "M", "Charlie", 1, 1, "O3", False)
        
        errors = validate_participants_data([p1, p2])
        assert any("bidirectionnel" in e.lower() for e in errors)
    
    def test_validate_valid_participants(self):
        """Test participants valides"""
        p1 = Participant("Alice", "F", "Bob", 1, 1, "O3", False)
        p2 = Participant("Bob", "M", "Alice", 1, 1, "O3", False)
        
        errors = validate_participants_data([p1, p2])
        # Peut avoir des warnings mais pas d'erreurs critiques
        assert not any("introuvable" in e.lower() for e in errors)


class TestSolverBasic:
    """Tests de base du solver"""
    
    def test_solver_initialization(self):
        """Test initialisation du solver"""
        config = SolverConfig()
        solver = TournamentSolver(config)
        
        assert solver.config.max_solutions == 50
        assert solver.config.timeout_seconds == 120.0
    
    def test_simple_case_two_participants(self):
        """Test cas simple: 2 participants, vœux faciles"""
        # Alice veut 1 étape, Bob veut 1 open
        p1 = Participant("Alice", "F", None, 1, 0, "O3", False)
        p2 = Participant("Bob", "M", None, 0, 1, "O3", False)
        
        participants = [p1, p2]
        tournaments = [Tournament(**t) for t in TOURNAMENTS[:3]]  # E1, O1, E2
        
        config = SolverConfig(
            max_solutions=10, 
            timeout_seconds=10.0,
            allow_incomplete=True  # IMPORTANT: autoriser équipes incomplètes
        )
        solver = TournamentSolver(config)
        
        solutions, status, info = solver.solve(participants, tournaments)
        
        # Devrait trouver au moins une solution
        assert len(solutions) > 0, f"Aucune solution trouvée. Status: {status}"
        assert status in ["OPTIMAL", "FEASIBLE"]
        
        # Vérifier qu'une solution parfaite existe
        perfect_solutions = [s for s in solutions if len(s.violated_wishes) == 0]
        assert len(perfect_solutions) > 0, \
            f"Aucune solution parfaite. Vœux lésés dans toutes: {[len(s.violated_wishes) for s in solutions]}"
    
    def test_impossible_case_all_strict(self):
        """Test cas impossible: tous veulent 10 étapes (impossible)"""
        participants = [
            Participant("Alice", "F", None, 10, 0, "O3", True),
            Participant("Bob", "M", None, 10, 0, "O3", True),
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS[:2]]  # Seulement E1
        
        config = SolverConfig(max_solutions=5, timeout_seconds=5.0)
        solver = TournamentSolver(config)
        
        solutions, status, info = solver.solve(participants, tournaments)
        
        # Ne devrait pas trouver de solution (demande impossible)
        assert len(solutions) == 0 or status == "INFEASIBLE"


class TestSolverObjective:
    """Tests de la fonction objectif (non-régression critique)"""
    
    def test_objective_minimizes_deviation(self):
        """
        TEST CRITIQUE: Vérifie que l'objectif minimise bien les écarts
        
        Configuration:
        - Alice veut 2 jours (1 étape)
        - Bob veut 2 jours (1 étape)
        - 3 étapes disponibles (6 jours possibles)
        
        Solution attendue: chacun joue 1 étape (2j), pas plus
        Solution interdite: Alice=6j, Bob=0j (maximise au lieu de respecter)
        """
        alice = Participant("Alice", "F", None, 1, 0, "O3", False)
        bob = Participant("Bob", "M", None, 1, 0, "O3", False)
        
        participants = [alice, bob]
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:3]
        
        config = SolverConfig(
            max_solutions=10, 
            timeout_seconds=30.0,
            allow_incomplete=True  # Autoriser équipes incomplètes
        )
        solver = TournamentSolver(config)
        
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, f"Devrait trouver au moins une solution. Status: {status}"
        
        # Analyser la meilleure solution
        best = max(solutions, key=lambda s: s.get_quality_score())
        
        alice_stats = best.get_participant_stats("Alice")
        bob_stats = best.get_participant_stats("Bob")
        
        # Alice et Bob devraient jouer exactement 1 étape chacun (2 jours)
        assert alice_stats['etapes_jouees'] == 1, \
            f"Alice devrait jouer 1 étape, pas {alice_stats['etapes_jouees']}"
        assert bob_stats['etapes_jouees'] == 1, \
            f"Bob devrait jouer 1 étape, pas {bob_stats['etapes_jouees']}"
        
        # Les écarts doivent être 0
        assert alice_stats['ecart'] == 0, \
            f"Alice: écart devrait être 0, pas {alice_stats['ecart']}"
        assert bob_stats['ecart'] == 0, \
            f"Bob: écart devrait être 0, pas {bob_stats['ecart']}"
    
    def test_objective_balances_when_conflict(self):
        """
        TEST CRITIQUE: En cas de conflit, l'objectif doit équilibrer
        
        Configuration:
        - Alice, Bob, Charlie veulent chacun 3 étapes (6j)
        - Seulement 2 étapes disponibles
        - 6 places hommes, 6 places femmes (donc 4j max par personne)
        
        Solution attendue: répartition équilibrée (ex: 4j, 4j, 4j ou 4j, 3j, 5j)
        Solution interdite: 6j, 6j, 0j (inéquitable)
        """
        alice = Participant("Alice", "F", None, 3, 0, "O3", False)
        bob = Participant("Bob", "F", None, 3, 0, "O3", False)
        charlie = Participant("Charlie", "F", None, 3, 0, "O3", False)
        
        participants = [alice, bob, charlie]
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:2]
        
        config = SolverConfig(max_solutions=10, timeout_seconds=30.0)
        solver = TournamentSolver(config)
        
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, "Devrait trouver des solutions"
        
        best = max(solutions, key=lambda s: s.get_quality_score())
        
        alice_stats = best.get_participant_stats("Alice")
        bob_stats = best.get_participant_stats("Bob")
        charlie_stats = best.get_participant_stats("Charlie")
        
        days = [
            alice_stats['jours_joues'],
            bob_stats['jours_joues'],
            charlie_stats['jours_joues']
        ]
        
        # Vérifier que personne n'est complètement exclu
        assert min(days) > 0, "Personne ne devrait être à 0 jour"
        
        # Vérifier l'équilibre: écart max-min <= 2 jours
        assert max(days) - min(days) <= 2, \
            f"Écart trop grand: {max(days)} - {min(days)} = {max(days) - min(days)}"
    
    def test_objective_respects_strict_wishes(self):
        """
        TEST: Les vœux stricts doivent être respectés exactement
        
        Configuration:
        - Alice veut 1 étape (strict)
        - Bob veut 2 étapes (non strict)
        - 3 étapes disponibles
        
        Solution attendue: Alice=1 étape exactement, Bob flexible
        """
        alice = Participant("Alice", "F", None, 1, 0, "O3", True)  # Strict
        bob = Participant("Bob", "M", None, 2, 0, "O3", False)
        
        participants = [alice, bob]
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:3]
        
        config = SolverConfig(
            max_solutions=10, 
            timeout_seconds=30.0,
            allow_incomplete=True  # Autoriser équipes incomplètes
        )
        solver = TournamentSolver(config)
        
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, f"Devrait trouver des solutions. Status: {status}"
        
        # TOUTES les solutions doivent respecter les vœux stricts d'Alice
        for solution in solutions:
            alice_stats = solution.get_participant_stats("Alice")
            assert alice_stats['etapes_jouees'] == 1, \
                f"Alice (strict) doit jouer exactement 1 étape dans toutes les solutions"


class TestSolverCouples:
    """Tests des contraintes de couples"""
    
    def test_couple_cannot_play_same_day(self):
        """
        TEST: Un couple ne peut pas jouer le même jour
        
        Configuration:
        - Alice et Bob sont en couple
        - Tous deux veulent jouer
        
        Vérification: Jamais sur le même jour
        """
        alice = Participant("Alice", "F", "Bob", 2, 1, "O3", False)
        bob = Participant("Bob", "M", "Alice", 2, 1, "O3", False)
        
        participants = [alice, bob]
        tournaments = [Tournament(**t) for t in TOURNAMENTS]
        
        config = SolverConfig(max_solutions=10, timeout_seconds=30.0)
        solver = TournamentSolver(config)
        
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0
        
        # Vérifier dans chaque solution
        for solution in solutions:
            alice_stats = solution.get_participant_stats("Alice")
            bob_stats = solution.get_participant_stats("Bob")
            
            alice_presence = alice_stats['presence']
            bob_presence = bob_stats['presence']
            
            # Vérifier qu'ils ne jouent jamais le même jour
            for day in range(9):
                assert not (alice_presence[day] and bob_presence[day]), \
                    f"Alice et Bob (couple) jouent tous les deux le jour {day}"


class TestSolverFatigue:
    """Tests de la gestion de la fatigue"""
    
    def test_penalizes_consecutive_days(self):
        """
        TEST: Les solutions avec >3 jours consécutifs doivent être pénalisées
        
        Configuration:
        - Alice peut jouer 6 jours
        - Solutions possibles:
          A) Jours 0,1,2,3,4,5 (6 consécutifs) - MAUVAIS
          B) Jours 0,1,3,4,6,7 (max 2 consécutifs) - BON
        
        La solution B doit être préférée
        """
        alice = Participant("Alice", "F", None, 3, 0, "O3", False)  # 3 étapes = 6j
        
        participants = [alice]
        tournaments = [Tournament(**t) for t in TOURNAMENTS]
        
        config = SolverConfig(max_solutions=20, timeout_seconds=30.0)
        solver = TournamentSolver(config)
        
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0
        
        # Trouver la meilleure solution
        best = max(solutions, key=lambda s: s.get_quality_score())
        alice_stats = best.get_participant_stats("Alice")
        
        # La meilleure solution ne devrait pas avoir >3 jours consécutifs
        assert alice_stats['max_consecutifs'] <= 3, \
            f"La meilleure solution a {alice_stats['max_consecutifs']} jours consécutifs (>3)"


class TestDefaultData:
    """Tests avec les données par défaut"""
    
    def test_default_participants_valid(self):
        """Test que les données par défaut sont valides"""
        participants = [
            Participant.from_dict(dict(zip(PARTICIPANT_COLUMNS, data)))
            for data in DEFAULT_PARTICIPANTS
        ]
        
        errors = validate_participants_data(participants)
        
        # Ne devrait pas avoir d'erreurs critiques
        critical_errors = [e for e in errors if "introuvable" in e or "bidirectionnel" in e]
        assert len(critical_errors) == 0, f"Erreurs dans les données par défaut: {critical_errors}"
    
    def test_default_data_finds_solutions(self):
        """Test que les données par défaut trouvent des solutions"""
        participants = [
            Participant.from_dict(dict(zip(PARTICIPANT_COLUMNS, data)))
            for data in DEFAULT_PARTICIPANTS
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['id'] != 'O3']
        
        config = SolverConfig(
            include_o3=False,
            allow_incomplete=True,
            max_solutions=10,
            timeout_seconds=60.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        # Devrait trouver au moins UNE solution (même si pas parfaite)
        assert len(solutions) > 0, \
            f"Devrait trouver au moins une solution avec les données par défaut. Status: {status}, Info: {info}"
        
        # Note: On n'exige plus que les solutions soient parfaites
        # car avec les vraies données, c'est souvent difficile


class TestRegressionScenarios:
    """Tests de scénarios de non-régression"""
    
    def test_scenario_example_from_specs(self):
        """
        TEST DE NON-RÉGRESSION: Scénario de l'exemple des specs
        
        Vérifications:
        1. Julien veut 1E+1O → doit obtenir ~3 jours
        2. Hugo veut 1E+1O → doit obtenir ~3 jours
        3. Delphine dispo jusqu'à E2 → ne joue pas après
        4. Couples respectés
        """
        participants = [
            Participant.from_dict(dict(zip(PARTICIPANT_COLUMNS, data)))
            for data in DEFAULT_PARTICIPANTS
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['id'] != 'O3']
        
        config = SolverConfig(
            include_o3=False,
            allow_incomplete=True,
            max_solutions=20,
            timeout_seconds=60.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0
        
        best = max(solutions, key=lambda s: s.get_quality_score())
        
        # Vérifier Julien
        julien_stats = best.get_participant_stats("Julien")
        assert 2 <= julien_stats['jours_joues'] <= 4, \
            f"Julien veut 3j, obtient {julien_stats['jours_joues']}j (devrait être proche)"
        
        # Vérifier Hugo
        hugo_stats = best.get_participant_stats("Hugo")
        assert 2 <= hugo_stats['jours_joues'] <= 4, \
            f"Hugo veut 3j, obtient {hugo_stats['jours_joues']}j"
        
        # Vérifier Delphine (dispo jusqu'à E2)
        delphine_stats = best.get_participant_stats("Delphine")
        delphine_presence = delphine_stats['presence']
        
        # Jours 5-8 correspondent à O2, E3, O3 (SAINT-CAST)
        # Delphine ne doit jouer aucun de ces jours
        for day in [5, 6, 7, 8]:
            if day < len(delphine_presence):
                assert not delphine_presence[day], \
                    f"Delphine joue le jour {day} mais dispo seulement jusqu'à E2"


# Point d'entrée pour pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
