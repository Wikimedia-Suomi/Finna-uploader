from django.core.management.base import BaseCommand
from images.models import FinnaSubjectActor
from django.db.models import Count


class Command(BaseCommand):
    help = 'List Finna subjects'
    def add_arguments(self, parser):

        parser.add_argument(
            '--lookfor',
            type=str,
            help='Finna lookfor argument.',
        )

    def handle(self, *args, **options):

        subject_counts = FinnaSubjectActor.objects.annotate(image_count=Count('finnaimage'))
        if options['lookfor']:
            lookfor = options['lookfor']
            subjects = subject_counts.filter(name__icontains=lookfor)
        else:
            subjects = subject_counts
        # for subject in subject_counts:
        #    print(f"Subject: {subject.name}, Image Count: {subject.image_count}")

        sorted_subjects = subjects.order_by('-image_count')[:100]
        # print('listaus 10 kpl')
        for subject in sorted_subjects:
            print(f"Subject: {subject.name}, Image Count: {subject.image_count}")
