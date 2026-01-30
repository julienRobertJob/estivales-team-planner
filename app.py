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
    initial_sidebar_state="expanded"
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
    st.header("📚 Aide")
    
    with st.expander("ℹ️ Comment utiliser"):
        st.markdown("""
        ### Étapes
        1. **Configurer les participants** avec leurs vœux
        2. **Ajuster les paramètres** (Include O3, équipes incomplètes)
        3. **Lancer le calcul** avec le bouton vert
        4. **Analyser les variantes** proposées
        5. **Choisir** la meilleure solution
        
        ### Conseils
        - Utilisez 'Respect_Voeux' avec parcimonie
        - Activez 'Équipes incomplètes' si besoin
        - Plus de vœux stricts = moins de solutions possibles
        """)
    
    with st.expander("🔍 Comprendre les résultats"):
        st.markdown("""
        ### Indicateurs
        - **Lésés**: Participants dont les vœux ne sont pas respectés
        - **Fatigue**: Participants jouant >3 jours consécutifs
        - **Score qualité**: Note de 0 à 100 de la solution
        
        ### Priorités
        1. Respecter les vœux de chacun
        2. Éviter >3 jours consécutifs
        3. Équilibrer les charges
        4. Compléter les équipes
        """)
    
    with st.expander("📅 Disponibilité"):
        st.markdown("""
        ### Colonne "Dispo jusqu'à"
        
        Indique le **dernier tournoi** auquel le participant peut participer.
        
        **Exemples** :
        - `E1` = Disponible uniquement pour l'Étape 1 (Sam-Dim)
        - `E2` = Disponible jusqu'à l'Étape 2 (Mar-Mer) inclus
        - `O3` = Disponible pour tous les tournois
        
        **Planning des tournois** :
        - E1 : Samedi-Dimanche (SABLES D'OR)
        - O1 : Lundi (ERQUY)
        - E2 : Mardi-Mercredi (ERQUY)
        - O2 : Jeudi (SAINT-CAST)
        - E3 : Vendredi-Samedi (SAINT-CAST)
        - O3 : Dimanche (SAINT-CAST)
        """)
    
    st.markdown("---")
    
    # Bouton reset
    if st.button("🔄 Réinitialiser", type="secondary", use_container_width=True):
        st.session_state.data = DEFAULT_PARTICIPANTS.copy()
        st.session_state.include_o3 = False
        st.session_state.allow_incomplete = False
        st.session_state.solutions = []
        st.session_state.solver_info = {}
        st.rerun()
    
    # Tests automatiques
    st.markdown("---")
    st.subheader("🧪 Tests")
    if st.button("▶️ Lancer Tests", use_container_width=True):
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
        use_container_width=True,
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
    if st.button("🔄 Réinitialiser", use_container_width=True, help="Recharger les données par défaut"):
        st.session_state.data = DEFAULT_PARTICIPANTS.copy()
        st.session_state.include_o3 = False
        st.session_state.allow_incomplete = False
        if 'solutions' in st.session_state:
            st.session_state.solutions = []
        if 'solver_info' in st.session_state:
            st.session_state.solver_info = {}
        st.rerun()
    
    # Valider les données
    if st.button("✅ Valider Données", use_container_width=True):
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
        max_value=100,
        value=50,
        step=10,
        help="""Nombre maximum de solutions différentes à générer.
        
        - Plus de solutions = plus de choix mais calcul plus long
        - L'algorithme s'arrête dès qu'il en trouve assez
        - Avec 50-100, vous ne ratez aucune solution intéressante
        - Seules les 10 meilleures seront affichées"""
    )

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

