import os
import io
import re
import urllib
from urllib.parse import urlparse, parse_qs
import pycurl
import certifi
import hashlib
import imagehash
from PIL import Image


# Perceptual hashing
# http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
def calculate_phash(im):
    hash = imagehash.phash(im)
    hash_int = int(str(hash), 16)
    return hash_int


# difference hashing
# http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.htm
def calculate_dhash(im):
    hash = imagehash.dhash(im)
    hash_int = int(str(hash), 16)
    return hash_int


def calculate_dhash_vertical(im):
    hash = imagehash.dhash_vertical(im)
    hash_int = int(str(hash), 16)
    return hash_int


def is_valid_path_and_filename(parts):
    # Regular expression pattern to match only allowed characters
    # (0-9, a-z, A-Z, ., _, -)
    pattern = r'^[0-9a-zA-Z._-]+$'
    for part in parts:
        if not bool(re.match(pattern, part)):
            return False
    return True

# let's try pycurl for download:
# it should be faster, better support for protocols
# and possibly avoid some bugs
def download_image(url):
    #print("DEBUG: downloading image from url:", url)
    
    buffer = io.BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.CAINFO, certifi.where())
    c.setopt(c.USERAGENT, 'FinnaUploader 0.2 (https://commons.wikimedia.org/wiki/User:FinnaUploadBot)')
    #c.setopt(pycurl.TIMEOUT, 120)
    c.perform()
    c.close()

    if (buffer.readable() == False or buffer.closed == True):
        #print("ERROR: can't read image from stream")
        return None
    # server is sending empty image instead?
    if (buffer.getbuffer().nbytes < 100):
        #print("ERROR: less than 100 bytes in buffer")
        return None

    #print("DEBUG: image downloaded, nbytes:", str(buffer.getbuffer().nbytes))
    
    # pillow might not be able to open the file:
    # just give a buffer and call some helper to maybe convert image
    #body = buffer.getvalue()
    return buffer

# get format from finna-record hires["format"]
# only add formats supported by pillow here
def isimageformatsupported(strformat):
    # are there png files in finna?
    if (strformat == "tif" 
        or strformat == "jpg"):
        return True
    return False


# format according to mime-type (commons file info):
# only add formats supported by pillow here
def isimageformatsupportedmime(strformat):
    if (strformat == "image/tiff" 
        or strformat == "image/jpeg" 
        or strformat == "image/png"):
        return True
    return False
    

def get_finna_image_url(finna_id, index):
    if not finna_id:
        return None

    url = 'https://finna.fi/Cover/Show?source=Solr&size=large'
    url += f'&id={finna_id}'
    url += f'&index={index}'
    
    return url


def get_imagehashes(url, thumbnail=False, filecache=False):
    im = None
    
    if filecache:
        print("filecache")
        # Extract the domain from the URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')

        # Cached files should be in human readable directories
        # and using human readable filenames. Files in directories
        # should be spread to multiple dirs so that there
        # is no directories with 100k files.

        # Target filename syntax
        # Finna: finna_id_index.jog
        # Finna: museovirasto.0F80A4CD84098203075256A6A395EE41_0.jpg
        # Commons: M123456.jpg
        # Ajapaik: ajapaik.123456.jpg

        if domain == 'finna.fi':
            query_components = parse_qs(parsed_url.query)
            # Extract the 'id' and 'index' parameters
            id_param = query_components.get('id', [None])[0]
            organization = id_param.split(".")[0]
            index_param = query_components.get('index', [None])[0]
            organizations = ['museovirasto', 'kansallisgalleria']
            if organization in organizations:
                filename = f'{id_param}_{index_param}.jpg'
                md5_hash = hashlib.md5(filename.encode()).hexdigest()
                parts = [domain, organization, filename]
                if not is_valid_path_and_filename(parts):
                    print('ERROR: filename test failed')
                    print(parts)
                    exit(1)

                directory = os.path.join('cache',
                                         domain,
                                         organization,
                                         md5_hash[:1], md5_hash[:2])
            else:
                print("ERROR: Unknown org")
                print(url)
                exit(1)
        else:
            # Limit filecached hashing to specific domains for
            if 1:
                print("ERROR: Unknown domain in imagehash_helpers.py")
                print(url)
                exit(1)

            # Use the first two characters of the hash for the directory name
            md5_hash = hashlib.md5(url.encode()).hexdigest()
            directory = os.path.join('cache',
                                     domain,
                                     md5_hash[:1], md5_hash[:2])
            filename = md5_hash + '.jpg'
            parts = [domain, filename]
            if not is_valid_path_and_filename(parts):
                print('ERROR: filename test failed')
                print(parts)
                exit(1)

        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        # The path where the image will be saved
        file_path = os.path.join(directory, filename)
        print(file_path)
        
        exists = False

        # Check if the file already exists
        if not os.path.exists(file_path):
            print("creating file")

            # use pycurl
            data = download_image(url)
            if (data != None):
                out_file = open(file_path, 'wb')
                out_file.write(data)
                
                exists = True
            else:
                print("could not download image from url:", url)
        else:
            print("cached")
            exists = True

        if (exists == True):
            # Open the image1 with Pillow
            im = Image.open(file_path)

    else:
        print("no filecache")

        # If no filecaching then open image from url
        data = download_image(url)
        if (data != None):
            im = Image.open(data)
        else:
            print("could not download image from url:", url)
    
    # image failed to be downloaded?
    # obsolete url?
    if (im == None):
        return None

    # Get width and height
    width, height = im.size

    ret = {
        'url': url,
        'phash': calculate_phash(im),
        'dhash': calculate_dhash(im),
        'dhash_vertical': calculate_dhash_vertical(im),
        'width': width,
        'height': height,
        'thumbnail': thumbnail
    }
    return ret

