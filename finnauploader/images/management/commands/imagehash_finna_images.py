from django.core.management.base import BaseCommand
from images.models import FinnaImage, FinnaImageHash, FinnaImageHashURL
from images.imagehash_helpers import get_finna_image_url, get_imagehashes
from images.conversion import unsigned_to_signed

# FinnaImageHashURL.objects.all().delete()
# FinnaImageHash.objects.all().delete()


class Command(BaseCommand):
    help = 'Imagehash Finna images on database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filecache',
            action='store_true',
            help='Cache downloaded images to disk.'
        )

    def handle(self, *args, **kwargs):
        filecache = kwargs['filecache']

        photos = FinnaImage.objects.all()
        for photo in photos:
            imagehash = FinnaImageHash.objects\
                                      .filter(finna_image=photo)\
                                      .first()

            for index in range(photo.number_of_images):
                imagehash_url = FinnaImageHashURL.objects\
                                                 .filter(imagehash=imagehash,
                                                         index=index)\
                                                 .first()
                if imagehash_url:
                    print(f'skipping: {photo.finna_id} {index}')
                    continue

                url = get_finna_image_url(photo.finna_id, index)
                if not url:
                    print("could not get valid url for image, id:", photo.finna_id)
                    continue

                print("Image:", photo.title, " url:", url)

                imh = None
                # supposed to use cache here
                if filecache:
                    imh = get_noncached_imagehashes(url, thumbnail=True)
                else:
                    imh = get_imagehashes(url, thumbnail=True)
                    
                if (imh == None):
                    print("Could not get imagehashes for:", photo.title, " url:", url)

                try:
                    imagehash, created = FinnaImageHash.objects.get_or_create(
                        finna_image=photo,
                        phash=unsigned_to_signed(imh['phash']),
                        dhash=unsigned_to_signed(imh['dhash']),
                        dhash_vertical=unsigned_to_signed(i['dhash_vertical'])
                        )
                    if created:
                        imagehash.save()

                    obj = FinnaImageHashURL.objects
                    imagehash_url, created = obj.get_or_create(
                                        imagehash = imagehash,
                                        url = url,
                                        width = imh['width'],
                                        height = imh['height'],
                                        index = index,
                                        thumbnail=True
                                    )
                    if created:
                        imagehash_url.save()
                except:
                    print("failed saving from url:", url)

        self.stdout.write(self.style.SUCCESS('Images hashed succesfully!'))
