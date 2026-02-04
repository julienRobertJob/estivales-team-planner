"""Test du scoring actuel avec les données par défaut"""

# Exemple d'analyse avec les données par défaut
# Total demandé : 
# - Delphine: 2 étapes = 4j
# - Emilie: 2 étapes = 4j  
# - Hugo: 1 étape + 1 open = 3j
# - Julien: 1 étape + 1 open = 3j
# - Kathleen: 2 étapes = 4j
# - Lise: 1 étape + 2 opens = 4j
# - Rémy: 2 étapes + 1 open = 5j
# - Robin: 2 étapes + 1 open = 5j
# - Sébastien A: 1 open = 1j
# - Sébastien S: 1 étape + 2 opens = 4j
# - Sophie L: 1 étape + 2 opens = 4j
# - Sophie S: 2 étapes + 1 open = 5j
# - Sylvain: 2 étapes + 1 open = 5j

# Total demandé: 51 jours
# Total disponible: 6 tournois × 3 places × 2-3 jours = ~54 jours théoriques
# Mais avec contraintes couples + disponibilités, souvent impossible d'avoir solution parfaite

# Problème actuel:
# Exemple solution "acceptable" (3 personnes lésées de 1j chacune):
# - 13 participants, 10 respectés, 3 lésés
# - Total jours lésés: 3

# Calcul actuel:
# wishes_score = (10/13) × 60 = 46.15
# ecart_penalty = 3 × 10 = 30
# balance_bonus = 40 × (1 - (3/(0.3×13))) × (1 - 3/10) = 40 × 0.23 × 0.7 = 6.44
# fatigue_penalty = 0 (aucun)
# consecutive_penalty = 0 (aucun)
# Score = 46.15 + 6.44 - 30 - 0 - 0 = 22.59

# Mais si 4 lésés de 1j:
# wishes_score = (9/13) × 60 = 41.54
# ecart_penalty = 4 × 10 = 40
# balance_bonus = 0 (>30%)
# Score = 41.54 + 0 - 40 = 1.54

# Avec 5 lésés:
# wishes_score = (8/13) × 60 = 36.92
# ecart_penalty = 5 × 10 = 50
# Score = 36.92 - 50 = -13.08 → 0

print("Analyse terminée - voir commentaires dans le fichier")
