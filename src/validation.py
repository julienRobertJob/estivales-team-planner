"""
Validation des données d'entrée
"""
from typing import List, Dict, Tuple
import pandas as pd
from src.models import Participant
from src.constants import VALID_GENRES, VALID_TOURNAMENT_IDS


class ValidationError(Exception):
    """Erreur de validation des données"""
    pass


def validate_participants_data(participants: List[Participant]) -> List[str]:
    """
    Valide les données des participants.
    
    Args:
        participants: Liste des participants
        
    Returns:
        Liste des erreurs trouvées (vide si tout est OK)
    """
    errors = []
    
    # Vérifier qu'il y a des participants
    if not participants:
        errors.append("Aucun participant défini")
        return errors
    
    # Vérifier les noms uniques
    names = [p.nom for p in participants]
    duplicates = [name for name in set(names) if names.count(name) > 1]
    if duplicates:
        errors.append(f"Noms en double: {', '.join(duplicates)}")
    
    # Créer un mapping nom -> participant
    participants_map = {p.nom: p for p in participants}
    
    # Vérifier les couples
    for participant in participants:
        if participant.couple:
            # Le partenaire existe-t-il ?
            if participant.couple not in participants_map:
                errors.append(
                    f"{participant.nom}: couple '{participant.couple}' introuvable"
                )
            else:
                partner = participants_map[participant.couple]
                
                # Le couple est-il bidirectionnel ?
                if partner.couple != participant.nom:
                    errors.append(
                        f"Couple non bidirectionnel: {participant.nom} dit être avec "
                        f"{participant.couple}, mais {participant.couple} dit être avec "
                        f"{partner.couple or 'personne'}"
                    )
                
                # Les genres sont-ils différents pour les étapes ?
                if participant.genre == partner.genre:
                    errors.append(
                        f"Attention: {participant.nom} et {participant.couple} ont le même "
                        f"genre ({participant.genre}). Cela peut limiter les possibilités "
                        f"dans les étapes (séparées H/F)."
                    )
    
    # Vérifier la cohérence des disponibilités dans les couples
    for participant in participants:
        if participant.couple:
            partner = participants_map.get(participant.couple)
            if partner:
                p_idx = VALID_TOURNAMENT_IDS.index(participant.dispo_jusqu_a)
                partner_idx = VALID_TOURNAMENT_IDS.index(partner.dispo_jusqu_a)
                
                if abs(p_idx - partner_idx) > 1:
                    errors.append(
                        f"Attention: {participant.nom} est disponible jusqu'à "
                        f"{participant.dispo_jusqu_a} mais son couple {participant.couple} "
                        f"jusqu'à {partner.dispo_jusqu_a}. Grande différence de disponibilité."
                    )
    
    # Vérifier que quelqu'un veut jouer
    if all(p.voeux_etape == 0 and p.voeux_open == 0 for p in participants):
        errors.append("Personne ne veut jouer (tous les vœux sont à 0)")
    
    # Avertissements sur les contraintes strictes
    strict_count = sum(1 for p in participants if p.respect_voeux)
    if strict_count == len(participants):
        errors.append(
            f"⚠️ Tous les participants ont 'Respect_Voeux' activé. "
            f"Cela peut rendre impossible de trouver des solutions. "
            f"Envisagez de relâcher cette contrainte pour certains participants."
        )
    
    return errors


