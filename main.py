
import os
import jinja2
import webapp2
import re
from google.appengine.ext import db

# Regex
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile(r"^.{3,20}$")

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),autoescape = True)
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)
class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)
	def render_str(self, template, **params):
		# **params = extra paramaters
		t = jinja_env.get_template(template)
		# load and render template
		return t.render(params)
	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

class BlogHandler(Handler):
	def render_front(self, subject="", content="", error=""):
		blogs = db.GqlQuery("SELECT * FROM Blog ORDER BY created DESC")
		self.render("blog.html", subject=subject, content=content, error=error, blogs=blogs)
	def get(self):
		self.render_front()

def render_post(response, blog):
    response.out.write('<b>' + blog.subject + '</b><br>')
    response.out.write(blog.content)

# Blog #
def blog_key(name='default'):
	return db.Key.from_path('blogs',name)

class Blog(db.Model):
	subject = db.StringProperty(required=True)
	content = db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add = True)

	def render(self):
		self._render_text = self.content.replace('\n', '<br>')
		return render_str("post.html", a=self)
class BlogFront(BlogHandler):
	def get(self):
		# posts = db.GqlQuery("select * from Post order by created desc limit 10")
		blogs = Blog.all().order('-created')
		self.render('blog.html', blogs=blogs)

class PostPage(BlogHandler):
	def get(self, blog_id):
		key = db.Key.from_path('Blog', int(blog_id), parent=blog_key())
		blog = db.get(key)
		if not blog:
			self.error(404)
			return
		self.render("permalink.html", blog = blog)

class NewPost(BlogHandler):
	def get(self):
		self.render("newpost.html")
	def post(self):
		subject = self.request.get("subject")
		content = self.request.get("content")
		if subject and content:
			a = Blog(parent=blog_key(), subject=subject, content=content)
			a.put()
			self.redirect('/blog/%s' % str(a.key().id()))
		else:
			error="subject and content please!"
			self.render("newpost.html", subject=subject, content=content, error=error)

app = webapp2.WSGIApplication([('/blog', BlogHandler),
							('/blog/?', BlogFront),
							('/blog/([0-9]+)', PostPage),
							('/blog/newpost', NewPost)
], debug=True)