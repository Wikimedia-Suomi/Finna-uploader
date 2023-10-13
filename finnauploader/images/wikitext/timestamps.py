import re

def parse_timestamp(datestr):
   # str = "valmistusaika: 22.06.2015"
   m = re.match("valmistusaika:? (\d\d)\.(\d\d)\.(\d\d\d\d)", datestr)
   if m!=None:
      year=m.group(3)
      month=m.group(2)
      day=m.group(1)
      timestamp="+" + year +"-" + month +"-" + day +"T00:00:00Z"
      precision=11  
      return timestamp, precision
    
   m = re.match("valmistusaika:? (\d\d\d\d)", datestr)
   if m!=None:
      year=m.group(1)
      timestamp="+" + year +"-01-01T00:00:00Z"
      precision=9
      return timestamp, precision

   if not datestr:
       return None, None

   exit(f'Parse_timestamp failed: {datestr}')
    

def parse_timestamp_string(datestr):
   if not datestr:
       return ''
    
   m = re.match("valmistusaika:? (\d\d)\.(\d\d)\.(\d\d\d\d)$", datestr.strip())
   if m!=None:
      year=m.group(3)
      month=m.group(2)  
      day=m.group(1)
      timestamp=year +"-" + month +"-" + day
      return timestamp  

   m = re.match("valmistusaika:? (\d\d\d\d)$", datestr.strip())
   if m!=None:
      year=m.group(1)
      return year
    
   if not datestr:
       return ''
   return '{{fi|' + datestr + '}}'

   #exit("Parse_timestamp failed")
