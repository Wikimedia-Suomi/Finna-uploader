import requests
import urllib


def finto_search(keyword, vocab='finaf'):
    keyword = keyword.replace('\n', ' ')
    keyword = keyword.replace(' ', '*') + '*'
    urlencoded_keyword = urllib.parse.quote_plus(str(keyword))
    urlparams = f'vocab={vocab}&query={urlencoded_keyword}'
    url = f'http://api.finto.fi/rest/v1/search?{urlparams}'
    try:
        response = requests.get(url)
        data = response.json()
    except:
        print("Finto API query failed: " + url)
        exit(1)
    for term in data['results']:
        return get_finto_term_information(vocab, term['uri'])


# Search detailed information for the term
def get_finto_term_information(vocab, term_url):
    urlencoded_term = urllib.parse.quote_plus(term_url)
    urlparams = f'format=application/json&uri={urlencoded_term}'
    url = f'http://api.finto.fi/rest/v1/{vocab}/data?{urlparams}'
    print(url)
    try:
        response = requests.get(url)
        data = response.json()

    except:
        print("Finto API query failed: " + url)
        exit(1)
    return data
