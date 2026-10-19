from clients import sheet_links as sl

PAGE = (
    '...[7,42,\\"maximum-consecutive-ones\\",\\"item\\",\\"practice\\",\\"Maximum Consecutive Ones\\",\\"3 min\\",'
    '{\\"layoutType\\":\\"practice\\",\\"itemSlug\\":\\"maximum-consecutive-ones\\",\\"category\\":\\"fundamentals\\"},'
    '\\"https://youtu.be/bYWLJb3vCWY?t=1124\\",\\"/blogs/data-structure-and-algorithm/mco\\",'
    '\\"https://leetcode.com/problems/max-consecutive-ones/\\",false,\\"unsolved\\",[\\"1\\"]],'
    '[1,17136,\\"breaking-the-myth\\",\\"item\\",\\"learning\\",\\"Breaking The Myth\\",'
    '{\\"layoutType\\":\\"learning\\",\\"itemSlug\\":\\"breaking-the-myth\\"},\\"https://youtu.be/qbw\\",'
    '\\"/blogs/data-structure-and-algorithm/btm\\",true,\\"unsolved\\"],'
    '[7,9,\\"no-video\\",\\"item\\",\\"practice\\",\\"No Video\\",\\"1 min\\",{\\"itemSlug\\":\\"no-video\\"},null,null,null,false]...'
)


def test_parse_links_handles_problems_lessons_and_gaps():
    rows = sl.parse_links(PAGE)
    assert rows[42]["youtube"] == "https://youtu.be/bYWLJb3vCWY?t=1124"
    assert rows[42]["article"] == "https://takeuforward.org/blogs/data-structure-and-algorithm/mco"
    assert rows[42]["leetcode"] == "https://leetcode.com/problems/max-consecutive-ones/" and rows[42]["duration"] == "3 min"
    assert rows[17136]["leetcode"] is None and rows[17136]["youtube"] == "https://youtu.be/qbw"
    assert rows[9]["youtube"] is None and rows[9]["article"] is None
