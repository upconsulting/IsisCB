# TODO: this should be combined with isisdata.utils.

import string
import unidecode
import re
import bleach


def strip_punctuation(s):
    """
    Removes all punctuation characters from a string.
    """
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
        return s

    return strip_punctuation(strip_tags(unidecode.unidecode(s))).lower()


def filter_abstract(s):
    return re.match("{AbstractBegin}(.*){AbstractEnd}", s).group(1)
