# templates and descriptions for commons,
# generated based on finna data for uploaded stuff

import mwparserfromhell
from images.wikitext.timestamps import parse_timestamp_string
from images.wikitext.categories import create_categories_new

from images.wikitext.wikidata_helpers import get_creator_nane_by_wikidata_id, \
                                      get_institution_name_by_wikidata_id, striprepeatespaces


#def lang_template(lang, text):
def make_lang_template(text, lang='fi'):
    
    # invalid language code: no commons template for a language like this
    # bug somewhere?
    if (len(lang) < 2 or len(lang) > 2):
        print("WARN: language code is not valid", lang) 
        exit(1)
        return ''

    text = str(text)
    if text:
        return '{{' + lang + '|' + text + '}}'
    else:
        return ''


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

# photographers specifically
def get_creator_templates_for_photographers(finna_image):
    creator_templates = []
    for creator in finna_image.non_presenter_authors.all():
        if (creator.is_photographer()):
            wikidata_id = creator.get_wikidata_id()
            creatorName = get_creator_nane_by_wikidata_id(wikidata_id)
            if (creatorName is not None):
                template = '{{Creator:' + creatorName + '}}'
                # don't add duplicates (error in source)
                if (template not in creator_templates):
                    creator_templates.append(template)

    return "".join(creator_templates)

# non-photographer authors (architects, illustrators)
def get_creator_templates_for_authors(finna_image):
    creator_templates = []
    for creator in finna_image.non_presenter_authors.all():
        if (creator.is_architect() or creator.is_illustrator() or creator.is_creator()):
            wikidata_id = creator.get_wikidata_id()
            creatorName = get_creator_nane_by_wikidata_id(wikidata_id)
            if (creatorName is not None):
                template = '{{Creator:' + creatorName + '}}'
                # don't add duplicates (error in source)
                if (template not in creator_templates):
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


def get_copyright_template_name(finna_image):
    copyright = finna_image.image_right.get_copyright()

    if "CC0" in copyright:
        return "CC0"
    elif "CC BY 4.0" in copyright:
        return "CC-BY-4.0"
    elif "CC BY-SA 4.0" in copyright:
        return "CC BY-SA 4.0"
    elif "PDM" in copyright:
        return "PDM"
    else:
        print("Copyright error")
        print(finna_image.image_right.copyright)
        exit(1)
        return ''

# generate comment to be shown in upload log?
def get_comment_text(finna_image):
    authorlist = list()
    npauthors = finna_image.non_presenter_authors.all()
    for author in npauthors:
        if (author.is_photographer() or author.is_architect() or author.is_creator()):
            # skip duplicate (error in source)
            if (author.name not in authorlist):
                authorlist.append(author.name)

    if not authorlist:
        authorlist.append('unknown')

    ret = "Uploading \'" + finna_image.short_title + "\'"
    ret = ret + " by \'" + "; ".join(authorlist) + "\'"

    copyrighttemplate = get_copyright_template_name(finna_image)

    ret = f'{ret} with licence {copyrighttemplate}'
    ret = f'{ret} from {finna_image.url}'

    return ret

def get_permission_string(finna_image):
    link = finna_image.image_right.get_link()
    copyright = finna_image.image_right.get_copyright()
    description = finna_image.image_right.get_description()
    if link:
        ret = f'[{link} {copyright}]; {description}'
    else:
        ret = f'{copyright}; {description}'
    return ret

def get_descriptions_from_summaries(finna_image):
    descriptions = []

    # there can be multiple separate entries in summary for each language:
    # the strings are in arrays -> combine them all since we can't know order of importance
    for summary in finna_image.summaries.all():
        if (summary):
            #print("DEBUG: summary lang", summary.lang)
            #print("DEBUG: summary text", summary.text)
            text = str(summary.text)
            
            # strip some unnecessary heading (if any)
            text = text.replace('sisällön kuvaus: ', '')
            text = text.replace('innehållsbeskrivning: ', '')
            text = text.replace('content description: ', '')

            # if there sequences of tabulators just strip them out,
            # they won't make any sense in HTML anyway
            text = striprepeatespaces(text)

            # wikimedia templates will break if there are equal signs in text
            text = text.replace("=", "&equals;")

            # in some images, the summary does not have related language?
            if (summary.lang):
                description = make_lang_template(text, summary.lang)
            else:
                description = text
            descriptions.append(description)
            
        #print(summary)

    return '\n'.join(descriptions)

