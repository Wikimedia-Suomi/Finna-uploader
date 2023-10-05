import urllib
import imagehash
from PIL import Image

# Perceptual hashing
# http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

def calculate_phash(im):
    hash = imagehash.phash(im)
    hash_int=int(str(hash),16)
    return hash_int

# difference hashing
# http://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html

def calculate_dhash(im):
    hash = imagehash.dhash(im)
    hash_int=int(str(hash),16)
    return hash_int

def calculate_dhash_vertical(im):
    hash = imagehash.dhash(im)
    hash_int=int(str(hash),16)
    return hash_int

def get_imagehashes(url, thumbnail=False):
    # Open the image1 with Pillow
    im = Image.open(urllib.request.urlopen(url))
    # Get width and height
    width, height = im.size

    ret = {
        'url'   : url,
        'phash' : calculate_phash(im),
        'dhash' : calculate_dhash(im),
        'dhash_vertical' : calculate_dhash_vertical(im),
        'width':width,
        'height':height,
        'thumbnail':thumbnail
    }
    return ret

def is_same_image(url1, url2):
    img1=get_imagehashes(url1)
    img2=get_imagehashes(url2)
    
    # Hamming distance difference
    phash_diff = bin(img1['phash'] ^ img2['phash']).count('1')
    dhash_diff = bin(img1['dhash'] ^ img2['dhash']).count('1')
    dhash_vertical_diff = bin(img1['dhash_vertical'] ^ img2['dhash_vertical']).count('1')
    
    print(f'{phash_diff}\t{dhash_diff}\t{dhash_vertical_diff}')
    
    if phash_diff == 0 and dhash_diff < 4:
        return True
    elif phash_diff < 4 and dhash_diff == 0:
        return True
    elif phash_diff < 4 and dhash_vertical_diff == 0:
        return True
    elif phash_diff+dhash_diff+dhash_vertical_diff <8:
        return True
    else:
        return False

