import pywikibot
from images.models import FinnaImage, FinnaSubjectWikidataPlace
from images.finna import get_finna_id_from_url, get_finna_record_by_id
from images.pywikibot_helpers import test_if_finna_id_exists_in_commons
from django.core.management.base import BaseCommand
from images.wikitext.photographer import get_wikitext_for_new_image
from images.duplicatedetection import is_already_in_commons
from images.sdc_helpers import get_structured_data_for_new_image
from images.locations import get_wikidata_items_using_yso, \
                             update_yso_places, \
                             is_location_within_administrative_entity
from images.location_hierarcy import convert_subject_places_to_hierarcy, \
                                     get_best_location_ids, \
                                     get_best_location_id
from images.wikitext.wikidata_helpers import get_subject_place_wikidata_id
from images.pywikibot_helpers import edit_commons_mediaitem, \
                                     upload_file_to_commons, \
                                     get_comment_text
import urllib.request
import xml.etree.ElementTree as ET


def get_rss_feed():
    ret = {}

    # URL of the RSS feed
    rss_url = "https://www.finna.fi/List/1607656?view=rss"

    # Fetch the RSS feed
    with urllib.request.urlopen(rss_url) as response:
        rss_content = response.read()

        # Parse the RSS feed
        root = ET.fromstring(rss_content)

        # List GUIDs of the items
        print("GUIDs of the RSS feed items:")
        for item in root.findall('.//item'):
            filename = None
            guid = item.find('guid')
            if guid is not None:
                link = guid.text

            description = item.find('description')
            if description is not None:
                filename = description.text.strip().split('\n')[0]

            ret[link] = filename

    return ret


def get_subject_place_parts(subject_place_string):
    subject_places = []
    for place_name in subject_place_string.split(', '):
        place_name = place_name.strip().rstrip(',').strip()
        if place_name == 'Suomen entinen kunta/pitäjä':
            continue
        # Too complex matches
        if place_name == 'Lappi':
            continue
        if place_name and place_name not in subject_places:
            subject_places.append(place_name)
    return subject_places


def get_wikidata_id_by_subject_extented(subject_extenteds, place_name):

    subjects = subject_extenteds.filter(heading=place_name,
                                        type='URI',
                                        record_id__isnull=False
                                        ).exclude(record_id='')
    # Just for sanity checking
    if len(subjects) > 1:
        msg = 'multiple results from get_wikidata_from_subject_extented'
        print(f'ERROR: {msg}')
        print(subjects)
        print(place_name)
        exit(1)

    # In addition to YSO there is Muinaisjäännösrekisteri links
    # which could be mapped to wikidata items

    for subject in subjects:
        if 'http://www.yso.fi/onto/yso/p' in subject.record_id:
            yso_id = subject.record_id
            yso_id = yso_id.replace('http://www.yso.fi/onto/yso/', '')
            wikidata_id = get_wikidata_items_using_yso(yso_id)
            print(wikidata_id)
            if wikidata_id:
                return wikidata_id


def fix_subject_places(f):
    subject_places = f.subject_places.all()
    ret = set()
    for subject_place in subject_places:
        print(subject_place)

        if subject_place.wikidata_id:
            print(f'{subject_place.wikidata_id} EXISTS.')
            return

        # Clean the place_name string for splitting
        place_name = subject_place.name.strip().replace('\n', ', ').rstrip(',')

        # Get wikidata_id from commons subjectPlace page
        # https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/subjectPlaces
        subject_place_wikidata_id = get_subject_place_wikidata_id(place_name)
        if subject_place_wikidata_id:
            subject_place.wikidata_id = subject_place_wikidata_id
            subject_place.save()
            return subject_place_wikidata_id

        # Not exact enough for final value,
        # but can be used for validating the parsed value
        ext_wikidata_id = get_wikidata_id_by_subject_extented(
                              f.subject_extented,
                              subject_place.name)

        # Split subject place string to list
        subject_place_parts = get_subject_place_parts(subject_place.name)

        if len(subject_place_parts) == 0:
            return None

        # Update YSO places cache
        update_yso_places(subject_place_parts, f.finna_id)

        row = convert_subject_places_to_hierarcy(subject_place_parts)
        wikidata_location_ids = get_best_location_ids(row, len(subject_place_parts))  # noqa
        if not wikidata_location_ids:
            wikidata_location_ids = ext_wikidata_id

        for wikidata_location_id in wikidata_location_ids:
            if not ext_wikidata_id:
                ret.add(wikidata_location_id)
                continue
            elif len(ext_wikidata_id) == 1:
                ext_wikidata_id = ext_wikidata_id[0]

            if wikidata_location_id == ext_wikidata_id:
                print("OK1")
                ret.add(wikidata_location_id)
            elif is_location_within_administrative_entity(
                     wikidata_location_id,
                     ext_wikidata_id,
                     True):

                ret.add(wikidata_location_id)
                print("OK2")
            elif is_location_within_administrative_entity(
                     ext_wikidata_id,
                     wikidata_location_id,
                     True):
                ret.add(ext_wikidata_id)
                print("OK2")
            else:
                print("NOT FOUND")
                exit(1)
    confirmed_locations = list(ret)

    filtered_locations = get_best_location_id(confirmed_locations)
    if filtered_locations:
        if isinstance(filtered_locations, str):
            confirmed_locations = [filtered_locations]
        else:
            confirmed_locations = filtered_locations

    print(confirmed_locations)

    obj = FinnaSubjectWikidataPlace.objects
    for confirmed_location in confirmed_locations:
        location, created = obj.get_or_create(uri=confirmed_location)
        f.best_wikidata_location.add(location)


