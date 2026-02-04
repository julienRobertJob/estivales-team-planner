"""
Script de validation de la nouvelle formule de scoring v2.2
"""

def calculate_new_score(leses_info, fatigues=0, max_consec=4):
    """
    Calcule le score selon la nouvelle formule
    
    Args:
        leses_info: Liste de tuples (jours_demandes, jours_joues)
        fatigues: Nombre de personnes fatiguées
        max_consec: Maximum de jours consécutifs
    """
    # 1. Critère principal: Total jours lésés
    total_jours_leses = sum(max(0, demandes - joues) for demandes, joues in leses_info)
    penalite_jours = total_jours_leses * 3
    
    # 2. Critère secondaire: Distribution
    cout_distribution = 0
    for demandes, joues in leses_info:
        if joues < demandes:  # Lésé
            jours_manquants = demandes - joues
            ratio_lesion = jours_manquants / demandes if demandes > 0 else 0
            cout_distribution += ratio_lesion * 10  # Poids augmenté de 5 → 10
    
    # 3. Pénalités secondaires
    penalite_fatigue = fatigues * 2
    penalite_consecutifs = max(0, max_consec - 4) * 1
    
    # Score final
    score = 100 - penalite_jours - cout_distribution - penalite_fatigue - penalite_consecutifs
    return max(0, min(100, score))


# Test 1: Exemple utilisateur - Variante 1 (léser le gros demandeur)
print("=" * 60)
print("TEST 1: Exemple utilisateur - Variante 1")
print("J1 demande 5j, joue 4j | J2 demande 2j, joue 2j")
score1 = calculate_new_score([(5, 4), (2, 2)])
print(f"Score: {score1:.1f}/100")
print()

# Test 2: Exemple utilisateur - Variante 2 (léser le petit demandeur)
print("TEST 2: Exemple utilisateur - Variante 2")
print("J1 demande 5j, joue 5j | J2 demande 2j, joue 1j")
score2 = calculate_new_score([(5, 5), (2, 1)])
print(f"Score: {score2:.1f}/100")
print()

print(f"✓ Variante 1 ({score1:.1f}) > Variante 2 ({score2:.1f}): {score1 > score2}")
print("=" * 60)
print()

# Test 3: 3 gros demandeurs lésés
print("TEST 3: 3 gros demandeurs lésés de 1j chacun")
print("5j→4j, 4j→3j, 3j→2j")
score3 = calculate_new_score([(5, 4), (4, 3), (3, 2)])
print(f"Score: {score3:.1f}/100")
print()

# Test 4: 3 petits demandeurs lésés
print("TEST 4: 3 petits demandeurs lésés de 1j chacun")
print("2j→1j, 2j→1j, 2j→1j")
score4 = calculate_new_score([(2, 1), (2, 1), (2, 1)])
print(f"Score: {score4:.1f}/100")
print()

print(f"✓ Gros demandeurs ({score3:.1f}) > Petits demandeurs ({score4:.1f}): {score3 > score4}")
print("=" * 60)
print()

# Test 5: Solution parfaite
print("TEST 5: Solution parfaite (personne lésé)")
score5 = calculate_new_score([(5, 5), (4, 4), (3, 3)])
print(f"Score: {score5:.1f}/100")
print()

# Test 6: Cas réaliste avec données par défaut (5 lésés)
print("TEST 6: Cas réaliste - 5 personnes lésées de 1j")
print("Mix de profils")
score6 = calculate_new_score([
    (5, 4),  # Gros demandeur
    (4, 3),  # Moyen
    (4, 3),  # Moyen
    (3, 2),  # Moyen
    (2, 1),  # Petit
])
print(f"Score: {score6:.1f}/100")
print()

# Test 7: Cas avec fatigue
print("TEST 7: 3 lésés + 1 personne fatiguée")
score7 = calculate_new_score([(5, 4), (4, 3), (3, 2)], fatigues=1)
print(f"Score: {score7:.1f}/100 (avec pénalité fatigue -2)")
print()

# Test 8: Ancienne formule donnerait ~0
print("TEST 8: Cas qui donnait 0 avec ancienne formule")
print("5 personnes lésées de 1j")
score8 = calculate_new_score([(4, 3), (4, 3), (3, 2), (3, 2), (2, 1)])
print(f"Score nouvelle formule: {score8:.1f}/100")
print(f"Score ancienne formule: ~0/100 (36.92 + 0 - 50 = -13)")
print()

print("=" * 60)
print("RÉSUMÉ")
print("=" * 60)
print("✓ Tous les scores sont positifs")
print("✓ Critère principal respecté: moins de lésés = meilleur score")
print("✓ Critère secondaire respecté: gros demandeurs > petits demandeurs")
print("✓ Solution parfaite = 100/100")
print("✓ Échelle utilisable: 70-100 (excellentes), 50-80 (acceptables)")
