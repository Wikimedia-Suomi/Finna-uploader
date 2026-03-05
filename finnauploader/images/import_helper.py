# import is used to populate djangodb with data from finna (fresh data) and/or commons (uploaded images)
# 
# this is used to reduce duplicated code (management commands) and simplify models.py
#


from images.models import FinnaImage
import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
from datetime import datetime
import time
from images.duplicatedetection import is_already_in_commons
from images.finna_record_api import do_finna_search
from images.wikitext.wikidata_helpers import get_author_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_institution_wikidata_id, \
                                    get_collection_wikidata_id, get_clean_institution_name

# todo: move more stuff from finna_record_api to here and make it simpler


def do_finna_import(opt_lookfor, opt_type, opt_collection):

    #if (collection == None and aliases != None):
    #    collection = aliases

    for page in range(1, 301):

        # images.finna.do_finna_search() will look again for a collection
        data = do_finna_search(page, opt_lookfor, opt_type, opt_collection)
        if (FinnaImage.objects.create_from_finna_record(data) == False):
            return False

        # Prevent looping too fast for Finna server
        time.sleep(1)

    update_wikidata_ids()
    
# when and where is this called?
# only case is from finna_search?
# potentially we should update ids when mapping information changes in commons/wikidata
# in the data-pages, not just when searching..
# FinnaRecordManager is a member of FinnaImage (objects)
# and it also contains these other objects..
# this lookup therefore calls back to parent to fetch the list it has
#
def update_wikidata_ids():
    
    #FinnaImage.objects.update_wikidata_ids()
    
    #authors = FinnaNonPresenterAuthor.objects.all()
    authors = FinnaImage.non_presenter_authors.all()
    for author in authors:
        try:
            wikidata_id = get_author_wikidata_id(author.name)
            author.set_wikidata_id(wikidata_id)
        except:
            pass

    #actors = FinnaSubjectActor.objects.all()
    actors = FinnaImage.subject_actors.all()
    for actor in actors:
        # there is bug in some data
        if (actor.name == None or actor.name == "" or actor.name == "null"):
            continue
        
        try:
            wikidata_id = get_subject_actors_wikidata_id(actor.name)
            actor.set_wikidata_id(wikidata_id)
        except:
            pass

    # try to update collections in case new ones were added
    #collections = FinnaCollection.objects.all()
    collections = FinnaImage.collections.all()
    for collection in collections:
        try:
            wikidata_id = get_collection_wikidata_id(collection.name)
            collection.set_wikidata_id(wikidata_id)
        except:
            pass

    images = FinnaImage.objects.filter(already_in_commons=False)
    for image in images:
        uploaded = is_already_in_commons(image.finna_id, fast=True)
        if uploaded:
            image.already_in_commons = uploaded
            image.save(update_fields=['already_in_commons'])

