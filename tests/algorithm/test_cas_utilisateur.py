"""
Test spécifique du cas utilisateur
Voir si l'algorithme trouve des variantes avec Sylvain lésé vs Sophie L lésée
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

# Tournois sans O3
tournaments = [Tournament(**t) for t in TOURNAMENTS if t['id'] != 'O3']

# Configuration pour trouver BEAUCOUP de solutions
config = SolverConfig(
    include_o3=False,
    allow_incomplete=False,
    max_solutions=100,
    timeout_seconds=60.0
)

print("=" * 70)
print("CAS UTILISATEUR: Sylvain (5j) vs Sophie L (4j)")
print("=" * 70)
print()

# Résoudre
print("Recherche de 100 solutions...")
solver = TournamentSolver(config)
solutions, status, info = solver.solve(participants, tournaments)

print(f"✓ {len(solutions)} solutions trouvées en {info.get('elapsed_time', 0):.1f}s")
print()

# Grouper par profil de lésions
from collections import defaultdict

profiles = defaultdict(list)

for sol in solutions:
    if not sol.violated_wishes:
        profiles["PARFAITE"].append(sol)
        continue
    
    leses_names = sorted(sol.violated_wishes)
    profile_key = ", ".join(leses_names)
    profiles[profile_key].append(sol)

print(f"Nombre de profils différents: {len(profiles)}")
print()

# Chercher spécifiquement les cas avec Sylvain ou Sophie L
sylvain_cases = []
sophieL_cases = []

for profile, sols in profiles.items():
    if "Sylvain" in profile and "Sophie L" not in profile:
        sylvain_cases.extend(sols)
    elif "Sophie L" in profile and "Sylvain" not in profile:
        sophieL_cases.extend(sols)

print("=" * 70)
print("RÉSULTATS")
print("=" * 70)
print(f"Solutions avec Sylvain lésé (pas Sophie L): {len(sylvain_cases)}")
print(f"Solutions avec Sophie L lésée (pas Sylvain): {len(sophieL_cases)}")
print()

if sylvain_cases and sophieL_cases:
    # Comparer les meilleurs de chaque catégorie
    best_sylvain = max(sylvain_cases, key=lambda s: s.get_quality_score())
    best_sophieL = max(sophieL_cases, key=lambda s: s.get_quality_score())
    
    score_syl = best_sylvain.get_quality_score()
    score_sop = best_sophieL.get_quality_score()
    
    print("MEILLEURE AVEC SYLVAIN LÉSÉ:")
    print("-" * 70)
    for nom in sorted(best_sylvain.violated_wishes):
        stats = best_sylvain.get_participant_stats(nom)
        print(f"  - {nom:15} : {stats['jours_souhaites']}j → {stats['jours_joues']}j ({stats['ecart']:+d}j)")
    print(f"Score: {score_syl:.2f}/100")
    print()
    
    print("MEILLEURE AVEC SOPHIE L LÉSÉE:")
    print("-" * 70)
    for nom in sorted(best_sophieL.violated_wishes):
        stats = best_sophieL.get_participant_stats(nom)
        print(f"  - {nom:15} : {stats['jours_souhaites']}j → {stats['jours_joues']}j ({stats['ecart']:+d}j)")
    print(f"Score: {score_sop:.2f}/100")
    print()
    
    print("=" * 70)
    print("COMPARAISON")
    print("=" * 70)
    diff = score_syl - score_sop
    print(f"Sylvain lésé (5j): {score_syl:.2f}/100")
    print(f"Sophie L lésée (4j): {score_sop:.2f}/100")
    print(f"Différence: {diff:+.2f} points")
    print()
    
    if diff > 0.5:
        print("✅ SUCCÈS ! Sylvain (5j) > Sophie L (4j)")
        print(f"   L'algorithme OR-Tools favorise bien léser les gros demandeurs")
        print(f"   Différence visible: {diff:.2f} points")
    elif diff > 0:
        print("⚠️  Différence faible mais positive: {diff:.2f} points")
        print("   Peut être arrondi à l'affichage")
    else:
        print("❌ Problème: Sophie L >= Sylvain")
        print("   L'algorithme ne favorise pas assez les gros demandeurs")
elif sylvain_cases:
    print("✅ Seulement des solutions avec Sylvain lésé")
    print("   L'algorithme élimine naturellement les solutions avec Sophie L lésée")
elif sophieL_cases:
    print("⚠️  Seulement des solutions avec Sophie L lésée")
    print("   L'algorithme préfère Sophie L (problème)")
else:
    print("ℹ️  Aucun cas avec Sylvain ou Sophie L lésé individuellement")
