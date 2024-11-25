import time
import json
from openai import OpenAI
from reddit_fetcher import fetch_next_top_post
from config import OPENAI_API_KEY
from tweepy import TweepyException
from x_poster import post_to_x

client = OpenAI(api_key=OPENAI_API_KEY)

# Prompt configuration for easy editing
PROMPT_CONFIG = {
    "subreddit": "PathOfExile2",
    "focus": (
        "highlighting the latest updates, gameplay reveals, community builds, and the collective sentiment for Path of Exile 2."
    ),
    "role_description": (
        "You are a seasoned Path of Exile player, well-versed in the game's mechanics, builds, and community culture. "
        "Your goal is to generate concise and insightful tweets that resonate with the gaming community. "
        "The tone should reflect genuine excitement and expertise, similar to how an active player would engage with fellow fans."
    ),
    "tweet_instructions": (
        "Write a tweet aimed at the Path of Exile community on social media. "
        "Use natural, conversational gamer language that avoids exaggeration or hype. "
        "Keep it straightforward, concise, and community-focused. "
        "Avoid emojis, excessive punctuation (e.g., multiple exclamation marks), or generic phrases. "
        "Incorporate #PoE2 or #PathOfExile2 naturally, ensuring the tweet stands alone without requiring Reddit context. "
        "Limit the tweet to 280 characters or less."
    ),
    "model": "gpt-4o"
}


def analyze_post_with_openai(post):
    """
    Uses OpenAI's chat completions API to analyze a Reddit post and its comments,
    and generates a structured analysis and a tweet.
    """
    try:
        print("\n### Full Context Sent to AI ###")
        # Output the full JSON data for context
        print(json.dumps(post, indent=4))
        print("##################################\n")

        # Build the prompt dynamically from the configuration
        prompt = f"""
            Analyze the following r/{PROMPT_CONFIG['subreddit']} post and comments to generate a concise tweet with all necessary context:

            - Focus on {PROMPT_CONFIG['focus']}.
            - {PROMPT_CONFIG['tweet_instructions']}
            - Use the following structure exactly:

            ### Analysis ###
            <A detailed analysis of the post and its comments, focusing on {PROMPT_CONFIG['focus']}.>

            ### Tweet ###
            <The generated tweet.>

            {json.dumps(post, indent=4)}
        """

        # Send the prompt to OpenAI
        completion = client.chat.completions.create(
            model=PROMPT_CONFIG["model"],
            messages=[{
                "role": "system",
                "content": PROMPT_CONFIG["role_description"]
            }, {
                "role": "user",
                "content": prompt
            }]
        )
        reponse = completion.choices[0].message.content.strip()

        print("\n### AI Response ###")
        print(reponse)
        print("\n##################################\n")

        # Extract and clean up the tweet
        tweet_start = reponse.find("### Tweet ###")
        if tweet_start != -1:
            # Extract from the start of "### Tweet ###" to the end
            tweet_section = reponse[tweet_start:].strip()
            # Find the line after "### Tweet ###"
            lines = tweet_section.split("\n")
            for line in lines[1:]:  # Skip the first line (the header)
                tweet = line.strip()
                if tweet:  # Return the first non-empty line
                    return tweet

            raise ValueError("No valid tweet found after ### Tweet ###.")
        else:
            raise ValueError("Missing '### Tweet ###' delimiter in response.")
    except Exception as e:
        print(f"Error generating tweet: {e}")
        return None


if __name__ == "__main__":
    subreddit_name = PROMPT_CONFIG["subreddit"]
    num_comments_to_fetch = 5  # Number of comments per post to include
    num_replies_to_fetch = 3  # Number of replies to comments to recursively fetch
    depth_limit = 3  # Depth limit of comment threads
    time_range_hours = 6  # Time frame of posts to consider
    wait_time = 3600  # Interval between cycles in seconds

    while True:
        # Fetch the next top post that hasn't been analyzed
        post = fetch_next_top_post(subreddit_name=subreddit_name,
                                   num_comments_to_fetch=num_comments_to_fetch,
                                   num_replies_to_fetch=num_replies_to_fetch,
                                   depth_limit=depth_limit,
                                   time_range_hours=time_range_hours)

        if post:
            print(f"Analyzing Post: {post['title']}\n")
            tweet = analyze_post_with_openai(post)
            if tweet:
                print("\n### Generated Tweet ###")
                print(tweet)
                print("\n##################################")
                try:
                    post_to_x(tweet)  # Post the generated tweet
                except TweepyException as e:
                    print(f"Failed to post tweet: {e}")
            else:
                print("Failed to generate a tweet.\n")
        else:
            print("No new posts available for analysis.\n")

        print(
            f"Waiting for {wait_time} seconds before fetching the next post...\n")
        time.sleep(wait_time)
