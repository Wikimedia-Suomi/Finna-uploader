from images.models import FinnaImage
import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
import urllib
from datetime import datetime

from images.finna_record_api import get_finna_record, is_valid_finna_record
from images.pywikibot_helpers import edit_commons_mediaitem
from images.pywikibot_helpers import get_wikidata_id_from_url
from images.sdc_helpers import get_structured_data_for_new_image
from images.wikitext.commons_wikitext import get_wikitext_for_new_image, \
                                      get_comment_text
from images.wikitext.wikidata_helpers import get_author_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_institution_wikidata_id, \
                                    get_collection_wikidata_id, striprepeatespaces
from images.wikitext.timestamps import parse_timestamp 


# before starting upload, recheck wikidata ids if they were not updated earlier:
# mapping may be added for authors/creators/subjects after data was fetched originally
# 
# this should simplify rest of data handling after this
def update_wikidata_id_for_record_data(finna_image):

    # this should not be empty, there should be institution
    institutions = finna_image.institutions.all()
    for institution in institutions:
        wikidata_id = get_institution_wikidata_id(institution.translated)
        institution.set_wikidata_id(wikidata_id)

    # if author(s) are not known the list should be empty
    non_presenter_authors = finna_image.non_presenter_authors.all()
    for author in non_presenter_authors:
        wikidata_id = get_author_wikidata_id(author.name)
        author.set_wikidata_id(wikidata_id)

    # if there are no collections the list should be empty, that should be fine
    collections = finna_image.collections.all()
    for collection in collections:
        wikidata_id = get_collection_wikidata_id(collection.name)
        collection.set_wikidata_id(wikidata_id)

    # if there are no known actors this list should be empty
    actors = finna_image.subject_actors.all()
    for actor in actors:
        # there is bug in some data
        if (actor.skip_actor() == True):
            continue
        
        wikidata_id = get_subject_actors_wikidata_id(actor.name)
        actor.set_wikidata_id(wikidata_id)

    for add_depict in finna_image.add_depicts.all():
        wikidata_id = get_wikidata_id_from_url(add_depict.value)
        add_depict.set_wikidata_id(wikidata_id)

    for add_category in finna_image.add_categories.all():
        wikidata_id = get_wikidata_id_from_url(add_category.value)
        add_category.set_wikidata_id(wikidata_id)
    
    return True

def update_dates_in_filename(input_str):
    # Regular expression to find the date in the format d.m.yyyy
    date_pattern = r"\d{1,2}\.\d{1,2}\.\d{4}"
    found_date = re.search(date_pattern, input_str)

    if found_date:
        # Extract the date
        date_str = found_date.group()

        # Parse the date
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")

        # Format the date into the desired format
        formatted_date = date_obj.strftime("%Y-%m-%d")

        # Replace the old date in the string with the new formatted date
        output_str = input_str.replace(date_str, formatted_date)
    else:
        output_str = input_str
    return output_str

def get_filename_extension(master_format):
    if (master_format == None or master_format == ""):
        print("format missing for file extension")
        return None
    
    format_to_extension = {
        'tif': 'tif',
        'tiff': 'tif',
        'image/tiff': 'tif',
        'png': 'png',
        'image/png': 'png',
        'jpg': 'jpg',
        'jpeg': 'jpg',
        'image/jpeg': 'jpg',
        'gif': 'gif',
        'image/gif': 'gif'
    }

    if (master_format in format_to_extension):
        extension = format_to_extension[master_format]
        return extension
    return None

# simplify data model: this is only place where we actually use this
#
def generate_filename_for_commons(finna_image):

    filename_extension = get_filename_extension(finna_image.master_format)
    if (filename_extension == None):
        print("unable to get extension for filename")
        return None
        
    summaries_name = finna_image.summaries.filter(lang='en').first()
    alt_title_name = finna_image.alternative_titles.filter(lang='en').first()

    name = None
    if summaries_name and alt_title_name:
        if len(str(summaries_name)) > len(str(alt_title_name)):
            name = alt_title_name.text
        else:
            name = summaries_name.text

    if not name:
        name = finna_image.short_title

    # filename in commons can't exceed 240 bytes:
    # let's assume we have narrow ASCII only..
    if (len(name) > 240):
        if (finna_image.short_title is not None and len(finna_image.short_title) < 240):
            print("using short title name")
            name = finna_image.short_title
        elif (alt_title_name is not None and len(str(alt_title_name)) < 240):
            print("using alt title name")
            name = alt_title_name.text
        elif (summaries_name is not None and len(str(summaries_name)) < 240):
            print("using summaries name")
            name = summaries_name.text
        else:
            print("unable to find name shorter than maximum for filename")

    # commons does not accept "å" in filename?
    # does not suffice, something else is wrong?
    #must_be_quoted_name = False
    #if (name.find("å") > 0):
    #    must_be_quoted_name = True

    name = update_dates_in_filename(name)
    name = name.replace('content description: ', '')
    name = name.replace(".", "_")
    name = name.replace(" ", "_")
    name = name.replace(":", "_")
    name = name.replace("#", "_")
    name = name.replace("_", " ").strip()

    if finna_image.year and str(finna_image.year) not in name:
        year = f'{finna_image.year}'
    else:
        year = ''

    # if there is large difference in year don't add it to name:
    # year in different fields can vary a lot
    if (finna_image.date_string is not None):
        timestamp, precision = parse_timestamp(finna_image.date_string)
        if (timestamp is not None):
            if (year != str(timestamp.year)):
                print("year " + year + " does not match date string " + str(timestamp.year) + ", ignoring it")
                year = ''

    # some images don't have identifier to be used
    if (finna_image.identifier_string is not None):
        identifier = striprepeatespaces(finna_image.identifier_string)
        # replace characters not allowed in commons filenames
        identifier = identifier.replace(":", "-")
        identifier = identifier.replace("/", "_")
    else:
        identifier = ''

    name = name.replace(" ", "_")
    name = name.replace("/", "_")   # don't allow slash in names
    name = name.replace("\n", " ")  # don't allow newline in names
    name = name.replace("\t", " ")  # don't allow tabulator in names
    name = name.replace("\r", " ")  # don't allow carriage return in names

    # try to remove soft-hyphens from name while we can
    # note: 0xC2 0xAD in utf-8, 0x00AD in utf-16, which one is used?
    name = name.replace(u"\u00A0", "")
    name = name.replace("\xc2\xa0", "")

    lenident = len(year) +1 + len(identifier)+2 + len(filename_extension)+1

    quoted_name = urllib.parse.quote_plus(name)

    # wiki doesn't allow soft hyphen in names:
    # normal replace() does not work on silent characters for some reason?
    # -> kludge around it
    quoted_name = quoted_name.replace("%C2%AD", "")

    # each character with umlaut becomes at least three in HTML-encoding..
    if ((len(quoted_name) + lenident) >=  200):
        print("WARN: quoted filename is becoming too long, limiting it")
        
        newnamelen = (220 - lenident)
        if (newnamelen > 200):
            newnamelen = 200
        
        quoted_name = quoted_name[:newnamelen] + "__"
        print("new name: ", quoted_name)

    # unquote again..
    name = urllib.parse.unquote(quoted_name)

    if (len(year) > 0):
        year = year + '_'
    if (len(identifier) > 0):
        file_name = f'{name}_{year}({identifier}).{filename_extension}'
    else:
        # in some odd cases there is no identifier (accession number) for the file
        file_name = f'{name}_{year}.{filename_extension}'

    # replace non-breakable spaces with normal spaces
    # 0xC2 0xA0 in utf-8, 0x00A0 in utf-16
    file_name = file_name.replace(u"\u00A0", " ")

    # wiki doesn't allow non-breakable spaces or soft-hyphens
    quoted_name = urllib.parse.quote_plus(file_name)
    quoted_name = quoted_name.replace("%C2%A0", " ")
   
    file_name = urllib.parse.unquote(quoted_name)

    print("DEBUG: generated file name for upload:", file_name)
    return file_name

