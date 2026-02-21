"""
Management command to update prospects with sweet spot ratings
"""
from django.core.management.base import BaseCommand
from outreach.models import Prospect


SWEET_SPOT_RATINGS = {
    # A-TIER (Immediate Outreach)
    "Crown Beverages Limited": {"tier": "A", "notes": "Pepsi bottler, private, ops-led"},
    "Mukwano Group": {"tier": "A", "notes": "Family-owned, diversified manufacturing"},
    "Roofings Group": {"tier": "A", "notes": "Private steel, construction boom"},
    "MTN Mobile Money Uganda": {"tier": "B+", "notes": "Competitive fintech, may need regional approval"},
    "Centenary Bank": {"tier": "B+", "notes": "Locally-owned, pragmatic culture"},
    "DFCU Bank": {"tier": "A-", "notes": "Mid-tier, aggressive growth, business-focused"},
    "SGA Security": {"tier": "A", "notes": "Regional ops, private, ops-critical"},
    "Jubilee Insurance Uganda": {"tier": "B+", "notes": "Regional insurer, multi-branch"},
    
    # B-TIER (Research & Qualify)
    "Airtel Money Uganda": {"tier": "B", "notes": "Indian parent may slow decisions"},
    "Stanbic Bank Uganda": {"tier": "C+", "notes": "South African parent, process-heavy"},
    "National Union of Coffee Agribusinesses (NUCAFE)": {"tier": "B", "notes": "Cooperative, may need member input"},
    "Umeme Limited": {"tier": "C", "notes": "Publicly listed, board governance"},
    "Uganda Christian University": {"tier": "B-", "notes": "Private but council governance"},
    
    # C-TIER (Nurture / Low Priority)
    "Uganda Revenue Authority": {"tier": "D", "notes": "State agency, procurement law"},
    "National Social Security Fund (NSSF)": {"tier": "D", "notes": "Parastatal, ministerial oversight"},
    "Uganda National Roads Authority (UNRA)": {"tier": "D", "notes": "Public agency, donor rules"},
    "Mulago National Referral Hospital": {"tier": "D", "notes": "Public hospital, ministry oversight"},
    "Makerere University": {"tier": "C-", "notes": "Public university, council governance"},
    "BRAC Uganda": {"tier": "C", "notes": "Bangladesh HQ, limited autonomy"},
    "World Vision Uganda": {"tier": "C", "notes": "Global NGO, standardized systems"},
    
    # NEEDS MORE RESEARCH
    "Uganda National Farmers Federation (UNFFE)": {"tier": "R", "notes": "RESEARCH: How federated is decision-making?"},
    "International Hospital Kampala": {"tier": "R", "notes": "RESEARCH: Who owns? Local or foreign?"},
    "Uganda National Oil Company (UNOC)": {"tier": "R", "notes": "RESEARCH: State-owned commercial - decision authority?"},
    "Uganda Telecom": {"tier": "R", "notes": "RESEARCH: Ownership structure?"},
    "Oxfam Uganda": {"tier": "R", "notes": "RESEARCH: Autonomy from Oxford HQ?"},
}


class Command(BaseCommand):
    help = 'Update prospects with sweet spot ratings'
    
    def handle(self, *args, **options):
        self.stdout.write('Updating prospect sweet spot ratings...')
        
        updated = 0
        for org_name, data in SWEET_SPOT_RATINGS.items():
            try:
                prospect = Prospect.objects.get(organization_name=org_name)
                
                # Update status based on tier
                if data["tier"] in ["A", "A-", "B+", "B"]:
                    new_status = "qualified"
                elif data["tier"] in ["C+", "C", "C-"]:
                    new_status = "nurture"
                elif data["tier"] == "D":
                    new_status = "rejected"  # Too bureaucratic
                else:  # R = research needed
                    new_status = "researching"
                
                # Append tier to notes
                tier_note = f"[Tier {data['tier']}] {data['notes']}"
                if tier_note not in prospect.notes:
                    prospect.notes = f"{prospect.notes}\n\n{tier_note}" if prospect.notes else tier_note
                
                prospect.status = new_status
                prospect.save()
                
                updated += 1
                
                color = self.get_color(data["tier"])
                self.stdout.write(color(f"{org_name}: Tier {data['tier']} → {new_status}"))
                
            except Prospect.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Prospect not found: {org_name}"))
        
        self.stdout.write(self.style.SUCCESS(f'\nUpdated {updated} prospects'))
        
        # Show summary
        self.show_summary()
    
    def get_color(self, tier):
        if tier in ["A", "A-"]:
            return self.style.SUCCESS
        elif tier in ["B+", "B", "B-"]:
            return self.style.NOTICE
        elif tier in ["C+", "C", "C-"]:
            return self.style.WARNING
        elif tier == "D":
            return self.style.ERROR
        else:
            return self.style.HTTP_INFO
    
    def show_summary(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('SWEET SPOT SUMMARY')
        self.stdout.write('='*50)
        
        tiers = Prospect.objects.filter(status='qualified').count()
        nurture = Prospect.objects.filter(status='nurture').count()
        rejected = Prospect.objects.filter(status='rejected').count()
        researching = Prospect.objects.filter(status='researching').count()
        
        self.stdout.write(f"✅ A/B Tier (Immediate outreach): {tiers}")
        self.stdout.write(f"⏳ C Tier (Nurture): {nurture}")
        self.stdout.write(f"❌ D Tier (Too bureaucratic): {rejected}")
        self.stdout.write(f"🔍 Needs Research: {researching}")
        self.stdout.write('\nRecommendation: Focus on A-tier first (8 prospects)')
