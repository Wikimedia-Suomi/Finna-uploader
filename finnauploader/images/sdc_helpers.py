# for updates to commons structured data context

from datetime import datetime
import pywikibot
import json
from images.wikitext.commons_wikitext import clean_depicted_places
from images.wikitext.timestamps import parse_timestamp

wikidata_site = pywikibot.Site("wikidata", "wikidata")  # Connect to Wikidata


def create_P7482_source_of_file(url, operator, publisher):
    # Q74228490 = file available on the internet

    if not url:
        return None

    if not operator:
        return None

    if not publisher:
        return None

    claim_target = pywikibot.ItemPage(wikidata_site, 'Q74228490')
    claim = pywikibot.Claim(wikidata_site, 'P7482')
    claim.setTarget(claim_target)

    # Now we'll add the qualifiers

    # P973 "described at URL"
    qualifier_url = pywikibot.Claim(wikidata_site, 'P973')
    qualifier_url.setTarget(url)
    summary = 'Adding P973 (described at URL) qualifier'
    claim.addQualifier(qualifier_url, summary=summary)

    # P137 "operator" - example: National Library of Finland
    qualifier_operator = pywikibot.Claim(wikidata_site, 'P137')
    qualifier_target = pywikibot.ItemPage(wikidata_site, operator)
    qualifier_operator.setTarget(qualifier_target)
    summary = 'Adding P137 (operator) qualifier'
    claim.addQualifier(qualifier_operator, summary=summary)

    # P123 "publisher" - exampe: Finnish Heritage Agency (Museovirasto)
    qualifier_publisher = pywikibot.Claim(wikidata_site, 'P123')
    qualifier_target = pywikibot.ItemPage(wikidata_site, publisher)
    qualifier_publisher.setTarget(qualifier_target)
    summary = 'Adding P123 (publisher) qualifier'
    claim.addQualifier(qualifier_publisher, summary=summary)

    return claim


def create_P275_licence(value, url):
    if not value:
        print("No licence error")
        exit(1)

    licences = {
        'CC0': 'Q6938433',
        'CC BY 4.0': 'Q20007257',
        'CC BY-SA 4.0': 'Q18199165'
    }

    if value not in licences:
        print(f'Licence not found {value}.')
        exit(1)
        return None

    qcode = licences[value]
    claim_target = pywikibot.ItemPage(wikidata_site, qcode)
    claim = pywikibot.Claim(wikidata_site, 'P275')
    claim.setTarget(claim_target)

    if url:
        # property ID for source URL (reference url)
        qualifier_url = pywikibot.Claim(wikidata_site, 'P854')
        qualifier_url.setTarget(url)
        summary = 'Adding reference URL qualifier'
        claim.addSource(qualifier_url, summary=summary)

    return claim


def create_P6216_copyright_state(value):
    if not value:
        return None

    # CC0: public domain? (Q19652)
    # -> no, copyright still exists
    copyright_states = {
        'CC0': 'Q50423863',
        'CC BY 4.0': 'Q50423863',
        'CC BY-SA 4.0': 'Q50423863'
    }

    if value not in copyright_states:
        print(f'Copyright state not found {value}.')
        exit(1)
        return None

    qcode = copyright_states[value]
    claim_target = pywikibot.ItemPage(wikidata_site, qcode)
    claim = pywikibot.Claim(wikidata_site, 'P6216')
    claim.setTarget(claim_target)

    return claim


def create_P9478_finna_id(value):
    if not value:
        return None

    claim_target = value
    claim = pywikibot.Claim(wikidata_site, 'P9478')
    claim.setTarget(claim_target)

    return claim


def create_P170_author(value, role):
    if not value:
        return None

    if not role:
        return None

    # P170 "Author"
    claim = pywikibot.Claim(wikidata_site, 'P170')
    claim_target = pywikibot.ItemPage(wikidata_site, value)
    claim.setTarget(claim_target)

    # P3831 "role"
    qualifier = pywikibot.Claim(wikidata_site, 'P3831')

    # Q33231 = "Kuvaaja"
    qualifier_target = pywikibot.ItemPage(wikidata_site, 'Q33231')
    qualifier.setTarget(qualifier_target)
    claim.addQualifier(qualifier, summary='Adding role qualifier')

    return claim