# this potentially downloads image(s) but ignores error handling
# -> not in use, see if anything else still calls this
#def is_same_image(url1, url2):
#    img1 = get_imagehashes(url1)
#    img2 = get_imagehashes(url2)
#    if (img1 != None and img2 != None):
#        return compare_image_hashes_strict(img1, img2)
#    return None


def compare_image_hashes_strict(img1, img2):
    # Hamming distance difference
    phash_diff = bin(img1['phash'] ^ img2['phash']).count('1')
    dhash_diff = bin(img1['dhash'] ^ img2['dhash']).count('1')
    dhash_vertical_diff = bin(
                             img1['dhash_vertical'] ^ img2['dhash_vertical']
                             ).count('1')

#    print(f'{phash_diff}\t{dhash_diff}\t{dhash_vertical_diff}')

    if phash_diff == 0 and dhash_diff < 4 and dhash_vertical_diff < 4:
        return True
    elif phash_diff < 4 and dhash_diff == 0 and dhash_vertical_diff < 4:
        return True
    elif phash_diff < 4 and dhash_vertical_diff == 0 and dhash_diff < 4:
        return True
    elif phash_diff + dhash_diff + dhash_vertical_diff < 10:
        return True
    else:
        return False


def compare_image_hashes(img1, img2):
    # Hamming distance difference
    phash_diff = bin(img1['phash'] ^ img2['phash']).count('1')
    dhash_diff = bin(img1['dhash'] ^ img2['dhash']).count('1')
    dhash_vertical_diff = bin(
                             img1['dhash_vertical'] ^ img2['dhash_vertical']
                             ).count('1')

#    print(f'{phash_diff}\t{dhash_diff}\t{dhash_vertical_diff}')

    if phash_diff == 0 and dhash_diff < 4:
        return True
    elif phash_diff < 4 and dhash_diff == 0:
        return True
    elif phash_diff < 4 and dhash_vertical_diff == 0:
        return True
    elif phash_diff + dhash_diff + dhash_vertical_diff < 8:
        return True
    else:
        return False

def compare_finna_hash(finnaurls, img2_hash):
    if (len(finnaurls) == 0):
        print('DEBUG: empty url list')
        return False

    for finna_thumbnail_url in finnaurls:

        # if image fails to be downloaded (obsolete url? removed?) don't crash on it
        try:
            finna_hash = get_imagehashes(finna_thumbnail_url)
            if (finna_hash != None and img2_hash != None):
                if compare_image_hashes_strict(finna_hash, img2_hash):
                    return record_finna_id
        except Image.UnidentifiedImageError:
            print('Pillow did not recognize image format, finna id:', finna_id)
            
            # one image not supported, are there other formats of same image?
            #return False

    # no match
    return False

