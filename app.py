"""
Application Streamlit pour l'Organisateur d'Équipes - Estivales de Volley
Version 2.1 avec Graphiques Plotly et Assistant Multi-Passes
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent))

from src.constants import (
    TOURNAMENTS, DEFAULT_PARTICIPANTS, PARTICIPANT_COLUMNS,
    MAX_SOLUTIONS_TO_DISPLAY
)
from src.models import Participant, Tournament, SolverConfig
from src.solver import TournamentSolver, analyze_solutions
from src.validation import (
    validate_participants_data,
    validate_solution_feasibility,
    suggest_improvements
)
from src.multipass_solver import (
    MultiPassSolver,
    ConflictAnalyzer,
    format_diagnostic_message
)
from src.visualizations import (
    create_timeline_chart,
    create_heatmap_chart,
    create_workload_distribution_chart,
    create_pie_chart_distribution,
    create_consecutive_days_chart,
    create_quality_comparison_chart,
    create_gantt_chart,
    create_statistics_overview
)
from src.ui_components import (
    render_participant_editor,
    render_configuration_panel,
    render_statistics_section,
    render_solution_tabs,
    render_help_section
)

# Configuration de la page
st.set_page_config(
    page_title="Organisateur d'Estivales de Volley",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="collapsed"  # Fermée par défaut
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ======================================================
# INITIALISATION SESSION STATE
# ======================================================
def initialize_session_state():
    """Initialise les variables de session"""
    if 'data' not in st.session_state:
        st.session_state.data = DEFAULT_PARTICIPANTS.copy()
    
    if 'include_o3' not in st.session_state:
        st.session_state.include_o3 = False
    
    if 'allow_incomplete' not in st.session_state:
        st.session_state.allow_incomplete = False
    
    if 'solutions' not in st.session_state:
        st.session_state.solutions = []
    
    if 'solver_info' not in st.session_state:
        st.session_state.solver_info = {}

initialize_session_state()

# ======================================================
# HEADER
# ======================================================
st.markdown('<div class="main-header">🏐 Organisateur d\'Équipes pour les Estivales de Volley</div>', 
            unsafe_allow_html=True)
st.markdown("---")

# ======================================================
# SIDEBAR - AIDE ET CONFIGURATION
# ======================================================
with st.sidebar:
    st.header("📚 Guide Utilisateur")
    
    with st.expander("🚀 Démarrage Rapide", expanded=True):
        st.markdown("""
        ### 📋 Workflow en 5 Étapes
        
        1. **📝 Configurer** les participants
           - Nom, genre, couple
           - Vœux étapes et opens
           - Disponibilité
           
        2. **⚙️ Paramètres**
           - Inclure O3 (dimanche) ?
           - Autoriser équipes incomplètes ?
           - Nombre de solutions à chercher
           
        3. **🚀 Calculer** (20-45 secondes)
           - PASS 1 : Trouve le score optimal
           - PASS 2 : Énumère TOUTES les variantes
           
        4. **🎯 Choisir le niveau**
           - Parfaites (0 lésé)
           - Excellentes (≤1j lésé)
           - Acceptables (≤2j lésés)
           - Compromis (>2j)
           
        5. **📊 Comparer** et **💾 Exporter**
           - Analyser avec graphiques
           - Choisir la meilleure variante
           - Exporter en CSV
        """)
    
    with st.expander("📊 Comprendre les Résultats"):
        st.markdown("""
        ### 🎯 Niveaux de Compromis
        
        **🎯 Parfaites**
        - Tous les vœux respectés
        - Aucun participant lésé
        - Le scénario idéal !
        
        **🟢 Excellentes**
        - Maximum 1 jour lésé par personne
        - Impact minimal
        - Très acceptable
        
        **🟡 Acceptables**
        - Maximum 2 jours lésés par personne
        - Compromis raisonnable
        - À discuter avec les lésés
        
        **🟠 Compromis**
        - Plus de 2 jours lésés
        - Impact significatif
        - Dernier recours
        
        ---
        
        ### 📈 Indicateurs Clés
        
        **Score Qualité (0-100)**
        - 90-100 : Excellent
        - 70-89 : Très bien
        - 50-69 : Acceptable
        - <50 : À éviter si possible
        
        **Lésés**
        - Format : `Nom (-Xj)`
        - Exemple : `Sophie (-2j)` = 2 jours de moins que souhaité
        
        **Fatigue**
        - Alerte si >4 jours consécutifs
        - Pénalise le score
        - À surveiller pour bien-être
        
        **Max Consécutifs**
        - Nombre max de jours d'affilée
        - Idéal : ≤3 jours
        - Acceptable : 4 jours
        - Attention : ≥5 jours
        """)
    
    with st.expander("🎓 Algorithme (Expert)"):
        st.markdown("""
        ### 🔬 Recherche Exhaustive 2-Passes
        
        **PASS 1 : Optimisation** (5-15s)
        - Trouve le meilleur score possible
        - Utilise optimisation OR-Tools
        - Résultat : Score optimal S*
        
        **PASS 2 : Énumération** (15-30s)
        - Transforme en problème de satisfaction
        - Contrainte : score = S*
        - Énumère TOUTES les solutions
        - Résultat : 20-200 variantes
        
        **Garantie Mathématique**
        - Complétude : Toutes les solutions optimales
        - Pas de permutation manquante
        - Emilie/Delphine interchangeables trouvées
        
        ### 🎯 Critères d'Optimisation
        
        1. **Respect vœux** (poids: 1000)
           - Minimiser écarts souhaits/réalité
           
        2. **Fatigue** (poids: 500)
           - Pénaliser >3j consécutifs
           
        3. **Équipes** (poids: 10)
           - Compléter à 3 si possible
        
        Score final = (écarts × 1000) + (fatigue × 500) + (incomplet × 10)
        """)
    
    with st.expander("📅 Planning des Tournois"):
        st.markdown("""
        ### 📍 SABLES D'OR
        **Étape 1** (E1) : Samedi-Dimanche
        - 2 jours
        - Séparé Hommes/Femmes
        - Équipes de 3
        
        ### 📍 ERQUY
        **Open 1** (O1) : Lundi
        - 1 jour
        - Mixte
        - Équipes de 3
        
        **Étape 2** (E2) : Mardi-Mercredi
        - 2 jours
        - Séparé Hommes/Femmes
        - Équipes de 3
        
        ### 📍 SAINT-CAST
        **Open 2** (O2) : Jeudi
        - 1 jour
        - Mixte
        - Équipes de 3
        
        **Étape 3** (E3) : Vendredi-Samedi
        - 2 jours
        - Séparé Hommes/Femmes
        - Équipes de 3
        
        **Open 3** (O3) : Dimanche
        - 1 jour
        - Mixte
        - Équipes de 3
        - Optionnel (case à cocher)
        
        ---
        
        **Total si tout** : 9 jours (6j étapes + 3j opens)
        **Sans O3** : 8 jours (6j étapes + 2j opens)
        """)
    
    with st.expander("⚙️ Paramètres Avancés"):
        st.markdown("""
        ### 🎛️ Configuration
        
        **Inclure O3**
        - Si décoché : Ignore le dimanche final
        - Si coché : Inclut O3 dans le planning
        - Recommandé : Selon disponibilités réelles
        
        **Autoriser équipes incomplètes**
        - Si décoché : Équipes de 3 strictement
        - Si coché : Permet 1-2 joueurs
        - Recommandé : Oui si peu de participants
        
        **Solutions à chercher**
        - 50-100 : Rapide, suffisant
        - 100-200 : Plus de choix
        - 200-500 : Maximum (lent)
        - Limite l'énumération en PASS 2
        
        **Respect_Voeux**
        - Case à cocher par participant
        - Force égalité stricte souhaits = réalité
        - ⚠️ Utiliser avec parcimonie !
        - Trop de cases cochées = aucune solution
        """)
    
    with st.expander("💡 Conseils & Astuces"):
        st.markdown("""
        ### ✅ Bonnes Pratiques
        
        1. **Commencer simple**
           - Lancer avec données par défaut
           - Observer les résultats
           - Ajuster progressivement
        
        2. **Gérer les contraintes**
           - Max 2-3 Respect_Voeux cochés
           - Vœux raisonnables (≤6j total)
           - Équilibrer H/F pour étapes
        
        3. **Interpréter les résultats**
           - Privilégier niveau "Parfaites"
           - Sinon "Excellentes" très OK
           - Discuter avec les lésés si "Acceptables"
        
        4. **Utiliser les filtres**
           - "Seulement opens lésés" = étapes OK
           - "Max consécutifs" = limiter fatigue
           - "Max total lésé" = global acceptable
        
        ### ⚠️ Pièges à Éviter
        
        - ❌ Trop de Respect_Voeux
        - ❌ Vœux impossibles (ex: 3 étapes)
        - ❌ Couples avec vœux opposés
        - ❌ Trop peu de participants
        
        ### 🔧 Si Aucune Solution
        
        1. Décocher tous les Respect_Voeux
        2. Activer "Équipes incomplètes"
        3. Réduire les vœux de certains
        4. Vérifier couples (disponibilités alignées)
        """)
    
    st.markdown("---")
    
    # Bouton reset
    if st.button("🔄 Réinitialiser", type="secondary", width="stretch"):
        st.session_state.data = DEFAULT_PARTICIPANTS.copy()
        st.session_state.include_o3 = False
        st.session_state.allow_incomplete = False
        st.session_state.solutions = []
        st.session_state.solver_info = {}
        st.rerun()
    
    # Tests automatiques
    st.markdown("---")
    st.subheader("🧪 Tests")
    if st.button("▶️ Lancer Tests", width="stretch"):
        with st.spinner("Exécution des tests..."):
            import subprocess
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/test_solver.py", "-v"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            
            if result.returncode == 0:
                st.success("✅ Tous les tests passent !")
                with st.expander("Voir les détails"):
                    st.code(result.stdout)
            else:
                st.error("❌ Certains tests échouent")
                with st.expander("Voir les erreurs"):
                    st.code(result.stdout + "\n" + result.stderr)

# ======================================================
# SECTION 1: CONFIGURATION DES PARTICIPANTS
# ======================================================
st.header("1. Configuration des Participants")

col_editor, col_actions = st.columns([3, 1])

with col_editor:
    # Créer le DataFrame
    df_participants = pd.DataFrame(
        st.session_state.data,
        columns=PARTICIPANT_COLUMNS
    )
    
    # Éditeur de données
    edited_df = st.data_editor(
        df_participants,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Genre": st.column_config.SelectboxColumn(
                "Genre",
                options=['M', 'F'],
                required=True
            ),
            "Dispo_Jusqu_a": st.column_config.SelectboxColumn(
                "Dispo jusqu'à",
                options=['E1', 'O1', 'E2', 'O2', 'E3', 'O3'],
                required=True
            ),
            "Respect_Voeux": st.column_config.CheckboxColumn(
                "Respecter strictement",
                help="Si coché, les vœux de ce participant doivent être respectés exactement"
            ),
            "Voeux_Etape": st.column_config.NumberColumn(
                "Vœux Étapes",
                min_value=0,
                max_value=3,
                step=1
            ),
            "Voeux_Open": st.column_config.NumberColumn(
                "Vœux Opens",
                min_value=0,
                max_value=3,
                step=1
            )
        },
        height=min(600, 35 * (len(df_participants) + 2))
    )
    
    # Sauvegarder les modifications
    st.session_state.data = edited_df.values.tolist()

with col_actions:
    st.markdown("#### Actions Rapides")
    
    # Un seul bouton Reset qui recharge les données par défaut
    if st.button("🔄 Réinitialiser", width="stretch", help="Recharger les données par défaut"):
        st.session_state.data = DEFAULT_PARTICIPANTS.copy()
        st.session_state.include_o3 = False
        st.session_state.allow_incomplete = False
        if 'solutions' in st.session_state:
            st.session_state.solutions = []
        if 'solver_info' in st.session_state:
            st.session_state.solver_info = {}
        st.rerun()
    
    # Valider les données
    if st.button("✅ Valider Données", width="stretch"):
        try:
            participants = [
                Participant.from_dict(dict(zip(PARTICIPANT_COLUMNS, row)))
                for row in st.session_state.data
            ]
            
            errors = validate_participants_data(participants)
            
            if not errors:
                st.success("✅ Données valides !")
            else:
                for error in errors:
                    if "⚠️" in error:
                        st.warning(error)
                    else:
                        st.error(error)
        except Exception as e:
            st.error(f"Erreur: {str(e)}")
    
    # Afficher les stats
    st.markdown("#### Statistiques")
    total = len(st.session_state.data)
    hommes = sum(1 for row in st.session_state.data if row[1] == 'M')
    femmes = sum(1 for row in st.session_state.data if row[1] == 'F')
    couples = sum(1 for row in st.session_state.data if row[2]) // 2
    
    st.metric("Total", total)
    st.metric("Hommes", hommes)
    st.metric("Femmes", femmes)
    st.metric("Couples", couples)

# ======================================================
# SECTION 2: PARAMÈTRES
# ======================================================
st.markdown("---")
st.header("2. Paramètres du Planning")

col_param1, col_param2, col_param3 = st.columns(3)

with col_param1:
    st.session_state.include_o3 = st.checkbox(
        "🌅 Inclure l'Open du Dimanche (O3)",
        value=st.session_state.include_o3,
        help="Ajoute un jour supplémentaire de compétition (dimanche à Saint-Cast)"
    )

with col_param2:
    st.session_state.allow_incomplete = st.checkbox(
        "👥 Autoriser équipes incomplètes",
        value=st.session_state.allow_incomplete,
        help="Permet des équipes de 1 ou 2 joueurs (pénalisé mais accepté)"
    )

with col_param3:
    max_solutions = st.slider(
        "🔢 Solutions à chercher",
        min_value=10,
        max_value=500,
        value=500,  # Par défaut à 500
        step=10,
        help="""Nombre maximum de solutions différentes à générer.
        
        - Plus de solutions = plus de choix mais calcul plus long
        - L'algorithme s'arrête dès qu'il en trouve assez
        - Recommandé: 50-100 (rapide et suffisant)
        - Maximum: 500 (calcul long, pour cas complexes)
        - Seules les 10 meilleures seront affichées"""
    )
    
    # Sauvegarder pour utilisation dans recalcul
    st.session_state.max_solutions = max_solutions

# ======================================================
# SECTION 3: VALIDATION ET SUGGESTIONS
# ======================================================
try:
    participants = [
        Participant.from_dict(dict(zip(PARTICIPANT_COLUMNS, row)))
        for row in st.session_state.data
    ]
    
    # Vérifier la faisabilité
    active_tournaments = [t for t in TOURNAMENTS if st.session_state.include_o3 or t['id'] != 'O3']
    is_feasible, warnings = validate_solution_feasibility(
        participants,
        active_tournaments,
        st.session_state.include_o3
    )
    
    if warnings:
        with st.expander("⚠️ Avertissements", expanded=not is_feasible):
            for warning in warnings:
                st.warning(warning)
    
    # Suggestions
    config_dict = {
        'include_o3': st.session_state.include_o3,
        'allow_incomplete': st.session_state.allow_incomplete
    }
    suggestions = suggest_improvements(participants, config_dict)
    
    if suggestions:
        with st.expander("💡 Suggestions d'amélioration"):
            for suggestion in suggestions:
                st.info(suggestion)

except Exception as e:
    st.error(f"Erreur de validation: {str(e)}")
    participants = []

# ======================================================
# SECTION 4: CALCUL AVEC MULTIPASS
# ======================================================
st.markdown("---")
st.header("3. Calcul des Variantes")

if st.button("🚀 Calculer les Variantes", type="primary", width="stretch"):
    # IMPORTANT: Recréer participants depuis session_state.data
    # pour être SÛR d'utiliser les données à jour du tableau
    try:
        participants = [
            Participant.from_dict(dict(zip(PARTICIPANT_COLUMNS, row)))
            for row in st.session_state.data
        ]
        
        # Vérifier qu'on a bien des participants
        if not participants:
            st.error("❌ Aucun participant trouvé dans le tableau")
            st.stop()
            
    except Exception as e:
        import traceback
        st.error(f"❌ Erreur lors de la lecture des participants: {str(e)}")
        st.code(traceback.format_exc())
        st.stop()
    
    # DEBUG: Afficher les participants utilisés
    with st.expander("🔍 Debug: Participants utilisés pour le calcul", expanded=False):
        st.write(f"Nombre: {len(participants)}")
        for p in participants:
            st.write(f"- {p.nom} ({p.genre}): {p.voeux_etape}E + {p.voeux_open}O")
    
    # Avertissement si calcul long
    if len(participants) > 15:
        st.warning(
            "⏱️ Avec plus de 15 participants, le calcul peut prendre 30-60 secondes. "
            "Patience !"
        )
    
    # Préparer les données
    active_tournaments = [
        Tournament(**t) for t in TOURNAMENTS
        if st.session_state.include_o3 or t['id'] != 'O3'
    ]
    
    config = SolverConfig(
        include_o3=st.session_state.include_o3,
        allow_incomplete=st.session_state.allow_incomplete,
        max_solutions=max_solutions,
        timeout_seconds=60.0  # Réduit pour Streamlit Cloud (timeout 90s)
    )
    
    # Zone de progression
    progress_container = st.empty()
    status_text = st.empty()
    
    # Utiliser le MultiPassSolver
    multipass = MultiPassSolver(config)
    
    # Callback de progression
    def progress_callback(phase, message):
        if phase == "pass1":
            status_text.info(f"🔍 **Pass 1**: {message}")
        elif phase == "pass2":
            status_text.warning(f"🔍 **Pass 2**: {message}")
        elif phase == "pass3":
            status_text.info(f"🔄 **Pass 3**: {message}")
    
    # Lancer la résolution multi-passes
    status_text.text("🔨 Construction du modèle...")
    
    result = multipass.solve_multipass(
        participants,
        active_tournaments,
        progress_callback=progress_callback
    )
    
    status_text.empty()
    
    # Traiter le résultat
    if result.status == 'success':
        st.success(result.message)
        
        # Sauvegarder les solutions
        st.session_state.solutions = result.solutions
        st.session_state.solver_info = {'pass': result.pass_number}
        
        # TOUJOURS sauvegarder les candidats pour permettre le choix manuel
        if result.candidates_if_failed:
            st.session_state.candidates = result.candidates_if_failed
            st.session_state.active_tournaments = active_tournaments
            st.session_state.participants_for_relax = participants
            st.info("💡 Des solutions ont été trouvées automatiquement. Vous pouvez affiner en choisissant manuellement dans 'Aide au Choix' ci-dessous.")
        
        if result.relaxed_participants:
            st.info(f"ℹ️ Participants lésés automatiquement: {', '.join(result.relaxed_participants)}")
    
    elif result.status == 'need_user_choice':
        st.warning(result.message)
        
        # Sauvegarder TOUJOURS solutions (même vide) pour afficher l'Aide au Choix
        st.session_state.solutions = result.solutions if result.solutions else []
        st.session_state.candidates = result.candidates_if_failed
        st.session_state.solver_info = {'pass': result.pass_number}
        st.session_state.active_tournaments = active_tournaments
        st.session_state.participants_for_relax = participants
        
        st.info("👇 Voir la section 'Aide au Choix' ci-dessous pour sélectionner qui léser")
    
    elif result.status == 'impossible':
        st.error(result.message)
        
        # Diagnostic automatique
        diagnostics = ConflictAnalyzer.analyze_why_no_solution(
            participants,
            active_tournaments,
            config
        )
        
        diagnostic_message = format_diagnostic_message(diagnostics)
        st.markdown(diagnostic_message)
        
        # Sauvegarder solutions partielles si elles existent
        if result.solutions:
            st.info(f"ℹ️ {len(result.solutions)} solution(s) partielle(s) trouvée(s) malgré tout")
            st.session_state.solutions = result.solutions
            st.session_state.solver_info = {'pass': result.pass_number}
    
    else:  # partial_success
        st.warning(result.message)
        if result.solutions:
            st.session_state.solutions = result.solutions
            st.session_state.solver_info = {'pass': result.pass_number}

# ======================================================
# SECTION 5: RÉSULTATS ET AIDE AU CHOIX
# ======================================================
# Afficher si on a des solutions OU des candidats à léser
if st.session_state.solutions or ('candidates' in st.session_state and st.session_state.candidates):
    st.markdown("---")
    st.header("4. Résultats")
    
    solutions = st.session_state.solutions if st.session_state.solutions else []
    
    # Reconstruire active_tournaments pour l'affichage
    active_tournaments = [
        Tournament(**t) for t in TOURNAMENTS
        if st.session_state.include_o3 or t['id'] != 'O3'
    ]
    
    # Aide au choix - Afficher EN PREMIER si pas de solutions
    st.markdown("---")
    st.subheader("🔍 Aide au Choix")
    
    # Vérifier s'il y a des candidats proposés par le multipass
    has_candidates = 'candidates' in st.session_state and st.session_state.candidates
    
    if has_candidates:
        # CAS 1: Le multipass a identifié des candidats à léser
        st.info("💡 L'algorithme a identifié des participants qu'on peut léser pour débloquer")
        
        candidates_data = []
        for candidate in st.session_state.candidates:
            candidates_data.append({
                'Nom': candidate.participant_name,
                'Vœux Étapes': candidate.current_wishes_etape,
                'Vœux Opens': candidate.current_wishes_open,
                'Jours si lésé': candidate.impact_days_if_relaxed,
                'Action': candidate.reason
            })
        
        # Trier par jours si lésé DESCENDANT (ceux qui joueraient le plus en premier)
        df_candidates = pd.DataFrame(candidates_data).sort_values('Jours si lésé', ascending=False)
        
        st.dataframe(df_candidates, width="stretch", hide_index=True)
        
        # Créer la liste avec "Nom étape" et "Nom open" pour chaque candidat
        # Éliminer les doublons en utilisant un set
        candidate_names = list(set([c['Nom'] for c in candidates_data]))
        
        relax_options = []
        for name in sorted(candidate_names):  # Tri alphabétique
            participant = next(p for p in st.session_state.participants_for_relax if p.nom == name)
            if participant.voeux_etape > 0:
                relax_options.append(f"{name} étape")
            if participant.voeux_open > 0:
                relax_options.append(f"{name} open")
        
        # Sélection directe avec type inclus
        st.markdown("#### 👥 Sélection des lésions")
        selected_relax_with_type = st.multiselect(
            "Choisissez qui léser et comment :",
            options=relax_options,
            help="Format : 'Nom étape' pour réduire les étapes, 'Nom open' pour réduire les opens"
        )
        
        if selected_relax_with_type and st.button("🔄 Recalculer avec ces relaxations", type="primary"):
            with st.spinner("Calcul avec relaxations..."):
                # Importer RelaxationCandidate
                from src.multipass_solver import RelaxationCandidate
                
                # Parser les choix "Nom étape" ou "Nom open"
                relax_candidates = []
                for choice in selected_relax_with_type:
                    # Parser le format "Nom type"
                    if " étape" in choice:
                        name = choice.replace(" étape", "")
                        relax_type = "étape"
                    elif " open" in choice:
                        name = choice.replace(" open", "")
                        relax_type = "open"
                    else:
                        continue  # Ignoré si format invalide
                    
                    # Trouver le participant
                    participant = next((p for p in st.session_state.participants_for_relax if p.nom == name), None)
                    if not participant:
                        continue
                    
                    if relax_type == "étape":
                        # Forcer réduction d'1 étape
                        proposed_etape = max(0, participant.voeux_etape - 1)
                        proposed_open = participant.voeux_open
                        reason = "Étape -1j (manuel)"
                    else:  # "open"
                        # Forcer réduction d'1 open
                        proposed_etape = participant.voeux_etape
                        proposed_open = max(0, participant.voeux_open - 1)
                        reason = "Open -1j (manuel)"
                    
                    relax_candidates.append(RelaxationCandidate(
                        participant_name=name,
                        current_wishes_etape=participant.voeux_etape,
                        current_wishes_open=participant.voeux_open,
                        proposed_wishes_etape=proposed_etape,
                        proposed_wishes_open=proposed_open,
                        impact_days_if_relaxed=proposed_etape + proposed_open,
                        reason=reason
                    ))
                
                multipass = MultiPassSolver(SolverConfig(
                    include_o3=st.session_state.include_o3,
                    allow_incomplete=st.session_state.allow_incomplete,
                    max_solutions=st.session_state.get('max_solutions', 50),
                    timeout_seconds=60.0
                ))
                
                result = multipass.solve_with_relaxation(
                    st.session_state.participants_for_relax,
                    st.session_state.active_tournaments,
                    relax_candidates  # Passer les RelaxationCandidate avec le bon type
                )
                
                if result.status == 'success':
                    st.success(result.message)
                    st.session_state.solutions = result.solutions
                    st.session_state.solver_info = {'pass': result.pass_number, 'relaxed': selected_relax_with_type}
                    
                    # GARDER les candidats pour permettre de changer la sélection
                    # Ne PAS nettoyer candidates, participants_for_relax, active_tournaments
                    # pour permettre à l'utilisateur de refaire un autre choix
                    
                    st.rerun()
                else:
                    st.error(result.message)
    
    # CAS 2: Afficher info sur les solutions existantes (pas de filtrage automatique)
    all_violated = sorted(list(set().union(*(s.violated_wishes for s in solutions))))
    
    if all_violated and not has_candidates:
        st.info("📊 Analyse des participants lésés dans les solutions")
        
        # Tableau récapitulatif avec vraies données
        violated_stats = []
        for name in all_violated:
            # Compter dans combien de solutions cette personne est lésée
            solutions_with_violation = [s for s in solutions if name in s.violated_wishes]
            
            if solutions_with_violation:
                # Écart moyen quand lésé
                avg_ecart = sum(
                    abs(s.get_participant_stats(name)['ecart'])
                    for s in solutions_with_violation
                ) / len(solutions_with_violation)
                
                violated_stats.append({
                    'Nom': name,
                    'Lésé dans': f"{len(solutions_with_violation)}/{len(solutions)} solutions",
                    'Écart moyen': f"{avg_ecart:.1f}j"
                })
        
        if violated_stats:
            df_violated = pd.DataFrame(violated_stats)
            st.dataframe(
                df_violated,
                width="stretch",
                hide_index=True,
                height=min(300, 35 * (len(df_violated) + 1))
            )
        
        # PAS DE FILTRAGE - Afficher toutes les solutions
        filtered = solutions
    else:
        if not has_candidates:
            st.success("🎉 Toutes les solutions respectent tous les vœux !")
        filtered = solutions
    
    # Trier par qualité (qui inclut déjà la fatigue dans son calcul)
    filtered = sorted(
        filtered,
        key=lambda s: -s.get_quality_score()  # Décroissant (meilleur d'abord)
    )
    
    # Navigation par niveaux de compromis (seulement si on a des solutions)
    if solutions:
        st.markdown("---")
        st.subheader("🎯 Navigation par Niveau de Compromis")
    
    # Calculer les catégories
    perfect = []
    one_day_max = []
    two_days_max = []
    more_than_two = []
    
    for sol in solutions:
        if len(sol.violated_wishes) == 0:
            perfect.append(sol)
        else:
            # Calculer l'écart max parmi tous les participants lésés
            max_ecart = 0
            for name in sol.violated_wishes:
                stats = sol.get_participant_stats(name)
                ecart = abs(stats['ecart'])
                if ecart > max_ecart:
                    max_ecart = ecart
            
            if max_ecart == 1:
                one_day_max.append(sol)
            elif max_ecart == 2:
                two_days_max.append(sol)
            else:
                more_than_two.append(sol)
    
    # Afficher les compteurs
    st.markdown("#### 📊 Répartition des Solutions")
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("🎯 Parfaites", len(perfect))
        st.caption("0 jour lésé")
    
    with col_stat2:
        st.metric("🟢 Excellentes", len(one_day_max))
        st.caption("Max 1j lésé/personne")
    
    with col_stat3:
        st.metric("🟡 Acceptables", len(two_days_max))
        st.caption("Max 2j lésés/personne")
    
    with col_stat4:
        st.metric("🟠 Compromis", len(more_than_two))
        st.caption("Plus de 2j lésés/personne")
    
    # Sélecteur de niveau
    st.markdown("#### 🔍 Choisir le Niveau de Compromis")
    
    niveau_options = []
    if len(perfect) > 0:
        niveau_options.append(f"🎯 Parfaites ({len(perfect)})")
    if len(one_day_max) > 0:
        niveau_options.append(f"🟢 Excellentes ({len(one_day_max)})")
    if len(two_days_max) > 0:
        niveau_options.append(f"🟡 Acceptables ({len(two_days_max)})")
    if len(more_than_two) > 0:
        niveau_options.append(f"🟠 Compromis ({len(more_than_two)})")
    
    if len(niveau_options) == 0:
        st.error("Aucune solution trouvée")
        st.stop()
    
    # Par défaut, sélectionner la meilleure catégorie disponible
    niveau_selectionne = st.selectbox(
        "Niveau de compromis à afficher",
        options=niveau_options,
        index=0,
        help="Sélectionnez le niveau de compromis acceptable pour filtrer les variantes"
    )
    
    # Filtrer selon le niveau sélectionné
    if "Parfaites" in niveau_selectionne:
        filtered_by_level = perfect
        st.success(f"✅ Affichage de {len(filtered_by_level)} solutions parfaites (tous les vœux respectés)")
    elif "Excellentes" in niveau_selectionne:
        filtered_by_level = one_day_max
        st.info(f"ℹ️ Affichage de {len(filtered_by_level)} solutions excellentes (max 1 jour lésé par personne)")
    elif "Acceptables" in niveau_selectionne:
        filtered_by_level = two_days_max
        st.warning(f"⚠️ Affichage de {len(filtered_by_level)} solutions acceptables (max 2 jours lésés par personne)")
    else:
        filtered_by_level = more_than_two
        st.error(f"⚠️ Affichage de {len(filtered_by_level)} solutions compromis (>2 jours lésés par personne)")
    
    # Filtres avancés supplémentaires
    st.markdown("#### 🔧 Filtres Avancés (optionnels)")
    
    col_filt1, col_filt2, col_filt3 = st.columns(3)
    
    with col_filt1:
        # Filtre sur catégorie (opens/étapes)
        show_opens_only = st.checkbox(
            "Seulement opens lésés",
            value=False,
            help="Afficher uniquement les solutions où seuls les opens sont lésés (étapes OK)"
        )
    
    with col_filt2:
        # Filtre sur max consécutifs
        max_consecutifs_vals = [sol.max_consecutive_days for sol in filtered_by_level]
        if max_consecutifs_vals:
            min_consec = min(max_consecutifs_vals)
            max_consec = max(max_consecutifs_vals)
            
            # Si min = max, pas besoin de slider
            if min_consec == max_consec:
                st.metric("Max jours consécutifs", min_consec)
                max_consec_filter = min_consec
            else:
                max_consec_filter = st.slider(
                    "Max jours consécutifs",
                    min_value=min_consec,
                    max_value=max_consec,
                    value=max_consec,
                    help="Afficher seulement les solutions avec au plus X jours consécutifs"
                )
        else:
            max_consec_filter = 10
    
    with col_filt3:
        # Filtre sur nombre total de jours lésés
        total_jours_leses_vals = []
        for sol in filtered_by_level:
            total = sum(
                abs(sol.get_participant_stats(p.nom)['ecart'])
                for p in participants
                if sol.get_participant_stats(p.nom)['ecart'] < 0
            )
            total_jours_leses_vals.append(total)
        
        if total_jours_leses_vals and max(total_jours_leses_vals) > 0:
            max_total_lese = st.slider(
                "Max jours lésés total",
                min_value=0,
                max_value=max(total_jours_leses_vals),
                value=max(total_jours_leses_vals),
                help="Somme de tous les jours lésés pour tous les participants"
            )
        else:
            max_total_lese = 0
    
    # Appliquer les filtres avancés
    filtered = []
    
    for sol in filtered_by_level:
        # Filtre opens only
        if show_opens_only:
            only_opens = True
            for name in sol.violated_wishes:
                stats = sol.get_participant_stats(name)
                participant = next(p for p in participants if p.nom == name)
                if stats['etapes_jouees'] < participant.voeux_etape:
                    only_opens = False
                    break
            if not only_opens:
                continue
        
        # Filtre max consécutifs
        if sol.max_consecutive_days > max_consec_filter:
            continue
        
        # Filtre total jours lésés
        total_lese = sum(
            abs(sol.get_participant_stats(p.nom)['ecart'])
            for p in participants
            if sol.get_participant_stats(p.nom)['ecart'] < 0
        )
        if total_lese > max_total_lese:
            continue
        
        filtered.append(sol)
    
    if len(filtered) == 0:
        st.warning("⚠️ Aucune solution ne correspond aux filtres sélectionnés. Essayez de les assouplir.")
        st.stop()
    
    # IMPORTANT: Re-trier par score APRÈS filtrage pour avoir les 10 MEILLEURS
    filtered = sorted(
        filtered,
        key=lambda s: -s.get_quality_score()
    )
    
    # ==================== AFFICHAGE DES PROFILS DE LÉSÉS UNIQUES ====================
    st.markdown("---")
    st.subheader("👥 Profils de Lésés (liste unique)")
    st.caption("Chaque profil représente une combinaison unique de personnes lésées avec leur nombre de jours")
    
    # Créer un dictionnaire des profils : clé = signature unique, valeur = liste des solutions
    profils_dict = {}
    
    for sol in filtered:
        # Créer la liste des personnes lésées avec leurs jours
        leses = []
        for p in participants:
            stats = sol.get_participant_stats(p.nom)
            ecart = stats['ecart']
            if ecart < 0:
                leses.append((p.nom, abs(ecart)))
        
        # Trier : d'abord par jours lésés (décroissant), puis par nom alphabétique
        leses_sorted = sorted(leses, key=lambda x: (-x[1], x[0]))
        
        # Créer une signature unique pour ce profil
        signature = tuple(leses_sorted)
        
        if signature not in profils_dict:
            profils_dict[signature] = []
        profils_dict[signature].append(sol)
    
    # Afficher les profils uniques
    st.info(f"🔍 {len(profils_dict)} profil(s) unique(s) de lésions parmi {len(filtered)} solutions")
    
    # BONUS: Checkbox pour limiter à 1 solution par profil
    col_profil1, col_profil2 = st.columns([2, 3])
    
    with col_profil1:
        limit_to_best_per_profile = st.checkbox(
            "🎯 1 seule variante par profil (la meilleure)",
            value=False,
            help="Garde uniquement la solution avec le meilleur score pour chaque profil unique"
        )
    
    with col_profil2:
        if limit_to_best_per_profile:
            st.caption("✅ Mode actif : 1 solution max par profil")
        else:
            st.caption("ℹ️ Mode désactivé : toutes les variantes affichées")
    
    # Appliquer la limitation si activée
    if limit_to_best_per_profile:
        # Ne garder que la meilleure solution de chaque profil
        best_per_profile = []
        for signature, solutions in profils_dict.items():
            # Trier par score et prendre la meilleure
            best_solution = max(solutions, key=lambda s: s.get_quality_score())
            best_per_profile.append(best_solution)
        
        # Remplacer filtered par les meilleures
        filtered = sorted(best_per_profile, key=lambda s: -s.get_quality_score())
        
        st.success(f"✅ {len(filtered)} solution(s) affichée(s) (1 par profil)")
    
    # Sélecteur de profil pour filtrer
    profil_labels = []
    profil_signatures = []
    for idx, (signature, solutions) in enumerate(profils_dict.items(), 1):
        profil_str = ", ".join([f"{nom} (-{jours}j)" for nom, jours in signature])
        nb_variantes = len(solutions)
        profil_labels.append(f"Profil #{idx} : {profil_str} ({nb_variantes} variantes)")
        profil_signatures.append(signature)
    
    selected_profil_index = st.selectbox(
        "🎯 Filtrer par profil (optionnel):",
        options=["Tous les profils"] + profil_labels,
        help="Sélectionnez un profil pour afficher uniquement ses variantes",
        disabled=limit_to_best_per_profile  # Désactivé si 1 par profil activé
    )
    
    # Appliquer le filtre de profil si sélectionné (et pas en mode 1 par profil)
    if selected_profil_index != "Tous les profils" and not limit_to_best_per_profile:
        # Extraire l'index du profil
        profil_idx = profil_labels.index(selected_profil_index)
        selected_signature = profil_signatures[profil_idx]
        
        # Filtrer pour ne garder que les solutions de ce profil
        filtered = profils_dict[selected_signature]
        
        st.success(f"✅ Affichage de {len(filtered)} variantes du profil sélectionné")
        
        # Re-trier par score
        filtered = sorted(filtered, key=lambda s: -s.get_quality_score())
    
    # Créer un expander pour voir tous les profils
    with st.expander(f"📋 Voir les {len(profils_dict)} profil(s) unique(s)", expanded=True):
        for idx, (signature, solutions) in enumerate(profils_dict.items(), 1):
            # Formater le profil
            profil_str = ", ".join([f"{nom} (-{jours}j)" for nom, jours in signature])
            
            # Nombre de variantes pour ce profil
            nb_variantes = len(solutions)
            
            # Score max
            score_max = max(s.get_quality_score() for s in solutions)
            
            # Total jours lésés
            total_lese = sum(jours for _, jours in signature)
            
            # Afficher le profil avec des métriques
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(f"**Profil #{idx}** : {profil_str}")
            with col2:
                st.metric("Variantes", nb_variantes)
            with col3:
                st.metric("Total lésé", f"{total_lese}j")
            with col4:
                st.metric("Score max", f"{score_max:.0f}/100")
    
    # Comparatif des 10 meilleures variantes
    st.markdown("---")
    best_10 = filtered[:10]
    st.subheader(f"📊 Comparatif des {len(best_10)} Meilleures Variantes")
    
    if len(best_10) > 1:
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            fig_comparison = create_quality_comparison_chart(best_10)
            st.plotly_chart(fig_comparison, width="stretch", key="comp_chart")
        
        with col_comp2:
            fig_overview = create_statistics_overview(best_10)
            st.plotly_chart(fig_overview, width="stretch", key="overview_chart")
    else:
        st.info("Une seule variante disponible - voir détails ci-dessous")
    
    # Affichage des variantes
    st.markdown("---")
    st.subheader("📋 Variantes Proposées")
    
    if not filtered:
        st.warning("Aucune solution ne correspond aux critères sélectionnés.")
    else:
        # Avertissement si trop de solutions
        if len(filtered) > MAX_SOLUTIONS_TO_DISPLAY:
            st.warning(
                f"⚠️ {len(filtered)} solutions correspondent aux critères. "
                f"Seules les {MAX_SOLUTIONS_TO_DISPLAY} meilleures sont affichées "
                f"(triées par score de qualité décroissant)."
            )
        
        # Créer les tabs
        tab_labels = [
            f"Option {i+1} (Score: {s.get_quality_score():.0f}/100)"
            for i, s in enumerate(filtered[:MAX_SOLUTIONS_TO_DISPLAY])
        ]
        
        tabs = st.tabs(tab_labels)
        
        for i, tab in enumerate(tabs):
            with tab:
                solution = filtered[i]
                
                # Header de la solution
                col_head1, col_head2, col_head3 = st.columns(3)
                
                with col_head1:
                    if solution.violated_wishes:
                        # Calculer les détails avec jours lésés
                        details = []
                        for nom in sorted(solution.violated_wishes):
                            stats = solution.get_participant_stats(nom)
                            ecart = stats['ecart']
                            details.append(f"{nom} ({ecart:+d}j)")
                        
                        st.warning(
                            f"🚨 **Lésés** : {', '.join(details)}"
                        )
                    else:
                        st.success("✅ **Tous les vœux respectés**")
                
                with col_head2:
                    if solution.fatigue_participants:
                        st.error(
                            f"🥵 **Fatigue** : {', '.join(solution.fatigue_participants)}"
                        )
                    else:
                        st.success("✅ **Max 3 jours consécutifs**")
                
                with col_head3:
                    st.metric(
                        "Score Qualité",
                        f"{solution.get_quality_score():.0f}/100",
                        help="Score calculé: 60pts vœux respectés - 10pts/j lésé - 5pts/personne fatiguée - 3pts/j consécutif>4"
                    )
                
                # Graphiques de détail de cette variante
                st.markdown("### 📈 Analyses de cette Variante")
                
                col_ana1, col_ana2 = st.columns(2)
                
                with col_ana1:
                    fig_workload = create_workload_distribution_chart(solution)
                    st.plotly_chart(fig_workload, width="stretch", key=f"workload_{i}")
                
                with col_ana2:
                    fig_consecutive = create_consecutive_days_chart(solution)
                    st.plotly_chart(fig_consecutive, width="stretch", key=f"consecutive_{i}")
                
                # Planning par lieu
                st.markdown("### 📍 Planning par Lieu")
                
                # Regrouper par lieu
                lieux = {}
                for t in active_tournaments:
                    if t.lieu not in lieux:
                        lieux[t.lieu] = []
                    lieux[t.lieu].append(t)
                
                for lieu_idx, (lieu, tournois) in enumerate(lieux.items(), 1):
                    st.markdown(f"#### {lieu_idx}. {lieu}")
                    
                    with st.container(border=True):
                        for tournoi in tournois:
                            teams = solution.assignments[tournoi.id]
                            
                            st.markdown(f"##### {tournoi.label} ({', '.join(tournoi.day_labels)})")
                            
                            if tournoi.is_etape:
                                col_m, col_f = st.columns(2)
                                
                                with col_m:
                                    nb_teams = len(teams['M']) // 3
                                    remainder = len(teams['M']) % 3
                                    team_str = f"{nb_teams} équipe(s)"
                                    if remainder > 0:
                                        team_str += f" + {remainder}"
                                    
                                    st.markdown(f"♂️ **Hommes** ({team_str})")
                                    if teams['M']:
                                        st.write(", ".join(sorted(teams['M'])))
                                    else:
                                        st.write("*Aucun*")
                                
                                with col_f:
                                    nb_teams = len(teams['F']) // 3
                                    remainder = len(teams['F']) % 3
                                    team_str = f"{nb_teams} équipe(s)"
                                    if remainder > 0:
                                        team_str += f" + {remainder}"
                                    
                                    st.markdown(f"♀️ **Femmes** ({team_str})")
                                    if teams['F']:
                                        st.write(", ".join(sorted(teams['F'])))
                                    else:
                                        st.write("*Aucune*")
                            
                            else:  # Open
                                nb_teams = len(teams['All']) // 3
                                remainder = len(teams['All']) % 3
                                team_str = f"{nb_teams} équipe(s)"
                                if remainder > 0:
                                    team_str += f" + {remainder}"
                                
                                st.markdown(f"👫 **Mixte** ({team_str})")
                                if teams['All']:
                                    st.write(", ".join(sorted(teams['All'])))
                                else:
                                    st.write("*Aucun*")
                            
                            st.markdown("")  # Espace
                
                # Tableau récapitulatif
                st.markdown("---")
                st.markdown("### 📈 Bilan Détaillé")
                
                recap_data = []
                total_days = 0
                
                # IMPORTANT: Utiliser solution.participants pour avoir les données
                # qui ont été utilisées lors du calcul, pas celles du tableau actuel
                for participant in solution.participants:
                    stats = solution.get_participant_stats(participant.nom)
                    
                    recap_data.append({
                        'Nom': participant.nom,
                        'Souhait Étapes': participant.voeux_etape,
                        'Joué Étapes': stats['etapes_jouees'],
                        'Souhait Opens': participant.voeux_open,
                        'Joué Opens': stats['opens_joues'],
                        'Total Souhaité': stats['jours_souhaites'],
                        'Total Joué': stats['jours_joues'],
                        'Écart': stats['ecart'],
                        'Max Consécutifs': stats['max_consecutifs']
                    })
                    
                    total_days += stats['jours_joues']
                
                df_recap = pd.DataFrame(recap_data).sort_values(
                    'Total Joué',
                    ascending=False
                )
                
                # Fonction de coloration des écarts
                def color_ecart(val):
                    """Colore selon l'écart: rouge si ±2+, orange si ±1"""
                    if val == 0:
                        return 'background-color: #28a745; color: white'  # Vert
                    elif abs(val) == 1:
                        return 'background-color: #FFA500; color: white'  # Orange
                    elif abs(val) >= 2:
                        return 'background-color: #DC3545; color: white'  # Rouge
                    return ''
                
                # Appliquer le style
                styled_df = df_recap.style.map(
                    color_ecart,
                    subset=['Écart']
                )
                
                st.dataframe(
                    styled_df,
                    width="stretch",
                    hide_index=True,
                    height=35 * (len(df_recap) + 1),
                    column_config={
                        'Écart': st.column_config.NumberColumn(
                            'Écart',
                            help="Différence entre joué et souhaité (+ = plus, - = moins). Vert=0, Orange=±1, Rouge=±2+"
                        )
                    }
                )
                
                # Moyenne
                avg_days = total_days / len(participants) if participants else 0
                st.metric(
                    "📊 Moyenne de jours joués par participant",
                    f"{avg_days:.1f} jours"
                )
                
                # Bouton d'export
                if st.button(f"💾 Exporter cette solution", key=f"export_{i}"):
                    csv = df_recap.to_csv(index=False)
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv,
                        file_name=f"solution_estivales_{i+1}.csv",
                        mime="text/csv"
                    )
else:
    # Pas de solutions, seulement Aide au Choix affichée
    st.info("ℹ️ Aucune solution trouvée. Utilisez l'Aide au Choix ci-dessus pour débloquer la situation.")

# ======================================================
# FOOTER
# ======================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Organisateur d'Estivales de Volley v2.0 | "
    "Optimisé avec OR-Tools | "
    "Tests automatiques inclus"
    "</div>",
    unsafe_allow_html=True
)