def create_P195_collection(wikidata_id, collection_number):
    if not wikidata_id:
        return None

    claim_target = pywikibot.ItemPage(wikidata_site, wikidata_id)
    claim = pywikibot.Claim(wikidata_site, 'P195')
    claim.setTarget(claim_target)

    if collection_number:
        # P217 collection number
        qualifier = pywikibot.Claim(wikidata_site, 'P217')
        qualifier.setTarget(collection_number)
        claim.addQualifier(qualifier, summary='Adding collection qualifier')
    else:
        print("collection number missing, wikidata_id:", wikidata_id)

    return claim


def create_P180_depict(wikidata_id):
    claim_target = pywikibot.ItemPage(wikidata_site, wikidata_id)
    claim = pywikibot.Claim(wikidata_site, 'P180')
    claim.setTarget(claim_target)
#    claim.changeRank("preferred") # "prominent"
    return claim


def create_P571_inception(date_obj, precision):
    print(date_obj)
    target = pywikibot.WbTime(
                              year=date_obj.year,
                              month=date_obj.month,
                              day=date_obj.day,
                              precision=precision
                             )
    claim = pywikibot.Claim(wikidata_site, 'P571')
    claim.setTarget(target)
    return claim


def wbEditEntity(site, page, data):
    # Reload file_page to be sure that we have updated page_id

    file_page = pywikibot.FilePage(site, page.title())
    media_identifier = 'M' + str(file_page.pageid)
    print(media_identifier)

    csrf_token = site.tokens['csrf']
    payload = {
       'action': 'wbeditentity',
       'format': u'json',
       'id': media_identifier,
       'data':  json.dumps(data),
       'token': csrf_token,
       'bot': True,  # in case you're using a bot account (which you should)
    }
    print(payload)
    request = site.simple_request(**payload)
    ret = request.submit()
    return ret


def get_source_of_file_claim(finna_image):
    # TODO: when using beyond JOKA-archive, fetch correct values per image
    # publisher = 'Q3029524'  # Finnish Heritage Agency
    operator = 'Q420747'    # National library
    url = finna_image.url

    instlist = list()
    for institution in finna_image.institutions.all():
        wikidata_id = institution.get_wikidata_id()
        instlist.append(wikidata_id)

    if (len(instlist) != 1):
        # TODO: check that create_P7482_source_of_file()
        # can handle multiple institutions
        print(('excpected one institution, found:', str(instlist)))
        exit(1)

    # TODO: fix handling so that potentially multiple
    # institutions can be supported
    # (do we have a real case for that though?)
    return create_P7482_source_of_file(url, operator, instlist[0])


def get_inception_claim(finna_image):
    try:
        timestamp, precision = parse_timestamp(finna_image.get_date_string())

        if timestamp and precision:
            claim = create_P571_inception(timestamp, precision)
            return claim
    except:
        print("failed to create inception")
        return None


# this context is for sdc data in commons
def get_claims_for_image_upload(finna_image):
    claims = []

    claim = get_source_of_file_claim(finna_image)
    claims.append(claim)

    claim = create_P9478_finna_id(finna_image.get_finna_id())
    claims.append(claim)

    claim = get_inception_claim(finna_image)
    claims.append(claim)

    # Handle image rights

    copyright_data = finna_image.image_right.get_copyright()
    claim = create_P275_licence(copyright_data, finna_image.url)
    claims.append(claim)

    claim = create_P6216_copyright_state(copyright_data)
    claims.append(claim)

    # Handle non presenter authors (photographers)
    # note: SLS uses "pht"
    known_roles = ['kuvaaja', 'reprokuvaaja', 'valokuvaaja',
                   'Valokuvaaja', 'pht', 'valokuvaamo']
    non_presenter_authors = finna_image.non_presenter_authors.all()

    for author in non_presenter_authors:
        if author.role not in known_roles:
            print(f'{author.role} is not known role')

        if (author.is_photographer()):
            wikidata_id = author.get_wikidata_id()
            role = 'Q33231'  # valokuvaaja
            claim = create_P170_author(wikidata_id, role)
            claims.append(claim)

    # Handle collections

    collections = finna_image.collections.all()
    identifier = finna_image.identifier_string

    for collection in collections:
        wikidata_id = collection.get_wikidata_id()
        claim = create_P195_collection(wikidata_id, identifier)
        claims.append(claim)

    # Handle subject actors

    subject_actors = finna_image.subject_actors.all()
    for subject_actor in subject_actors:
        wikidata_id = subject_actor.get_wikidata_id()
        claim = create_P180_depict(wikidata_id)
        claims.append(claim)

    # Handle local subjects

    for add_depict in finna_image.add_depicts.all():
        wikidata_id = add_depict.get_wikidata_id()
        claim = create_P180_depict(wikidata_id)
        claims.append(claim)

    p1771_location_claims = create_P1071_location(finna_image)
    for p1771_location_claim in p1771_location_claims:
        claims.append(p1771_location_claim)

    return claims

