import pywikibot
import json


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


def create_P275_licence(value):
    if not value:
        print("No licence error")
        exit(1)

    licences = {
        'CC BY 4.0': 'Q20007257',
        'CC BY-SA 4.0': 'Q18199165'
    }

    if value not in licences:
        print(f'Licence not found {value}.')
        if 1:
            exit(1)
        return None

    claim_target = pywikibot.ItemPage(wikidata_site, licences[value])
    claim = pywikibot.Claim(wikidata_site, 'P275')
    claim.setTarget(claim_target)

    return claim


def create_P6216_copyright_state(value):
    if not value:
        return None

    copyright_states = {
        'CC BY 4.0': 'Q50423863',
        'CC BY-SA 4.0': 'Q50423863'
    }

    if value not in copyright_states:
        print(f'Copyright state not found {value}.')
        if 1:
            exit(1)
        return None

    claim_target = pywikibot.ItemPage(wikidata_site, copyright_states[value])
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
        claim.addQualifier(qualifier, summary='Adding role qualifier')
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
