"""
Management command to seed initial Ugandan prospects
"""
from django.core.management.base import BaseCommand
from outreach.research import UgandaCompanyResearcher
from outreach.models import Prospect, Contact


class Command(BaseCommand):
    help = 'Seed initial Ugandan prospects from research data'
    
    def handle(self, *args, **options):
        self.stdout.write('Seeding Ugandan prospects...')
        
        targets = UgandaCompanyResearcher.get_initial_ugandan_targets()
        
        created_count = 0
        for target in targets:
            # Determine company size based on industry/notes
            size_estimate = 'medium'  # Default
            if any(x in target['notes'].lower() for x in ['large', 'major', 'premier', 'national']):
                size_estimate = 'large'
            elif any(x in target['notes'].lower() for x in ['micro', 'small']):
                size_estimate = 'small'
            
            # Determine if multi-region
            multi_region = any(x in target['notes'].lower() for x in [
                'nationwide', 'multi-region', 'multi-branch', 'regional'
            ])
            
            # Calculate complexity score
            complexity = UgandaCompanyResearcher.calculate_complexity_score(
                company_size=size_estimate,
                multi_region=multi_region,
                industry=target['industry'],
                indicators=[]
            )
            
            # Create or update prospect
            prospect, created = Prospect.objects.update_or_create(
                organization_name=target['name'],
                defaults={
                    'industry': target['industry'],
                    'country': 'Uganda',
                    'company_size': size_estimate,
                    'complexity_score': complexity,
                    'multi_region': multi_region,
                    'archetype': target['archetype'],
                    'source': 'Research Module',
                    'status': 'new',
                    'notes': target['notes']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {prospect.organization_name}"))
            else:
                self.stdout.write(f"Updated: {prospect.organization_name}")
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSeeding complete! Created {created_count} new prospects, '
            f'{len(targets) - created_count} updated.'
        ))
