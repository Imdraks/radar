"""
Radar Scorer - Intelligent lead scoring system

Evaluates leads based on:
- Timing (urgency, optimal window)
- Information quality (contacts, pricing, conditions)
- Agency profile match
- Budget alignment
- Success potential
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TimingScore(str, Enum):
    URGENT = "urgent"       # < 7 days
    OPTIMAL = "optimal"     # 7-30 days
    GOOD = "good"           # 30-60 days
    EARLY = "early"         # 60-90 days
    LATE = "late"           # Past deadline or very close
    UNKNOWN = "unknown"


class LeadGrade(str, Enum):
    """Lead quality grade based on score"""
    A_PLUS = "A+"   # Score >= 90
    A = "A"         # Score >= 80
    B_PLUS = "B+"   # Score >= 70
    B = "B"         # Score >= 60
    C = "C"         # Score >= 50
    D = "D"         # Score >= 40
    F = "F"         # Score < 40

# Backward compatibility alias
OpportunityGrade = LeadGrade


@dataclass
class ScoringResult:
    """Result of lead scoring"""
    total_score: float
    grade: LeadGrade
    timing_score: TimingScore
    breakdown: Dict[str, float]
    recommendations: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_score': self.total_score,
            'grade': self.grade.value,
            'timing': self.timing_score.value,
            'breakdown': self.breakdown,
            'recommendations': self.recommendations,
            'warnings': self.warnings,
        }


class RadarScorer:
    """
    Intelligent scoring system that evaluates leads based on:
    - Timing (urgency, optimal window)
    - Information quality (contacts, pricing, conditions)
    - Agency profile match
    - Available budget vs estimate
    - Success potential
    """
    
    # Criteria weights
    WEIGHTS = {
        'timing': 0.20,
        'information_quality': 0.15,
        'budget_match': 0.20,
        'relevance': 0.25,
        'competition': 0.10,
        'potential': 0.10,
    }
    
    # Keywords by category for agency relevance
    RELEVANCE_KEYWORDS = {
        'high_priority': {
            'rap': 5,
            'hip-hop': 5,
            'concert': 4,
            'festival': 5,
            'événement privé': 5,
            'corporate': 4,
            'fashion week': 5,
            'défilé': 4,
            'mode': 4,
            'lancement': 4,
            'inauguration': 3,
            'soirée privée': 5,
            'marque': 4,
            'brand activation': 5,
        },
        'medium_priority': {
            'culturel': 3,
            'spectacle': 3,
            'animation': 2,
            'salon': 2,
            'convention': 2,
            'conférence': 2,
            'séminaire': 2,
        },
        'low_priority': {
            'administratif': 1,
            'fourniture': 0,
            'maintenance': 0,
            'travaux': 0,
        },
    }
    
    def __init__(self, agency_profile: Optional[Dict[str, Any]] = None):
        """
        Args:
            agency_profile: Profil de l'agence avec ses préférences
        """
        self.agency_profile = agency_profile or self._default_agency_profile()
    
    def _default_agency_profile(self) -> Dict[str, Any]:
        """Profil par défaut de l'agence événementielle"""
        return {
            'name': 'Agence Événementielle',
            'specialties': ['rap', 'hip-hop', 'mode', 'corporate', 'festival'],
            'budget_range': {
                'min': 5000,
                'max': 500000,
            },
            'preferred_locations': ['paris', 'ile-de-france', 'france'],
            'max_distance_km': 500,
            'preferred_event_types': ['concert', 'festival', 'soirée privée', 'corporate'],
            'avoid_keywords': ['funéraire', 'medical', 'travaux'],
        }
    
    def score(self, opportunity: Dict[str, Any]) -> ScoringResult:
        """
        Score une opportunité complète
        
        Args:
            opportunity: Dict avec les données extraites de l'opportunité
        """
        breakdown = {}
        recommendations = []
        warnings = []
        
        # 1. Score Timing
        timing_result = self._score_timing(opportunity)
        breakdown['timing'] = timing_result['score']
        if timing_result['warning']:
            warnings.append(timing_result['warning'])
        if timing_result['recommendation']:
            recommendations.append(timing_result['recommendation'])
        
        # 2. Score Qualité d'information
        info_result = self._score_information_quality(opportunity)
        breakdown['information_quality'] = info_result['score']
        if info_result['warnings']:
            warnings.extend(info_result['warnings'])
        
        # 3. Score Budget
        budget_result = self._score_budget_match(opportunity)
        breakdown['budget_match'] = budget_result['score']
        if budget_result['recommendation']:
            recommendations.append(budget_result['recommendation'])
        
        # 4. Score Pertinence
        relevance_result = self._score_relevance(opportunity)
        breakdown['relevance'] = relevance_result['score']
        
        # 5. Score Concurrence
        competition_result = self._score_competition(opportunity)
        breakdown['competition'] = competition_result['score']
        if competition_result['warning']:
            warnings.append(competition_result['warning'])
        
        # 6. Score Potentiel
        potential_result = self._score_potential(opportunity)
        breakdown['potential'] = potential_result['score']
        
        # Calcul du score total pondéré
        total_score = sum(
            breakdown[k] * self.WEIGHTS[k] 
            for k in self.WEIGHTS.keys()
        )
        
        # Ajustements
        if timing_result['timing'] == TimingScore.LATE:
            total_score *= 0.5  # Pénalité sévère si deadline passée
        
        # Déterminer le grade
        grade = self._calculate_grade(total_score)
        
        # Ajouter des recommandations basées sur le grade
        if grade in [OpportunityGrade.A_PLUS, OpportunityGrade.A]:
            recommendations.insert(0, "🔥 PRIORITÉ HAUTE - Opportunité à saisir rapidement")
        elif grade in [OpportunityGrade.B_PLUS, OpportunityGrade.B]:
            recommendations.insert(0, "✅ Bonne opportunité - À étudier")
        elif grade == OpportunityGrade.C:
            recommendations.insert(0, "⚠️ Opportunité moyenne - Nécessite plus d'analyse")
        
        return ScoringResult(
            total_score=round(total_score, 1),
            grade=grade,
            timing_score=timing_result['timing'],
            breakdown={k: round(v, 1) for k, v in breakdown.items()},
            recommendations=recommendations,
            warnings=warnings,
        )
    
    def _score_timing(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Score le timing de l'opportunité"""
        deadline = opportunity.get('deadline')
        event_date = opportunity.get('event_date')
        
        result = {
            'score': 50.0,
            'timing': TimingScore.UNKNOWN,
            'warning': None,
            'recommendation': None,
        }
        
        # Utiliser deadline ou event_date
        target_date = None
        if deadline:
            if isinstance(deadline, str):
                try:
                    target_date = datetime.fromisoformat(deadline)
                except ValueError:
                    pass
            elif isinstance(deadline, datetime):
                target_date = deadline
        
        if not target_date and event_date:
            if isinstance(event_date, str):
                try:
                    target_date = datetime.fromisoformat(event_date)
                except ValueError:
                    pass
            elif isinstance(event_date, datetime):
                target_date = event_date
        
        if not target_date:
            return result
        
        now = datetime.now()
        days_until = (target_date - now).days
        
        if days_until < 0:
            result['score'] = 10.0
            result['timing'] = TimingScore.LATE
            result['warning'] = f"⚠️ Date limite dépassée depuis {abs(days_until)} jours"
        elif days_until < 3:
            result['score'] = 30.0
            result['timing'] = TimingScore.URGENT
            result['warning'] = f"🚨 URGENT: Plus que {days_until} jours!"
            result['recommendation'] = "Répondre aujourd'hui si intéressé"
        elif days_until < 7:
            result['score'] = 70.0
            result['timing'] = TimingScore.URGENT
            result['recommendation'] = "Traiter cette semaine"
        elif days_until < 30:
            result['score'] = 100.0
            result['timing'] = TimingScore.OPTIMAL
            result['recommendation'] = "Fenêtre idéale pour postuler"
        elif days_until < 60:
            result['score'] = 85.0
            result['timing'] = TimingScore.GOOD
        elif days_until < 90:
            result['score'] = 70.0
            result['timing'] = TimingScore.EARLY
        else:
            result['score'] = 60.0
            result['timing'] = TimingScore.EARLY
            result['recommendation'] = "Ajouter au suivi long terme"
        
        return result
    
    def _score_information_quality(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Score la qualité des informations disponibles"""
        score = 0.0
        warnings = []
        
        # Contacts
        contacts = opportunity.get('contacts', [])
        if contacts:
            if any(c.get('email') for c in contacts):
                score += 25
            if any(c.get('phone') for c in contacts):
                score += 15
            if any(c.get('name') for c in contacts):
                score += 10
        else:
            warnings.append("Aucun contact trouvé")
        
        # Prix/Budget
        if opportunity.get('budget') or opportunity.get('prices'):
            score += 25
        else:
            warnings.append("Pas d'information de budget")
        
        # Description
        description = opportunity.get('description', '')
        if len(description) > 500:
            score += 15
        elif len(description) > 100:
            score += 10
        
        # Conditions
        if opportunity.get('conditions'):
            score += 10
        
        return {'score': min(100, score), 'warnings': warnings}
    
    def _score_budget_match(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Score l'adéquation du budget"""
        result = {'score': 50.0, 'recommendation': None}
        
        budget = opportunity.get('budget')
        prices = opportunity.get('prices', [])
        
        if not budget and prices:
            # Utiliser le prix le plus élevé comme référence
            max_price = max(p.get('value', 0) for p in prices if p.get('value'))
            if max_price:
                budget = max_price
        
        if not budget:
            return result
        
        agency_min = self.agency_profile['budget_range']['min']
        agency_max = self.agency_profile['budget_range']['max']
        
        if budget < agency_min * 0.5:
            result['score'] = 20.0
            result['recommendation'] = f"Budget faible ({budget}€) - Vérifier la rentabilité"
        elif budget < agency_min:
            result['score'] = 40.0
            result['recommendation'] = "Budget en dessous de la normale"
        elif budget <= agency_max:
            # Score optimal si dans la fourchette
            # Plus c'est proche du max, mieux c'est
            ratio = (budget - agency_min) / (agency_max - agency_min)
            result['score'] = 60 + (ratio * 40)
        else:
            result['score'] = 90.0  # Budget élevé = bonne opportunité
            result['recommendation'] = f"Gros budget ({budget}€) - Opportunité majeure"
        
        return result
    
    def _score_relevance(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Score la pertinence avec le profil de l'agence"""
        score = 0.0
        text = f"{opportunity.get('title', '')} {opportunity.get('description', '')}".lower()
        
        # Vérifier les mots-clés à éviter
        for keyword in self.agency_profile.get('avoid_keywords', []):
            if keyword.lower() in text:
                return {'score': 0.0}  # Éliminer directement
        
        # Score par keywords de pertinence
        for priority, keywords in self.RELEVANCE_KEYWORDS.items():
            for keyword, points in keywords.items():
                if keyword.lower() in text:
                    score += points * 10
        
        # Bonus si correspond aux spécialités
        for specialty in self.agency_profile.get('specialties', []):
            if specialty.lower() in text:
                score += 15
        
        # Bonus localisation
        location = opportunity.get('location', '').lower()
        for pref_loc in self.agency_profile.get('preferred_locations', []):
            if pref_loc.lower() in location:
                score += 10
                break
        
        return {'score': min(100, score)}
    
    def _score_competition(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Estime le niveau de concurrence"""
        result = {'score': 50.0, 'warning': None}
        
        # Indicateurs de forte concurrence
        text = f"{opportunity.get('title', '')} {opportunity.get('description', '')}".lower()
        
        high_competition = ['appel d\'offres ouvert', 'marché public', 'consultation', 'boamp']
        low_competition = ['gré à gré', 'direct', 'exclusif', 'invitation', 'privé']
        
        for indicator in high_competition:
            if indicator in text:
                result['score'] -= 20
                result['warning'] = "Concurrence probable élevée (marché public)"
        
        for indicator in low_competition:
            if indicator in text:
                result['score'] += 25
        
        # Vérifier si deadline très courte = moins de concurrents
        deadline = opportunity.get('deadline')
        if deadline:
            try:
                if isinstance(deadline, str):
                    deadline = datetime.fromisoformat(deadline)
                days = (deadline - datetime.now()).days
                if days < 5:
                    result['score'] += 15  # Moins de concurrence si urgent
            except (ValueError, TypeError):
                pass
        
        return {'score': max(0, min(100, result['score'])), 'warning': result['warning']}
    
    def _score_potential(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Score le potentiel futur (récurrence, relation client)"""
        score = 50.0
        text = f"{opportunity.get('title', '')} {opportunity.get('description', '')}".lower()
        
        # Indicateurs de potentiel
        recurring = ['récurrent', 'annuel', 'régulier', 'accord-cadre', 'pluriannuel']
        major_client = ['ministère', 'région', 'métropole', 'grande marque', 'groupe']
        growth = ['croissance', 'expansion', 'nouveau', 'lancement', 'inauguration']
        
        for indicator in recurring:
            if indicator in text:
                score += 15
        
        for indicator in major_client:
            if indicator in text:
                score += 10
        
        for indicator in growth:
            if indicator in text:
                score += 10
        
        return {'score': min(100, score)}
    
    def _calculate_grade(self, score: float) -> OpportunityGrade:
        """Calcule le grade final"""
        if score >= 90:
            return OpportunityGrade.A_PLUS
        elif score >= 80:
            return OpportunityGrade.A
        elif score >= 70:
            return OpportunityGrade.B_PLUS
        elif score >= 60:
            return OpportunityGrade.B
        elif score >= 50:
            return OpportunityGrade.C
        elif score >= 40:
            return OpportunityGrade.D
        else:
            return OpportunityGrade.F
    
    def quick_score(self, title: str, description: str = "") -> float:
        """Score rapide basé uniquement sur le texte"""
        text = f"{title} {description}".lower()
        
        score = 50.0
        
        # Keywords positifs
        for priority, keywords in self.RELEVANCE_KEYWORDS.items():
            for keyword, points in keywords.items():
                if keyword.lower() in text:
                    score += points * 5
        
        # Keywords négatifs
        for keyword in self.agency_profile.get('avoid_keywords', []):
            if keyword.lower() in text:
                score -= 50
        
        return max(0, min(100, score))
    
    def filter_opportunities(
        self, 
        opportunities: List[Dict[str, Any]],
        min_grade: OpportunityGrade = OpportunityGrade.C
    ) -> List[Dict[str, Any]]:
        """Filtre et trie les opportunités par pertinence"""
        scored = []
        
        grades_order = [
            OpportunityGrade.A_PLUS, OpportunityGrade.A,
            OpportunityGrade.B_PLUS, OpportunityGrade.B,
            OpportunityGrade.C, OpportunityGrade.D, OpportunityGrade.F
        ]
        min_idx = grades_order.index(min_grade)
        
        for opp in opportunities:
            result = self.score(opp)
            grade_idx = grades_order.index(result.grade)
            
            if grade_idx <= min_idx:
                opp['_scoring'] = result.to_dict()
                scored.append(opp)
        
        # Trier par score décroissant
        return sorted(scored, key=lambda x: x['_scoring']['total_score'], reverse=True)
