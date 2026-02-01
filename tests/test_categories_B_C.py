"""
Tests focalisés sur les catégories B (Contraintes) et C (Qualité)
Selon tes priorités
"""
import pytest
from src.models import Participant, Tournament, SolverConfig
from src.solver import TournamentSolver
from src.constants import TOURNAMENTS


# ========================================
# CATÉGORIE B : TESTS DE CONTRAINTES
# ========================================

class TestContraintes:
    """Tests que les contraintes sont bien respectées"""
    
    def test_contrainte_couples_meme_jour(self):
        """Un couple ne doit JAMAIS jouer le même jour"""
        participants = [
            Participant("Alice", "F", "Bob", 2, 0, "O3", False),
            Participant("Bob", "M", "Alice", 2, 0, "O3", False),
            Participant("Clara", "F", None, 2, 0, "O3", False),
            Participant("Dan", "M", None, 2, 0, "O3", False),
            Participant("Eve", "F", None, 2, 0, "O3", False),
            Participant("Fred", "M", None, 2, 0, "O3", False),
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:2]
        
        config = SolverConfig(
            allow_incomplete=False,
            max_solutions=10,
            timeout_seconds=20.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, "Devrait trouver des solutions"
        
        # Vérifier chaque solution
        for sol in solutions:
            for tournament in tournaments:
                joueurs = sol.assignments[tournament.id]
                
                # Alice et Bob ne doivent JAMAIS être dans la même étape
                assert not ('Alice' in joueurs and 'Bob' in joueurs), \
                    f"VIOLATION COUPLE: Alice et Bob jouent ensemble au tournoi {tournament.id}"
        
        print(f"✅ Contrainte couples respectée dans {len(solutions)} solutions")
    
    def test_contrainte_equipes_de_3(self):
        """Si incomplètes désactivées, équipes doivent être de 3 exactement"""
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
        
        config = SolverConfig(
            allow_incomplete=False,  # ← Équipes de 3 strictement
            max_solutions=10,
            timeout_seconds=20.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, "Devrait trouver des solutions"
        
        # Vérifier chaque solution
        for sol in solutions:
            joueurs_e1 = sol.assignments['E1']
            
            # Compter hommes et femmes
            hommes = [j for j in joueurs_e1 if j in ['Dan', 'Ed', 'Fred']]
            femmes = [j for j in joueurs_e1 if j in ['Alice', 'Betty', 'Clara']]
            
            # Les équipes d'étape sont séparées H/F
            assert len(hommes) % 3 == 0, \
                f"Hommes doivent être multiple de 3, trouvé {len(hommes)}"
            assert len(femmes) % 3 == 0, \
                f"Femmes doivent être multiple de 3, trouvé {len(femmes)}"
        
        print(f"✅ Contrainte équipes de 3 respectée dans {len(solutions)} solutions")
    
    def test_contrainte_disponibilite(self):
        """Personne ne joue après sa date de disponibilité"""
        participants = [
            Participant("Alice", "F", None, 1, 0, "E1", False),  # Dispo jusqu'à E1
            Participant("Betty", "F", None, 2, 0, "O3", False),  # Dispo jusqu'au bout
            Participant("Clara", "F", None, 1, 0, "E2", False),  # Dispo jusqu'à E2
            Participant("Dan", "M", None, 1, 0, "E1", False),
            Participant("Ed", "M", None, 2, 0, "O3", False),
            Participant("Fred", "M", None, 1, 0, "E2", False),
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:3]
        
        config = SolverConfig(
            allow_incomplete=True,  # Pour faciliter
            max_solutions=10,
            timeout_seconds=20.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, "Devrait trouver des solutions"
        
        # Vérifier chaque solution
        for sol in solutions:
            # Alice ne doit jouer QUE E1 (id='E1')
            for t in tournaments:
                if t.id != 'E1' and 'Alice' in sol.assignments[t.id]:
                    assert False, f"VIOLATION DISPO: Alice joue {t.id} mais dispo jusqu'à E1"
            
            # Clara peut jouer E1 et E2, mais PAS E3
            if 'E3' in [t.id for t in tournaments]:
                e3_joueurs = sol.assignments.get('E3', [])
                assert 'Clara' not in e3_joueurs, \
                    "VIOLATION DISPO: Clara joue E3 mais dispo jusqu'à E2"
        
        print(f"✅ Contrainte disponibilité respectée dans {len(solutions)} solutions")
    
    def test_contrainte_respect_voeux_strict(self):
        """Si respect_voeux=True, égalité stricte vœux=joué"""
        participants = [
            Participant("Alice", "F", None, 2, 0, "O3", True),  # Strict: DOIT jouer 2 étapes
            Participant("Betty", "F", None, 2, 0, "O3", False),
            Participant("Clara", "F", None, 2, 0, "O3", False),
            Participant("Dan", "M", None, 2, 0, "O3", True),  # Strict: DOIT jouer 2 étapes
            Participant("Ed", "M", None, 2, 0, "O3", False),
            Participant("Fred", "M", None, 2, 0, "O3", False),
        ]
        
        tournaments = [Tournament(**t) for t in TOURNAMENTS if t['type'] == 'etape'][:3]
        
        config = SolverConfig(
            allow_incomplete=False,
            max_solutions=10,
            timeout_seconds=20.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        # Si respect_voeux=True, le solver DOIT trouver solution respectant exactement
        # OU ne rien trouver (INFEASIBLE)
        if len(solutions) > 0:
            # Vérifier Alice et Dan
            for sol in solutions:
                alice_stats = sol.get_participant_stats("Alice")
                dan_stats = sol.get_participant_stats("Dan")
                
                assert alice_stats['etapes_jouees'] == 2, \
                    f"Alice strict doit jouer exactement 2 étapes, trouvé {alice_stats['etapes_jouees']}"
                assert dan_stats['etapes_jouees'] == 2, \
                    f"Dan strict doit jouer exactement 2 étapes, trouvé {dan_stats['etapes_jouees']}"
        
        print(f"✅ Contrainte respect_voeux strict respectée")


# ========================================
# CATÉGORIE C : TESTS DE QUALITÉ
# ========================================

class TestQualite:
    """Tests de la qualité des solutions"""
    
    def test_trouve_solution_parfaite_si_possible(self):
        """Si solution parfaite existe, le solver doit la trouver"""
        # Configuration parfaite: 6 participants, 2 étapes, chacun veut 1 étape
        participants = [
            Participant("Alice", "F", None, 1, 0, "E2", False),
            Participant("Betty", "F", None, 1, 0, "E2", False),
            Participant("Clara", "F", None, 1, 0, "E2", False),
            Participant("Dan", "M", None, 1, 0, "E2", False),
            Participant("Ed", "M", None, 1, 0, "E2", False),
            Participant("Fred", "M", None, 1, 0, "E2", False),
        ]
        
        tournaments = [
            Tournament('E1', 'Étape 1', 'LIEU1', "etape", [0, 1], ['S', 'D']),
            Tournament('E2', 'Étape 2', 'LIEU2', "etape", [2, 3], ['M', 'M'])
        ]
        
        config = SolverConfig(
            allow_incomplete=False,
            max_solutions=10,
            timeout_seconds=20.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, "Devrait trouver des solutions"
        
        # Vérifier qu'au moins UNE solution est parfaite
        solutions_parfaites = [
            sol for sol in solutions
            if len(sol.violated_wishes) == 0
        ]
        
        assert len(solutions_parfaites) > 0, \
            "Devrait trouver au moins une solution parfaite avec cette config"
        
        # Vérifier score
        meilleur_score = max(sol.get_quality_score() for sol in solutions)
        assert meilleur_score >= 90, \
            f"Solution parfaite devrait avoir score ≥90, trouvé {meilleur_score}"
        
        print(f"✅ {len(solutions_parfaites)} solutions parfaites trouvées (score={meilleur_score:.0f})")
    
    def test_trouve_multiples_variantes_si_existent(self):
        """Si plusieurs variantes équivalentes existent, le solver doit en trouver plusieurs"""
        # 4 participantes veulent 1 étape, 1 étape disponible
        # → 4 façons de choisir 3 parmi 4
        participants = [
            Participant("Alice", "F", None, 1, 0, "E1", False),
            Participant("Betty", "F", None, 1, 0, "E1", False),
            Participant("Clara", "F", None, 1, 0, "E1", False),
            Participant("Diana", "F", None, 1, 0, "E1", False),
            Participant("Dan", "M", None, 1, 0, "E1", False),
            Participant("Ed", "M", None, 1, 0, "E1", False),
            Participant("Fred", "M", None, 1, 0, "E1", False),
            Participant("Greg", "M", None, 1, 0, "E1", False),
        ]
        
        tournaments = [
            Tournament('E1', 'Étape 1', 'LIEU', "etape", [0, 1], ['S', 'D'])
        ]
        
        config = SolverConfig(
            allow_incomplete=False,
            max_solutions=20,
            timeout_seconds=30.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, "Devrait trouver des solutions"
        
        # Compter les variantes uniques (qui joue parmi les 4 femmes)
        femmes_combos = set()
        for sol in solutions:
            femmes_e1 = frozenset([p for p in sol.assignments['E1'] 
                                   if p in ['Alice', 'Betty', 'Clara', 'Diana']])
            femmes_combos.add(femmes_e1)
        
        # Devrait trouver au moins 2 variantes différentes (idéalement 4)
        assert len(femmes_combos) >= 2, \
            f"Devrait trouver au moins 2 variantes, trouvé {len(femmes_combos)}"
        
        print(f"✅ {len(femmes_combos)} variantes uniques trouvées sur {len(solutions)} solutions")
    
    def test_score_coherent(self):
        """Les scores des solutions doivent être cohérents"""
        participants = [
            Participant("Alice", "F", None, 1, 0, "E2", False),
            Participant("Betty", "F", None, 1, 0, "E2", False),
            Participant("Clara", "F", None, 1, 0, "E2", False),
            Participant("Dan", "M", None, 1, 0, "E2", False),
            Participant("Ed", "M", None, 1, 0, "E2", False),
            Participant("Fred", "M", None, 1, 0, "E2", False),
        ]
        
        tournaments = [
            Tournament('E1', 'Étape 1', 'LIEU1', "etape", [0, 1], ['S', 'D']),
            Tournament('E2', 'Étape 2', 'LIEU2', "etape", [2, 3], ['M', 'M'])
        ]
        
        config = SolverConfig(
            allow_incomplete=False,
            max_solutions=20,
            timeout_seconds=20.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, "Devrait trouver des solutions"
        
        # Analyser les scores
        scores = [sol.get_quality_score() for sol in solutions]
        
        # Vérifications
        assert all(0 <= s <= 100 for s in scores), \
            "Tous les scores doivent être entre 0 et 100"
        
        # Avec recherche 2-passes, toutes solutions devraient avoir score similaire
        min_score = min(scores)
        max_score = max(scores)
        ecart = max_score - min_score
        
        assert ecart <= 30, \
            f"Écart de scores trop grand: {ecart:.1f} (min={min_score:.0f}, max={max_score:.0f})"
        
        print(f"✅ Scores cohérents: min={min_score:.0f}, max={max_score:.0f}, écart={ecart:.1f}")
    
    def test_minimise_ecarts(self):
        """Le solver doit minimiser les écarts aux vœux"""
        # 3 femmes veulent 2 étapes chacune, 2 étapes disponibles
        # → Au moins une ne pourra avoir que 1 étape
        # → Le solver doit équilibrer (pas 2+2+0, mais 2+1+1)
        participants = [
            Participant("Alice", "F", None, 2, 0, "E2", False),
            Participant("Betty", "F", None, 2, 0, "E2", False),
            Participant("Clara", "F", None, 2, 0, "E2", False),
            Participant("Dan", "M", None, 2, 0, "E2", False),
            Participant("Ed", "M", None, 2, 0, "E2", False),
            Participant("Fred", "M", None, 2, 0, "E2", False),
        ]
        
        tournaments = [
            Tournament('E1', 'Étape 1', 'LIEU1', "etape", [0, 1], ['S', 'D']),
            Tournament('E2', 'Étape 2', 'LIEU2', "etape", [2, 3], ['M', 'M'])
        ]
        
        config = SolverConfig(
            allow_incomplete=False,
            max_solutions=10,
            timeout_seconds=20.0
        )
        
        solver = TournamentSolver(config)
        solutions, status, info = solver.solve(participants, tournaments)
        
        assert len(solutions) > 0, "Devrait trouver des solutions"
        
        # Analyser la meilleure solution
        best = max(solutions, key=lambda s: s.get_quality_score())
        
        # Compter les écarts
        ecarts = []
        for p in participants:
            stats = best.get_participant_stats(p.nom)
            ecarts.append(abs(stats['ecart']))
        
        total_ecart = sum(ecarts)
        max_ecart = max(ecarts)
        
        # Le total des écarts doit être minimisé
        # Avec 6 personnes voulant 2 étapes et 2 étapes dispo (6 places par genre)
        # Chaque genre a 3 personnes pour 6 places → tout le monde peut jouer 2 étapes!
        assert total_ecart == 0, \
            f"Tous devraient avoir leurs vœux respectés, total écart = {total_ecart}"
        
        print(f"✅ Écarts minimisés: total={total_ecart}, max={max_ecart}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
