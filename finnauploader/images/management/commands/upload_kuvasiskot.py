from django.core.management.base import BaseCommand
from images.models import FinnaImage
import pywikibot
import time
from images.finna import do_finna_search
from images.wikitext.photographer import get_wikitext_for_new_image
from images.duplicatedetection import is_already_in_commons
from images.finna_image_sdc_helpers import get_structured_data_for_new_image
from images.pywikibot_helpers import edit_commons_mediaitem, \
                                     upload_file_to_commons


def get_comment_text(finna_image):
    authors = list(finna_image.non_presenter_authors
                              .filter(role='kuvaaja')
                              .values_list('name', flat=True))

    ret = "Uploading \'" + finna_image.short_title + "\'"
    ret = ret + " by \'" + "; ".join(authors) + "\'"

    if "CC BY 4.0" in finna_image.image_right.copyright:
        copyrighttemplate = "CC-BY-4.0"
    else:
        print("Copyright error")
        print(finna_image.image_right.copyright)
        exit(1)

    ret = f'{ret} with licence {copyrighttemplate}'
    ret = f'{ret} from {finna_image.url}'
    return ret


class Command(BaseCommand):
    help = 'Upload kuvasiskot images'

    def process_finna_record(self, record):
        print(record['id'])
        print(record['title'])
        print(record['summary'])

        finna_image = FinnaImage.objects.create_from_data(record)
        file_name = finna_image.pseudo_filename
        image_url = finna_image.master_url

        structured_data = get_structured_data_for_new_image(finna_image)
        wikitext = get_wikitext_for_new_image(finna_image)
        comment = get_comment_text(finna_image)

        pywikibot.info('')
        pywikibot.info(wikitext)
        pywikibot.info('')
        pywikibot.info(comment)
        pywikibot.info(file_name)

        question = 'Do you want to upload this file?'

        choice = pywikibot.input_choice(
            question,
            [('Yes', 'y'), ('No', 'N')],
            default='N',
            automatic_quit=False
        )

        if choice == 'y':
            page = upload_file_to_commons(image_url, file_name,
                                          wikitext, comment)
            ret = edit_commons_mediaitem(page, structured_data)
            print(ret)

    def handle(self, *args, **kwargs):
        lookfor = None
        type = None
        collection = 'Studio Kuvasiskojen kokoelma'
#        collection='JOKA Journalistinen kuva-arkisto'

        for page in range(1, 201):
            # Prevent looping too fast for Finna server
            time.sleep(0.2)
            data = do_finna_search(page, lookfor, type, collection)
            if 'records' in data:
                for record in data['records']:
                    if 'Kekkonen, Urho Kaleva' not in str(record):
                        continue
                    # Not photo
                    if 'imagesExtended' not in record:
                        continue

                    print(".")
                    if not is_already_in_commons(record['id']):
                        self.process_finna_record(record)
