from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImageHash, FinnaNonPresenterAuthor, FinnaImage

class Command(BaseCommand):
  help = 'Print stats on images on database'

  def handle(self, *args, **kwargs):
    images = FinnaImage.objects.all()
    for image in images:
      if image.identifier_string:
        print(image.identifier_string)
