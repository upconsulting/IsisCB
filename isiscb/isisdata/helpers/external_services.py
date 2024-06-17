import requests
from isisdata.models import *
from django.conf import settings


def get_wikipedia_image_synopsis(authority, author_contributor_count, related_citations_count):
        wikiImage = wikiCredit = wikiIntro = ''

        if not authority.type_controlled == authority.SERIAL_PUBLICATION and not(authority.type_controlled == authority.PERSON and author_contributor_count != 0 and related_citations_count > 0 and author_contributor_count/related_citations_count > .9):
            wikipedia_data = WikipediaData.objects.filter(authority__id=authority.id).first()

            if wikipedia_data and (datetime.datetime.now(datetime.timezone.utc) - wikipedia_data.last_modified).days < settings.WIKIPEDIA_REFRESH_TIME:
                wikiImage = wikipedia_data.img_url
                wikiCredit = wikipedia_data.credit
                wikiIntro = wikipedia_data.intro

            else:
                authorityName = authority.name
                if hasattr(authority, 'person'):
                    if authorityName.find(',') >= 0:
                        firstName = authorityName[authorityName.index(',')+1:len(authorityName)].strip()
                        if firstName.find(',') >= 0:
                            firstName = firstName[:firstName.find(',')].strip()
                        lastName = authorityName[:authorityName.find(',')].strip()
                        authorityName = firstName + ' ' + lastName
                elif authority.type_controlled == authority.CONCEPT:
                    if authorityName.find(';') >= 0:
                        authorityName = authorityName[:authorityName.find(';')].strip()
                elif authority.type_controlled == authority.GEOGRAPHIC_TERM:
                    if authorityName.find('(') >= 0:
                        authorityName = authorityName[:authorityName.find('(')].strip()

                if authorityName:
                    imgURL = settings.WIKIPEDIA_IMAGE_API_PATH.format(authorityName = authorityName)
                    introURL = settings.WIKIPEDIA_INTRO_API_PATH.format(authorityName = authorityName)
                    imgJSON = requests.get(imgURL).json()

                    if list(imgJSON['query']['pages'].items())[0][0] != '-1':
                        imgPage = list(imgJSON['query']['pages'].items())[0][1]
                        imgPageID = imgPage['pageid']
                        wikiCredit = f'{settings.WIKIPEDIA_PAGE_PATH}{imgPageID}'
                        if imgPage.get('original') and imgPage['original'].get('source'):
                            wikiImage = imgPage['original']['source']

                        introJSON = requests.get(introURL).json()
                        extract = list(introJSON['query']['pages'].items())[0][1]['extract']
                        if extract.find('may refer to') < 0:
                            wikiIntro = extract

                wikipedia_data = WikipediaData(img_url=wikiImage, credit=wikiCredit, intro=wikiIntro, authority_id=authority.id)
                wikipedia_data.save()

            return wikiImage, wikiIntro, wikiCredit