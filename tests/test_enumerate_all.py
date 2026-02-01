"""
Tests pour vérifier que TOUTES les solutions sont trouvées
"""
import pytest
from src.models import Participant, Tournament, SolverConfig
from src.solver import TournamentSolver


def test_enumerate_all_solutions_4_players_1_etape():
    """
    Test critique: 4 joueurs veulent 1 étape, 1 seule étape disponible
    
    Sans équipes incomplètes → Impossible (4 joueurs != multiple de 3)
    Avec équipes incomplètes → 4 solutions (C(4,3) = 4 choix de qui ne joue pas)
    """
    # 4 participants, tous veulent 1 étape
    participants = [
        Participant(
            nom=f"Joueur{i}",
            genre="M" if i < 2 else "F",
            couple=None,
            voeux_etape=1,
            voeux_open=0,
            dispo_jusqu_a='E1',
            respect_voeux=False
        )
        for i in range(1, 5)
    ]
    
    # 1 seule étape
    tournaments = [
        Tournament(
            id='E1',
            label='Étape 1',
            lieu='TEST',
            type="etape",
            days=[0, 1],
            day_labels=['Jour 1', 'Jour 2']
        )
    ]
    
    # Config AVEC équipes incomplètes
    config = SolverConfig(
        include_o3=False,
        allow_incomplete=True,
        max_solutions=10,
        timeout_seconds=10.0
    )
    
    solver = TournamentSolver(config)
    solutions, status, info = solver.solve(participants, tournaments)
    
    # Vérifications
    assert len(solutions) > 0, "Devrait trouver des solutions avec équipes incomplètes"
    
    # Analyser les solutions
    joueurs_par_solution = []
    for sol in solutions:
        joueurs_e1 = set(sol.assignments['E1'])
        joueurs_par_solution.append(frozenset(joueurs_e1))
    
    # Enlever les doublons
    solutions_uniques = set(joueurs_par_solution)
    
    print(f"\n✅ {len(solutions_uniques)} solutions uniques trouvées:")
    for i, joueurs in enumerate(solutions_uniques, 1):
        print(f"   Solution {i}: {sorted(joueurs)}")
    
    # Avec 4 joueurs et 1 étape de 3 places:
    # On peut choisir 3 joueurs parmi 4 = C(4,3) = 4 combinaisons
    # MAIS il faut respecter le genre (2H + 1F ou 1H + 2F pour étape)
    # Donc on attend 2-4 solutions selon contraintes genre
    
    assert len(solutions_uniques) >= 2, \
        f"Devrait trouver au moins 2 variantes différentes, trouvé {len(solutions_uniques)}"


def test_enumerate_all_solutions_permutations():
    """
    Test: Vérifier que les permutations équivalentes sont toutes trouvées
    
    Scénario: Alice et Bob veulent 2j, 1 étape de 2j disponible
    → On devrait trouver les 2 solutions: (Alice+Bob) OU aucun des deux
    """
    participants = [
        Participant(
            nom="Alice",
            genre="F",
            couple=None,
            voeux_etape=1,
            voeux_open=0,
            dispo_jusqu_a='E1',
            respect_voeux=False
        ),
        Participant(
            nom="Bob",
            genre="M",
            couple=None,
            voeux_etape=1,
            voeux_open=0,
            dispo_jusqu_a='E1',
            respect_voeux=False
        ),
        Participant(
            nom="Charlie",
            genre="M",
            couple=None,
            voeux_etape=1,
            voeux_open=0,
            dispo_jusqu_a='E1',
            respect_voeux=False
        )
    ]
    
    tournaments = [
        Tournament(
            id='E1',
            label='Étape 1',
            lieu='TEST',
            type="etape",
            days=[0, 1],
            day_labels=['J1', 'J2']
        )
    ]
    
    config = SolverConfig(
        allow_incomplete=False,  # Équipes de 3 exactement
        max_solutions=50,
        timeout_seconds=10.0
    )
    
    solver = TournamentSolver(config)
    solutions, status, info = solver.solve(participants, tournaments)
    
    assert len(solutions) > 0, "Devrait trouver au moins une solution"
    
    # Il n'y a qu'une seule combinaison possible: les 3 jouent
    # MAIS on devrait vérifier qu'il n'y a pas de variantes cachées
    print(f"\n✅ {len(solutions)} solution(s) trouvée(s) avec 3 joueurs")
    
    # Avec 3 joueurs pour 3 places, 1 seule solution
    assert len(solutions) == 1, \
        f"Avec 3 joueurs pour 3 places, devrait avoir 1 solution exacte"


