import mwparserfromhell

from images.wikitext.wikidata_helpers import get_subject_image_category_from_wikidata_id, \
                                    get_creator_nane_by_wikidata_id

def get_category_by_wikidata_id(wikidata_id):
    if not wikidata_id:
        return None
    
    category = get_subject_image_category_from_wikidata_id(wikidata_id)
    if category:
        # this is error in the data if someone has added this way (unlikely, but check it anyway)
        if (category.find("Category:") >= 0):
            category = category.replace('Category:', '')
        return category
    return None

def get_photography_category_by_photographer_id(wikidata_id):
    if not wikidata_id:
        print('DEBUG: no wikidata id, unable to find photographer category')
        return None

    creatorName = get_subject_image_category_from_wikidata_id(wikidata_id)
    if (creatorName != None):
        print('DEBUG: creator name ', creatorName ,' for wikidata id: ', wikidata_id)
        
        if (creatorName.startswith("Photographs by") == True):
            category = creatorName
        else:
            category = "Photographs by " + creatorName

        #if (isCategoryExistingInCommons(category)):
            #return category
        print('DEBUG: using photography category', category)
        return category
        
    return None

# if picture is categorized under architecture
# and authors includes person with role "arkkitehti"
# categorize under "buildings by <architect>"
# subject should include "rakennukset"
def get_building_category_by_architect_id(wikidata_id):
    if not wikidata_id:
        print('DEBUG: no wikidata id, unable to find architect category')
        return None
    
    creatorName = get_subject_image_category_from_wikidata_id(wikidata_id)
    if (creatorName != None):
        print('DEBUG: creator name ', creatorName ,' for wikidata id: ', wikidata_id)

        if 'Buildings by' in creatorName:
            category = creatorName
        else:
            category = "Buildings by " + creatorName

        #if (isCategoryExistingInCommons(category)):
            #return category
        print('DEBUG: using photography category', category)
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
    #if ('Helsingin maalaiskunta' in depicted_places):
        #return "Vantaa"

    cat_place = {
        "Helsinki","Hanko","Hamina","Heinola","Hyvinkää","Hämeenlinna","Espoo","Forssa","Iisalmi","Imatra","Inari","Joensuu","Jyväskylä","Jämsä","Kaarina","Kajaani","Kauhajoki","Kerava","Kemi","Kokkola","Kotka","Kuopio","Kuusamo","Kouvola","Lahti","Lappajärvi","Lappeenranta","Lohja","Loviisa","Mikkeli","Naantali","Pietarsaari","Porvoo","Pori","Pornainen","Oulu","Raahe","Raisio","Rauma","Rovaniemi","Salo","Savonlinna","Seinäjoki","Siilinjärvi","Sipoo","Sotkamo","Turku","Tampere","Tornio","Uusikaupunki","Vantaa","Vaasa","Virolahti"
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
    subject_names = finna_image.subjects.values_list('name', flat=True)
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
        if category:
            categories.add(category)

    authors = finna_image.non_presenter_authors.all()
    for author in authors:
        if (author.is_photographer()):
            # "photographs by" category under photographer
            wikidata_id = author.get_wikidata_id()
            category = get_photography_category_by_photographer_id(wikidata_id)
            if (category != None):
                categories.add(category)

        if (author.is_architect()):
            # is image about a building?
            if (finna_image.is_entry_in_subjects("rakennukset") or finna_image.is_entry_in_subjects("kirkkorakennukset")):
                # "buildings by" category under architect
                wikidata_id = author.get_wikidata_id()
                category = get_building_category_by_architect_id(wikidata_id)
                if (category != None):
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
        'Raaseporin linna' : 'Raseborg castle',
        'Hvitträsk': 'Hvitträsk'
        #'kiväärit' : 'Rifles'
    }
    
    ## categories by type of photograph (portrait, nature..)
    # luontokuvat
    
    # must have place 'Suomi' to generate ' in Finland'
    #
    # note: there are also "from" and "of" categories in Commons, 
    # can we guess the right one automatically?
    # aircraft may be "in" city or "at" airport..
    subject_categories_with_country = {
        'professorit': 'Professors from',
        'kauppaneuvokset' : 'Businesspeople from',
        'toimitusjohtajat' : 'Businesspeople from',
        'miehet' : 'Men of',
        'naiset' : 'Women of',
        'perheet' : 'Families of',
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
        'kirjastorakennukset' : 'Libraries in',
        'rakennushankkeet' : 'Construction in',
        'rakennustarvikkeet' : 'Construction equipment in',
        'puusepänteollisuus' : 'Carpentry in',
        'laulujuhlat' : 'Music festivals in',
        'festivaalit' : 'Music festivals in',
        'neulonta' : 'Knitting in',
        'työvaatteet' : 'Work clothing in',
        'rukit' : 'Spinning wheels in',
        'meijerit' : 'Dairies in',
        'elintarvikeliikkeet' : 'Grocery stores in',
        'myymälät' : 'Shops in',
        'ravintolat' : 'Restaurants in',
        'kahvilat' : 'Coffee shops in',
        'konditoriat' : 'Konditoreien in',
        'leipomoteollisuus' : 'Bread industry in',
        #'leipomotuotteet' : '',
        #'leipomotyöntekijät' : '',
        'leivinuunit' : 'Baking ovens in',
        'musiikkiliikkeet' : 'Music stores in',
        'vaateliikkeet' : 'Clothing shops in',
        'mainoskuvat' : 'Advertisements in',
        'näyteikkunat' : 'Shop windows in',
        'koira' : 'Dogs of',
        'hevosajoneuvot' : 'Horse-drawn vehicles in',
        'polkupyörät' : 'Bicycles in',
        'aikakauslehdet' : 'Magazines of',
        # sanomalehtipaperi
        'sanomalehdet' : 'Newspapers of',
        'ammattikoulutus' : 'Vocational schools in',
        'salmet' : 'Straits of',
        'uimarannat' : 'Beaches of',
        'uimapuvut' : 'Swimwear in',
        'kylvö' : 'Agriculture in',
        'peltoviljely' : 'Agriculture in',
        'maanviljely' : 'Agriculture in',
        'maatalous' : 'Agriculture in',
        'uitto' : 'Timber floating in',
        'uittorännit' : 'Timber floating in',
        # retkeilyalueet, retkeilyvarusteet
        'retkeily' : 'Camping in',
        'tuolit' : 'Chairs in',
        'keittiöt' : 'Kitchens in',
        'näyttelyt' : 'Exhibitions in',
        'messut' : 'Trade fairs in',
        'messut (tapahtumat)' : 'Trade fairs in',
        'pikaluistelu' : 'Speed skating in',
        'talviurheilulajit' : 'Winter sports in',
        'talviurheilu' : 'Winter sports in',
        'kilpaurheilu' : 'Sports competitions in'
        #'maaottelut' : ''
    }
    
    # iron works
    # metal industry
    # Metalworkers

    manor_categories_by_location = {
        'Louhisaari' : 'Louhisaari Manor',
        'Piikkiö' : 'Pukkila Manor',
        'Kuusisto' : 'Kuusisto Manor',
        'Knuutila' : 'Knuutila Manor'
    }
    
    isInFinland = False
    cat_place = get_category_place(subject_places, depicted_places)
    if (len(cat_place) == 0):
        # TODO: try to cache the lookups
        # if we didn't have fast recognizing, try slow one
        #for place in reversed(subject_places):
            #location_id = get_location_by_name(place)
            #if (location_id != None):
        
        # fallback, if all else fails, at least try to detect counry
        if (depicted_places.find('Suomi') >= 0):
            cat_place = "Finland"
            isInFinland = True
            print("Place recognized as Finland, no further")
        #if 'Suomen entinen kunta/pitäjä' in depicted_places:
            #cat_place = "Finland"
    else:
        # for now, we recognize mostly places in finland..
        if ('Viipuri' not in depicted_places and 'Petsamo' not in depicted_places):
            isInFinland = True

    isInPortraits = False
    for subject in finna_image.subjects.all():
        if subject.name in subject_categories:
            category = subject_categories[subject.name]
            if (category == "Portrait photographs" and isInFinland == True):
                if 'miehet' in subject_names:
                    categories.add("Portrait photographs of men of Finland")
                    isInPortraits = True
                if 'naiset' in subject_names:
                    categories.add("Portrait photographs of women of Finland")
                    isInPortraits = True
                    
                if ('Portrait photographs of men of Finland' not in categories and 'Portrait photographs of women of Finland' not in categories):
                    categories.add("Portrait photographs of Finland")
                    isInPortraits = True
            elif (category == "Portrait photographs"):
                categories.add(category)
                isInPortraits = True
            else:
                categories.add(category)

        if (subject.name == "työ" and isInFinland == True):
            isGenderedWork = False
            if 'miehet' in subject_names:
                categories.add("Men at work in Finland")
                isGenderedWork = True
            if 'naiset' in subject_names:
                categories.add("Women at work in Finland")
                isGenderedWork = True
            if (isGenderedWork == False):
                # working in finland but no tag for gender
                categories.add("People at work in Finland")

        if (subject.name in subject_categories_with_country and isInFinland == True):
            category = subject_categories_with_country[subject.name] + " " + "Finland"
            categories.add(category)

        # or Askainen
        if (subject.name == 'kartanot' and 'Louhisaari' in depicted_places):
            categories.add('Louhisaari Manor')

        if (subject.name == 'kartanot' and 'Piikkiö' in depicted_places):
            categories.add('Pukkila Manor')

        #if (subject.name == 'kartanot' and 'Vesilahti' in depicted_places):
            #categories.add('Laukko Manor')
        if (subject.name == "Laukon kartano"):
            categories.add('Laukko Manor')

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

        if (subject.name == 'kanavat' and 'Kimolan kanava' in depicted_places):
            categories.add('Kimola Canal')
        if (subject.name == 'kanavat' and 'Vääksyn Vesijärven kanava' in depicted_places):
            categories.add('Vääksy Canal')

        #if (subject.name == "teatterirakennukset" and 'Turku' in depicted_places):
            #categories.add('Turku City Theatre')

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
        if (isInPortraits == True and isInFinland == True):
            categories.add(f'People of Finland in {finna_image.year}')
        if (isInPortraits == True):
            categories.add(f'{finna_image.year} portrait photographs')

        if (len(cat_place) > 0):
            categories.add(f'{finna_image.year} in {cat_place}')
    else:
        # if we can't determine year, use only location name
        # and only if it something other than country (at least a city)
        if (len(cat_place) > 0 and (cat_place != 'Suomi' and cat_place != 'Finland') and isInFinland == True):
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
