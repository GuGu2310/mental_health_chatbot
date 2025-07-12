from django.core.management.base import BaseCommand
from chatbot.models import SupportResource

class Command(BaseCommand):
    help = 'Populate database with mental health support resources'

    def handle(self, *args, **options):
        resources = [
            {
                'title': 'National Suicide Prevention Lifeline',
                'description': '24/7 crisis support for people in suicidal crisis or emotional distress.',
                'phone_number': '988',
                'url': 'https://suicidepreventionlifeline.org',
                'category': 'crisis',
                'is_emergency': True
            },
            {
                'title': 'Crisis Text Line',
                'description': 'Free, confidential support via text message, available 24/7.',
                'phone_number': '741741',
                'url': 'https://www.crisistextline.org',
                'category': 'crisis',
                'is_emergency': True
            },
            {
                'title': 'SAMHSA National Helpline',
                'description': 'Treatment referral and information service for mental health and substance abuse.',
                'phone_number': '1-800-662-4357',
                'url': 'https://www.samhsa.gov/find-help/national-helpline',
                'category': 'treatment',
                'is_emergency': False
            },
            {
                'title': 'NAMI HelpLine',
                'description': 'Information, resource referrals and support for people with mental health conditions.',
                'phone_number': '1-800-950-6264',
                'url': 'https://www.nami.org/help',
                'category': 'support',
                'is_emergency': False
            },
            {
                'title': 'Teen Line',
                'description': 'Confidential hotline for teenagers, staffed by trained teen volunteers.',
                'phone_number': '1-800-852-8336',
                'url': 'https://teenlineonline.org',
                'category': 'youth',
                'is_emergency': False
            },
            {
                'title': 'Veterans Crisis Line',
                'description': '24/7 crisis support specifically for veterans and their families.',
                'phone_number': '1-800-273-8255',
                'url': 'https://www.veteranscrisisline.net',
                'category': 'veterans',
                'is_emergency': True
            },
            {
                'title': 'LGBT National Hotline',
                'description': 'Confidential support for the LGBT community.',
                'phone_number': '1-888-843-4564',
                'url': 'https://www.lgbthotline.org',
                'category': 'lgbt',
                'is_emergency': False
            },
            {
                'title': 'National Domestic Violence Hotline',
                'description': '24/7 support for domestic violence survivors.',
                'phone_number': '1-800-799-7233',
                'url': 'https://www.thehotline.org',
                'category': 'domestic_violence',
                'is_emergency': True
            }
        ]

        created_count = 0
        for resource_data in resources:
            resource, created = SupportResource.objects.get_or_create(
                title=resource_data['title'],
                defaults=resource_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created resource: {resource.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Resource already exists: {resource.title}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new resources')
        )