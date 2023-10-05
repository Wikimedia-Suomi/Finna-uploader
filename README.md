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
pip install --upgrade pip
pip install pywikibot imagehash django
```


Setup the user-config.py
```bash
nano ./user-config.py
```

makemigrations will generate SQL change files based on models.py changes
- See https://docs.djangoproject.com/en/4.2/topics/migrations/
```bash
python manage.py makemigrations
python manage.py migrate
```

IMPORT DATA
- Commands are in directory images/management/commands

```bash
# Import names and urls of all images with externallinks containing Finna_id to local database
python manage.py import_commons_images_with_link_to_finna

# Import all P9478 Finna id values to local dabase 
# - This uses https://commons-query.wikimedia.org service so login and OAUTH needs to be working
python manage.py python manage.py import_P9478_finna_id_values_to_images

# Add 'best' finna_id from SDC to Image.finna_id 
python manage.py set_finna_id_from_SDC_to_image

# Add 'best' finna_id from externallinks to Image.finna_id after confirming it using imagehash 
# - This is very slow and you can skip this if you are just testing
python manage.py set_finna_id_from_externallinks_to_image

# Check the current number of the images in the database
python manage.py image_status
```

Howto delete dabase and migrations to start database from zero
```bash
rm db.sqlite3
rm -rf images/migrations/000*.py
```

# Howto create Django boilerplate project 
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
    'images',
]

# These files were created manually on initial repo
./user-config.py
./images/models.py 
./images/finna.py 
./images/imagehash_helpers.py 

# Management commands created
mkdir images/management/commands 
./images/management/commands/import_commons_images_with_link_to_finna.py
./images/management/commands/import_P9478_finna_id_values_to_images.py
./images/management/commands/set_finna_id_from_SDC_to_image.py
./images/management/commands/set_finna_id_from_externallinks_to_image.py
./images/management/commands/image_status.py

```

