import bleach
import re
import string
import unidecode
import unicodedata


def remove_control_characters(s):
    s = unicode(s)
    return u"".join(ch for ch in s if unicodedata.category(ch)[0]!="C")


def strip_punctuation(s):
    """
    Removes all punctuation characters from a string.
    """
    if not s:
        return ''
    if type(s) is str:    # Bytestring (default in Python 2.x).
        return s.translate(string.maketrans("",""), string.punctuation.replace('-', ''))
    else:                 # Unicode string (default in Python 3.x).
        translate_table = dict((ord(char), u'') for char
                                in u'!"#%\'()*+,./:;<=>?@[\]^_`{|}~')
        return s.translate(translate_table)


def strip_tags(s):
    """
    Remove all tags without remorse.
    """
    return bleach.clean(s, tags={}, attributes={}, strip=True)


def normalize(s):
    """
    Convert to ASCII.
    Remove HTML.
    Remove punctuation.
    Lowercase.
    """
    if not s:
        return ''
    if type(s) is str:
        s = s.decode('utf-8')
    return remove_control_characters(strip_punctuation(strip_tags(unidecode.unidecode(s))).lower())


# TODO: is that the best way to do this???
def strip_hyphen(s):
    """
    Remove hyphens and replace with space.
    Need to find hyphenated names.
    """
    if not s:
        return ''

    return s.replace('-', ' ')


def help_text(s):
    """
    Cleans up help strings so that we can write them in ways that are
    human-readable without screwing up formatting in the admin interface.
    """
    return re.sub('\s+', ' ', s).strip()