class Command(BaseCommand):
    help = ('Reads list of Finna images from a Wikimedia Commons ',
            'upload request page and upload those to Wikimedia Commons.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the command without writing to Wikimedia Commons.'
        )

    def upload_finna_record(self,
                            record,
                            local_data,
                            dry_run=None,
                            file_name=None):
        print('https://finna.fi/Record/' + str(record['id']))

        finna_image = FinnaImage.objects.create_from_data(record, local_data)
        fix_subject_places(finna_image)

        for s in finna_image.best_wikidata_location.all():
            print(s)

        if file_name:
            if len(file_name) > 64:
                print(f'Filename: {file_name} is too long')
                exit(1)

        identifier = ''
        # some images don't have identifier to be used
        if file_name and finna_image.identifier_string is not None:
            identifier = finna_image.identifier_string.strip()
            identifier = identifier.replace(":", "-")
            identifier = identifier.replace("/", "_")
            if identifier:
                identifier = f'_({identifier})'

            file_name = file_name.replace(' ', '_')
            extension = finna_image.filename_extension
            file_name = f'{file_name}{identifier}.{extension}'
        else:
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
            if dry_run:
                print("Dry_run selected. Skipping the actual upload.")
                return
            page = upload_file_to_commons(image_url, file_name,
                                          wikitext, comment)
            ret = edit_commons_mediaitem(page, structured_data)
            print(ret)
            print("OK")

    def handle(self, *args, **options):
        site = pywikibot.Site('commons', 'commons')
        page = pywikibot.Page(site, 'User:FinnaUploadBot/uploadrequest')
        external_links = []
        add_categories = []
        add_depicts = []
        dry_run = options['dry_run']

        local_data = {
            'add_categories': add_categories,
            'add_depicts': add_depicts
        }

        # Iterate over the external links on the page
        finna_ids = {}
        for link in page.extlinks():
            if 'https://www.finna.fi/List/' in link:
                rssfeed = get_rss_feed()
                for link in rssfeed:
                    finna_id = get_finna_id_from_url(link)
                    filename = rssfeed[link]
                    finna_ids[finna_id] = filename
            else:
                finna_id = get_finna_id_from_url(link)
                if finna_id:
                    finna_ids[finna_id] = None

        rssfeed = get_rss_feed()
        for link in rssfeed:
            finna_id = get_finna_id_from_url(link)
            filename = rssfeed[link]
            finna_ids[finna_id] = filename

        for finna_id in finna_ids:
            if finna_id:
                filename = finna_ids[finna_id]
                finna_record = get_finna_record_by_id(finna_id)
                existing_files = test_if_finna_id_exists_in_commons(finna_id)
                if existing_files:
                    msg = f'Finna ID {finna_id} already exists in Wikimedia Commons with files: {existing_files}'  # noqa
                    pywikibot.info(msg)
                    continue
                else:
                    msg = f'Finna ID {finna_id} does not exist in Wikimedia Commons.'  # noqa
                    pywikibot.info(msg)
                    self.upload_finna_record(finna_record,
                                             local_data,
                                             dry_run,
                                             filename)

                params = {
                         'url': link,
                         'finna_id': finna_id,
                         'record': finna_record,
                         'record': finna_record,
                         'existing_files': existing_files
                         }
                external_links.append(params)

                msg = f'Found external link: {link} with Finna ID: {finna_id}'
                pywikibot.info(msg)
            else:
                pywikibot.info(f'No Finna ID found in link: {link}')

        # Optionally, do something with the external links
        pywikibot.info(f'Total external links found: {len(external_links)}')
