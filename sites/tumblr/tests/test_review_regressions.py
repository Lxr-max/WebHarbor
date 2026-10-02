import json
import app as m


def test_anonymous_ask_hides_sender_in_conversation(bob):
    with m.app.app_context():
        owner=m.User.query.filter_by(email='alice.j@test.com').one()
        blog=m.db.session.get(m.Blog,owner.blog_id)
        bid=blog.id;original=blog.ask_anon;blog.ask_anon=True;m.db.session.commit()
    bob.post('/blog/alice-j/ask',data={'body':'Anonymous privacy regression question','anon':'on'})
    with m.app.app_context():
        msg=m.Message.query.filter_by(body='Anonymous privacy regression question').one()
        conv=m.db.session.get(m.Conversation,msg.conversation_id)
        assert msg.sender_name==conv.blog_name=='anonymous'
        m.db.session.delete(msg);m.db.session.delete(conv)
        m.db.session.get(m.Blog,bid).ask_anon=original;m.db.session.commit()


def test_local_likes_agree_between_api_and_permalink(bob):
    with m.app.app_context():
        post=m.Post.query.first();pid=post.id;path=f'/blog/{post.blog.name}/{pid}'
        before=post.live_like_count()
    data=bob.post(f'/post/{pid}/like').json
    assert abs(data['like_count']-before)==1
    page=bob.get(path).text
    assert f'{data["like_count"]:,} likes' in page
    bob.post(f'/post/{pid}/like')


def test_quote_summary_contains_the_quote(alice):
    text='A useful quote for a summary regression.'
    alice.post('/new/post?type=quote',data={'quote':text,'source':'Test author','tags':'quotes'})
    with m.app.app_context():
        post=m.Post.query.filter_by(summary=text).one()
        assert json.loads(post.content)[0]['text']==text
        blog=post.blog;blog.posts_count-=1;m.db.session.delete(post);m.db.session.commit()


def test_archive_count_matches_visible_tiles(client):
    from bs4 import BeautifulSoup
    page = BeautifulSoup(client.get('/blog/nasa/archive').text, 'html.parser')
    count = len(page.select('.archive-tile'))
    assert count > 0
    assert f'{count:,} archived posts' in page.select_one('.page-sub').text


def test_imported_dark_blog_titles_remain_readable(client):
    for name in ['teaboot', 'arainthepara', 'sparth', 'cabinporn']:
        assert 'class="blog-title" style="color: #ffffff"' in client.get('/blog/'+name).text
    assert m.readable_title_color('#FFAD9D') == '#FFAD9D'