def validate_solution_feasibility(
    participants: List[Participant],
    tournaments: List[Dict],
    include_o3: bool
) -> Tuple[bool, List[str]]:
    """
    Vérifie si une solution est théoriquement possible.
    
    Args:
        participants: Liste des participants
        tournaments: Liste des tournois
        include_o3: Inclure l'open O3
        
    Returns:
        Tuple (is_feasible, warnings)
    """
    warnings = []
    
    # Filtrer les tournois actifs
    active_tournaments = [
        t for t in tournaments
        if include_o3 or t['id'] != 'O3'
    ]
    
    # Compter les places disponibles par genre pour les étapes
    etapes = [t for t in active_tournaments if t['type'] == 'etape']
    opens = [t for t in active_tournaments if t['type'] == 'open']
    
    # Vérifier les hommes
    men = [p for p in participants if p.genre == 'M']
    total_men_wishes_etapes = sum(p.voeux_etape for p in men)
    max_men_etapes = len(etapes) * 10  # Arbitraire: max 10 équipes par étape
    
    if total_men_wishes_etapes > max_men_etapes:
        warnings.append(
            f"⚠️ Les hommes veulent jouer {total_men_wishes_etapes} étapes au total, "
            f"mais seulement ~{max_men_etapes} places disponibles"
        )
    
    # Vérifier les femmes
    women = [p for p in participants if p.genre == 'F']
    total_women_wishes_etapes = sum(p.voeux_etape for p in women)
    max_women_etapes = len(etapes) * 10
    
    if total_women_wishes_etapes > max_women_etapes:
        warnings.append(
            f"⚠️ Les femmes veulent jouer {total_women_wishes_etapes} étapes au total, "
            f"mais seulement ~{max_women_etapes} places disponibles"
        )
    
    # Vérifier les opens (mixtes)
    total_open_wishes = sum(p.voeux_open for p in participants)
    max_opens = len(opens) * 10
    
    if total_open_wishes > max_opens:
        warnings.append(
            f"⚠️ Total de {total_open_wishes} opens souhaités, "
            f"mais seulement ~{max_opens} places disponibles"
        )
    
    # Vérifier les contraintes strictes vs ressources
    strict_participants = [p for p in participants if p.respect_voeux]
    
    if strict_participants:
        strict_etapes = sum(p.voeux_etape for p in strict_participants)
        strict_opens = sum(p.voeux_open for p in strict_participants)
        
        if strict_etapes > len(etapes) * 3:  # Au moins 1 équipe par étape
            warnings.append(
                f"⚠️ {len(strict_participants)} participants ont des vœux stricts totalisant "
                f"{strict_etapes} étapes. Risque de solution impossible."
            )
    
    is_feasible = len(warnings) == 0
    
    return is_feasible, warnings


def check_couples_consistency(participants: List[Participant]) -> List[str]:
    """
    Vérifie la cohérence des couples.
    
    Args:
        participants: Liste des participants
        
    Returns:
        Liste des erreurs
    """
    errors = []
    participants_map = {p.nom: p for p in participants}
    
    processed_pairs = set()
    
    for participant in participants:
        if not participant.couple:
            continue
        
        pair = tuple(sorted([participant.nom, participant.couple]))
        
        if pair in processed_pairs:
            continue
        
        processed_pairs.add(pair)
        
        partner = participants_map.get(participant.couple)
        
        if not partner:
            errors.append(f"{participant.nom}: partenaire {participant.couple} introuvable")
            continue
        
        # Vérifier bidirectionnalité
        if partner.couple != participant.nom:
            errors.append(
                f"Couple {participant.nom} <-> {participant.couple} : "
                f"{participant.couple} est en couple avec {partner.couple or 'personne'}"
            )
        
        # Vérifier que les deux ne veulent pas jouer le même jour impossible
        # (cette vérification est complexe, on la fera dans le solver)
    
    return errors


def suggest_improvements(
    participants: List[Participant],
    config: Dict
) -> List[str]:
    """
    Suggère des améliorations pour augmenter les chances de trouver une solution.
    
    Args:
        participants: Liste des participants
        config: Configuration du solver
        
    Returns:
        Liste de suggestions
    """
    suggestions = []
    
    # Vérifier si trop de contraintes strictes
    strict_count = sum(1 for p in participants if p.respect_voeux)
    if strict_count > len(participants) * 0.7:
        suggestions.append(
            "💡 Envisagez de décocher 'Respecter strictement les vœux' pour certains "
            "participants afin d'augmenter les chances de trouver une solution."
        )
    
    # Vérifier les équipes incomplètes
    if not config.get('allow_incomplete', False):
        suggestions.append(
            "💡 Activer 'Autoriser équipes incomplètes' peut aider à trouver des solutions "
            "si le nombre de participants ne tombe pas juste."
        )
    
    # Vérifier l'inclusion de O3
    if not config.get('include_o3', False):
        total_wishes = sum(p.voeux_jours_total for p in participants)
        if total_wishes > 24:  # 8 jours max sans O3
            suggestions.append(
                "💡 Inclure l'Open du Dimanche (O3) pourrait permettre de satisfaire "
                "plus de vœux (actuellement beaucoup de demande)."
            )
    
    # Vérifier les couples avec des vœux très différents
    participants_map = {p.nom: p for p in participants}
    for participant in participants:
        if participant.couple:
            partner = participants_map.get(participant.couple)
            if partner:
                diff = abs(participant.voeux_jours_total - partner.voeux_jours_total)
                if diff >= 3:
                    suggestions.append(
                        f"💡 {participant.nom} et {participant.couple} ont des vœux très "
                        f"différents ({participant.voeux_jours_total}j vs "
                        f"{partner.voeux_jours_total}j). La contrainte de couple peut "
                        f"rendre difficile de satisfaire les deux."
                    )
    
    return suggestions
