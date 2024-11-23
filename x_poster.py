import tweepy
from config import (
    X_BEARER_TOKEN,
    X_API_KEY,
    X_API_SECRET,
    X_ACCESS_TOKEN,
    X_ACCESS_SECRET,
)

# Initialize the Tweepy client with all parameters
client = tweepy.Client(
    bearer_token=X_BEARER_TOKEN,
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_SECRET,
    return_type=dict,  # Ensures responses are returned as dictionaries
    wait_on_rate_limit=True,  # Automatically waits when rate limits are hit
)

def post_to_x(tweet):
    """Post a tweet using the Tweepy client and X API v2."""
    try:
        # Use Tweepy's create_tweet method to post
        response = client.create_tweet(text=tweet)
        if "data" in response:  # Check if the response contains 'data'
            print(f"Tweet posted successfully: {tweet}")
            print(f"Tweet ID: {response['data']['id']}")
        else:
            print("Failed to post tweet. No 'data' in response.")
    except tweepy.TweepyException as e:
        print(f"Error posting to X: {e}")