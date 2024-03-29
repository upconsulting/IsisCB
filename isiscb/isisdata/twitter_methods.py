import requests, random, re
from django.conf import settings

#recent_tweets_url = settings.TWITTER_API_RECENT_TWEETS_PATH
#twitter_bearer_token = settings.TWITTER_API_BEARER_TOKEN
tweet_url = settings.TWITTER_API_TWEET_PATH

def get_five_most_recent_tweets(api_key, user_name): 
    with requests.get(settings.TWITTER_API_RECENT_TWEETS_PATH.format(user_id=user_name), headers={"Authorization": f"Bearer {api_key}"}) as resp:
        if resp.status_code != 200:
            return []
        return resp.json()

def get_featured_tweet(api_key, user_name):
    recent_tweet_image = recent_tweet_text = recent_tweet_url = ''

    recent_tweets = get_five_most_recent_tweets(api_key, user_name)
    print(recent_tweets)
    recent_tweet_id = recent_tweets['data'][random.randint(0,len(recent_tweets['data'])-1)]['id'] if 'data' in recent_tweets and len(recent_tweets['data']) > 0 else ''

    if recent_tweet_id:
        with requests.get(tweet_url.format(tweetID=recent_tweet_id), headers={"Authorization": f"Bearer {twitter_bearer_token}"}) as resp:
            if resp.status_code == 200:
                recent_tweet = resp.json()
                recent_tweet_text = recent_tweet['data']['text']
                recent_tweet_url = recent_tweet_text[recent_tweet_text.rfind('https://'):]

                recent_tweet_text = recent_tweet_text[:recent_tweet_text.rfind('https://')]
                url_regex = re.compile(r'''((?:https://).{15})''')
                recent_tweet_text = url_regex.sub(r'<a href="\1">\1</a>', recent_tweet_text)

                if 'includes' in recent_tweet and recent_tweet['includes'] and recent_tweet['includes']['media'] and recent_tweet['includes']['media'][0]:
                    recent_tweet_image = recent_tweet['includes']['media'][0]['url']
                else:
                    recent_tweet_image = ''
    
    return recent_tweet_url, recent_tweet_text, recent_tweet_image