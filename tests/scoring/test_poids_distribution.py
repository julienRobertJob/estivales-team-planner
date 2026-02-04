"""
Validation du poids augmenté de distribution (5 → 10)
Cas utilisateur: Sophie S lésée dans les 2 cas, Sylvain vs Sophie L
"""

# Données par défaut (rappel)
demandes = {
    'Hugo': 1 * 2 + 1,  # 1 étape + 1 open = 3j
    'Rémy': 2 * 2 + 1,  # 2 étapes + 1 open = 5j
    'Sophie L': 1 * 2 + 2,  # 1 étape + 2 opens = 4j
    'Sophie S': 2 * 2 + 1,  # 2 étapes + 1 open = 5j
    'Sébastien S': 1 * 2 + 2,  # 1 étape + 2 opens = 4j
    'Sylvain': 2 * 2 + 1,  # 2 étapes + 1 open = 5j
}

print("=" * 70)
print("CAS UTILISATEUR: Même total de jours lésés (6j)")
print("=" * 70)
print()

# Solution 1: Hugo, Rémy, Sophie S (-2j), Sylvain, Sébastien S lésés
print("SOLUTION 1: Sylvain lésé (au lieu de Sophie L)")
print("-" * 70)
leses_1 = [
    ('Hugo', 3, 1),
    ('Rémy', 5, 1),
    ('Sophie S', 5, 2),
    ('Sylvain', 5, 1),
    ('Sébastien S', 4, 1),
]

total_jours = sum(manque for _, _, manque in leses_1)
print(f"Total jours lésés: {total_jours}j")
print()

cout_distrib_1 = 0
for nom, demande, manque in leses_1:
    ratio = manque / demande
    cout = ratio * 10  # Nouveau poids
    cout_distrib_1 += cout
    print(f"  {nom:12} : {demande}j demandés, lésé {manque}j → ratio={ratio:.3f} → coût={cout:.2f}")

penalite_jours = total_jours * 3
score_1 = 100 - penalite_jours - cout_distrib_1

print()
print(f"Pénalité jours: {total_jours} × 3 = {penalite_jours}")
print(f"Pénalité distribution: {cout_distrib_1:.2f}")
print(f"Score = 100 - {penalite_jours} - {cout_distrib_1:.2f} = {score_1:.2f} / 100")
print()

# Solution 2: Hugo, Rémy, Sophie L, Sophie S (-2j), Sébastien S lésés
print("=" * 70)
print("SOLUTION 2: Sophie L lésée (au lieu de Sylvain) - MOINS BIEN")
print("-" * 70)
leses_2 = [
    ('Hugo', 3, 1),
    ('Rémy', 5, 1),
    ('Sophie L', 4, 1),  # 4j au lieu de 5j (Sylvain)
    ('Sophie S', 5, 2),
    ('Sébastien S', 4, 1),
]

total_jours_2 = sum(manque for _, _, manque in leses_2)
print(f"Total jours lésés: {total_jours_2}j")
print()

cout_distrib_2 = 0
for nom, demande, manque in leses_2:
    ratio = manque / demande
    cout = ratio * 10  # Nouveau poids
    cout_distrib_2 += cout
    print(f"  {nom:12} : {demande}j demandés, lésé {manque}j → ratio={ratio:.3f} → coût={cout:.2f}")

penalite_jours_2 = total_jours_2 * 3
score_2 = 100 - penalite_jours_2 - cout_distrib_2

print()
print(f"Pénalité jours: {total_jours_2} × 3 = {penalite_jours_2}")
print(f"Pénalité distribution: {cout_distrib_2:.2f}")
print(f"Score = 100 - {penalite_jours_2} - {cout_distrib_2:.2f} = {score_2:.2f} / 100")
print()

# Comparaison
print("=" * 70)
print("COMPARAISON")
print("=" * 70)
print(f"Solution 1 (Sylvain 5j lésé)  : {score_1:.2f} / 100")
print(f"Solution 2 (Sophie L 4j lésé) : {score_2:.2f} / 100")
print()
print(f"Différence: {abs(score_1 - score_2):.2f} points")
print()

if score_1 > score_2:
    print("✅ Solution 1 > Solution 2")
    print("   → On préfère léser Sylvain (5j) plutôt que Sophie L (4j)")
    print("   → Critère secondaire respecté !")
else:
    print("❌ Problème: Solution 2 >= Solution 1")

print()
print("=" * 70)
print("ANALYSE DU POIDS")
print("=" * 70)
print(f"Différence de ratio: 0.250 - 0.200 = 0.050")
print(f"Avec ancien poids (×5): 0.050 × 5 = 0.25 points → arrondi invisible")
print(f"Avec nouveau poids (×10): 0.050 × 10 = 0.50 points → visible ✓")
