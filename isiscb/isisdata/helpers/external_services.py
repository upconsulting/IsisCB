import requests
from isisdata.models import *
import isisdata.helpers.isiscb_utils as iutils
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_wikipedia_image_synopsis(authority, author_contributor_count, related_citations_count):
        """
        Method to get information from wikipedia about an authority.

        Returns:
            A triplet consisting of:
            - image of wikipedia entry
            - intro text of wikipedia entry
            - link for crediting wikipedia entry 
        """
        
        # we don’t want to show images for people that have published but are not subject of any publications
        # as the chance to get the image of a contemporary person with the same name is too high
        # So we want to make sure the ratio of authored work to work about the person is big enough
        def has_been_written_about():
            return authority.type_controlled == authority.PERSON \
                    and author_contributor_count != 0 \
                    and related_citations_count > 0 \
                    and author_contributor_count/related_citations_count > .9
        
        if authority.type_controlled == Authority.SERIAL_PUBLICATION or has_been_written_about():
            # avoid getting too many wrong images from wikipedia
            return '', '', ''
        
        wikipedia_data = WikipediaData.objects.filter(authority__id=authority.id).first()
        # if we already have wikipedia data cached and the cached data is less than
        # what is set as cache time, just use the cached data
        if wikipedia_data and (datetime.datetime.now(datetime.timezone.utc) - wikipedia_data.last_modified).days < settings.WIKIPEDIA_REFRESH_TIME:
            return wikipedia_data.img_url, wikipedia_data.intro, wikipedia_data.credit

        wikiImage = ''
        wikiIntro = ''
        wikiCredit = ''
        authorityName = authority.name
        
        # clean up the authority name to send to wikipedia
        if hasattr(authority, 'person'):
            authorityName = iutils.build_name_first_last(authorityName)
        elif authority.type_controlled == authority.CONCEPT:
            if authorityName.find(';') >= 0:
                authorityName = authorityName[:authorityName.find(';')].strip()
        elif authority.type_controlled == authority.GEOGRAPHIC_TERM:
            if authorityName.find('(') >= 0:
                authorityName = authorityName[:authorityName.find('(')].strip()

        if not authorityName:
            return wikiImage, wikiIntro, wikiCredit

        # urls to get information from wikipedia
        imgURL = settings.WIKIPEDIA_IMAGE_API_PATH.format(authorityName = authorityName)
        introURL = settings.WIKIPEDIA_INTRO_API_PATH.format(authorityName = authorityName)

        # IEXP-585: we need to provide a user agent header or Wikipedia will return a 403 
        headers = {
            'User-Agent': settings.WIKIPEDIA_EXPLORE_USERAGENT
        }
        imgJSON = None
        try:
            request_data = requests.get(imgURL, headers=headers)
            imgJSON = request_data.json()
        except Exception as e:
            logger.error(request_data)
            logger.error(imgURL)
            logger.error("Wikipedia call failed. Proceedings without Wikipedia content.")
            logger.exception(e)

        # if successful, we get something like:
        # {
        #   'batchcomplete': '', 
        #   'query': {
        #        'pages': {
        #           '29688374': {
        #               'pageid': 29688374, 
        #               'ns': 0, 
        #               'title': 'Galileo Galilei', 
        #               'original': {
        #                   'source': 'img-url', 
        #                   'width': 2964, 
        #                   'height': 3765
        #                }
        #            }
        #         }
        #     }
        # }
        # it's unclear to me why we are testing for -1 here ¯\_(ツ)_/¯
        if imgJSON and list(imgJSON['query']['pages'].items())[0][0] != '-1':
            imgPage = list(imgJSON['query']['pages'].items())[0][1]
            imgPageID = imgPage['pageid']
            wikiCredit = f'{settings.WIKIPEDIA_PAGE_PATH}{imgPageID}'
            if imgPage.get('original') and imgPage['original'].get('source'):
                wikiImage = imgPage['original']['source']

            introJSON = requests.get(introURL, headers=headers).json()
            extract = list(introJSON['query']['pages'].items())[0][1]['extract']
            # if retrieved page is a page listing possible results
            if extract.find('may refer to') < 0:
                wikiIntro = extract

        # create a new cached object
        wikipedia_data = WikipediaData(img_url=wikiImage, credit=wikiCredit, intro=wikiIntro, authority_id=authority.id)
        wikipedia_data.save()

        return wikiImage, wikiIntro, wikiCredit