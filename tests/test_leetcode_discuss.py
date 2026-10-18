import json

from clients import leetcode_discuss as ld


def test_search_posts_builds_urls_and_sends_post():
    seen = {}

    def fake_fetch(page, api, init=None):
        seen.update(page=page, api=api, init=init)
        node = {"uuid": "u1", "title": "T", "slug": "t-slug", "summary": "s", "createdAt": "2026-01-01", "topicId": 7}
        return json.dumps({"data": {"ugcArticleDiscussionArticles": {"edges": [{"node": node}]}}})

    posts = ld.search_posts(["anthropic", "senior"], first=3, fetch=fake_fetch)
    assert posts[0]["url"] == "https://leetcode.com/discuss/post/7/t-slug"
    body = json.loads(seen["init"]["body"])
    assert body["variables"]["keywords"] == ["anthropic", "senior"] and seen["init"]["method"] == "POST"


def test_get_post_none_when_missing():
    assert ld.get_post("1", fetch=lambda *a, **k: json.dumps({"data": {}})) is None