# bad name due to existing methods, rename later
# called from views.py on upload
#
def upload_file_update_metadata(finna_id):
    
    # Update to latest finna_record
    response = get_finna_record(finna_id, True)
    if (is_valid_finna_record(response) == False):
        print("could not get finna record by id:", finna_id)
        return ""
    new_record = response['records'][0]

    print("DEBUG: new record from finna for id:", finna_id)
    print(str(new_record))

    # 
    finna_image = FinnaImage.objects.create_from_data(new_record)
    
    # verify we have valid wikidata id where necessary
    if (update_wikidata_id_for_record_data(finna_image) == False):
        print("failed to update wikidata ids for record:", finna_id)
        return ""

    # generate name for the upload, show it to the user as well
    filename = generate_filename_for_commons(finna_image)
    if (filename == None):
        print("failed to get filename for:", finna_id)
        return ""
    image_url = finna_image.master_url
    
    # if we store incomplete url -> needs fixing
    if (image_url.find("http://") < 0 and image_url.find("https://") < 0):
        print("URL is not complete:", image_url)
        return ""

    # can't upload from redirector with copy-upload:
    # must handle differently
    if (image_url.find("siiri.urn") > 0 or image_url.find("profium.com") > 0):
        print("Cannot use copy-upload from URL:", image_url)
        return ""

    commonssite = pywikibot.Site('commons', 'commons')
    commonssite.login()
    
    # before doing other tasks it would be good to check first if file with same name exists
    #also make sure not to create it by mistake while checking..

    commons_file_name = "File:" + filename
    file_page = pywikibot.FilePage(commonssite, commons_file_name)

    # Check if the page exists
    if file_page.exists():
        print(f"The file {commons_file_name} exists already in Commons, skipping.")
        return ""

    # try to generate early so it is possible to return before trying to upload
    structured_data = get_structured_data_for_new_image(finna_image)
    wikitext = get_wikitext_for_new_image(finna_image)
    comment = get_comment_text(finna_image)

    if (len(comment) > 250):
        print("WARN: length of comment exceeds 250 characters")
        #comment = comment[:250]

    # Debug log
    print('')
    print(wikitext)
    print('')
    print(comment)
    print(filename)

    print('uploading from:', image_url)

    # TODO: if there are multiple images in same record,
    # we would need the index in the name and loop thorugh the urls in record
    # (currently only first is used)

    # TODO: add download + local upload for some problematic cases where copy-upload isn't possible
    # see if we can solve redirect-urls that way?
    
    file_page.text = wikitext
    try:
        # Load file from url
        file_page.upload(image_url, comment=comment, asynchronous=True)
    except:
        print(f"The file {commons_file_name} failed to be uploaded.")
        raise

    # TODO: in case image upload went to sleep for a while pywikibot does not handle it correctly:
    # image might be there but server thinks it is locked by someone else?
    # -> cannot save structured data for it
    # can we solve this by synchronous method? recreated structured data?

    # generate structured data here instead?
    #structured_data = get_structured_data_for_new_image(finna_image)

    page_title = file_page.title()
    print("page uploaded", page_title)

    # this is supposed to reload same page to make sure id is updated?
    ret = edit_commons_mediaitem(commonssite, page_title, structured_data)

    print("saving status..", page_title)
    
    # what is returned on success? what about failure?
    #if ret:

    finna_image.already_in_commons = True
    finna_image.save()

    # saved
    print(ret)

    #print('saved:', image_url)

    # ok, this is just for user information now
    return filename
