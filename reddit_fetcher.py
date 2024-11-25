import praw
import json
from datetime import datetime, timedelta
from praw.models import MoreComments
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

# Set to track already-analyzed posts
analyzed_posts = set()


def fetch_comment_replies(comment, num_replies, depth, depth_limit):
    """
    Recursively fetches replies for a comment up to a given depth limit.

    Args:
        comment: A PRAW comment object.
        num_replies (int): Number of replies to fetch for each comment.
        depth (int): Current depth in the comment thread.
        depth_limit (int): Maximum depth of the thread to fetch.

    Returns:
        list: A list of dictionaries representing replies.
    """
    if depth >= depth_limit:
        return []

    replies = []
    for reply in sorted(comment.replies, key=lambda r: r.score if hasattr(r, 'score') else 0, reverse=True)[:num_replies]:
        if isinstance(reply, MoreComments):
            continue
        replies.append({
            "author": str(reply.author),
            "body": reply.body,
            "score": reply.score,
            "replies": fetch_comment_replies(reply, num_replies, depth + 1, depth_limit)
        })
    return replies


def fetch_next_top_post(subreddit_name,
                        num_comments_to_fetch=5,
                        num_replies_to_fetch=3,
                        depth_limit=3,
                        time_range_hours=24):
    """
    Fetches the next top post with the most comments within a custom time range that hasn't been analyzed yet.

    Args:
        subreddit_name (str): The subreddit to fetch posts from.
        num_comments_to_fetch (int): Number of top-level comments to fetch.
        num_replies_to_fetch (int): Number of replies to fetch per comment.
        depth_limit (int): Maximum depth for fetching comment threads.
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
    # Fetch a large number of recent posts
    for submission in subreddit.new(limit=500):
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
            top_comments.append({
                "author": str(comment.author),
                "body": comment.body,
                "score": comment.score,
                "replies": fetch_comment_replies(comment, num_replies_to_fetch, 1, depth_limit)
            })

        # Prepare and return the post data
        return {
            "title": submission.title,
            "author": str(submission.author),
            "body": submission.selftext.strip() or "No content (link or image post).",
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
