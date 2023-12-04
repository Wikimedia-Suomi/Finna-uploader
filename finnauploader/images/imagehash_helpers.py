import os
import urllib
from urllib.parse import urlparse
import hashlib
import imagehash
from images.finna import get_finna_record
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


def get_imagehashes(url, thumbnail=False, filecache=False):
    if filecache:
        print("filecache")
        md5_hash = hashlib.md5(url.encode()).hexdigest()
        # Extract the domain from the URL
        domain = urlparse(url).netloc.replace('www.', '')

        # Use the first two characters of the hash for the directory name
        directory = os.path.join('cache', domain, md5_hash[:1], md5_hash[:2])

        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        # The path where the image will be saved
        file_path = os.path.join(directory, md5_hash + '.jpg')
        print(file_path)

        # Check if the file already exists
        if not os.path.exists(file_path):
            with urllib.request.urlopen(url) as response, open(file_path, 'wb') as out_file:
                data = response.read()
                out_file.write(data)

        # Open the image1 with Pillow
        im = Image.open(file_path)

    else:
        print("no filecache")

        # If no filecaching then open image from url
        im = Image.open(urllib.request.urlopen(url))

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


def is_same_image(url1, url2):
    img1 = get_imagehashes(url1)
    img2 = get_imagehashes(url2)
    return compare_image_hashes_strict(img1, img2)


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


def is_correct_finna_record(finna_id, image_url, allow_multiple_images=True):
    finna_record = get_finna_record(finna_id, True)

    if finna_record['status'] != 'OK':
        print('Finna status not OK')
        return False

    if finna_record['resultCount'] != 1:
        print('Finna resultCount != 1')
        return False

    if not allow_multiple_images \
       and len(finna_record['records'][0]['imagesExtended']) > 1:
        print('Multiple images in single record. Skipping')
        return False

    record_finna_id = finna_record['records'][0]['id']
    if record_finna_id != finna_id:
        print(f'finna_id update: {finna_id} -> {record_finna_id}')

    for imageExtended in finna_record['records'][0]['imagesExtended']:
        # Test copyright
        allowed_copyrighs = ['CC BY 4.0', 'CC0']
        if imageExtended['rights']['copyright'] not in allowed_copyrighs:
            copyright_msg = imageExtended['rights']['copyright']
            print(f'Incorrect copyright: {copyright_msg}')
            return False

        # Confirm that images are same using imagehash

        file_path = imageExtended['urls']['large']
        finna_thumbnail_url = f'https://finna.fi{file_path}'
        print(finna_thumbnail_url)
        if is_same_image(finna_thumbnail_url, image_url):
            return record_finna_id
