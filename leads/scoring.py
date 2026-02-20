"""
Qualification Scoring Algorithm for Pilot Applications.

Scoring Breakdown (0-100 points):
- Team Size: 0-25 pts
- Organizational Scope: 0-25 pts
- Industry Fit: 0-20 pts
- Challenge Severity: 0-15 pts
- File Upload Bonus: +10 pts
"""

# Scoring weights
TEAM_SIZE_SCORES = {
    '500+': 25,
    '101-500': 20,
    '21-100': 15,
    '1-20': 5
}

SCOPE_SCORES = {
    'National-Level': 25,
    'Multi-Country': 20,
    'Multi-Region': 15,
    'Single Location': 5
}

INDUSTRY_SCORES = {
    'Government Agency': 20,
    'NGO': 18,
    'Healthcare': 15,
    'Fintech': 15,
    'Manufacturing': 10,
    'Religious Organization': 12,
    'Other': 5
}

CHALLENGE_SCORES = {
    'Risk & Compliance Oversight': 15,
    'Fragmented Reporting': 12,
    'KPI Visibility Gaps': 12,
    'Slow Decision Cycles': 10,
    'Operational Complexity': 8,
    'Other': 5
}

FILE_UPLOAD_BONUS = 10
MAX_SCORE = 100


def calculate_score(application):
    """
    Calculate qualification score (0-100) for a PilotApplication.
    
    Args:
        application: PilotApplication instance or dict with scoring fields
        
    Returns:
        int: Score from 0 to 100
    """
    score = 0
    
    # Team Size (0-25 pts)
    team_size = getattr(application, 'team_size', None)
    score += TEAM_SIZE_SCORES.get(team_size, 0)
    
    # Organizational Scope (0-25 pts)
    scope = getattr(application, 'organizational_scope', None)
    score += SCOPE_SCORES.get(scope, 0)
    
    # Industry Fit (0-20 pts)
    industry = getattr(application, 'industry', None)
    score += INDUSTRY_SCORES.get(industry, 0)
    
    # Challenge Severity (0-15 pts)
    challenge = getattr(application, 'primary_challenge', None)
    score += CHALLENGE_SCORES.get(challenge, 0)
    
    # File Upload Bonus (+10 pts)
    sample_report = getattr(application, 'sample_report', None)
    if sample_report and sample_report.name:
        score += FILE_UPLOAD_BONUS
    
    return min(score, MAX_SCORE)


def get_tier(score):
    """
    Get priority tier based on qualification score.
    
    Args:
        score: Integer score (0-100)
        
    Returns:
        str: 'hot', 'warm', 'cool', or 'nurture'
    """
    if score >= 80:
        return 'hot'      # Immediate response (4h)
    if score >= 60:
        return 'warm'     # Same day response
    if score >= 40:
        return 'cool'     # Next day response
    return 'nurture'      # Automated sequence


def get_score_breakdown(application):
    """
    Get detailed breakdown of how the score was calculated.
    
    Args:
        application: PilotApplication instance
        
    Returns:
        dict: Breakdown of each scoring component
    """
    breakdown = {
        'total_score': 0,
        'max_possible': MAX_SCORE,
        'tier': '',
        'components': {}
    }
    
    # Team Size
    team_size = getattr(application, 'team_size', None)
    team_size_score = TEAM_SIZE_SCORES.get(team_size, 0)
    breakdown['components']['team_size'] = {
        'value': team_size,
        'score': team_size_score,
        'max': 25,
        'weight': '25%'
    }
    breakdown['total_score'] += team_size_score
    
    # Organizational Scope
    scope = getattr(application, 'organizational_scope', None)
    scope_score = SCOPE_SCORES.get(scope, 0)
    breakdown['components']['organizational_scope'] = {
        'value': scope,
        'score': scope_score,
        'max': 25,
        'weight': '25%'
    }
    breakdown['total_score'] += scope_score
    
    # Industry
    industry = getattr(application, 'industry', None)
    industry_score = INDUSTRY_SCORES.get(industry, 0)
    breakdown['components']['industry'] = {
        'value': industry,
        'score': industry_score,
        'max': 20,
        'weight': '20%'
    }
    breakdown['total_score'] += industry_score
    
    # Primary Challenge
    challenge = getattr(application, 'primary_challenge', None)
    challenge_score = CHALLENGE_SCORES.get(challenge, 0)
    breakdown['components']['primary_challenge'] = {
        'value': challenge,
        'score': challenge_score,
        'max': 15,
        'weight': '15%'
    }
    breakdown['total_score'] += challenge_score
    
    # File Upload Bonus
    sample_report = getattr(application, 'sample_report', None)
    has_file = bool(sample_report and sample_report.name)
    file_score = FILE_UPLOAD_BONUS if has_file else 0
    breakdown['components']['sample_report'] = {
        'value': 'Yes' if has_file else 'No',
        'score': file_score,
        'max': 10,
        'weight': '10% (Bonus)'
    }
    breakdown['total_score'] += file_score
    
    # Ensure score doesn't exceed max
    breakdown['total_score'] = min(breakdown['total_score'], MAX_SCORE)
    breakdown['tier'] = get_tier(breakdown['total_score'])
    
    return breakdown