def test_enumerate_emilie_delphine_swap():
    """
    Test du cas réel: Emilie et Delphine devraient être interchangeables
    
    AVEC LA RECHERCHE 2-PASSES, on devrait maintenant trouver:
    - Variante 1: Emilie joue E1, Delphine joue E1+E2
    - Variante 2: Emilie joue E1+E2, Delphine joue E1
    
    Ces 2 variantes ont le MÊME score mais sont différentes.
    """
    participants = [
        Participant(
            nom="Emilie",
            genre="F",
            couple=None,
            voeux_etape=2,
            voeux_open=0,
            dispo_jusqu_a='E2',
            respect_voeux=False
        ),
        Participant(
            nom="Delphine",
            genre="F",
            couple=None,
            voeux_etape=2,
            voeux_open=0,
            dispo_jusqu_a='E2',
            respect_voeux=False
        ),
        # Ajouter des hommes pour compléter
        Participant(
            nom="Hugo",
            genre="M",
            couple=None,
            voeux_etape=2,
            voeux_open=0,
            dispo_jusqu_a='E2',
            respect_voeux=False
        ),
        Participant(
            nom="Julien",
            genre="M",
            couple=None,
            voeux_etape=2,
            voeux_open=0,
            dispo_jusqu_a='E2',
            respect_voeux=False
        ),
        Participant(
            nom="Robin",
            genre="M",
            couple=None,
            voeux_etape=2,
            voeux_open=0,
            dispo_jusqu_a='E2',
            respect_voeux=False
        ),
    ]
    
    tournaments = [
        Tournament(
            id='E1',
            label='Étape 1',
            lieu='LIEU1',
            type="etape",
            days=[0, 1],
            day_labels=['Sam', 'Dim']
        ),
        Tournament(
            id='E2',
            label='Étape 2',
            lieu='LIEU2',
            type="etape",
            days=[2, 3],
            day_labels=['Mar', 'Mer']
        )
    ]
    
    config = SolverConfig(
        allow_incomplete=False,
        max_solutions=100,
        timeout_seconds=30.0
    )
    
    solver = TournamentSolver(config)
    solutions, status, info = solver.solve(participants, tournaments)
    
    print(f"\n✅ {len(solutions)} solutions trouvées (PASS {info.get('pass', '?')})")
    
    # Analyser les combinaisons Emilie/Delphine
    emilie_delphine_combos = []
    for sol in solutions:
        emilie_etapes = 0
        delphine_etapes = 0
        
        if 'Emilie' in sol.assignments['E1']:
            emilie_etapes += 1
        if 'Emilie' in sol.assignments['E2']:
            emilie_etapes += 1
        if 'Delphine' in sol.assignments['E1']:
            delphine_etapes += 1
        if 'Delphine' in sol.assignments['E2']:
            delphine_etapes += 1
        
        combo = (emilie_etapes, delphine_etapes)
        if combo not in emilie_delphine_combos:
            emilie_delphine_combos.append(combo)
            print(f"   Combo: Emilie={emilie_etapes} étapes, Delphine={delphine_etapes} étapes")
    
    # AVEC 2-PASSES: On DOIT trouver les variantes symétriques
    print(f"\n✅ Combinaisons uniques trouvées: {emilie_delphine_combos}")
    
    # Vérifier qu'on a plusieurs combinaisons
    assert len(emilie_delphine_combos) > 1, \
        f"Devrait trouver plusieurs combinaisons Emilie/Delphine, trouvé seulement {emilie_delphine_combos}"
    
    # Si on a (2,1), on DOIT aussi avoir (1,2) grâce à la recherche exhaustive
    if (2, 1) in emilie_delphine_combos:
        assert (1, 2) in emilie_delphine_combos, \
            "ÉCHEC: Recherche 2-passes devrait trouver (2,1) ET (1,2) mais manque (1,2)"
        print("✅ SUCCÈS: Variantes symétriques (2,1) et (1,2) trouvées !")
    
    if (1, 2) in emilie_delphine_combos:
        assert (2, 1) in emilie_delphine_combos, \
            "ÉCHEC: Recherche 2-passes devrait trouver (1,2) ET (2,1) mais manque (2,1)"
        print("✅ SUCCÈS: Variantes symétriques (1,2) et (2,1) trouvées !")
    
    print(f"✅ Test Emilie/Delphine swap RÉUSSI: {len(emilie_delphine_combos)} combinaisons différentes")


def test_max_solutions_limit():
    """
    Test que max_solutions limite bien le nombre de solutions
    """
    # 6 joueurs pour créer beaucoup de combinaisons
    participants = [
        Participant(
            nom=f"Joueur{i}",
            genre="M" if i < 3 else "F",
            couple=None,
            voeux_etape=1,
            voeux_open=0,
            dispo_jusqu_a='E1',
            respect_voeux=False
        )
        for i in range(1, 7)
    ]
    
    tournaments = [
        Tournament(
            id='E1',
            label='Étape 1',
            lieu='TEST',
            type="etape",
            days=[0, 1],
            day_labels=['J1', 'J2']
        )
    ]
    
    # Limite à 5 solutions
    config = SolverConfig(
        allow_incomplete=True,
        max_solutions=5,
        timeout_seconds=10.0
    )
    
    solver = TournamentSolver(config)
    solutions, status, info = solver.solve(participants, tournaments)
    
    print(f"\n✅ Limite max_solutions=5: {len(solutions)} solutions trouvées")
    
    # Ne devrait pas dépasser la limite
    assert len(solutions) <= 5, \
        f"Devrait respecter max_solutions=5, mais trouvé {len(solutions)}"


if __name__ == '__main__':
    # Lancer les tests
    pytest.main([__file__, '-v', '-s'])
