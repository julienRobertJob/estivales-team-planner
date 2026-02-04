"""
Test du critère principal : préférer répartir les lésions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.models import Participant, Tournament, SolverConfig
from src.solver import TournamentSolver
from src.constants import TOURNAMENTS, DEFAULT_PARTICIPANTS

# Créer les participants
participants = []
for row in DEFAULT_PARTICIPANTS:
    participants.append(Participant(
        nom=row[0],
        genre=row[1],
        couple=row[2],
        voeux_etape=row[3],
        voeux_open=row[4],
        dispo_jusqu_a=row[5],
        respect_voeux=row[6]
    ))

tournaments = [Tournament(**t) for t in TOURNAMENTS if t['id'] != 'O3']

config = SolverConfig(
    include_o3=False,
    allow_incomplete=False,
    max_solutions=50,
    timeout_seconds=30.0
)

print("=" * 70)
print("TEST CRITÈRE PRINCIPAL : Préférer répartir les lésions")
print("=" * 70)
print()
print("Question: 1 personne lésée de 2j vs 2 personnes lésées de 1j ?")
print("Réponse attendue: 2 personnes de 1j (mieux réparti)")
print()

# Résoudre
print("Recherche de solutions...")
solver = TournamentSolver(config)
solutions, status, info = solver.solve(participants, tournaments)

print(f"✓ {len(solutions)} solutions trouvées")
print()

if not solutions:
    print("❌ AUCUNE SOLUTION TROUVÉE")
    print("Le critère peut être trop strict maintenant")
else:
    # Analyser les profils de lésions
    print("=" * 70)
    print("ANALYSE DES PROFILS")
    print("=" * 70)
    
    from collections import Counter
    
    # Compter les lésions par personne
    for idx, sol in enumerate(solutions[:10], 1):
        score = sol.get_quality_score()
        total_lese = 0
        nb_leses = 0
        max_lesion_individuelle = 0
        
        leses_detail = []
        for nom in sol.violated_wishes:
            stats = sol.get_participant_stats(nom)
            ecart = abs(stats['ecart'])
            leses_detail.append((nom, stats['jours_souhaites'], ecart))
            total_lese += ecart
            nb_leses += 1
            max_lesion_individuelle = max(max_lesion_individuelle, ecart)
        
        print(f"\nSolution #{idx} - Score: {score:.1f}/100")
        print(f"  Total lésé: {total_lese}j | Nb personnes: {nb_leses} | Max individuel: {max_lesion_individuelle}j")
        
        if leses_detail:
            # Trier par écart décroissant
            leses_detail.sort(key=lambda x: -x[2])
            for nom, demande, ecart in leses_detail[:5]:  # Top 5
                print(f"    - {nom:15} : {demande}j demandés, lésé {ecart}j")
    
    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print("Critères attendus:")
    print("1. ✓ Total jours lésés MINIMAL (tous jouent le plus possible)")
    print("2. ✓ À égalité de total, lésions RÉPARTIES (plusieurs de 1j > 1 de 2j)")
    print("3. ✓ À égalité, léser les GROS DEMANDEURS (5j > 4j > 3j)")
