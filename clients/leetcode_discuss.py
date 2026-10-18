"""Search and read LeetCode Discuss posts through the user's signed-in Arc session.

Uses LeetCode's own GraphQL endpoint from inside a leetcode.com tab, so the user's cookies
apply and no credentials are handled here. Keep call volume low (a handful per company).
"""
from __future__ import annotations

import json
from typing import Callable, List, Optional

from clients.arc_browser import fetch_json_via_page

PAGE_URL = "https://leetcode.com/discuss/"
API_URL = "https://leetcode.com/graphql"

SEARCH_QUERY = (
    "query q($orderBy: ArticleOrderByEnum, $keywords: [String]!, $skip: Int, $first: Int) {"
    " ugcArticleDiscussionArticles(orderBy: $orderBy, keywords: $keywords, skip: $skip, first: $first) {"
    " totalNum edges { node { uuid title slug summary createdAt topicId } } } }"
)
POST_QUERY = (
    "query p($topicId: ID!) { ugcArticleDiscussionArticle(topicId: $topicId) {"
    " uuid title content createdAt topicId } }"
)

Fetch = Callable[..., str]


def _post(query: str, variables: dict, fetch: Fetch = fetch_json_via_page) -> dict:
    body = json.dumps({"query": query, "variables": variables})
    raw = fetch(PAGE_URL, API_URL, init={"method": "POST", "headers": {"content-type": "application/json"}, "body": body})
    return json.loads(raw)


def search_posts(keywords: List[str], first: int = 10, order_by: str = "MOST_RELEVANT",
                 fetch: Fetch = fetch_json_via_page) -> List[dict]:
    """Return posts as dicts (uuid, title, slug, summary, createdAt, url), most relevant first."""
    data = _post(SEARCH_QUERY, {"orderBy": order_by, "keywords": keywords, "skip": 0, "first": first}, fetch)
    edges = data["data"]["ugcArticleDiscussionArticles"]["edges"]
    out = []
    for e in edges:
        n = e["node"]
        n["url"] = f"https://leetcode.com/discuss/post/{n['topicId']}/{n['slug']}"
        out.append(n)
    return out


def get_post(topic_id: str, fetch: Fetch = fetch_json_via_page) -> Optional[dict]:
    """Return a post including its body text, or None if unavailable."""
    return _post(POST_QUERY, {"topicId": str(topic_id)}, fetch)["data"].get("ugcArticleDiscussionArticle")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(prog="leetcode_discuss")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("keywords", nargs="+"); s.add_argument("--first", type=int, default=10)
    g = sub.add_parser("post"); g.add_argument("topic_id", help="topicId from a search result URL")
    a = ap.parse_args()
    if a.cmd == "search":
        for p in search_posts(a.keywords, a.first):
            print(f"{p['createdAt'][:10]}\t{p['uuid']}\t{p['title']}\t{p['url']}\n    {p['summary'][:160]}")
    else:
        post = get_post(a.topic_id)
        print(json.dumps(post, indent=1)[:20000] if post else "NOT AVAILABLE")
