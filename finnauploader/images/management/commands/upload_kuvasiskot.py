from django.core.management.base import BaseCommand
from images.models import FinnaImage
import pywikibot
import time
from images.finna import do_finna_search
from images.wikitext.photographer import get_wikitext_for_new_image
from images.duplicatedetection import is_already_in_commons
from images.finna_image_sdc_helpers import get_structured_data_for_new_image
from images.pywikibot_helpers import edit_commons_mediaitem, \
                                     upload_file_to_commons, \
                                     get_comment_text


class Command(BaseCommand):
    help = 'Upload kuvasiskot images'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--type',
            type=str,
            choices=['AllFields', 'Subjects'],
            help=('Finna type argument. '
                  'Argument selects where lookfor matches.')
        )

        parser.add_argument(
            '--lookfor',
            type=str,
            help='Finna lookfor argument.',
        )

        parser.add_argument(
            '--require-text',
            action='append',
            type=str,
            help=('Include record only if text is in Finna record. '
                  'This option can be defined multiple times.')
        )

        parser.add_argument(
            '--skip-text',
            action='append',
            type=str,
            help=('Skip record if text is in Finna record. '
                  'This option can be defined multiple times.')
        )

    # Return True if all inputs are found or there is no input
    def find_all_texts(self, texts, record):
        record_text = str(record)

        if not texts:
            return True

        for text in texts:
            if text not in record_text:
                return False
        return True

    # Return True if any of the inputs are found
    def find_any_text(self, texts, record):
        record_text = str(record)

        if not texts:
            return False

        for text in texts:
            if text in record_text:
                return True
        return False

    def process_finna_record(self, record):
        print(record['id'])

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

    def handle(self, *args, **options):
        lookfor = options['lookfor'] or None
        type = options['type'] or None
        required_filter = options['require_text']
        skip_filter = options['skip_text']

        collection = 'Studio Kuvasiskojen kokoelma'
#        collection='JOKA Journalistinen kuva-arkisto'

        for page in range(1, 201):
            # Prevent looping too fast for Finna server
            time.sleep(0.2)
            data = do_finna_search(page, lookfor, type, collection)

            # If no results from Finna then exit
            if not 'records' in data:
                break
            else:
                for record in data['records']:
                    # Not photo
                    if 'imagesExtended' not in record:
                        continue

                    # skip if no required text is found
                    if not self.find_all_texts(required_filter, record):
                        continue

                    # skip if skip filter text is found
                    if self.find_any_text(skip_filter, record):
                        continue

                    print(".")
                    if not is_already_in_commons(record['id']):
                        self.process_finna_record(record)