def get_sdc_labels(finna_image):

    labels = {}
    
    labelname = None
    if (len(finna_image.title) < 250):
        print("using title as label")
        labelname = finna_image.title
    elif (finna_image.short_title is not None and len(finna_image.short_title) < 250):
        print("using short title as label")
        labelname = finna_image.short_title
    
    if (labelname != None):
        labels['fi'] = {'language': 'fi', 'value': labelname}

    for title in finna_image.alternative_titles.all():
        if (title.lang not in labels):
            # if text exceeds 250 characters: 
            # Commons label does not allow larger while wikitext does
            # -> full text can be in wikitext instead
            if (len(title.text) < 250):
                print("adding title as label for: ", title.lang)
                labels[title.lang] = {'language': title.lang, 'value': title.text}
            else:
                print("WARN: title text choice exceeds 250 characters")
            
    for summary in finna_image.summaries.all():
        if (summary.lang not in labels):
            if (len(summary.text) < 250):
                print("adding summary as label for: ", summary.lang)
                labels[summary.lang] = {'language': summary.lang, 'value': summary.text}
            else:
                print("WARN: summary text choice exceeds 250 characters")
        

    # TODO if label exceeds max length use title or short title instead,
    # use long description only if known to fit in 250 character limit
    # for summary in self.summaries.all():
        # text = str(summary.text)
        # text = text.replace('sisällön kuvaus: ', '')
        # text = text.replace('innehållsbeskrivning: ', '')
        # text = text.replace('content description: ', '')

        # labels[summary.lang] = {'language': summary.lang, 'value': text}

    return labels

# this context is for sdc data in commons,
# used by views.py
def get_structured_data_for_new_image(finna_image):
    claims = get_claims_for_image_upload(finna_image)

    json_claims = []
    for claim in claims:
        if claim:
            claim = claim.toJSON()
            json_claims.append(claim)

    # labels in commons
    labels = get_sdc_labels(finna_image)

    ret = {
        'labels': labels,
        'claims': json_claims
    }

    return ret


def create_P1071_location(finna_image):

    ret = []
    wikidata_ids = set()
    for best_wikidata_location in finna_image.best_wikidata_location.all():
        print(best_wikidata_location)
        uri = best_wikidata_location.uri
        uri = uri.replace('http://www.wikidata.org/entity/', '')
        wikidata_ids.add(uri)

    subject_places = finna_image.subject_places
    depicted_places = list(subject_places.values_list('name', flat=True))
    location_string = clean_depicted_places("; ".join(depicted_places))

    print(location_string)

    for wikidata_id in wikidata_ids:
        # Create a new Claim
        # P1071 is 'location'
        claim = pywikibot.Claim(wikidata_site, 'P1071')
        target = pywikibot.ItemPage(wikidata_site, wikidata_id)
        claim.setTarget(target)

        # Create source Claims
        source_claims = []

        # Location text
        ref_claim = pywikibot.Claim(wikidata_site, 'P5997')
        ref_claim.setTarget(location_string)
        source_claims.append(ref_claim)

        # Source url
        source_url = finna_image.url
        ref_claim = pywikibot.Claim(wikidata_site, 'P854')
        ref_claim.setTarget(source_url)
        source_claims.append(ref_claim)

        # Date
        current_date = datetime.now()
        wbtime_date = pywikibot.WbTime(year=current_date.year,
                                       month=current_date.month,
                                       day=current_date.day)

        ref_claim = pywikibot.Claim(wikidata_site, 'P813')
        ref_claim.setTarget(wbtime_date)
        source_claims.append(ref_claim)

        P1071_value = str(wikidata_ids)
        summary = f'Adding referenses to P1071 (location) = {P1071_value}'
        claim.addSources(source_claims, summary=summary)

        ret.append(claim)
    return ret
