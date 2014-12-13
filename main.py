import jinja2
import os
import webapp2

from google.appengine.ext import db

from models import User
from repositories import (UserRepository,
                          PageRepository)
import hashing
import validation


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


def format_datetime(datetime):
    return datetime.strftime("%c")


def allow_linebreaks(content):
    return content.replace("\n", "<br>")

jinja_env.filters['datetime'] = format_datetime
jinja_env.filters['linebreaks'] = allow_linebreaks


class Handler(webapp2.RequestHandler):

    def write(self, *args, **kwargs):
        self.response.out.write(*args, **kwargs)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kwargs):
        self.write(self.render_str(template, **kwargs))

    # only render page if valid user_id cookie exists
    # otherwise redirect to signup page
    def render_secure(self, template, **kwargs):
        hashed_user_id = self.request.cookies.get('user_id')
        try:
            if hashed_user_id and hashing.check_secure_val(hashed_user_id):
                self.write(self.render_str(template, **kwargs))
            else:
                self.redirect("/login")
        except ValueError:
            self.redirect("/login")


class SignupHandler(Handler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.render("signup.html")

    def post(self):

        kwargs = {}

        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')

        new_username = UserRepository.username_not_taken(username)
        valid_username = validation.valid_username(username)
        valid_password = validation.valid_password(password)
        valid_verify = (verify == password)
        valid_email = True
        if email:
            valid_email = validation.valid_email(email)

        kwargs['username'] = username
        kwargs['email'] = email

        if not new_username:
            kwargs['username_exists'] = "That user already exists"
        if not valid_username:
            kwargs['username_error'] = "That's not a valid username"
        if not valid_password:
            kwargs['password_error'] = "That wasn't a valid password"
        if not valid_verify:
            kwargs['verify_error'] = "Your passwords didn't match"
        if not valid_email:
            kwargs['email_error'] = "That's not a valid email"

        error_dict = {'username_exists',
                      'username_error',
                      'password_error',
                      'verify_error',
                      'email_error'
                      }

        # check if any error messages are in kwargs
        if error_dict & set(kwargs.keys()) != set():
            self.render("signup.html", **kwargs)
        else:
            # salt and hash password
            password_hash_salt = hashing.make_pw_hash(username, password)

            # create new user
            new_user = User(username=username,
                            password_hash_salt=password_hash_salt,
                            email=email
                            )
            # use ip address to find lat/lon
            n = new_user.put()
            user_id = n.id()

            # create cookie using hashed id
            hashed_cookie = hashing.make_secure_val(user_id)
            self.response.headers.add_header('Set-Cookie',
                                             'user_id={}; '
                                             'Path=/'.format(hashed_cookie))
            self.redirect("/")


class LoginHandler(Handler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.render("login.html")

    def post(self):

        kwargs = {}

        username = self.request.get('username')
        password = self.request.get('password')

        user_id = UserRepository.user_id_from_username_password(username,
                                                                password)

        kwargs['username'] = username

        if not user_id:
            kwargs['invalid'] = "Invalid Login"
            self.render("login.html", **kwargs)
        else:
            # create cookie useing hashed id
            hashed_cookie = hashing.make_secure_val(user_id)
            self.response.headers.add_header('Set-Cookie',
                                             'user_id={}; '
                                             'Path=/'.format(hashed_cookie))
            self.redirect("/")


class LogoutHandler(Handler):

    def get(self):
        self.response.delete_cookie('user_id')
        self.redirect('/login')


class WelcomeHandler(Handler):

    def get(self):
        hashed_user_id = self.request.cookies.get('user_id')
        if hashed_user_id:
            user_id = hashing.check_secure_val(hashed_user_id)
            try:
                user = User.get_by_id(int(user_id))
                self.response.headers['Content-Type'] = 'text/html'
                users = db.GqlQuery("SELECT * FROM User ")
                users = list(users)
                self.render("welcome.html", username=user.username)
            except TypeError:
                self.redirect("/login")
        else:
            self.redirect("/login")


class PageHandler(Handler):

    def get(self, pagename):
        page = PageRepository.get_page_by_name(pagename)
        if page:
            self.render("page.html", page=page)
        else:
            self.redirect('/_edit' + pagename)


class EditHandler(Handler):

    def get(self, pagename):
        page = PageRepository.get_page_by_name(pagename, create_if_none=True)
        self.render("editpage.html", page=page)

    def post(self, pagename):
        content = self.request.get('content')
        page = PageRepository.get_page_by_name(pagename, create_if_none=True)
        page.content = content
        page.put()
        self.redirect(pagename)


PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'
app = webapp2.WSGIApplication([('/signup', SignupHandler),
                              ('/login', LoginHandler),
                              ('/logout', LogoutHandler),
                              ('/_edit' + PAGE_RE, EditHandler),
                              (PAGE_RE, PageHandler),
                              ('/', WelcomeHandler)],
                              debug=True
                              )
