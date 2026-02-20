"""
Ugandan Company Research Module

This module provides utilities for researching and scoring
Ugandan companies for Executive Intelligence Infrastructure fit.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CompanyResearchResult:
    """Result of company research"""
    name: str
    website: Optional[str]
    industry: str
    size_estimate: str  # micro, small, medium, large
    multi_region: bool
    complexity_score: int  # 1-10
    archetype: str
    data_sources: List[str]
    confidence: str  # high, medium, low


class UgandaCompanyResearcher:
    """Research Ugandan companies for EIS fit"""
    
    # Industries that typically need executive oversight
    HIGH_FIT_INDUSTRIES = [
        'Manufacturing',
        'Financial Services',
        'Fintech',
        'Mobile Money',
        'Banking',
        'Insurance',
        'Agriculture (Cooperatives)',
        'Education',
        'Healthcare',
        'Logistics',
        'Telecommunications',
        'Energy',
        'Construction',
        'Real Estate',
        'NGO/Development',
        'Government Agency',
    ]
    
    # Known multi-region organizations
    MULTI_REGION_INDICATORS = [
        'nationwide', 'national', 'multi-region', 'east africa',
        'kampala', 'entebbe', 'jinja', 'mbarara', 'gulu', 'arua',
        'branches', 'districts', 'regional offices'
    ]
    
    @classmethod
    def calculate_complexity_score(
        cls,
        company_size: str,
        multi_region: bool,
        industry: str,
        indicators: List[str]
    ) -> int:
        """
        Calculate complexity score (1-10)
        Higher = better fit for EIS
        """
        score = 0
        
        # Size weighting
        size_scores = {
            'micro': 2,
            'small': 4,
            'medium': 7,
            'large': 10
        }
        score += size_scores.get(company_size, 3)
        
        # Multi-region bonus
        if multi_region:
            score += 2
        
        # Industry fit
        if industry in cls.HIGH_FIT_INDUSTRIES:
            score += 2
        
        # Cap at 10
        return min(score, 10)
    
    @classmethod
    def determine_archetype(
        cls,
        industry: str,
        company_description: str
    ) -> str:
        """
        Determine which archetype the company fits
        """
        desc_lower = company_description.lower()
        
        # Public Sector indicators
        public_indicators = [
            'ministry', 'agency', 'authority', 'commission', 'council',
            'government', 'public', 'regulatory', 'oversight'
        ]
        for indicator in public_indicators:
            if indicator in desc_lower or indicator in industry.lower():
                return 'public_sector'
        
        # Growth/Efficiency indicators
        growth_indicators = [
            'fintech', 'venture', 'startup', 'scaling', 'investment',
            'capital', 'digital', 'innovation', 'technology'
        ]
        for indicator in growth_indicators:
            if indicator in desc_lower:
                return 'growth_efficiency'
        
        # Default to Distributed Operations
        return 'distributed_ops'
    
    @classmethod
    def get_initial_ugandan_targets(cls) -> List[Dict]:
        """
        Return initial list of high-fit Ugandan organizations
        Based on public information - to be researched further
        """
        
        targets = [
            # Manufacturing
            {
                'name': 'Crown Beverages Limited',
                'industry': 'Manufacturing',
                'notes': 'Pepsi bottler, multi-region distribution',
                'archetype': 'distributed_ops'
            },
            {
                'name': 'Mukwano Group',
                'industry': 'Manufacturing',
                'notes': 'Diversified manufacturing, household products',
                'archetype': 'distributed_ops'
            },
            {
                'name': 'Roofings Group',
                'industry': 'Manufacturing',
                'notes': 'Steel and construction materials',
                'archetype': 'distributed_ops'
            },
            
            # Financial Services
            {
                'name': 'MTN Mobile Money Uganda',
                'industry': 'Fintech/Mobile Money',
                'notes': 'Leading mobile money provider',
                'archetype': 'growth_efficiency'
            },
            {
                'name': 'Airtel Money Uganda',
                'industry': 'Fintech/Mobile Money',
                'notes': 'Major mobile money competitor',
                'archetype': 'growth_efficiency'
            },
            {
                'name': 'Centenary Bank',
                'industry': 'Banking',
                'notes': 'Large microfinance bank, nationwide',
                'archetype': 'distributed_ops'
            },
            {
                'name': 'DFCU Bank',
                'industry': 'Banking',
                'notes': 'Commercial bank, business focus',
                'archetype': 'growth_efficiency'
            },
            {
                'name': 'Stanbic Bank Uganda',
                'industry': 'Banking',
                'notes': 'Major commercial bank',
                'archetype': 'distributed_ops'
            },
            
            # Agriculture/Cooperatives
            {
                'name': 'Uganda National Farmers Federation (UNFFE)',
                'industry': 'Agriculture',
                'notes': 'National farmer representation',
                'archetype': 'distributed_ops'
            },
            {
                'name': 'National Union of Coffee Agribusinesses (NUCAFE)',
                'industry': 'Agriculture',
                'notes': 'Coffee cooperative union',
                'archetype': 'distributed_ops'
            },
            
            # Education
            {
                'name': 'Makerere University',
                'industry': 'Education',
                'notes': 'Premier university, multiple colleges',
                'archetype': 'public_sector'
            },
            {
                'name': 'Uganda Christian University',
                'industry': 'Education',
                'notes': 'Multi-campus university',
                'archetype': 'distributed_ops'
            },
            
            # Healthcare
            {
                'name': 'Mulago National Referral Hospital',
                'industry': 'Healthcare',
                'notes': 'National referral hospital complex',
                'archetype': 'public_sector'
            },
            {
                'name': 'International Hospital Kampala',
                'industry': 'Healthcare',
                'notes': 'Private hospital group',
                'archetype': 'distributed_ops'
            },
            
            # Energy
            {
                'name': 'Umeme Limited',
                'industry': 'Energy',
                'notes': 'Power distribution, nationwide',
                'archetype': 'distributed_ops'
            },
            {
                'name': 'Uganda National Oil Company (UNOC)',
                'industry': 'Energy',
                'notes': 'National oil company',
                'archetype': 'public_sector'
            },
            
            # Logistics
            {
                'name': 'SGA Security',
                'industry': 'Security/Logistics',
                'notes': 'Regional security firm',
                'archetype': 'distributed_ops'
            },
            {
                'name': 'Jubilee Insurance Uganda',
                'industry': 'Insurance',
                'notes': 'Insurance group, multi-branch',
                'archetype': 'distributed_ops'
            },
            
            # Telecom
            {
                'name': 'Uganda Telecom',
                'industry': 'Telecommunications',
                'notes': 'National telecom operator',
                'archetype': 'distributed_ops'
            },
            
            # Government Agencies
            {
                'name': 'Uganda Revenue Authority',
                'industry': 'Government Agency',
                'notes': 'Tax authority, national oversight',
                'archetype': 'public_sector'
            },
            {
                'name': 'National Social Security Fund (NSSF)',
                'industry': 'Government Agency',
                'notes': 'Social security, national coverage',
                'archetype': 'public_sector'
            },
            {
                'name': 'Uganda National Roads Authority (UNRA)',
                'industry': 'Government Agency',
                'notes': 'Roads authority, nationwide projects',
                'archetype': 'public_sector'
            },
            
            # NGOs/Development
            {
                'name': 'BRAC Uganda',
                'industry': 'NGO/Development',
                'notes': 'Large international NGO, multi-region',
                'archetype': 'distributed_ops'
            },
            {
                'name': 'World Vision Uganda',
                'industry': 'NGO/Development',
                'notes': 'International development NGO',
                'archetype': 'distributed_ops'
            },
            {
                'name': 'Oxfam Uganda',
                'industry': 'NGO/Development',
                'notes': 'International development organization',
                'archetype': 'distributed_ops'
            },
        ]
        
        return targets
    
    @classmethod
    def research_company(cls, company_name: str) -> Optional[CompanyResearchResult]:
        """
        Research a specific company
        In production, this would integrate with:
        - LinkedIn Sales Navigator API
        - Clearbit
        - Hunter.io for email verification
        - Company websites
        """
        # Placeholder - would do actual research
        logger.info(f"Researching company: {company_name}")
        
        # Return template for manual research
        return CompanyResearchResult(
            name=company_name,
            website=None,
            industry='Unknown',
            size_estimate='unknown',
            multi_region=False,
            complexity_score=0,
            archetype='distributed_ops',
            data_sources=[],
            confidence='low'
        )


class ProspectScorer:
    """Score prospects for outreach priority"""
    
    @classmethod
    def score_prospect(
        cls,
        complexity_score: int,
        multi_region: bool,
        decision_authority: str,
        archetype: str
    ) -> Dict:
        """
        Score a prospect and determine outreach priority
        """
        score = complexity_score
        
        # Multi-region bonus
        if multi_region:
            score += 2
        
        # Decision authority bonus
        authority_scores = {
            'c_suite': 3,
            'vp': 2,
            'manager': 1,
            'unknown': 0
        }
        score += authority_scores.get(decision_authority, 0)
        
        # Determine priority tier
        if score >= 10:
            priority = 'hot'
            outreach_timing = 'immediate'
        elif score >= 7:
            priority = 'warm'
            outreach_timing = 'within_3_days'
        elif score >= 4:
            priority = 'cool'
            outreach_timing = 'within_week'
        else:
            priority = 'nurture'
            outreach_timing = 'nurture_sequence'
        
        return {
            'total_score': score,
            'priority': priority,
            'outreach_timing': outreach_timing,
            'recommendation': f"{priority.upper()} priority - {outreach_timing.replace('_', ' ')}"
        }
