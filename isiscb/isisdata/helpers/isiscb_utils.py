import hashlib
import base64

def generate_search_key(path):
    """
    Method to generate a key to store search results in the session.

    Arguments:
    path -- path of the search
    """
    md5_hash = hashlib.md5(path.encode())
    return base64.b64encode(md5_hash.hexdigest().encode()).decode(errors="ignore")

def build_name_first_last(name):
    if name.find(',') >= 0:
        firstName = name[name.index(',')+1:len(name)].strip()
        if firstName.find(',') >= 0:
            firstName = firstName[:firstName.find(',')].strip()
        lastName = name[:name.find(',')].strip()
        name = firstName + ' ' + lastName
        
    return name