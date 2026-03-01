from images.models import FinnaImage
import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
from datetime import datetime

from images.finna_record_api import get_finna_record, is_valid_finna_record
from images.pywikibot_helpers import edit_commons_mediaitem
from images.sdc_helpers import get_structured_data_for_new_image
from images.wikitext.commons_wikitext import get_wikitext_for_new_image, \
                                      get_comment_text
from images.wikitext.wikidata_helpers import get_author_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_institution_wikidata_id, \
                                    get_collection_wikidata_id, get_clean_institution_name


# before starting upload, recheck wikidata ids if they were not updated earlier:
# mapping may be added for authors/creators/subjects after data was fetched originally
# 
# this should simplify rest of data handling after this
def update_wikidata_id_for_record_data(finna_image):

    institutions = finna_image.institutions.all()
    for institution in institutions:
        try:
            wikidata_id = get_institution_wikidata_id(institution.translated)
            institution.set_wikidata_id(wikidata_id)
        except:
            pass

    non_presenter_authors = finna_image.non_presenter_authors.all()
    for author in non_presenter_authors:
        try:
            wikidata_id = get_author_wikidata_id(author.name)
            author.set_wikidata_id(wikidata_id)
        except:
            pass

    collections = finna_image.collections.all()
    for collection in collections:
        try:
            wikidata_id = get_collection_wikidata_id(collection.name)
            collection.set_wikidata_id(wikidata_id)
        except:
            pass

    actors = finna_image.subject_actors.all()
    for actor in actors:
        # there is bug in some data
        if (actor.name == None or actor.name == "" or actor.name == "null"):
            continue
        
        try:
            wikidata_id = get_subject_actors_wikidata_id(actor.name)
            actor.set_wikidata_id(wikidata_id)
        except:
            pass

    for add_depict in finna_image.add_depicts.all():
        try:
            wikidata_id = get_wikidata_id_from_url(add_depict.value)
            add_depict.set_wikidata_id(wikidata_id)
        except:
            pass

    for add_category in finna_image.add_categories.all():
        try:
            wikidata_id = get_wikidata_id_from_url(add_category.value)
            add_category.set_wikidata_id(wikidata_id)
        except:
            pass


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
    filename = finna_image.pseudo_filename
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
    
    # what is returned on success? what about failure?
    #if ret:

    finna_image.already_in_commons = True
    finna_image.save()

    # saved
    print(ret)

    #print('saved:', image_url)

    # ok, this is just for user information now
    return filename
