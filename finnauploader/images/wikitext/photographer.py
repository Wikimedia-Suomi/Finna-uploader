import mwparserfromhell
from images.wikitext.timestamps import parse_timestamp_string
from images.wikitext.categories import create_categories_new


def language_template_wrap(lang, text):
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
    template.add('description', language_template_wrap('fi', '\n'.join(r['template_descriptions'])))
    template.add('depicted people', language_template_wrap('fi', r['subjectActors']))
    template.add('depicted place', language_template_wrap('fi', r['subjectPlaces']))
    template.add('date', parse_timestamp_string(r['date']))
    template.add('medium', '')
    template.add('dimensions', "\n".join(r['measurements']))
    template.add('institution', r['institution_template'])
    template.add('department', language_template_wrap('fi', "; ".join(r['collections'])))
    template.add('references', '')
    template.add('object history', '')
    template.add('exhibition history', '')
    template.add('credit line', '')
    template.add('inscriptions', '')
    template.add('notes', '')
    template.add('accession number', r['identifierString'])
    template.add('source', r['source'])
    template.add('permission',  language_template_wrap('fi', r['permission']))
    template.add('other_versions', '')
    template.add('wikidata', '')
    template.add('camera coord', '')

    # Add the template to the WikiCode object
    wikicode.append(template)
    flatten_wikitext = str(wikicode)

    # Add newlines before parameter name
    params = ['photographer', 'title', 'description', 'depicted people', 'depicted place', 'date', 'medium', 'dimensions',
              'institution', 'department', 'references', 'object history', 'exhibition history', 'credit line', 'inscriptions',
              'notes', 'accession number', 'source', 'permission', 'other_versions', 'wikidata', 'camera coord']

    for param in params:
        flatten_wikitext = flatten_wikitext.replace('|' + param + '=', '\n|' + param + ' = ')

    # return the wikitext
    return flatten_wikitext


def get_photographer_template(finna_image):

    r = {}

    # depicted
    depicted_people = list(finna_image.subject_actors.values_list('name', flat=True))
    depicted_places = list(finna_image.subject_places.values_list('name', flat=True))

    # misc
    collections = list(finna_image.collections.values_list('name', flat=True))
    wrapped_title = language_template_wrap('fi', finna_image.title)

    r['creator_template'] = finna_image.get_creator_templates()
    r['template_titles'] = [wrapped_title]
    r['template_descriptions'] = []
    r['subjectActors'] = "; ".join(depicted_people)
    r['subjectPlaces'] = "; ".join(depicted_places)
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
