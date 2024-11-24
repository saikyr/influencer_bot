import praw
import json
from datetime import datetime, timedelta
from praw.models import MoreComments
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

# Set to track already-analyzed posts
analyzed_posts = set()


def fetch_next_top_post(subreddit_name,
                        num_comments_to_fetch=5,
                        time_range_hours=24):
    """
    Fetches the next top post with the most comments within a custom time range that hasn't been analyzed yet.

    Args:
        subreddit_name (str): The subreddit to fetch posts from.
        num_comments_to_fetch (int): Number of comments per post to fetch, and number of comment replies per comment to include.
        time_range_hours (int): Time range in hours for filtering posts.

    Returns:
        dict: The top post with its comments, or None if no eligible posts are found.
    """
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

    subreddit = reddit.subreddit(subreddit_name)

    # Calculate the earliest timestamp for the time range
    current_time = datetime.utcnow()
    earliest_timestamp = current_time - timedelta(hours=time_range_hours)

    # Fetch posts from 'new' and filter by timestamp and analysis status
    eligible_posts = []
    for submission in subreddit.new(
            limit=500):  # Fetch a large number of recent posts
        created_time = datetime.utcfromtimestamp(submission.created_utc)
        if created_time < earliest_timestamp:
            break  # Stop fetching once we're past the desired time range

        # Skip already-analyzed posts
        if submission.id in analyzed_posts:
            continue

        eligible_posts.append(submission)

    # Sort posts by the number of comments in descending order
    eligible_posts.sort(key=lambda x: x.num_comments, reverse=True)

    # Return the top post with the most comments
    for submission in eligible_posts:
        # Mark the post as analyzed
        analyzed_posts.add(submission.id)

        # Fetch top-level comments
        submission.comments.replace_more(limit=0)
        sorted_comments = sorted(submission.comments,
                                 key=lambda c: c.score,
                                 reverse=True)[:num_comments_to_fetch]

        # Prepare comment data
        top_comments = []
        for comment in sorted_comments:
            if isinstance(comment, MoreComments):
                continue
            replies = sorted(comment.replies[:num_comments_to_fetch],
                             key=lambda r: r.score
                             if hasattr(r, 'score') else 0,
                             reverse=True)
            top_comments.append({
                "author":
                str(comment.author),
                "body":
                comment.body,
                "score":
                comment.score,
                "replies": [{
                    "author": str(reply.author),
                    "body": reply.body,
                    "score": reply.score
                } for reply in replies]
            })

        # Prepare and return the post data
        return {
            "title": submission.title,
            "author": str(submission.author),
            "body": submission.selftext.strip()
            or "No content (link or image post).",
            "url": submission.url,
            "num_comments": submission.num_comments,
            "score": submission.score,
            "created_utc": created_time.strftime('%Y-%m-%d %H:%M:%S'),
            "comments": top_comments
        }

    print(f"No eligible posts found in the last {time_range_hours} hours.")
    return None


def output_hierarchical_json(post_details):
    """
    Outputs the post details in a hierarchical JSON format.
    """
    if post_details:
        print(json.dumps(post_details, indent=4))
    else:
        print("No post to display.")
