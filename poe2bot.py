import praw
import time
from openai import OpenAI
from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    OPENAI_API_KEY,
)
from x_poster import post_to_x

# Load OpenAI client with the API key
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize the Reddit client
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
)

# Track already analyzed posts to avoid repetition
analyzed_posts = set()

def fetch_reddit_data(subreddit_name, post_limit=20, comment_limit=20):
    """
    Fetches newest text-based posts from the last 2 hours with the most comments from a given subreddit.
    """
    print(f"Fetching up to {post_limit} posts from subreddit: {subreddit_name}")
    subreddit = reddit.subreddit(subreddit_name)
    posts = []

    current_time = time.time()  # Current time in seconds since epoch

    for submission in subreddit.new(limit=post_limit):
        # Check if the post is within the last 2 hours
        post_age = current_time - submission.created_utc  # Age in seconds
        if post_age <= 7200 and submission.id not in analyzed_posts and submission.selftext.strip():  # 7200 seconds = 2 hours
            submission.comments.replace_more(limit=0)
            top_comments = [
                comment.body for comment in submission.comments[:comment_limit]
                if comment.author
                and "bot" not in comment.author.name.lower()
                and comment.author.name.lower() != "automoderator"
            ]
            posts.append({
                "id": submission.id,
                "title": submission.title,
                "content": submission.selftext,
                "top_comments": top_comments,
                "comment_count": submission.num_comments,
                "url": submission.url,
            })

    print(f"Fetched {len(posts)} eligible posts from the last 2 hours.\n")
    return posts

def select_post_with_most_comments(posts):
    """
    Selects the post with the most comments.
    """
    if not posts:
        return None

    most_commented_post = max(posts, key=lambda post: post["comment_count"])
    print(f"Selected post with the most comments ({most_commented_post['comment_count']}): {most_commented_post['title']}\n")
    return most_commented_post

def analyze_post_with_openai(post):
    """
    Uses OpenAI's chat completions API to analyze a Reddit post and its comments,
    and generates a structured analysis and a tweet.
    """
    try:
        print("\n### Full Context Sent to AI ###")
        print(f"Title: {post['title']}")
        print(f"Content: {post['content']}")
        print(f"Top Comments: {'; '.join(post['top_comments'])}")
        print(f"URL: {post['url']}")
        print("##################################\n")

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an ARPG fan excited about Path of Exile 2. Your tweets are concise, insightful, and conversational, like a real gamer sharing their opinions on Twitter. Tweets must include all necessary context without relying on external references (e.g., 'that Reddit post') and should incorporate #PoE2 naturally. Avoid leading hashtags or excessive punctuation, and make the tweets feel standalone and engaging."
                },
                {
                    "role": "user",
                    "content": f"""
                    Analyze the following Path of Exile 2 post and comments to generate a concise tweet with all necessary context:
                    
                    - Focus on mechanics, builds, or community sentiment revealed in the post and comments.
                    - Ensure the tweet feels like a standalone statement or discussion starter, not reliant on the post itself.
                    - Include #PoE2 naturally where it fits.
                    - Use the following structure exactly:

                    ### Analysis ###
                    <A detailed analysis of the post’s relevance, focusing on builds, mechanics, or community sentiment.>

                    ### Tweet ###
                    <A standalone, engaging tweet with personality, incorporating #PoE2 naturally. Avoid leading hashtags or punctuation.>

                    Title: {post['title']}
                    Content: {post['content']}
                    Comments: {post['top_comments']}
                    URL: {post['url']}
                    """
                }
            ]
        )
        analysis = completion.choices[0].message.content.strip()

        print("\n### AI Analysis ###")
        print(analysis)
        print("\n##################################\n")

        # Extract and clean up the tweet
        tweet_start = analysis.find("### Tweet ###")
        if tweet_start != -1:
            tweet = analysis[tweet_start + 12:].strip()
            
            # Ensure the tweet is valid and clean
            tweet = tweet.lstrip("#").strip()  # Remove leading hashtags or whitespace
            if not tweet[0].isalnum():  # Ensure it starts with a word/letter
                tweet = tweet.lstrip(".!?,").strip()

            if len(tweet) > 0:
                return tweet
            else:
                raise ValueError("Tweet content is empty or invalid.")
        else:
            raise ValueError("Missing '### Tweet ###' delimiter in response.")
    except Exception as e:
        print(f"Error generating tweet: {e}")
        return None

if __name__ == "__main__":
    subreddit_name = "PathOfExile2"
    post_limit = 20  # Number of posts to fetch
    comment_limit = 20  # Number of comments per post to fetch

    while True:
        posts = fetch_reddit_data(subreddit_name, post_limit=post_limit, comment_limit=comment_limit)
        
        if posts:
            selected_post = select_post_with_most_comments(posts)
            if selected_post:
                analyzed_posts.add(selected_post["id"])
                print(f"Selected Post: {selected_post['title']}\n")
                tweet = analyze_post_with_openai(selected_post)
                if tweet:
                    print("\n### Generated Tweet ###")
                    print(tweet)
                    print("\n##################################")
                    # Post the tweet to X
                    post_to_x(tweet)
                else:
                    print("Failed to generate a tweet.\n")
            else:
                print("No eligible posts found.\n")
        else:
            print("No eligible posts found.\n")

        print("Waiting for 1 hour before fetching the next post...\n")
        time.sleep(3600)  # Wait for 1 hour