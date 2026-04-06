import os
import io
import urllib
from urllib.parse import urlparse, parse_qs
import pycurl
import certifi


# generic download helper:
# gzipped data dumps can benefit.
# 
def download_file(url, redirect=False):
    #print("DEBUG: downloading from url:", url)
    
    buffer = io.BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.CAINFO, certifi.where())
    c.setopt(c.USERAGENT, 'pywikibot')
    #c.setopt(pycurl.TIMEOUT, 120)

    # follow redirect
    if (redirect == True):
        c.setopt(c.FOLLOWLOCATION, True)
    c.perform()
    c.close()

    if (buffer.readable() == False or buffer.closed == True):
        #print("ERROR: can't read data from stream")
        return None

    #print("DEBUG: data downloaded, nbytes:", str(buffer.getbuffer().nbytes))
    
    return buffer

# note: when downloading image via redirect service,
# see what options might need to be used:
# this should help with the problem where copy-upload can't be used.
