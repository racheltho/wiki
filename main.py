import jinja2
import os
import webapp2

from models import (Page,
                    User)
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

    # only render page if valid username cookie exists
    # otherwise redirect to signup page
    def render_secure(self, template, **kwargs):
        hashed_username = self.request.cookies.get('username')
        if hashed_username:
            username = hashing.check_secure_val(hashed_username)
            if username:
                kwargs['username'] = username
                self.write(self.render_str(template, **kwargs))
            else:
                self.redirect("/login")
        else:
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

        username_taken = User.get_by_key_name(username)
        valid_username = validation.valid_username(username)
        valid_password = validation.valid_password(password)
        valid_verify = (verify == password)
        valid_email = True
        if email:
            valid_email = validation.valid_email(email)

        kwargs['username'] = username
        kwargs['email'] = email

        if username_taken:
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
            new_user = User(key_name=username,
                            username=username,
                            password_hash_salt=password_hash_salt,
                            email=email
                            )
            new_user.put()

            # create cookie using hashed id
            hashed_cookie = hashing.make_secure_val(username)
            self.response.headers.add_header('Set-Cookie',
                                             'username={}; '
                                             'Path=/'.format(hashed_cookie))
            self.redirect("/welcome")


class LoginHandler(Handler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.render("login.html")

    def post(self):

        kwargs = {}

        username = self.request.get('username')
        password = self.request.get('password')

        kwargs['username'] = username

        user = User.get_by_key_name(username)
        if user:
            h = user.password_hash_salt
            if not hashing.valid_pw(username, password, h):
                kwargs['password_error'] = "Invalid Password"
        else:
            kwargs['username_error'] = "Invalid Username"

        error_dict = {'username_error', 'password_error'}
        if error_dict & set(kwargs.keys()) != set():
            self.render("login.html", **kwargs)
        else:
            # create cookie using hashed id
            hashed_cookie = hashing.make_secure_val(username)
            self.response.headers.add_header('Set-Cookie',
                                             'username={}; '
                                             'Path=/'.format(hashed_cookie))
            self.redirect("/welcome")


class LogoutHandler(Handler):

    def get(self):
        self.response.delete_cookie('username')
        self.redirect('/login')


class WelcomeHandler(Handler):

    def get(self):
        hashed_username = self.request.cookies.get('username')
        if hashed_username:
            username = hashing.check_secure_val(hashed_username)
            if username:
                page = Page.get_or_insert("/welcome", pagename="/welcome")
                if page.content is None:
                    page.content = ""
                self.response.headers['Content-Type'] = 'text/html'
                self.render_secure("welcome.html",
                            username=username,
                            page=page)
            else:
                self.redirect("/login")
        else:
            self.redirect("/login")


class PageHandler(Handler):

    def get(self, pagename):
        page = Page.get_by_key_name(pagename)
        if page:
            self.render_secure("page.html", page=page)
        else:
            self.redirect('/_edit' + pagename)


class EditHandler(Handler):

    def get(self, pagename):
        page = Page.get_or_insert(pagename, pagename=pagename)
        if page.content is None:
            page.content = ""
        self.render_secure("editpage.html", page=page)

    def post(self, pagename):
        content = self.request.get('content')
        page = Page.get_or_insert(pagename, pagename=pagename)
        page.content = content
        page.put()
        self.redirect(pagename)


PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'
app = webapp2.WSGIApplication([('/signup', SignupHandler),
                              ('/login', LoginHandler),
                              ('/logout', LogoutHandler),
                              ('/welcome', WelcomeHandler),
                              ('/_edit' + PAGE_RE, EditHandler),
                              (PAGE_RE, PageHandler)],
                              debug=True
                              )
