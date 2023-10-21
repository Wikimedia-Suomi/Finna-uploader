import mwparserfromhell
from images.wikitext.creator import get_creator_image_category_from_wikidata_id, \
                                    get_subject_image_category_from_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_author_wikidata_id


def create_categories(r):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the categories
    categories = set()

    for wikidata_id in r['subjectActors_wikidata_ids']:
        subject_category = get_subject_image_category_from_wikidata_id(wikidata_id)
        if subject_category:
            subject_category = subject_category.replace('Category:', '')
            categories.add(subject_category)

    creator_category = get_creator_image_category_from_wikidata_id(r['creator_wikidata_id'])
    creator_category = creator_category.replace('Category:', '')
    categories.add(creator_category)

    subject_categories = {
        'muotokuvat': 'Portrait photographs',
        'henkilökuvat': 'Portrait photographs',
        'professorit': 'Professors from Finland',
        'miesten puvut': 'Men wearing suits in Finland'
    }

    for subject_category in subject_categories.keys():
        if subject_category in str(r['subjects']):
            categories.add(subject_categories[subject_category])

    if 'year' in r:
        if 'Category:Portrait photographs' in categories:
            categories.add('People of Finland in ' + r['year'])
        else:
            categories.add(r['year'] + ' in Finland')

    categories.add('Files uploaded by FinnaUploadBot')

    for category in categories:
        # Create the Wikilink
        wikilink = mwparserfromhell.nodes.Wikilink(title='Category:' + category)

        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)

    flatten_wikicode = str(wikicode).replace('[[Category:', '\n[[Category:')

    # return the wikitext
    return flatten_wikicode


def create_categories_new(finna_image):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the categories
    categories = set()

    for subject in finna_image.subject_actors.all():
        wikidata_id = get_subject_actors_wikidata_id(subject.name)
        subject_category = get_subject_image_category_from_wikidata_id(wikidata_id)
        if subject_category:
            subject_category = subject_category.replace('Category:', '')
            categories.add(subject_category)

    authors = finna_image.non_presenter_authors.filter(role='kuvaaja')
    for author in authors:
        wikidata_id = get_author_wikidata_id(author.name)
        creator_category = get_creator_image_category_from_wikidata_id(wikidata_id)
        creator_category = creator_category.replace('Category:', '')
        categories.add(creator_category)

    subject_categories = {
        'muotokuvat': 'Portrait photographs',
        'henkilökuvat': 'Portrait photographs',
        'professorit': 'Professors from Finland',
        'miesten puvut': 'Men wearing suits in Finland'
    }

    for subject in finna_image.subjects.all():
        if subject.name in subject_categories:
            categories.add(subject_categories[subject.name])

    if finna_image.year:
        if 'Category:Portrait photographs' in categories:
            categories.add('People of Finland in ' + finna_image.year)
        else:
            categories.add(finna_image.year + ' in Finland')

    categories.add('Files uploaded by FinnaUploadBot')

    for category in categories:
        # Create the Wikilink
        wikilink = mwparserfromhell.nodes.Wikilink(title='Category:' + category)

        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)

    flatten_wikicode = str(wikicode).replace('[[Category:', '\n[[Category:')

    # return the wikitext
    return flatten_wikicode
