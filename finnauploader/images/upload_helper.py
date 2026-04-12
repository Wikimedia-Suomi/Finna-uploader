from images.models import FinnaImage
import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
import urllib
from datetime import datetime

from images.finna_record_api import get_finna_record, is_valid_finna_record
from images.sdc_helpers import get_structured_data_for_new_image
#from images.wikitext.wikidata_helpers import get_wikidata_id_from_url
from images.wikitext.commons_wikitext import get_wikitext_for_new_image, \
                                      get_comment_text
from images.wikitext.wikidata_helpers import get_author_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_institution_wikidata_id, \
                                    get_collection_wikidata_id, striprepeatespaces
from images.wikitext.timestamps import parse_timestamp 

from images.download_helper import download_file 


# before starting upload, recheck wikidata ids if they were not updated earlier:
# mapping may be added for authors/creators/subjects after data was fetched originally
# 
# this should simplify rest of data handling after this
def update_wikidata_id_for_record_data(finna_image):

    # this should not be empty, there should be institution
    institutions = finna_image.institutions.all()
    for institution in institutions:

        # fixup before lookup
        instname = striprepeatespaces(institution.translated)
        
        wikidata_id = get_institution_wikidata_id(instname)
        institution.set_wikidata_id(wikidata_id)

    # if author(s) are not known the list should be empty
    non_presenter_authors = finna_image.non_presenter_authors.all()
    for author in non_presenter_authors:

        # fixup before lookup
        authname = striprepeatespaces(author.name)
        
        wikidata_id = get_author_wikidata_id(authname)
        author.set_wikidata_id(wikidata_id)

    # if there are no collections the list should be empty, that should be fine
    collections = finna_image.collections.all()
    for collection in collections:

        # fixup before lookup
        collname = striprepeatespaces(collection.name)

        wikidata_id = get_collection_wikidata_id(collname)
        collection.set_wikidata_id(wikidata_id)

    # if there are no known actors this list should be empty
    actors = finna_image.subject_actors.all()
    for actor in actors:
        # there is bug in some data
        if (actor.skip_actor() == True):
            continue

        # fixup before lookup
        actname = striprepeatespaces(actor.name)
        
        wikidata_id = get_subject_actors_wikidata_id(actname)
        actor.set_wikidata_id(wikidata_id)

    # empty set, not in use
    #for add_depict in finna_image.add_depicts.all():
    #    wikidata_id = get_wikidata_id_from_url(add_depict.value)
    #    add_depict.set_wikidata_id(wikidata_id)

    # empty set, not in use
    #for add_category in finna_image.add_categories.all():
    #    wikidata_id = get_wikidata_id_from_url(add_category.value)
    #    add_category.set_wikidata_id(wikidata_id)
    
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
    name = striprepeatespaces(name)

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
    name = name.replace(" ", "_")  # ensure replaced characters have underscore (no need for %20)

    # try to remove soft-hyphens from name while we can
    # note: 0xC2 0xAD in utf-8, 0x00AD in utf-16, which one is used?
    name = name.replace(u"\u00A0", "")
    name = name.replace("\xc2\xa0", "")
    name = name.replace("‎", "") # remove non-printable space

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
        
        # instead of cutting between word (or multi-byte character)
        # look for preceding space to cut in (and avoid illegal encoding)
        inewend = quoted_name.rfind("_", 1, newnamelen-1)
        if (inewend > 1 and inewend < newnamelen):
            newnamelen = inewend
            print("found underscore, limiting to", newnamelen)
        else:
            print("no underscore", inewend)
        
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
    file_name = file_name.replace("‎", "") # remove non-printable space

    # wiki doesn't allow non-breakable spaces or soft-hyphens
    quoted_name = urllib.parse.quote_plus(file_name)
    quoted_name = quoted_name.replace("%C2%A0", " ")
   
    file_name = urllib.parse.unquote(quoted_name)

    print("DEBUG: generated file name for upload:", file_name)
    return file_name

# check and return correct url with some encoding (if needed)
def get_image_url(finna_image):

    image_url = finna_image.master_url

    # should not need this here
    #if (image_url.startswith("/Cover/Show") is True):
    
    # if we store incomplete url -> needs fixing
    if (image_url.find("http://") < 0 and image_url.find("https://") < 0):
        print("URL is not complete:", image_url)
        return None

    # can't upload from redirector with copy-upload:
    # must handle differently
    #if (image_url.find("siiri.urn") > 0): 
    if (image_url.find("profium.com") > 0):
        print("Cannot use copy-upload from URL:", image_url)
        return None
    
    return image_url

# we have some cases where might need to download locally first
# and apply format conversion or use different source domain (not copy-upload).
# some urls might have redirect service in use.
def download_image(remote_url):
#
# siiri can have redirect of the image from url given in Finna
# so follow correct location: we can't use copy-upload for this if we don't know where it is..
#
    redirect = False
    if (remote_url.find("siiri.urn") > 0):
        redirect = True

    buffer = download_file(remote_url, redirect)
    if (buffer == None):
        print("ERROR: could not get buffer")
        return None
    if (buffer.readable() == False or buffer.closed == True):
        print("ERROR: can't read image from stream")
        return None
    if (buffer.getbuffer().nbytes < 100):
        print("ERROR: less than 100 bytes in buffer")
        return None

    img = None
    try:
        img = Image.open(buffer)
        # TODO:
        # check image format, validity
        return img
    except:
        print("ERROR: pillow failed to open image from buffer")
        return None
    return img


