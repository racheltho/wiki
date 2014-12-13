from google.appengine.ext import db


class Page(db.Model):
    pagename = db.StringProperty(required=True)
    content = db.TextProperty()


class User(db.Model):
    username = db.StringProperty(required=True)
    password_hash_salt = db.StringProperty(required=True)
    email = db.StringProperty()
