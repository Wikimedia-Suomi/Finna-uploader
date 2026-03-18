# import is used to populate djangodb with data from finna (fresh data) and/or commons (uploaded images)
# 
# this is used to reduce duplicated code (management commands) and simplify models.py
#


from images.models import FinnaImage
import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
import urllib.parse
from datetime import datetime
import time
from images.duplicatedetection import is_already_in_commons, get_existing_finna_ids_from_sparql, get_upload_summary, isToolforgeFinnaId

from images.finna_record_api import do_finna_search, \
                                    get_collection_name_from_alias, \
                                    get_finna_id_from_url

from images.wikitext.wikidata_helpers import get_author_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_institution_wikidata_id, \
                                    get_collection_wikidata_id, get_clean_institution_name

# todo: move more stuff from finna_record_api to here and make it simpler


def do_finna_import(opt_lookfor, opt_type, opt_collection, opt_alias, skip_update=False):

    # command handling will not call this method without a collection but keep this
    #default_collection = 'Studio Kuvasiskojen kokoelma'
    #if (opt_collection == None):
    #    opt_collection = default_collection

    #if (collection == None and aliases != None):
    #    collection = aliases

    if (opt_alias != None):
        opt_collection = get_collection_name_from_alias(opt_alias)


    print("fetching with search..")

    for page in range(1, 301):

        # images.finna.do_finna_search() will look again for a collection
        finna_records = do_finna_search(page, opt_lookfor, opt_type, opt_collection)
        if not finna_records:
            print("no result from search, stopping")
            break
        if not 'records' in finna_records:
            print("no records in search results, stopping")
            break
        
        if 'resultCount' in finna_records:
            print("received ", finna_records['resultCount'])

        for record in finna_records['records']:
            print(" -- -- -- ") # add a simple separator

            if (FinnaImage.objects.create_from_finna_record(record) == False):
                print("could not store record")
                return False

        # Prevent looping too fast for Finna server
        time.sleep(1)

    # this is actually pointless here since the record creation should use current configuration,
    # user(s) have to change the mapping first to make sense with running this,
    # but we can check the ids just before upload too..
    #print("updating ids..")
    #update_imported_wikidata_ids()

    # slow
    if (skip_update == False):
        print("updating uploaded images..")
        update_uploaded_images(opt_collection)
    else:
        print("skipping update of uploaded images")
    
    print("import done")
    
# only case used is from finna_search
# potentially we should update ids when mapping information changes in commons/wikidata
# in the data-pages, not just when searching..
#
# note that before uploading we need to recheck ids anyway 
# since mapping configuration from string to qcode is in commons instead of local/finna..
#
def update_imported_wikidata_ids():

    # TODO: should only check for new items that were imported instead of everything..
    # currently creating items tries to fetch id already

    institutions = FinnaImage.institutions
    for institution in institutions:
        if institution.wikidata_id: 
            continue
        try:
            wikidata_id = get_institution_wikidata_id(institution.translated)
            institution.set_wikidata_id(wikidata_id)
        except:
            pass

    # try to update collections in case new ones were added
    #collections = FinnaCollection.objects.all()
    collections = FinnaImage.collections
    for collection in collections:
        if collection.wikidata_id: 
            continue
        try:
            wikidata_id = get_collection_wikidata_id(collection.name)
            collection.set_wikidata_id(wikidata_id)
        except:
            pass
    
    #authors = FinnaNonPresenterAuthor.objects.all()
    authors = FinnaImage.non_presenter_authors
    for author in authors:
        if author.wikidata_id: 
            continue
        try:
            wikidata_id = get_author_wikidata_id(author.name)
            author.set_wikidata_id(wikidata_id)
        except:
            pass

    #actors = FinnaSubjectActor.objects.all()
    actors = FinnaImage.subject_actors
    for actor in actors:
        # there is bug in some data
        if (actor.skip_actor() == True):
            continue
        
        if actor.wikidata_id: 
            continue
        try:
            wikidata_id = get_subject_actors_wikidata_id(actor.name)
            actor.set_wikidata_id(wikidata_id)
        except:
            pass

# the list of uploaded summaries is much shorter so we should use different approach
# to update uploaded list based on that list
def update_existing_by_contribs():

    print("Loading 1000 most recent edit summaries for skipping uploaded files")

    # load recent contributions
    uploadsummary = get_upload_summary(1000)

    for url in uploadsummary:
        
        finnaid = get_finna_id_from_url(url)
        if (finnaid == None):
            print("no id in url:", url)
            continue
        #print("looking up local image by id:", finnaid)
        
        images = FinnaImage.objects.filter(finna_id = finnaid)
        for image in images:
            if (image.finna_id != finnaid):
                print("query gave image with different id:", image.finna_id)
                continue
                
            print("found local image with id:", image.finna_id)
            if (image.already_in_commons == False or image.already_in_commons == None):
                print("marking as uploaded with id:", finnaid)
                image.already_in_commons = True
                image.save(update_fields=['already_in_commons'])
        #else:
            # database might have only newer id in case it has changed
            #print("no local image for identifier:", finnaid)


def update_uploaded_images(collection=None):
    
    # TODO: push the list into database somewhere so we don't need to refetch often
    # and we can do lookups faster (maybe with mixed-case even)
    
    print("Loading existing ids by sparql")
    sparql_finna_ids_data = get_existing_finna_ids_from_sparql()

    #print("Loading 1000 most recent edit summaries for skipping uploaded files")
    #update_existing_by_contribs()

    print("Searching for existing images..")
    
    # TODO: filter by collection to reduce searches into those that are relevant
    # or add another flag for those that were added but not checked yet?
    
    images = FinnaImage.objects.filter(already_in_commons=False)
    for image in images:

        uploaded = False

        # in some cases id needs quoting
        # and data in commons may have quoted id instead of plain id
        if (image.finna_id.find("%25") < 0):
            quoted_finna_id = urllib.parse.quote_plus(image.finna_id)
            if (quoted_finna_id != image.finna_id):
                if quoted_finna_id in sparql_finna_ids_data:
                    uploaded = True
                elif (isToolforgeFinnaId(quoted_finna_id) == True):
                    uploaded = True

        if (uploaded == False):
            if image.finna_id in sparql_finna_ids_data:
                uploaded = True
            elif (isToolforgeFinnaId(image.finna_id) == True):
                uploaded = True
        
        if uploaded:
            image.already_in_commons = uploaded
            image.save(update_fields=['already_in_commons'])

    print("Update done.")