# bad name due to existing methods, rename later
# called from views.py on upload
#
def upload_file_update_metadata(finna_id):

    # refetch finna_image.already_in_commons,
    # it seems the display still has images that are already uploaded
    # so they should be skipped
    
    # try to lookup first if image really was uploaded already
    # since the something still lists uploaded images..
    #
    existing = FinnaImage.objects.filter(finna_id = finna_id)
    for old_image in existing:
        if (old_image.already_in_commons == True):
            print("image has been uploaded already with id:", finna_id)
            return ""

        # if/when there is timeout in upload, track the unfinished uploads
        #old_image.upload_started = True
        if (old_image.upload_started == True and old_image.already_in_commons == False):
            print("upload started but not finished for:", finna_id)
            # TODO: file may exist but metadata doesn't?
            # if so, add only metadata for it

    
    # Update to latest finna_record
    response = get_finna_record(finna_id, True)
    if (is_valid_finna_record(response) == False):
        print("could not get finna record by id:", finna_id)
        return ""
    new_record = response['records'][0]

    print("DEBUG: new record from finna for id:", finna_id)
    print(str(new_record))

    # ok, so we verify we got current data before upload,
    # but why create new record instance instead of looking up old and updating?
    # see what can be done..
    finna_image = FinnaImage.objects.create_from_data(new_record)
    
    # verify we have valid wikidata id where necessary
    if (update_wikidata_id_for_record_data(finna_image) == False):
        print("failed to update wikidata ids for record:", finna_id)
        return ""

    # TODO: when using local file in upload, verify image format from file
    # generate name for the upload, show it to the user as well
    filename = generate_filename_for_commons(finna_image)
    if (filename == None):
        print("failed to get filename for:", finna_id)
        return ""

    # check url and apply some encoding (if necessary)
    image_url = get_image_url(finna_image)
    if (image_url == None):
        print("failed to get image url for:", finna_id)
        return ""

    local_img = None
    #local_file = False
    if (image_url.find("siiri.urn") > 0):
        #local_file = True
        local_img = download_image(image_url)
        if (local_img == None):
            print("failed to get image from url:", image_url)
            return ""


    # TODO: if necessary, in case of redirector (copy-upload can't be used)
    # download the file first before uploading
    #buf = download_file(image_url)
    # TODO: should we use buffer directly or save to temp file?
    # TODO: when using local file in upload, verify image format from file

    commonssite = pywikibot.Site('commons', 'commons')
    commonssite.login()
    
    # before doing other tasks it would be good to check first if file with same name exists
    #also make sure not to create it by mistake while checking..

    commons_file_name = "File:" + filename
    file_page = pywikibot.FilePage(commonssite, commons_file_name)

    # TODO: if image exists but metadata does not: try write that?
    # see how commons server responds..
    # !! we should be careful here not to overwrite something that was maybe done manually or by another script already
    # so some special care is needed -> needs different checking of what is in structured data already etc. !!
    #if (old_image.upload_started == True and file_page.exists() == True):
        #metadataupdate()

    # Check if the page exists
    if file_page.exists():
        print(f"The file {commons_file_name} exists already in Commons, skipping.")

        # need to check further before accepting it as same?
        #old_image.already_in_commons = True
        #old_image.save()
        #print("saved status for ", old_image.finna_id)
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

    # if/when there is timeout in upload, track the unfinished uploads
    old_image.upload_started = True
    old_image.save()

    # TODO: if there are multiple images in same record,
    # we would need the index in the name and loop thorugh the urls in record
    # (currently only first is used)

    # TODO: add download + local upload for some problematic cases where copy-upload isn't possible
    # see if we can solve redirect-urls that way?
    
    file_page.text = wikitext
    
    if (local_img == None):
        try:
            # Load file from url
            file_page.upload(image_url, comment=comment, asynchronous=True)
        except:
            print(f"The file {commons_file_name} failed to be uploaded.")
            raise
    else:
        try:
            # Load file from url
            file_page.upload(local_img, comment=comment, asynchronous=False)
        except:
            print(f"The file {commons_file_name} failed to be uploaded.")
            raise
        

    # if we need to do download/conversion first
    # upload from local file
    #if (upload_local == True):
    #    print("uploading converted local file ")
    # TODO : use buffer directly instead of file?
    #    file_page.upload(image_file_name, comment=comment,ignore_warnings=True)

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

# Edit Wikimedia Commons mediaitem using wbeditentity
def edit_commons_mediaitem(commonssite, page_title, data):
    
    # Reload file_page to be sure that we have updated page_id

    file_page = pywikibot.FilePage(commonssite, page_title)
    media_identifier = 'M' + str(file_page.pageid) # what is in pageid on error?
    print("media identifier: ", media_identifier)

    csrf_token = commonssite.tokens['csrf']
    payload = {
        'action': 'wbeditentity',
        'format': u'json',
        'id': media_identifier,
        'data':  json.dumps(data),
        'token': csrf_token,
        'bot': True,  # in case you're using a bot account (which you should)
    }
    request = commonssite.simple_request(**payload)
    ret = request.submit()
    return ret
