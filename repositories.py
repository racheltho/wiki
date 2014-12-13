from datetime import datetime
from google.appengine.api import memcache
from google.appengine.ext import db

from models import Page
import hashing


def age_set(key, value):
    save_time = datetime.now()
    memcache.set(key, (save_time, value))


def age_get(key):
    results = memcache.get(key)
    if results:
        save_time, value = results
        age = (datetime.now() - save_time).total_seconds()
    else:
        value, age = None, 0
    return value, age


class UserRepository():

    @classmethod
    def user_id_from_username_password(cls, username, password):
        user = db.GqlQuery("SELECT * FROM User "
                           "WHERE username = '{}'".format(username)).get()
        if user:
            h = user.password_hash_salt
            if hashing.valid_pw(username, password, h):
                return user.key().id()

    @classmethod
    def username_not_taken(cls, username):
        query = db.GqlQuery("SELECT * FROM User "
                            "WHERE username = '{}'".format(username))
        if not query.get():
            return True


class PageRepository():

    @classmethod
    def get_page_by_name(cls, pagename, create_if_none=False):
            page = db.GqlQuery("SELECT * FROM Page WHERE "
                               "pagename = '{}'".format(pagename)).get()
            if create_if_none and not page:
                page = Page(pagename=pagename, content="")
            return page
