#!/usr/bin/env python3

' url handlers '

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post
from apis import Page, APIValueError, APIPermissionError, APIResourceNotFoundError

from models import User, Shopping, next_id
from config import configs

COOKIE_NAME = 'mfsession'
_COOKIE_KEY = configs.session.secret

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

def user2cookie(user, max_age):
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

@asyncio.coroutine
def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@get('/')
def index(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Shopping.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        shoppings = []
    else:
        shoppings = yield from Shopping.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'shoppings.html',
        'page': page,
        'shoppings': shoppings
    }

@get('/shopping/{id}')
def get_shopping(id):
    shopping = yield from Shopping.find(id)
    shopping.html_content = markdown2.markdown(shopping.content)
    return {
        '__template__': 'shopping.html',
        'shopping': shopping
    }

@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

@post('/api/authenticate')
def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = yield from User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out.')
    return r

@get('/manage/')
def manage():
    return 'redirect:/manage/shoppings'


@get('/manage/shoppings')
def manage_shoppings(*, page='1'):
    return {
        '__template__': 'manage_shoppings.html',
        'page_index': get_page_index(page)
    }

@get('/manage/shoppings/create')
def manage_create_shopping():
    return {
        '__template__': 'manage_shopping_edit.html',
        'id': '',
        'action': '/api/shoppings'
    }

@get('/manage/shoppings/edit')
def manage_edit_shopping(*, id):
    return {
        '__template__': 'manage_shopping_edit.html',
        'id': id,
        'action': '/api/shoppings/%s' % id
    }

@get('/manage/users')
def manage_users(*, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }

@get('/api/users')
def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = yield from User.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, users=())
    users = yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = yield from User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    yield from user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/api/shoppings')
def api_shoppings(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Shopping.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, shoppings=())
    shoppings = yield from Shopping.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, shoppings=shoppings)

@get('/api/shoppings/{id}')
def api_get_shopping(*, id):
    shopping = yield from Shopping.find(id)
    return shopping

@post('/api/shoppings')
def api_create_shopping(request, *, name, summary, content, price):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    if not price or not price.strip():
        raise APIValueError('price', 'price cannot be empty.')

    shopping = Shopping(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip(), price=price.strip())
    yield from shopping.save()
    return shopping

@post('/api/shoppings/{id}')
def api_update_shopping(id, request, *, name, summary, content, price):
    check_admin(request)
    shopping = yield from Shopping.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    if not price or not price.strip():
        raise APIValueError('price', 'price cannot be empty.')

    shopping.name = name.strip()
    shopping.summary = summary.strip()
    shopping.content = content.strip()
    shopping.price = price.strip()
    yield from shopping.update()
    return shopping

@post('/api/shoppings/{id}/delete')
def api_delete_shopping(request, *, id):
    check_admin(request)
    shopping = yield from Shopping.find(id)
    yield from shopping.remove()
    return dict(id=id)