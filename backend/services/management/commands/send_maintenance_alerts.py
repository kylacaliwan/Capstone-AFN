from django.core.management.base import BaseCommand

from services.maintenance import process_maintenance_alerts


class Command(BaseCommand):
    help = 'Send due-soon and due maintenance alerts to admin and follow-up users.'

    def handle(self, *args, **options):
        summary = process_maintenance_alerts()
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed maintenance alerts: {summary['due_soon']} due soon, {summary['due']} due."
            )
        )

