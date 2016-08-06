import webapp2
from google.appengine.ext import db
import time

from views import templates_dir, jinja_env, render_str, render_post
from models import User, Post, Comment, users_key, blog_key
from validations import secret, make_secure_val, check_secure_val, valid_username, valid_password, valid_email, make_salt, make_pw_hash, valid_pw

# Main Handler


class BlogHandler(webapp2.RequestHandler):

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))


class BlogFront(BlogHandler):

    def get(self):
        posts = Post.all().order('-created')
        comments = Comment.all()
        self.render('front.html', posts=posts, comments=comments)


class Error(BlogHandler):
'''
    Some pages redirect to an error page that displays their current error
    will remove this feature as I'd rather have errors displayed directly
    on page without a new page
'''

    def get(self):
        self.render('error.html', error=error)

# Posts operations


class PostPage(BlogHandler):

    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        self.render("permalink.html", post=post)


class NewPost(BlogHandler):

    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect('/login')

        subject = self.request.get('subject')
        content = self.request.get('content')
        author = self.request.get('author')
        comment = self.request.get('comment')
        if subject and content:
            p = Post(parent=blog_key(), subject=subject,
                     content=content, author=author, comment=comment, likes=0, liked_by=[])
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))
        else:
            error = "subject and content, please!"
            self.render("newpost.html", subject=subject,
                        content=content, error=error, comment=comment)


class DeletePost(BlogHandler):
    '''
        user can delete a post.
    '''

    def get(self, post_id):
        if not self.user:
            self.redirect('/login')
        else:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            author = post.author
            loggedUser = self.user.name

            if author == loggedUser:
                key = db.Key.from_path('Post', int(post_id), parent=blog_key())
                post = db.get(key)
                post.delete()
                self.render("delete.html")
            else:
                self.redirect("/")


class LikePost(BlogHandler):

    def get(self, post_id):
        if not self.user:
            self.redirect('/login')
        else:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            author = post.author
            logged_user = self.user.name

            if author == logged_user:
                error = "You can't like your own post"
                self.render('error.html', error=error)

            elif logged_user in post.liked_by:
                error = "You can only like this once!"
                self.render('error.html', error=error)
            else:
                post.likes += 1
                post.liked_by.append(logged_user)
                post.put()
                self.redirect("/blog")


class EditPost(BlogHandler):

    def get(self, post_id):
        if not self.user:
            self.redirect('/login')
        else:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)
            author = post.author
            loggedUser = self.user.name

            if author == loggedUser:
                key = db.Key.from_path('Post', int(post_id), parent=blog_key())
                post = db.get(key)
                error = ""
                self.render("edit.html", subject=post.subject,
                            content=post.content, error=error)
            else:
                error = "you can't edit this"
                self.redirect("/error", error=error)

    def post(self, post_id):
        if not self.user:
            self.redirect("/login")
        else:
            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            p = db.get(key)
            p.subject = self.request.get('subject')
            p.content = self.request.get('content')
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))

# All Comment operations


class NewComment(BlogHandler):

    def get(self, post_id):
        if not self.user:
            self.redirect("/login")
            return
        post = Post.get_by_id(int(post_id), parent=blog_key())
        subject = post.subject
        content = post.content
        comment = self.request.get('comment')
        author = self.request.get('author')
        self.render("comments.html", subject=subject, content=content,
                    author=author, comment=comment, pkey=post.key())

    def post(self, post_id):

        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return
        if not self.user:
            self.redirect('login')
        author = self.request.get('author')
        comment = self.request.get('comment')
        if comment:
            c = Comment(comment=comment, post=post_id,
                        author=author, parent=self.user.key())
            c.put()
            self.redirect('/blog/%s' % str(post_id))
        else:
            self.render("permalink.html", post=post,
                        content=content, author=author, error=error)


class EditComment(BlogHandler):

    def get(self, post_id, comment_id):
        if not self.user:
            self.redirect('/login')
        else:
            post = Post.get_by_id(int(post_id), parent=blog_key())
            subject = post.subject
            content = post.content
            comment = self.request.get('comment')
            author = self.request.get('author')
            self.render("commentpage.html", subject=subject, content=content,
                        author=author, comment=comment, pkey=post.key())

    def post(self, post_id, comment_id):
        c = Comment.get_by_id(int(comment_id), parent=self.user.key())
        if c.parent().key().id() == self.user.key().id():
            c.comment = self.request.get('comment')
            c.put()
            self.redirect('/blog/%s' % str(post_id))


class DeleteComment(BlogHandler):

    def get(self, post_id, comment_id):
        error = ""
        post = Post.get_by_id(int(post_id), parent=blog_key())
        comment = Comment.get_by_id(int(comment_id), parent=self.user.key())
        if comment:
            comment.delete()
            self.redirect('/blog/%s' % str(post_id))
        else:
            error = "Please only delete your own comment"
            self.render('permalink.html', error=error, post=post)

# User methods


class Signup(BlogHandler):

    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username=self.username,
                      email=self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError


class Unit2Signup(Signup):

    def done(self):
        self.redirect('/unit2/welcome?username=' + self.username)


class Register(Signup):

    def done(self):
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username=msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/blog')


class Login(BlogHandler):

    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/blog')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error=msg)


class Logout(BlogHandler):

    def get(self):
        self.logout()
        self.redirect('/blog')


class Unit3Welcome(BlogHandler):

    def get(self):
        if self.user:
            self.render('welcome.html', username=self.user.name)
        else:
            self.redirect('/signup')

# custom 404 page


class MissingPage(BlogHandler):

    def get(self):
        self.response.set_status(404)
        self.render('404.html')


class Welcome(BlogHandler):

    def get(self):
        username = self.request.get('username')
        if valid_username(username):
            self.render('welcome.html', username=username)
        else:
            self.redirect('/unit2/signup')

# routes
app = webapp2.WSGIApplication([('/', BlogFront),
                               ('/unit2/signup', Unit2Signup),
                               ('/unit2/welcome', Welcome),
                               ('/blog/([0-9]+)/newcomment', NewComment),
                               ('/blog/?', BlogFront),
                               ('/blog/([0-9]+)', PostPage),
                               ('/blog/([0-9]+)/edit', EditPost),
                               ('/blog/([0-9]+)/like', LikePost),
                               ('/blog/([0-9]+)/deletecomment/([0-9]+)',
                                DeleteComment),
                               ('/blog/([0-9]+)/editcomment/([0-9]+)',
                                EditComment),
                               ('/blog/([0-9]+)/delete', DeletePost),
                               ('/error', Error),
                               ('/blog/newpost', NewPost),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/unit3/welcome', Unit3Welcome),
                               ('/.*', MissingPage)
                               ],
                              debug=True)
