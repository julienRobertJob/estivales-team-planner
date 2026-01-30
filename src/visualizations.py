"""
Visualisations interactives avec Plotly
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict
import numpy as np

from src.models import Solution, Participant, Tournament


def create_timeline_chart(solution: Solution, tournaments: List[Tournament]) -> go.Figure:
    """
    Crée une timeline visuelle montrant qui joue quand
    
    Args:
        solution: Solution à visualiser
        tournaments: Liste des tournois
        
    Returns:
        Figure Plotly
    """
    # Préparer les données
    data = []
    
    for participant in solution.participants:
        stats = solution.get_participant_stats(participant.nom)
        presence = stats['presence']
        
        for day in range(len(presence)):
            if presence[day]:
                # Trouver le tournoi de ce jour
                tournament_day = None
                for t in tournaments:
                    if day in t.days:
                        tournament_day = t
                        break
                
                data.append({
                    'Participant': participant.nom,
                    'Jour': day,
                    'Tournoi': tournament_day.label if tournament_day else f"Jour {day}",
                    'Lieu': tournament_day.lieu if tournament_day else "?",
                    'Type': tournament_day.type if tournament_day else "?"
                })
    
    if not data:
        # Cas vide
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune participation dans cette solution",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    df = pd.DataFrame(data)
    
    # Créer le graphique
    fig = px.timeline(
        df,
        x_start='Jour',
        x_end='Jour',
        y='Participant',
        color='Lieu',
        hover_data=['Tournoi', 'Type'],
        title='📅 Timeline des Participations'
    )
    
    # Améliorer l'affichage
    fig.update_xaxes(
        title_text="Jours",
        tickmode='linear',
        tick0=0,
        dtick=1
    )
    fig.update_yaxes(title_text="")
    
    fig.update_layout(
        height=max(400, len(solution.participants) * 30),
        showlegend=True,
        hovermode='closest'
    )
    
    return fig


def create_heatmap_chart(solution: Solution) -> go.Figure:
    """
    Crée une heatmap de présence (participants × jours)
    
    Args:
        solution: Solution à visualiser
        
    Returns:
        Figure Plotly
    """
    # Préparer la matrice
    participants_names = [p.nom for p in solution.participants]
    presence_matrix = []
    
    for participant in solution.participants:
        stats = solution.get_participant_stats(participant.nom)
        presence_matrix.append(stats['presence'])
    
    # Créer la heatmap
    fig = go.Figure(data=go.Heatmap(
        z=presence_matrix,
        x=[f"J{i}" for i in range(9)],
        y=participants_names,
        colorscale=[[0, '#f0f0f0'], [1, '#2ecc71']],
        showscale=False,
        hovertemplate='%{y}<br>Jour %{x}<br>%{z}<extra></extra>',
        text=[['' if val == 0 else '✓' for val in row] for row in presence_matrix],
        texttemplate='%{text}',
        textfont={"size": 14}
    ))
    
    fig.update_layout(
        title='🗓️ Présence par Jour',
        xaxis_title='Jours',
        yaxis_title='',
        height=max(400, len(solution.participants) * 30),
        yaxis=dict(autorange='reversed')  # Inverser pour avoir premier en haut
    )
    
    return fig


def create_workload_distribution_chart(solution: Solution) -> go.Figure:
    """
    Crée un graphique de distribution de la charge
    
    Args:
        solution: Solution à visualiser
        
    Returns:
        Figure Plotly
    """
    # Collecter les données
    data = []
    
    for participant in solution.participants:
        stats = solution.get_participant_stats(participant.nom)
        
        data.append({
            'Participant': participant.nom,
            'Souhaité': stats['jours_souhaites'],
            'Joué': stats['jours_joues'],
            'Écart': stats['ecart']
        })
    
    df = pd.DataFrame(data).sort_values('Joué', ascending=False)
    
    # Créer le graphique
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Jours Souhaités',
        x=df['Participant'],
        y=df['Souhaité'],
        marker_color='lightblue',
        text=df['Souhaité'],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Jours Joués',
        x=df['Participant'],
        y=df['Joué'],
        marker_color='green',
        text=df['Joué'],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='📊 Comparaison Souhaits vs Réalité',
        xaxis_title='',
        yaxis_title='Nombre de Jours',
        barmode='group',
        height=500,
        showlegend=True,
        xaxis={'tickangle': -45}
    )
    
    return fig


def create_pie_chart_distribution(solution: Solution) -> go.Figure:
    """
    Crée un camembert de répartition des charges
    
    Args:
        solution: Solution à visualiser
        
    Returns:
        Figure Plotly
    """
    # Catégoriser les participants par charge
    categories = {
        '1-2 jours': 0,
        '3-4 jours': 0,
        '5-6 jours': 0,
        '7+ jours': 0
    }
    
    for participant in solution.participants:
        stats = solution.get_participant_stats(participant.nom)
        days = stats['jours_joues']
        
        if days <= 2:
            categories['1-2 jours'] += 1
        elif days <= 4:
            categories['3-4 jours'] += 1
        elif days <= 6:
            categories['5-6 jours'] += 1
        else:
            categories['7+ jours'] += 1
    
    # Filtrer les catégories vides
    labels = [k for k, v in categories.items() if v > 0]
    values = [v for v in categories.values() if v > 0]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,
        marker_colors=['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
    )])
    
    fig.update_layout(
        title='🥧 Répartition de la Charge de Travail',
        height=400
    )
    
    return fig


def create_quality_comparison_chart(solutions: List[Solution]) -> go.Figure:
    """
    Compare la qualité de plusieurs solutions
    
    Args:
        solutions: Liste de solutions à comparer
        
    Returns:
        Figure Plotly
    """
    if not solutions:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune solution à comparer",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Préparer les données
    data = []
    
    for i, solution in enumerate(solutions[:10], 1):  # Max 10 solutions
        data.append({
            'Solution': f"Option {i}",
            'Score Qualité': solution.get_quality_score(),
            'Vœux Respectés': len(solution.participants) - len(solution.violated_wishes),
            'Fatigue (>3j)': len(solution.fatigue_participants),
            'Max Consécutifs': solution.max_consecutive_days
        })
    
    df = pd.DataFrame(data)
    
    # Créer subplot avec 4 graphiques
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Score Qualité',
            'Vœux Respectés',
            'Participants Fatigués',
            'Jours Consécutifs Max'
        )
    )
    
    # Score qualité
    fig.add_trace(
        go.Bar(x=df['Solution'], y=df['Score Qualité'], marker_color='#3498db'),
        row=1, col=1
    )
    
    # Vœux respectés
    fig.add_trace(
        go.Bar(x=df['Solution'], y=df['Vœux Respectés'], marker_color='#2ecc71'),
        row=1, col=2
    )
    
    # Fatigue
    fig.add_trace(
        go.Bar(x=df['Solution'], y=df['Fatigue (>3j)'], marker_color='#e74c3c'),
        row=2, col=1
    )
    
    # Max consécutifs
    fig.add_trace(
        go.Bar(x=df['Solution'], y=df['Max Consécutifs'], marker_color='#f39c12'),
        row=2, col=2
    )
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="📈 Comparaison des Solutions"
    )
    
    return fig


def create_gantt_chart(solution: Solution, tournaments: List[Tournament]) -> go.Figure:
    """
    Crée un diagramme de Gantt par lieu
    
    Args:
        solution: Solution à visualiser
        tournaments: Liste des tournois
        
    Returns:
        Figure Plotly
    """
    # Regrouper par lieu
    lieux = {}
    for t in tournaments:
        if t.lieu not in lieux:
            lieux[t.lieu] = []
        lieux[t.lieu].append(t)
    
    # Préparer les données
    data = []
    
    for lieu, tournois in lieux.items():
        for tournoi in tournois:
            # Compter les participants
            teams = solution.assignments[tournoi.id]
            nb_participants = len(teams['M']) + len(teams['F']) + len(teams['All'])
            
            start_day = min(tournoi.days)
            end_day = max(tournoi.days)
            
            data.append({
                'Lieu': lieu,
                'Tournoi': tournoi.label,
                'Début': start_day,
                'Fin': end_day + 1,  # +1 pour la durée
                'Participants': nb_participants,
                'Type': tournoi.type
            })
    
    df = pd.DataFrame(data)
    
    # Créer le Gantt
    fig = px.timeline(
        df,
        x_start='Début',
        x_end='Fin',
        y='Lieu',
        color='Type',
        hover_data=['Tournoi', 'Participants'],
        title='📍 Planning par Lieu'
    )
    
    fig.update_xaxes(
        title_text="Jours",
        tickmode='linear',
        tick0=0,
        dtick=1
    )
    
    fig.update_layout(
        height=300,
        showlegend=True
    )
    
    return fig


def create_consecutive_days_chart(solution: Solution) -> go.Figure:
    """
    Visualise les jours consécutifs par participant
    
    Args:
        solution: Solution à visualiser
        
    Returns:
        Figure Plotly
    """
    data = []
    
    for participant in solution.participants:
        stats = solution.get_participant_stats(participant.nom)
        
        data.append({
            'Participant': participant.nom,
            'Max Consécutifs': stats['max_consecutifs'],
            'Status': 'OK' if stats['max_consecutifs'] <= 3 else 'Fatigue'
        })
    
    df = pd.DataFrame(data).sort_values('Max Consécutifs', ascending=False)
    
    # Couleurs selon le status
    colors = ['#2ecc71' if s == 'OK' else '#e74c3c' for s in df['Status']]
    
    fig = go.Figure(data=[
        go.Bar(
            x=df['Participant'],
            y=df['Max Consécutifs'],
            marker_color=colors,
            text=df['Max Consécutifs'],
            textposition='outside'
        )
    ])
    
    # Ligne de seuil à 3
    fig.add_hline(
        y=3,
        line_dash="dash",
        line_color="orange",
        annotation_text="Seuil (3j)",
        annotation_position="right"
    )
    
    fig.update_layout(
        title='⚡ Jours Consécutifs Maximum par Participant',
        xaxis_title='',
        yaxis_title='Nombre de Jours Consécutifs',
        height=400,
        xaxis={'tickangle': -45}
    )
    
    return fig


def create_statistics_overview(solutions: List[Solution]) -> go.Figure:
    """
    Vue d'ensemble des statistiques sur toutes les solutions
    
    Args:
        solutions: Liste de toutes les solutions
        
    Returns:
        Figure Plotly
    """
    if not solutions:
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune solution disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    # Compter par catégorie
    perfect = sum(1 for s in solutions if len(s.violated_wishes) == 0)
    one_violated = sum(1 for s in solutions if len(s.violated_wishes) == 1)
    two_violated = sum(1 for s in solutions if len(s.violated_wishes) == 2)
    three_plus = sum(1 for s in solutions if len(s.violated_wishes) >= 3)
    
    # Créer le graphique en barres empilées
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='✅ Parfaites',
        x=['Solutions'],
        y=[perfect],
        marker_color='#2ecc71',
        text=f"{perfect}",
        textposition='inside'
    ))
    
    fig.add_trace(go.Bar(
        name='⚠️ 1 Vœu',
        x=['Solutions'],
        y=[one_violated],
        marker_color='#f39c12',
        text=f"{one_violated}",
        textposition='inside'
    ))
    
    fig.add_trace(go.Bar(
        name='⚠️⚠️ 2 Vœux',
        x=['Solutions'],
        y=[two_violated],
        marker_color='#e67e22',
        text=f"{two_violated}",
        textposition='inside'
    ))
    
    fig.add_trace(go.Bar(
        name='❌ 3+ Vœux',
        x=['Solutions'],
        y=[three_plus],
        marker_color='#e74c3c',
        text=f"{three_plus}",
        textposition='inside'
    ))
    
    fig.update_layout(
        title=f'📊 Vue d\'Ensemble des {len(solutions)} Solutions',
        barmode='stack',
        height=300,
        showlegend=True,
        xaxis={'visible': False},
        yaxis_title='Nombre de Solutions'
    )
    
    return fig