if st.button("🚀 Calculer les Variantes", type="primary", use_container_width=True):
    if not participants:
        st.error("❌ Veuillez configurer au moins un participant valide")
    else:
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
            
            if result.relaxed_participants:
                st.info(f"ℹ️ Participants lésés: {', '.join(result.relaxed_participants)}")
        
        elif result.status == 'need_user_choice':
            st.warning(result.message)
            
            # Sauvegarder les solutions partielles et les candidats
            if result.solutions:
                st.session_state.solutions = result.solutions
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
# SECTION 5: RÉSULTATS
# ======================================================
if st.session_state.solutions:
    st.markdown("---")
    st.header("4. Résultats")
    
    solutions = st.session_state.solutions
    
    # Reconstruire active_tournaments pour l'affichage
    active_tournaments = [
        Tournament(**t) for t in TOURNAMENTS
        if st.session_state.include_o3 or t['id'] != 'O3'
    ]
    
    # Statistiques générales
    st.subheader("📊 Statistiques Générales")
    
    stats = analyze_solutions(solutions)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Solutions",
            stats['total'],
            help="Nombre total de solutions trouvées"
        )
    
    with col2:
        pct = (stats['perfect'] / stats['total'] * 100) if stats['total'] > 0 else 0
        st.metric(
            "✅ Parfaites",
            stats['perfect'],
            delta=f"{pct:.0f}%",
            help="Tous les vœux respectés"
        )
    
    with col3:
        st.metric(
            "⚠️ 1 Vœu",
            stats['one_violated'],
            help="1 seul vœu non respecté"
        )
    
    with col4:
        st.metric(
            "⚠️⚠️ 2 Vœux",
            stats['two_violated'],
            help="2 vœux non respectés"
        )
    
    with col5:
        st.metric(
            "❌ 3+ Vœux",
            stats['three_plus_violated'],
            help="3 vœux ou plus non respectés"
        )
    
    # Qualité moyenne
    st.metric(
        "Score Qualité Moyen",
        f"{stats['avg_quality']:.1f}/100",
        help="Score moyen de toutes les solutions (plus élevé = mieux)"
    )
    
    # Aide au choix - FUSIONNÉE
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
        
        st.dataframe(df_candidates, use_container_width=True, hide_index=True)
        
        # Sélection
        selected_to_relax = st.multiselect(
            "Sélectionnez qui accepter de léser:",
            options=[c['Nom'] for c in candidates_data],
            help="Cochez les participants dont vous acceptez de ne pas respecter entièrement les vœux"
        )
        
        if selected_to_relax and st.button("🔄 Recalculer avec ces relaxations", type="primary"):
            with st.spinner("Calcul avec relaxations..."):
                multipass = MultiPassSolver(SolverConfig(
                    include_o3=st.session_state.include_o3,
                    allow_incomplete=st.session_state.allow_incomplete,
                    max_solutions=max_solutions,
                    timeout_seconds=60.0
                ))
                
                result = multipass.solve_with_relaxation(
                    st.session_state.participants_for_relax,
                    st.session_state.active_tournaments,
                    relax_names=selected_to_relax
                )
                
                if result.status == 'success':
                    st.success(result.message)
                    st.session_state.solutions = result.solutions
                    st.session_state.solver_info = {'pass': result.pass_number}
                    # Nettoyer les candidats
                    if 'candidates' in st.session_state:
                        del st.session_state.candidates
                    st.rerun()
                else:
                    st.error(result.message)
    
    # CAS 2: Filtrer les solutions existantes par participants lésés
    all_violated = sorted(list(set().union(*(s.violated_wishes for s in solutions))))
    
    if all_violated and not has_candidates:
        st.info("📊 Certains participants ont leurs vœux non respectés dans les solutions")
        
        col_filter1, col_filter2 = st.columns([2, 3])
        
        with col_filter1:
            accepted_violated = st.multiselect(
                "Filtrer par participants lésés acceptés:",
                options=all_violated,
                help="Sélectionnez pour ne voir que les solutions où SEULEMENT ces participants sont lésés"
            )
        
        with col_filter2:
            # Tableau récapitulatif avec données correctes
            violated_stats = []
            for name in all_violated:
                # Trouver les stats dans les solutions où cette personne est lésée
                days_when_violated = [
                    s.get_participant_stats(name)['jours_joues']
                    for s in solutions
                    if name in s.violated_wishes
                ]
                
                if days_when_violated:
                    violated_stats.append({
                        'Nom': name,
                        'Jours si lésé': max(days_when_violated)  # Max pour montrer le meilleur cas
                    })
            
            if violated_stats:
                df_violated = pd.DataFrame(violated_stats).sort_values(
                    'Jours si lésé',
                    ascending=False  # DESCENDANT: les plus hauts en premier
                )
                
                st.dataframe(
                    df_violated,
                    use_container_width=True,
                    hide_index=True,
                    height=min(300, 35 * (len(df_violated) + 1))
                )
        
        # Filtrer les solutions
        if accepted_violated:
            filtered = [
                s for s in solutions
                if s.violated_wishes.issubset(set(accepted_violated))
            ]
        else:
            filtered = solutions
    else:
        if not has_candidates:
            st.success("🎉 Toutes les solutions respectent tous les vœux !")
        filtered = solutions
    
    # Trier par max_consecutive_days puis qualité
    filtered = sorted(
        filtered,
        key=lambda s: (s.max_consecutive_days, -s.get_quality_score())
    )
    
    # Visualisations interactives
    st.markdown("---")
    st.subheader("📊 Visualisations Interactives")
    
    tab_viz1, tab_viz2, tab_viz3 = st.tabs(["📈 Comparaisons", "📅 Calendrier", "🎯 Détails"])
    
    with tab_viz1:
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            if len(filtered) > 0:
                fig_comparison = create_quality_comparison_chart(filtered[:10])
                st.plotly_chart(fig_comparison, use_container_width=True, key="comp_chart")
        
        with col_comp2:
            if len(filtered) > 0:
                fig_pie = create_pie_chart_distribution(filtered[0])
                st.plotly_chart(fig_pie, use_container_width=True, key="pie_chart")
    
    with tab_viz2:
        if len(filtered) > 0:
            col_cal1, col_cal2 = st.columns(2)
            
            with col_cal1:
                fig_timeline = create_timeline_chart(filtered[0], active_tournaments)
                st.plotly_chart(fig_timeline, use_container_width=True, key="timeline_chart")
            
            with col_cal2:
                fig_heatmap = create_heatmap_chart(filtered[0])
                st.plotly_chart(fig_heatmap, use_container_width=True, key="heatmap_chart")
    
    with tab_viz3:
        if len(filtered) > 0:
            fig_workload = create_workload_distribution_chart(filtered[0])
            st.plotly_chart(fig_workload, use_container_width=True, key="workload_chart")
            
            fig_consecutive = create_consecutive_days_chart(filtered[0])
            st.plotly_chart(fig_consecutive, use_container_width=True, key="consecutive_chart")
    
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
                f"(triées par fatigue puis qualité)."
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
                        st.warning(
                            f"🚨 **Lésés** : {', '.join(sorted(solution.violated_wishes))}"
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
                        f"{solution.get_quality_score():.0f}/100"
                    )
                
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
                
                for participant in participants:
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
                
                st.dataframe(
                    df_recap,
                    use_container_width=True,
                    hide_index=True,
                    height=35 * (len(df_recap) + 1),
                    column_config={
                        'Écart': st.column_config.NumberColumn(
                            'Écart',
                            help="Différence entre joué et souhaité (+ = plus que voulu, - = moins)"
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
