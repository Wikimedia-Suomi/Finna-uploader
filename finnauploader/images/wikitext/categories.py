import mwparserfromhell

from images.wikitext.wikidata_helpers import get_subject_image_category_from_wikidata_id, \
                                    get_creator_image_category_from_wikidata_id

def get_category_by_wikidata_id(wikidata_id):
    if wikidata_id:
        category = get_subject_image_category_from_wikidata_id(wikidata_id)
        if category:
            #if not prefix:
            category = category.replace('Category:', '')
            return category
    return None

def get_creator_category_by_wikidata_id(wikidata_id):
    if wikidata_id:
        category = get_creator_image_category_from_wikidata_id(wikidata_id)
        if category:
            #if not prefix:
            category = category.replace('Category:', '')
            return category
    return None

def get_subject_category(finna_subject):
    value = finna_subject.value.replace('category:', 'Category:')

    if 'https://commons.wikimedia.org/wiki/Category:' in value:
        return value.replace('https://commons.wikimedia.org/wiki/Category:', '')

    if 'http://commons.wikimedia.org/wiki/category:' in value:
        return value.replace('http://commons.wikimedia.org/wiki/Category:', '')

    if '^Category:' in value:
        return value.replace('Category:', '')

    wikidata_id = finna_subject.get_wikidata_id()
    return get_category_by_wikidata_id(wikidata_id)

def get_category_place(subject_places, depicted_places):
    print("DEBUG: get_category_place, subject places: ", str(subject_places) )
    print("DEBUG: get_category_place, depicted places: ", str(depicted_places) )

    # for now, use hack to translate into category
    if ('Nokia' in depicted_places):
        return "Nokia, Finland"
    if ('Maarianhamina' in depicted_places):
        return "Mariehamn"
    if ('Viipuri' in depicted_places):
        return "Vyborg"

    cat_place = {
        "Helsinki","Hanko","Hamina","Hyvinkää","Hämeenlinna","Espoo","Forssa","Iisalmi","Imatra","Inari","Joensuu","Jyväskylä","Jämsä","Kaarina","Kajaani","Kerava","Kemi","Kokkola","Kotka","Kuopio","Kuusamo","Kouvola","Lahti","Lappajärvi","Lappeenranta","Lohja","Loviisa","Mikkeli","Naantali","Pietarsaari","Porvoo","Pori","Pornainen","Oulu","Raahe","Raisio","Rauma","Rovaniemi","Salo","Savonlinna","Seinäjoki","Siilinjärvi","Sipoo","Sotkamo","Turku","Tampere","Tornio","Uusikaupunki","Vantaa","Vaasa","Virolahti"
    }
    for p in cat_place:
        if p in depicted_places:
            return p
        # may need combination location (country, subdivision etc)
        tmp = "Suomi, " + p
        if (tmp in depicted_places):
            return p
    return ""

