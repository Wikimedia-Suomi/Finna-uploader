import mwparserfromhell
from images.wikitext.timestamps import parse_timestamp_string
from images.wikitext.categories import create_categories_new

from images.wikitext.wikidata_helpers import get_creator_nane_by_wikidata_id, \
                                      get_institution_name_by_wikidata_id
from images.pywikibot_helpers import get_copyright_template_name


def lang_template(lang, text):
    text = str(text)
    if text:
        return '{{' + lang + '|' + text + '}}'
    else:
        return ''


def create_photographer_template(r):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the template
    template = mwparserfromhell.nodes.Template(name='Photograph')

    # Add the parameters to the template
    template.add('photographer', r['creator_template'])
    template.add('title', '\n'.join(r['template_titles']))
    template.add('description', '\n'.join(r['template_descriptions']))
    template.add('depicted people', lang_template('fi', r['subjectActors']))
    template.add('depicted place', lang_template('fi', r['subjectPlaces']))
    template.add('date', parse_timestamp_string(r['date']))
    template.add('medium', '')
    template.add('dimensions', str(r['measurements']))
    template.add('institution', r['institution_template'])
    template.add('department', lang_template('fi', "; ".join(r['collections'])))  # noqa
    template.add('references', '')
    template.add('object history', '')
    template.add('exhibition history', '')
    template.add('credit line', '')
    template.add('inscriptions', '')
    template.add('notes', '')
    template.add('accession number', r['identifierString'])
    template.add('source', r['source'])
    template.add('permission',  lang_template('fi', r['permission']))
    template.add('other_versions', '')
    template.add('wikidata', '')
    template.add('camera coord', '')

    # Add the template to the WikiCode object
    wikicode.append(template)
    flat_wikitext = str(wikicode)

    # Add newlines before parameter name
    params = ['photographer', 'title', 'description', 'depicted people',
              'depicted place', 'date', 'medium', 'dimensions', 'institution',
              'department', 'references', 'object history',
              'exhibition history', 'credit line', 'inscriptions', 'notes',
              'accession number', 'source', 'permission', 'other_versions',
              'wikidata', 'camera coord']

    for param in params:
        flat_wikitext = flat_wikitext.replace(f'|{param}=', f'\n|{param} = ')

    # return the wikitext
    return flat_wikitext


def clean_depicted_places(location_string):
    locations = location_string.split(';')
    sorted_locations = sorted(locations,
                              key=lambda s: len(s.strip()),
                              reverse=True)

    ret = sorted_locations[0].strip()
    for location in sorted_locations:
        location = location.strip()
        if location not in ret:
            ret = f'{ret}; {location}'

    return ret


def get_creator_templates(finna_image):
    creator_templates = []
    for creator in finna_image.non_presenter_authors.all():
        if (creator.is_photographer()):
            wikidata_id = creator.get_wikidata_id()
            creatorName = get_creator_nane_by_wikidata_id(wikidata_id)
            if (creatorName is not None):
                template = '{{Creator:' + creatorName + '}}'
                creator_templates.append(template)
    return "".join(creator_templates)


def get_institution_templates(finna_image):
    institution_templates = []
    for institution in finna_image.institutions.all():
        wikidata_id = institution.get_wikidata_id()
        institutionName = get_institution_name_by_wikidata_id(wikidata_id)
        if (institutionName is not None):
            template = '{{Institution:' + institutionName + '}}'
            institution_templates.append(template)
    return "".join(institution_templates)


def get_copyright_template_with_review(finna_image):
    template_name = get_copyright_template_name(finna_image)
    return "{{" + template_name + "}}\n{{FinnaReview}}"


def get_permission_string(finna_image):
    link = finna_image.image_right.get_link()
    copyright = finna_image.image_right.get_copyright()
    description = finna_image.image_right.get_description()
    if link:
        ret = f'[{link} {copyright}]; {description}'
    else:
        ret = f'{copyright}; {description}'
    return ret


def get_photographer_template(finna_image):

    r = {}

    # depicted
    depicted_people = list(finna_image.subject_actors.values_list('name', flat=True))  # noqa
    depicted_places = list(finna_image.subject_places.values_list('name', flat=True))  # noqa

    # misc
    collections = list(finna_image.collections.values_list('name', flat=True))

    langs = ['fi', 'sv', 'en']
    titles = []
    for lang in langs:
        if lang == 'fi':
            text = finna_image.title
        else:
            text = finna_image.alternative_titles.filter(lang=lang).first()
        if text:
            title = lang_template(lang, text)
            titles.append(str(title))

    descriptions = []
    # there can be multiple separate entries in summary for each language:
    # the strings are in arrays -> combine them all since we can't know order of importance
    for summary in finna_image.summaries.all():
        if (summary):
            print("DEBUG: summary lang", summary.lang)
            print("DEBUG: summary text", summary.text)
            text = str(summary.text)
            
            # strip some unnecessary heading (if any)
            text = text.replace('sisällön kuvaus: ', '')
            text = text.replace('innehållsbeskrivning: ', '')
            text = text.replace('content description: ', '')

            # in some images, the summary does not have related language?
            if (summary.lang):
                description = lang_template(summary.lang, text)
            else:
                description = text
            descriptions.append(description)
            
        #print(summary)

    r['creator_template'] = get_creator_templates(finna_image)
    r['template_titles'] = titles
    r['template_descriptions'] = descriptions
    r['subjectActors'] = "; ".join(depicted_people)
    r['subjectPlaces'] = clean_depicted_places("; ".join(depicted_places))
    r['date'] = finna_image.date_string
    #medium : physical description (colored, vertical/horizontal, paper, film negative..)
    r['measurements'] = finna_image.measurements
    r['institution_template'] = get_institution_templates(finna_image)
    r['collections'] = collections
    r['identifierString'] = finna_image.identifier_string
    r['source'] = finna_image.url
    r['permission'] = get_permission_string(finna_image)

    return create_photographer_template(r)


def get_wikitext_for_new_image(finna_image):
    creator = get_photographer_template(finna_image)

    wikitext_parts = []
    wikitext_parts.append("== {{int:filedesc}} ==")
    wikitext_parts.append(creator + '\n')
    wikitext_parts.append("== {{int:license-header}} ==")
    wikitext_parts.append(get_copyright_template_with_review(finna_image))
    wikitext_parts.append(create_categories_new(finna_image))
    wikitext = "\n".join(wikitext_parts)
    return wikitext
