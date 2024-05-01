from __future__ import unicode_literals
from django import template
from isisdata.models import *

import requests


def get_google_books_image(citation, featured, api_key=None):

    # Provide image for citation
    if citation.type_controlled not in [Citation.BOOK, Citation.CHAPTER]:
        return {}

    cover_image = {}

    parent_id = None
    parent_relations = CCRelation.objects.filter(object_id=citation.id, type_controlled='IC')
    if parent_relations and parent_relations[0].subject:
        parent_id = parent_relations[0].subject.id

    if citation.type_controlled in [Citation.CHAPTER] and parent_id:
        google_books_data = GoogleBooksData.objects.filter(citation__id=parent_id).first()
    else:
        google_books_data = GoogleBooksData.objects.filter(citation__id=citation.id).first()

    google_books_refresh_time = settings.GOOGLE_BOOKS_REFRESH_TIME

    # If we have the google books data cached, we can just return the cached data
    if google_books_data and (datetime.datetime.now(datetime.timezone.utc) - google_books_data.last_modified).days < google_books_refresh_time and not featured:
        cover_image['size'] = google_books_data.image_size
        cover_image['url'] = google_books_data.image_url

        return cover_image

    contrib = ''
    title = ''

    if citation.type_controlled in [Citation.BOOK]:
        title = citation.title
        if citation.get_all_contributors and citation.get_all_contributors[0].authority and citation.get_all_contributors[0].authority.name:
            contrib = citation.get_all_contributors[0].authority.name.strip()
    elif citation.type_controlled in [Citation.CHAPTER] and parent_relations and parent_relations[0].subject and parent_relations[0].subject.title:
        title = parent_relations[0].subject.title
        if parent_relations[0].subject.get_all_contributors and parent_relations[0].subject.get_all_contributors[0].authority and parent_relations[0].subject.get_all_contributors[0].authority.name:
            contrib = parent_relations[0].subject.get_all_contributors[0].authority.name.strip()
    if not title:
        return

    if ',' in contrib:
        contrib = contrib[:contrib.find(',')]
    elif ' ' in contrib:
        contrib = contrib[contrib.find(' '):]

    if api_key:
        # apparently the google books api works without a key, so we only use one if we have one
        url = settings.GOOGLE_BOOKS_TITLE_QUERY_PATH.format(title=title, apiKey=api_key)
    else:
        url = settings.GOOGLE_BOOKS_TITLE_QUERY_PATH_NO_KEY.format(title=title)
    url = url.replace(" ", "%20")

    with requests.get(url) as resp:
        if resp.status_code != 200:
            return {}

        books = resp.json()
        items = books["items"]

    bookGoogleId = ''

    for i in items:
        if i["volumeInfo"]["title"].lower() in title.lower() or 'authors' in i["volumeInfo"] and any(contrib in s for s in i["volumeInfo"]["authors"]):
            bookGoogleId = i["id"]
            break

    if not bookGoogleId:
        return {}

    if api_key:
        url2 = settings.GOOGLE_BOOKS_ITEM_GET_PATH.format(bookGoogleId=bookGoogleId, apiKey=api_key)
    else:
        url2 = settings.GOOGLE_BOOKS_ITEM_GET_PATH_NO_KEY.format(bookGoogleId=bookGoogleId)
    url2 = url2.replace(" ", "%20")

    with urlopen(url2) as response:
        book = json.load(response)

        if 'imageLinks' in book["volumeInfo"]:
            imageLinks = book["volumeInfo"]["imageLinks"].keys()

            # we probably always want the thumbnail since the other ones are often just the top part of the image
            if "thumbnail" in imageLinks:
                cover_image["size"] = "thumbnail"
                cover_image["url"] = book["volumeInfo"]["imageLinks"]["thumbnail"].replace("http://", "https://")
            elif "medium" in imageLinks and not featured:
                cover_image["size"] = "standard"
                cover_image["url"] = book["volumeInfo"]["imageLinks"]["medium"].replace("http://", "https://")
            elif "small" in imageLinks and not featured:
                cover_image["size"] = "standard"
                cover_image["url"] = book["volumeInfo"]["imageLinks"]["thumbnail"].replace("http://", "https://")
            
            if citation.type_controlled in [Citation.BOOK]:
                google_books_data = GoogleBooksData(image_url=cover_image['url'], image_size=cover_image['size'], citation_id=citation.id)
            elif citation.type_controlled in [Citation.CHAPTER] and parent_id:
                google_books_data = GoogleBooksData(image_url=cover_image['url'], image_size=cover_image['size'], citation_id=parent_id)
            google_books_data.save()

    return cover_image