def create_categories_new(finna_image):
    subject_places = finna_image.subject_places.values_list('name', flat=True)
    depicted_places = str(list(subject_places))

    # may start with comma and space -> clean it
    if (depicted_places.startswith(",")):
        depicted_places = depicted_places[1:]
    depicted_places = depicted_places.lstrip()

    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the categories
    categories = set()

    for subject_actor in finna_image.subject_actors.all():
        wikidata_id = subject_actor.get_wikidata_id()
        category = get_category_by_wikidata_id(wikidata_id)
        categories.add(category)

    authors = finna_image.non_presenter_authors.all()
    for author in authors:
        if (author.is_photographer()):
            wikidata_id = author.get_wikidata_id()
            category = get_creator_category_by_wikidata_id(wikidata_id)
            categories.add(category)

    # Ssteamboats: non ocean-going
    # Steamships of Finland
    # Naval ships of Finland
    # Sailing ships of Finland
    subject_categories = {
        'muotokuvat': 'Portrait photographs',
        'henkilökuvat': 'Portrait photographs',
        'saamenpuvut' : 'Sami clothing',
        'Osuusliike Elanto': 'Elanto',
        'Valmet Oy': 'Valmet',
        'Salora Oy': 'Salora',
        'Veljekset Åström Oy': 'Veljekset Åström',
        'Yntyneet Paperitehtaat': 'Yntyneet Paperitehtaat',
        'Turun linna' : 'Turku Castle',
        'Hämeen linna' : 'Häme Castle',
        'Olavinlinna' : 'Olavinlinna',
        'Hvitträsk': 'Hvitträsk',
        'kiväärit' : 'Rifles'
    }
    
    # must have place 'Suomi' to generate ' in Finland'
    #
    # note: there are also "from" and "of" categories in Commons, 
    # can we guess the right one automatically?
    # aircraft may be "in" city or "at" airport..
    subject_categories_with_country = {
        'professorit': 'Professors from',
        'kauppaneuvokset' : 'Businesspeople from',
        'toimitusjohtajat' : 'Businesspeople from',
        'miesten puvut': 'Men wearing suits in',
        'muotinäytökset' : 'Fashion shows in',
        'lentonäytökset': 'Air shows in',
        'veturit' : 'Locomotives of',
        'junat' : 'Trains of',
        'junanvaunut' : 'Railway coaches of',
        'rautatieasemat' : 'Train stations in',
        'laivat' : 'Ships in',
        'veneet' : 'Boats in',
        'matkustajalaivat' : 'Passenger ships in',
        'purjeveneet' : 'Sailboats in',
        'moottoriveneet' : 'Motorboats in',
        'lossit' : 'Cable ferries in',
        'lentokoneet' : 'Aircraft in',
        'moottoripyörät' : 'Motorcycles in',
        'moottoripyöräurheilu' : 'Motorcycle racing in',
        'moottoriurheilu' : 'Motorsports in',
        'linja-autot': 'Buses in',
        'kuorma-autot' : 'Trucks in',
        'autot' : 'Automobiles in',
        'henkilöautot' : 'Automobiles in',
        'autourheilu' : 'Automobile racing in',
        'autokilpailut' : 'Automobile races in',
        'auto-onnettomuudet' : 'Automobile accidents in',
        'hotellit' : 'Hotels in',
        'kodit' : 'Accommodation buildings in',
        'asuinrakennukset' : 'Houses in',
        'liikerakennukset' : 'Buildings in',
        'kerrostalot' : 'Apartment buildings in',
        'osuusliikkeet' : 'Consumers\' cooperatives in',
        'saunat' : 'Sauna buildings in',
        'nosturit' : 'Cranes in',
        'kaivinkoneet' : 'Excavators in',
        'tehtaat' : 'Factories in',
        'teollisuusrakennukset' : 'Factories in',
        'konepajateollisuus' : 'Machinery industry in',
        'paperiteollisuus' : 'Pulp and paper industry in',
        'sahateollisuus' : 'Sawmills in',
        'koulurakennukset' : 'School buildings in',
        'sairaalat' : 'Hospitals in',
        'museot' : 'Museums in',
        'rakennushankkeet' : 'Construction in',
        'laulujuhlat' : 'Music festivals in',
        'festivaalit' : 'Music festivals in',
        'rukit' : 'Spinning wheels in',
        'meijerit' : 'Dairies in',
        'ravintolat' : 'Restaurants in',
        'mainoskuvat' : 'Advertisements in',
        'koira' : 'Dogs of',
        'hevosajoneuvot' : 'Horse-drawn vehicles in',
        'polkupyörät' : 'Bicycles in',
        'ammattikoulutus' : 'Vocational schools in'
    }

    manor_categories_by_location = {
        'Louhisaari' : 'Louhisaari Manor',
        'Piikkiö' : 'Pukkila Manor',
        'Kuusisto' : 'Kuusisto Manor',
        'Knuutila' : 'Knuutila Manor'
    }
    
    isInFinland = False
    cat_place = get_category_place(subject_places, depicted_places)
    if (len(cat_place) == 0):
        if 'Suomi' in depicted_places:
            cat_place = "Finland"
    else:
        # for now, we recognize mostly places in finland..
        if ('Viipuri' not in depicted_places and 'Petsamo' not in depicted_places):
            isInFinland = True

    for subject in finna_image.subjects.all():
        if subject.name in subject_categories:
            category = subject_categories[subject.name]
            categories.add(category)

        if subject.name in subject_categories_with_country and isInFinland == True:
            category = subject_categories_with_country[subject.name] + " " + "Finland"
            categories.add(category)

        if (subject.name == 'kartanot' and 'Louhisaari' in depicted_places):
            categories.add('Louhisaari Manor')

        if (subject.name == 'kartanot' and 'Piikkiö' in depicted_places):
            categories.add('Pukkila Manor')

        # Kuusisto, Kaarina
        if (subject.name == 'kartanot' and 'Kuusisto' in depicted_places):
            categories.add('Kuusisto Manor')

        # Knuutila, Nokia
        if (subject.name == 'kartanot' and 'Knuutila' in depicted_places):
            categories.add('Knuutila Manor')

        if (subject.name == 'parlamentit' and 'Helsinki' in depicted_places):
            categories.add('Parliament House, Helsinki')

        # Svartholma, Loviisa
        if (subject.name == 'linnakkeet' and 'Svartholma' in depicted_places):
            categories.add('Svartholm Fortress')
        elif (subject.name == 'linnakkeet' and isInFinland == True):
            categories.add('Fortresses in Finland')

        # categorize by city if in Finland
        if (subject.name == 'kirkot' and len(cat_place) > 0 and isInFinland == True):
            cattext = 'Churches in ' + cat_place
            categories.add(cattext)

    
    for add_category in finna_image.add_categories.all():
        wikidata_id = finna_subject.get_wikidata_id()
        category_name = get_category_by_wikidata_id(wikidata_id)
        if category_name:
            categories.add(category_name)

    if finna_image.year:
        if 'Portrait photographs' in categories and 'Suomi' in depicted_places:
            categories.add(f'People of Finland in {finna_image.year}')

        if (len(cat_place) > 0):
            categories.add(f'{finna_image.year} in {cat_place}')
    else:
        # if we can't determine year, use only location name
        # and only if it something other than country (at least a city)
        if (len(cat_place) > 0 and (cat_place != 'Suomi' and cat_place != 'Finland')):
            categories.add(cat_place)

    # TODO: to categorize under "Black and white photographs of Finland",
    # see models about parsing the full record xml from Finna for more terms

    categories.add('Files uploaded by FinnaUploadBot')

    for category in categories:
        # is it possible to get this somehow?
        if '^Category:' in category:
            print("Should strip category")
            exit(1)
        # is it possible to get this somehow?
        if 'http' in category:
            print("Should strip url from category")
            exit(1)
        
        # Create the Wikilink
        category_title = 'Category:' + category
        wikilink = mwparserfromhell.nodes.Wikilink(title=category_title)

        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)

    flatten_wikicode = str(wikicode).replace('[[Category:', '\n[[Category:')

    # return the wikitext
    return flatten_wikicode
