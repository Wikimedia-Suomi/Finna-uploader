## Finna-uploader
**Wikimedia Commons Finna photo tagging and uploading**

### Install

```bash
git clone git@github.com:Wikimedia-Suomi/Finna-uploader.git
cd Finna-uploader
python -m venv venv
source venv/bin/activate
```
Install packages
```bash
pip install --upgrade pip setuptools wheel
pip install pywikibot imagehash django django-extensions djangorestframework flake8 beautifulsoup4 django-watson
pip install pycurl certifi
```

Setup the user-config.py
```bash
cd finnauploader
nano ./user-config.py
```

makemigrations will generate SQL change files based on models.py changes
- See https://docs.djangoproject.com/en/4.2/topics/migrations/
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```

IMPORT DATA
- Commands source code is in directory finnauploader/images/management/commands
- Commands are executed from the ./finnauploader directory
- Order of execution of scropts is important as scripts will refine the data in database

Quickstart for uploading images.

```bash
# Import JOKA journalistic photo archive records to Finna
python manage.py finna_search --collection JOKA

# Import precalculated imagehashes for Finna records
python manage.py import_finna_imagehashes
python manage.py import_toolforge_imagehashes

# Start webserver for uploading
python manage.py runserver 

# Open web ui
http://127.0.0.1:8000/
```

FULL IMPORT

```bash

# ** Wikimedia Commons image info **

# Import names and urls of all images with externallinks containing Finna_id to local database
python manage.py import_commons_images_with_link_to_finna

# Import all P9478 Finna id values to local dabase 
# - This uses https://commons-query.wikimedia.org service so login and OAUTH needs to be working
python manage.py import_P9478_finna_id_values_to_images

# Add 'best' finna_id from SDC to Image.finna_id 
python manage.py set_finna_id_from_SDC_to_image

# Add 'best' finna_id from externallinks to Image.finna_id after confirming it using imagehash 
# - This is very slow and you can skip this if you are just testing
python manage.py set_finna_id_from_externallinks_to_image

# Update Image.finna_id to id from Finna.fi record
python manage.py set_finna_id_to_latest_from_finna

# ** Finna records ( THESE DOESNT NEED Commons image info to work ) **

# Import JOKA journalistic photo archive records to Finna
python manage.py finna_search --collection "JOKA Journalistinen kuva-arkisto"

# Imagehash images linked from Finna records
python manage.py imagehash_finna_images

# Export imagehashes
python manage.py dump_finna_imagehashes

# ** STATUS **

# Check the current number of the images in the database
python manage.py image_status
```

### Upload_kuvasiskot.py parameters
```bash
python manage.py image_status --lookfor KEYWORD --require-text KEYWORD --skip-text KEYWORD --add_category ADDED_CATEGORY --add_depict ADDED_DEPICT --add_depict_and_cat ADDED_VALUE
```


Parameters
- lookfor = Finna search keyword
- require-text = text needs to be found in Finna record. Parameter can be defined multiple times. 
- skip-text = if text is found in record then record is skipped. Parameter can be defined multiple times.
- add_category = add this category to the photos. Value is QID, link to wikipedia/wikimedia page, link to commons category or commons category name. Parameter can be defined multiple times. 
- add_depict = add this depict to the photos. Value is QID, link to wikipedia/wikimedia page, link to commons category or commons category name. Parameter can be defined multiple times.
- add_depict_and_cat = add this value to depicts and categories.


### Database operations
Howto connect to sqlite3 db from commandline

```bash
sqlite3 db.sqlite3 
```

Howto do basic commands inside sqlite3
```bash

# Show tables
.tables

# Describe table 
.schema images_image

# Run select 
SELECT * FROM images_image LIMIT 10;

# Exit from sqlite3 console
.exit
```

Howto visualize the database as a graph 

- with graphviz
```bash
sudo apt-get install graphviz
# OR in OS X
brew install graphviz

# And then
python manage.py graph_models -a -o database_model.png
```

- without graphviz
```bash
python manage.py graph_models -a > database_model.dot
# Render .dot file using web page
# https://dreampuf.github.io/GraphvizOnline
```

Howto delete dabase and migrations to start database from zero
```bash
rm db.sqlite3
rm -rf images/migrations/000*.py
```

### Running flake8
Flake8 is code syntax and formatting checker.


```bash
flake8 images/models.py
```

### Switching to PostgreSQL
For instructions on using PostgreSQL instead of SQLite, see: [README_postgresql](README_postgresql).

### Howto create Django boilerplate project 
- this is documentation on how first commit version was created

```bash
# Create boilerplate Django app
django-admin startproject finnauploader
cd finnauploader
python manage.py startapp images

#Add pages to Installed Apps:
#
#In finnauploader/settings.py, add 'pages' to the INSTALLED_APPS list:
#python
#
INSTALLED_APPS = [
    ...
    'django_extensions', # graph_models needs this
    'images',
]

# These files were created manually on initial repo
./finnauploader/user-config.py
./finnauploader/images/models.py 
./finnauploader/images/finna.py 
./finnauploader/images/imagehash_helpers.py 

# Management commands created
mkdir finnauploader/images/management/commands 
./finnauploader/images/management/commands/import_commons_images_with_link_to_finna.py
./finnauploader/images/management/commands/import_P9478_finna_id_values_to_images.py
./finnauploader/images/management/commands/set_finna_id_from_SDC_to_image.py
./finnauploader/images/management/commands/set_finna_id_from_externallinks_to_image.py
./finnauploader/images/management/commands/image_status.py

```