def get_titles_from_image(finna_image):
    langs = ['fi', 'sv', 'en']
    titles = []
    for lang in langs:
        if lang == 'fi':
            text = finna_image.title
        else:
            text = finna_image.alternative_titles.filter(lang=lang).first()
        if text:
            title = make_lang_template(text, lang)
            titles.append(str(title))
            
    return '\n'.join(titles)

def get_depicted_people_from_image(finna_image):
    depicted_people = list(finna_image.subject_actors.values_list('name', flat=True))  # noqa
    return "; ".join(depicted_people)

def get_depicted_places_from_image(finna_image):
    depicted_places = list(finna_image.subject_places.values_list('name', flat=True))  # noqa
    return clean_depicted_places("; ".join(depicted_places))

def get_collections_from_image(finna_image):
    collections = list(finna_image.collections.values_list('name', flat=True))
    return "; ".join(collections)

def create_photograph_template(finna_image):
    lang = 'fi' # no need to repeat
    
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the template
    template = mwparserfromhell.nodes.Template(name='Photograph')

    # Add the parameters to the template
    # creator: photographer
    template.add('photographer', get_creator_templates_for_photographers(finna_image))

    # other creators or authors: architects, illustrators
    template.add('author', get_creator_templates_for_authors(finna_image))

    # short title
    template.add('title', get_titles_from_image(finna_image))
    
    # there can be multiple separate entries in summary for each language:
    # the strings are in arrays -> combine them all since we can't know order of importance
    template.add('description', get_descriptions_from_summaries(finna_image))

    joinedactors = get_depicted_people_from_image(finna_image)
    joinedplaces = get_depicted_places_from_image(finna_image)
    joinedcollections = get_collections_from_image(finna_image)
    permissionstring = get_permission_string(finna_image)

    template.add('depicted people', make_lang_template(joinedactors, lang))
    template.add('depicted place', make_lang_template(joinedplaces, lang))
    template.add('date', parse_timestamp_string(finna_image.date_string))
    template.add('medium', '')
    template.add('dimensions', str(finna_image.measurements))
    template.add('institution', get_institution_templates(finna_image))
    template.add('department', make_lang_template(joinedcollections, lang))  # noqa
    template.add('references', '')
    template.add('object history', '')
    template.add('exhibition history', '')
    template.add('credit line', '')
    template.add('inscriptions', '')
    template.add('notes', '')
    template.add('accession number', finna_image.identifier_string)
    template.add('source', finna_image.url)
    template.add('permission',  make_lang_template(permissionstring, lang))

    template.add('other_versions', '')
    template.add('wikidata', '')
    template.add('camera coord', '')

    # Add the template to the WikiCode object
    wikicode.append(template)
    flat_wikitext = str(wikicode)

    # Add newlines before parameter name
    params = ['photographer', 'author', 'title', 'description', 'depicted people',
              'depicted place', 'date', 'medium', 'dimensions', 'institution',
              'department', 'references', 'object history',
              'exhibition history', 'credit line', 'inscriptions', 'notes',
              'accession number', 'source', 'permission', 'other_versions',
              'wikidata', 'camera coord']

    for param in params:
        flat_wikitext = flat_wikitext.replace(f'|{param}=', f'\n|{param} = ')

    # return the wikitext
    return flat_wikitext


def get_wikitext_for_new_image(finna_image):
    photo_template = create_photograph_template(finna_image)

    copyrighttemplatename = get_copyright_template_name(finna_image)

    wikitext_parts = []
    wikitext_parts.append("== {{int:filedesc}} ==")
    wikitext_parts.append(photo_template + '\n')
    wikitext_parts.append("== {{int:license-header}} ==")
    wikitext_parts.append("{{" + copyrighttemplatename + "}}\n{{FinnaReview}}")
    wikitext_parts.append(create_categories_new(finna_image))
    wikitext = "\n".join(wikitext_parts)
    return wikitext
