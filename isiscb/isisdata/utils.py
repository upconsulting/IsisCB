"""
Utility functions that do not depend on other app modules.

Functions that rely on app modules (e.g. models) should be placed in
:mod:`isisdata.operations`\.
"""

import bleach, re, string, unidecode, unicodedata, regex


def remove_control_characters(s):
    s = unicode(s)
    return u"".join(ch for ch in s if unicodedata.category(ch)[0]!="C")


def strip_punctuation(text):
    return regex.sub(ur"\p{P}+", u" ", text)


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
