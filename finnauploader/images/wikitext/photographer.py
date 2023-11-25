import mwparserfromhell
from images.wikitext.timestamps import parse_timestamp_string
from images.wikitext.categories import create_categories_new


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
    template.add('dimensions', "\n".join(r['measurements']))
    template.add('institution', r['institution_template'])
    template.add('department', lang_template('fi', "; ".join(r['collections'])))
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


def get_photographer_template(finna_image):

    r = {}

    # depicted
    depicted_people = list(finna_image.subject_actors.values_list('name', flat=True))
    depicted_places = list(finna_image.subject_places.values_list('name', flat=True))

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
    for lang in langs:
        text = finna_image.summaries.filter(lang=lang).first()
        if text:
            text = str(text)
            text = text.replace('sisällön kuvaus: ', '')
            text = text.replace('innehållsbeskrivning: ', '')
            text = text.replace('content description: ', '')
            description = lang_template(lang, text)
            descriptions.append(description)

    r['creator_template'] = finna_image.get_creator_templates()
    r['template_titles'] = titles
    r['template_descriptions'] = descriptions
    r['subjectActors'] = "; ".join(depicted_people)
    r['subjectPlaces'] = clean_depicted_places("; ".join(depicted_places))
    r['date'] = finna_image.date_string
    r['measurements'] = finna_image.measurements
    r['institution_template'] = finna_image.get_institution_templates()
    r['collections'] = collections
    r['identifierString'] = finna_image.identifier_string
    r['source'] = finna_image.url
    r['permission'] = finna_image.get_permission_string()

    return create_photographer_template(r)


def get_wikitext_for_new_image(finna_image):
    wikitext_parts = []
    wikitext_parts.append("== {{int:filedesc}} ==")
    wikitext_parts.append(get_photographer_template(finna_image) + '\n')
    wikitext_parts.append("== {{int:license-header}} ==")
    wikitext_parts.append(finna_image.get_copyright_template())
    wikitext_parts.append(create_categories_new(finna_image))
    wikitext = "\n".join(wikitext_parts)
    return wikitext
