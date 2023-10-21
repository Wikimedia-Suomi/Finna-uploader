import mwparserfromhell


def create_categories_new(finna_image):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the categories
    categories = set()

    for subject_actor in finna_image.subject_actors.all():
        category = subject_actor.get_commons_category()
        categories.add(category)

    authors = finna_image.non_presenter_authors.filter(role='kuvaaja')
    for author in authors:
        category = author.get_photos_category()
        categories.add(category)

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
        if 'Portrait photographs' in categories:
            categories.add('People of Finland in ' + finna_image.year)
        else:
            categories.add(finna_image.year + ' in Finland')

    categories.add('Files uploaded by FinnaUploadBot')

    for category in categories:
        # Create the Wikilink
        category_title = 'Category:' + category
        wikilink = mwparserfromhell.nodes.Wikilink(title=category_title)

        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)

    flatten_wikicode = str(wikicode).replace('[[Category:', '\n[[Category:')

    # return the wikitext
    return flatten_wikicode
