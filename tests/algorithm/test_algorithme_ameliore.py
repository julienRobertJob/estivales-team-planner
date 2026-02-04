"""
Test de l'amélioration de l'algorithme OR-Tools
Vérifie que les solutions trouvées favorisent bien léser les gros demandeurs
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

# Créer les tournois (sans O3 pour cet exemple)
tournaments = [Tournament(**t) for t in TOURNAMENTS if t['id'] != 'O3']

# Configuration
config = SolverConfig(
    include_o3=False,
    allow_incomplete=False,
    max_solutions=10,  # Limiter à 10 pour test rapide
    timeout_seconds=30.0
)

print("=" * 70)
print("TEST DE L'ALGORITHME AMÉLIORÉ")
print("=" * 70)
print(f"Participants: {len(participants)}")
print(f"Tournois: {len(tournaments)}")
print()

# Afficher les demandes
print("DEMANDES DES PARTICIPANTS:")
print("-" * 70)
for p in sorted(participants, key=lambda x: -x.voeux_jours_total):
    poids_solver = max(1, 6 - p.voeux_jours_total)
    print(f"{p.nom:15} : {p.voeux_jours_total}j demandés "
          f"(étapes={p.voeux_etape}, opens={p.voeux_open}) "
          f"→ poids OR-Tools={poids_solver}")
print()

# Résoudre
print("RÉSOLUTION EN COURS...")
print("-" * 70)
solver = TournamentSolver(config)
solutions, status, info = solver.solve(participants, tournaments)

print(f"Status: {status}")
print(f"Solutions trouvées: {len(solutions)}")
print(f"Temps: {info.get('elapsed_time', 0):.2f}s")
print()

if solutions:
    print("=" * 70)
    print("ANALYSE DES 5 MEILLEURES SOLUTIONS")
    print("=" * 70)
    
    # Trier par score de qualité
    solutions_sorted = sorted(solutions, key=lambda s: -s.get_quality_score())[:5]
    
    for idx, sol in enumerate(solutions_sorted, 1):
        score = sol.get_quality_score()
        print(f"\nSOLUTION #{idx} - Score: {score:.2f}/100")
        print("-" * 70)
        
        if sol.violated_wishes:
            leses = []
            for nom in sol.violated_wishes:
                stats = sol.get_participant_stats(nom)
                demande = stats['jours_souhaites']
                joue = stats['jours_joues']
                ecart = joue - demande
                leses.append((nom, demande, joue, ecart))
            
            # Trier par demandes décroissantes
            leses.sort(key=lambda x: -x[1])
            
            print("Lésés:")
            total_lese = 0
            for nom, demande, joue, ecart in leses:
                poids_solver = max(1, 6 - demande)
                ratio = abs(ecart) / demande if demande > 0 else 0
                print(f"  - {nom:15} : {demande}j demandés → {joue}j joués ({ecart:+d}j) "
                      f"| poids={poids_solver} | ratio={ratio:.2f}")
                total_lese += abs(ecart)
            
            print(f"\nTotal jours lésés: {total_lese}j")
            
            # Calculer la moyenne des demandes des lésés
            avg_demande = sum(d for _, d, _, _ in leses) / len(leses) if leses else 0
            print(f"Moyenne demandes lésés: {avg_demande:.1f}j")
        else:
            print("✅ Solution PARFAITE - Aucun lésé")

    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print("Si l'algorithme fonctionne bien, on devrait voir:")
    print("✓ Les solutions préfèrent léser ceux qui demandent 4-5j")
    print("✓ Peu ou pas de lésions sur ceux qui demandent 1-2j")
    print("✓ Moyenne des demandes lésés >= 4j")
else:
    print("❌ Aucune solution trouvée")
