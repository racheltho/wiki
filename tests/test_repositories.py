import time
from datetime import datetime
import unittest
from google.appengine.ext import testbed

from hashing import make_pw_hash
from repositories import UserRepository
from models import User
from main import get_page_by_name, Page


class PageTestCase(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_get_existing(self):
        page = Page(pagename="/testpage", content="test_content")
        page.put()
        result = get_page_by_name("/testpage")
        assert result.content == "test_content"

    def test_get_new(self):
        result = get_page_by_name("/testpage")
        assert result is None
        result = get_page_by_name("/testpage", create_if_none=True)
        assert result.pagename == "/testpage"
        assert result.content == ""


class UserTestCase(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

    def teardown(self):
        self.testbed.deactivate()

    def test_get_username(self):
        username = "test_user"
        password = "password"
        password_hash_salt = make_pw_hash(username, password)
        user = User(username=username, password_hash_salt=password_hash_salt)
        assert UserRepository.username_not_taken(username)
        user.put()
        assert not UserRepository.username_not_taken(username)
        user_id = UserRepository.user_id_from_username_password(username, password)
        assert user_id == user.key().id()
