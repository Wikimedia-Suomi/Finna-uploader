import pywikibot
import re
import psycopg2

def escapesinglequote(s):
    return s.replace("'", "''")

# simple mapping for text (name, label) from Finna 
# into a matching Qcode for wikidata
class MapTextToQcode:
    def __init__(self):
        self.mapping = {}
        
        # keep time of refreshing contents
        #self.refreshtime = dt
        
    # modify just one pair
    def setPair(self, text, qcode):
        if (text not in self.mapping):
            self.mapping[text] = qcode

    def clearMap(self):
        self.mapping.clear()
        
    # update full mapping
    def setParsedData(self, pd):
        self.mapping.clear()
        for text, qcode in pd:
            self.mapping[text] = qcode

    def getQcode(self, text):
        if (text in self.mapping):
            return self.mapping[text]
        return None


class CachedMappingDb:
    def __init__(self, tablename):
        self.tablename = tablename
    
    def opencachedb(self):
        print("DEBUG, opening cache", self.tablename)
        # support multiple mapping tables
        self.conn = psycopg2.connect("dbname=wikidb")
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS " + self.tablename + " (name varchar(100), qcode varchar(50))")
        return True

    def closecachedb(self):
        self.conn.close()

    def addtocache(self, name, qcode):
        name = escapesinglequote(name)
        #print("adding name", name)
        sqlq = "INSERT INTO " + self.tablename + "(name, qcode) VALUES ('" + name + "', '" + qcode + "')"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def updatecache(self, name, qcode):
        name = escapesinglequote(name)
        #print("updating name", name)
        sqlq = "UPDATE " + self.tablename + " SET qcode = '" + qcode + "' WHERE name = '" + name + "'"

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def clearcache(self):
        sqlq = "DELETE FROM " + self.tablename + ""

        cur = self.conn.cursor()
        cur.execute(sqlq)
        self.conn.commit()

    def findfromcache(self, name):
        name = escapesinglequote(name)
        #print("finding name", name)
        sqlq = "SELECT name, qcode FROM " + self.tablename + " WHERE name = '" + name + "'"
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        rset = cur.fetchall()
        if (rset == None):
            print("DEBUG: no resultset for query")
            return None
        if (len(rset) > 1):
            # too many found
            return None
        for row in rset:
            return row[1]
        return None

    def loadcache(self):
        sqlq = "SELECT name, qcode FROM " + self.tablename + ""
        
        cur = self.conn.cursor()
        res = cur.execute(sqlq)
        rset = cur.fetchall()
        if (rset == None):
            print("DEBUG: no resultset for query")
            return None
        
        mpq = MapTextToQcode()
        for row in rset:
            name = row[0]
            qcode = row[1]
            mpq.setPair(name, qcode)
        return mpq

    def addorupdate(self, name, qcode):
        qctmp = self.findfromcache(name)
        if (qctmp == None):
            self.addtocache(name, qcode)
        else:
            self.updatecache(name, qcode)

    # mp = MapTextToQcode
    def updatemapping(self, mpq):
        self.clearcache()

        #for name, qcode in mpq.mapping:
        for name in mpq.mapping:
            qcode = mpq.mapping[name]
            self.addorupdate(name, qcode)


def parse_mapping_page(page_title):
    page = pywikibot.Page(site, page_title)
    print("DEBUG, mapping page loaded ", page_title)

    pattern = r'\*\s(.*?)\s:\s\{\{Q\|(Q\d+)\}\}'
    matches = re.findall(pattern, page.text)

    # Extracted names and Q-items
    parsed_data = MapTextToQcode()
    for name, q_item in matches:
        parsed_data.setPair(name, q_item)
    return parsed_data


def refreshCache():
    print("refreshing cache..")
    
    nonPresenterAuthorsMap = parse_mapping_page('User:FinnaUploadBot/data/nonPresenterAuthors') # noqa
    nonPresenterAuthorsCache = CachedMappingDb("cache_nonpresenterauthors")
    nonPresenterAuthorsCache.opencachedb()
    nonPresenterAuthorsCache.updatemapping(nonPresenterAuthorsMap)
    nonPresenterAuthorsCache.closecachedb()

    institutionsMap = parse_mapping_page('User:FinnaUploadBot/data/institutions')
    institutionsCache = CachedMappingDb("cache_institutions")
    institutionsCache.opencachedb()
    institutionsCache.updatemapping(institutionsMap)
    institutionsCache.closecachedb()

    collectionsMap = parse_mapping_page('User:FinnaUploadBot/data/collections')
    collectionsCache = CachedMappingDb("cache_collections")
    collectionsCache.opencachedb()
    collectionsCache.updatemapping(collectionsMap)
    collectionsCache.closecachedb()

    subjectActorsMap = parse_mapping_page('User:FinnaUploadBot/data/subjectActors')
    subjectActorsCache = CachedMappingDb("cache_subjectactors")
    subjectActorsCache.opencachedb()
    subjectActorsCache.updatemapping(subjectActorsMap)
    subjectActorsCache.closecachedb()

    # may have very long strings
    #subjectPlacesMap = parse_mapping_page('User:FinnaUploadBot/data/subjectPlaces')
    #subjectPlacesCache = CachedMappingDb("cache_subjectplaces")
    #subjectPlacesCache.opencachedb()
    #subjectPlacesCache.updatemapping(subjectPlacesMap)
    #subjectPlacesCache.closecachedb()
    
    print("cache refreshed")

# main()

pywikibot.config.socket_timeout = 120
site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
site.login()

refreshCache()
