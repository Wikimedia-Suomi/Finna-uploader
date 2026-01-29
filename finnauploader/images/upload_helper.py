import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
from datetime import datetime

from images.pywikibot_helpers import edit_commons_mediaitem
from images.sdc_helpers import get_structured_data_for_new_image
from images.wikitext.commons_wikitext import get_wikitext_for_new_image, \
                                      get_comment_text


# bad name due to existing methods, rename later
# called from views.py on upload
#
def upload_file_update_metadata(finna_image):

    commonssite = pywikibot.Site('commons', 'commons')
    commonssite.login()

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
