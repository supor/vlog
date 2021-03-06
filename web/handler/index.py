#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/14 17:19:47
#   Desc    :
#
import os

from MySQLdb import OperationalError
from tornado.web import StaticFileHandler

from config import STATIC_PATH as STATIC_ROOT, UPLOAD_PATH, THEME, DEBUG
from core.util import md5
from core.web import BaseHandler

from web.logic import Logic


class WebHandler(BaseHandler):
    """ web前台handler基类 """
    #TODO 可配置的主题
    template_path = os.path.join(BaseHandler.template_path, THEME)
    option = Logic.option
    def initialize(self):
        self.pagesize = self.cache.get("pagesize")
        if not self.pagesize:
            pagesize = self.option.pagesize
            self.pagesize = pagesize if pagesize else 10
            self.cache.set("pagesize", self.pagesize)

    def get_error_html(self, status_code = 500, **kwargs):
        kwargs['status_code'] = status_code
        errpath = os.path.join(self.template_path,
                               "{0}.jinja".format(status_code))
        if not DEBUG and kwargs.has_key("exception"):
            kwargs["exception"] = None
        if os.path.exists(errpath):
            self.render("{0}.jinja".format(status_code), **kwargs)
        else:
            self.render("error.jinja", **kwargs)

    def prepare(self):
        super(WebHandler, self).prepare()
        try:
            admin = Logic.user.check_has_admin()
            if not admin:
                self.redirect('/install/')
        except:
            self.redirect('/install/')

    def render(self, template_path, **kwargs):
        tags = Logic.tag.get_tags()
        categories = Logic.category.get_categories()
        pl = Logic.post
        kwargs['comments'] = Logic.comment.get_last_comments()
        kwargs['tags'] = tags.get('data')
        kwargs['new'] = pl.get_new()
        kwargs['months'] = pl.get_months()
        kwargs['categories'] = categories.get('data')
        kwargs['SITE_TITLE'] = self.option.site_title
        kwargs['SITE_SUB_TITLE'] = self.option.sub_title
        kwargs["links"] = Logic.link.get_all_links()
        if not kwargs.has_key("description"):
            kwargs['description'] = self.option.description
        if not kwargs.has_key("keywords"):
            kwargs['keywords'] = self.option.keywords
        kwargs['page'] = Logic.page.get_all_pages()
        kwargs['uid'] = self.uid
        kwargs['username'] = self.username
        self.logger.debug("%r", kwargs)
        BaseHandler.render(self, template_path, **kwargs)

class IndexHandler(WebHandler):
    _url = r"/(\d*)"
    def get(self, index = 1):
        index = index if index else 1
        posts = Logic.post.get_posts(int(index), self.pagesize)
        if not posts.get("data"):
            self.send_error(404, info = u"页面不存在")
        self.render('index.jinja', posts=posts.get('data'),
                    pageinfo=posts.get('pageinfo'),
                    base_path = "/")

class WPHandler(WebHandler):
    _url = r"/index\.php/archives/(\d+)/?.*"
    def get(self, pid):
        post = Logic.post.get_post_by_id(pid).get("data")
        pubdate = post.get("pubdate")
        if not post:
            self.send_error(404, info = u"页面不存在")
        url = u"/{0}/{1}/{2}/{3}/".format(pubdate.year, pubdate.month,
                                          pubdate.day, post.get("link_title"))
        self.redirect(url)

class WPAboutHandler(WebHandler):
    _url = r"/index\.php/about"
    def get(self):
        self.redirect("/page/About/")

class PostHandler(WebHandler):
    _url = r"/post/(\d+)/?(\d*)"
    def get(self, pid, index):
        index = index if index else 1
        post = Logic.post.get_post_by_id(pid).get("data")
        if not post:
            self.send_error(404, info = u"文章不存在")
        comments = Logic.comment.get_post_comments(pid, index, self.pagesize)
        user = {}
        if self.uid and self.username:
            user = Logic.user.get_user_by_id(self.uid)
        self.render("page.jinja", post = post,
                    post_comments = comments.get("data"), user = user,
                    title=post.get("title"), pageinfo = comments.get("pageinfo"),
                    description = post.get("short_content"),
                    keywords = post.get("keywords"))

    def post(self, pid, index):
        name = self.get_argument("name")
        email = self.get_argument("email")
        url = self.get_argument("url")
        content = self.get_argument("content")
        parent = self.get_argument("parent", None)
        comment_dict = {}
        comment_dict['name'] = name
        comment_dict['email'] = email
        comment_dict['url'] = url
        comment_dict['content'] = content
        comment_dict['ip'] = self.request.remote_ip
        if parent: comment_dict['parent'] = parent
        cid = Logic.comment.add_comment(pid, comment_dict, self.request)
        if self.uid and self.username:
            Logic.comment.allow_comment(cid)
        self.write({"status":True, "msg":u"评论提交成功,等待管理员审核"})


class TitlePostHandler(WebHandler):
    #XXX (.+?) 捕捉中文如不以/结尾则会传入一个%值 奇怪
    _url = r"/\d{4}/\d{1,2}/\d{1,2}/(.+?)/(?:comment-page)*-*(\d*)"
    def get(self, link_title, index):
        index = index if index else 1
        post = Logic.post.get_post_by_link(link_title).get("data")
        pid = post.get("id")
        if not post:
            self.send_error(404, info = u"文章不存在")
        comments = Logic.comment.get_post_comments(pid, index, self.pagesize)
        user = {}
        if self.uid and self.username:
            user = Logic.user.get_user_by_id(self.uid)
        self.render("page.jinja", post = post,
                    post_comments = comments.get("data"), user = user,
                    title=post.get("title"), pageinfo = comments.get("pageinfo"),
                    description = post.get("short_content"),
                    keywords = post.get("keywords"))


class CategoryHandler(WebHandler):
    _url = r"/category/(.+?)/(\d*)"
    def get(self, cate, index):
        index = index if index else 1
        title = cate
        cid = Logic.category.check_exists(cate).get("id")
        if not cid:
            self.send_error(404, info=u"没有 {0} 这个类别".format(cate))
        posts = Logic.post.get_post_by_category(cid, int(index), self.pagesize)
        self.render("index.jinja", posts = posts.get("data"),
                    pageinfo = posts.get("pageinfo"), title = title,
                    base_path = u"/category/{0}/".format(cate))

class TagHandler(WebHandler):
    _url = r"/tag/(.+?)/(\d*)"
    def get(self, tag, index):
        index = index if index else 1
        tid = Logic.tag.check_exists(tag)
        if not tid:
            self.send_error(404, info=u"没有 {0} 这个标签".format(tag))
        posts = Logic.post.get_post_by_tag(tid, int(index), self.pagesize)
        self.render("index.jinja", posts = posts.get("data"),
                    pageinfo = posts.get("pageinfo"), title  = tag,
                    base_path = u"/tag/{0}/".format(tag))

class PageHandler(WebHandler):
    #XXX 如不传(.+?)后面的/会传进一个很奇特的%字符导致解码失败
    _url = r"/page/(.+?)/(?:comment-page-)*(\d*)"
    def get(self, link_title, index):
        index = index if index.strip() else 1
        if self.uid and self.username:
            user = Logic.user.get_user_by_id(self.uid)
        else:
            user = None
        page = Logic.page.get_page_by_link(link_title).get("data")
        if not page:
            self.send_error(404, info = u"页面不存在")
        comments = Logic.comment.get_post_comments(page.get("id"), index,
                                                    self.pagesize)
        post_comments = comments.get("data")
        pageinfo = comments.get("pageinfo")
        self.render("page.jinja", post = page, title=page.get("title"),
                    ispage = True, user = user, pageinfo = pageinfo,
                    post_comments = post_comments)

class DateHandler(WebHandler):
    _url = r"/date/(\d+)/(\d+)/?(\d*)"
    def get(self, year, month, index):
        index = index if index else 1
        data = Logic.post.get_by_month(year, month, index, self.pagesize)
        pageinfo = data.get("pageinfo")
        posts = data.get("data")
        self.render("index.jinja", posts = posts, pageinfo = pageinfo,
                    title = u"{0}年 {1} 月".format(year, month),
                    base_path = "/date/{0}/{1}/".format(year, month))

class ArchivesHandler(WebHandler):
    _url = r"/archives/"
    def get(self):
        archives = Logic.post.get_archives()
        self.render("archive.jinja", title=u"文章归档", archives = archives)

class NotesHandler(WebHandler):
    _url = r"/notes/(?:p)*/?(\d*)/?"
    def get(self, index):
        index = index if index else 1
        data = Logic.note.get_notes(index)
        notes = data.get("data")
        pageinfo = data.get("pageinfo")
        gravatar = None
        if self.uid and self.username:
            admin = Logic.user.check_has_admin().get("email")
            gravatar = md5(admin)
        self.render("notes.jinja", notes = notes, title = u"便签",
                    gravatar = gravatar, pageinfo = pageinfo,
                    basepath = r'/notes/p/')

class VlAjaxHandler(WebHandler):
    _url = r"/vl-ajax"
    def post(self):
        action = self.get_argument("action")
        if action == "add_post_view":
            pid = self.get_argument("pid")
            Logic.post.add_post_view(pid)

class FeedHandler(StaticFileHandler):
    def initialize(self):
        StaticFileHandler.initialize(self, STATIC_ROOT)

    def get(self):
        StaticFileHandler.get(self, 'rss.xml')

class WPFeedHandler(StaticFileHandler):
    _url = "/index.php/feed"
    def initialize(self):
        StaticFileHandler.initialize(self, STATIC_ROOT)

    def get(self):
        StaticFileHandler.get(self, 'rss.xml')

class SitemapHandler(StaticFileHandler):
    _url = r'/sitemap.xml'
    def initialize(self):
        StaticFileHandler.initialize(self, STATIC_ROOT)

    def get(self):
        StaticFileHandler.get(self, 'sitemap.xml')

class UploadHandler(StaticFileHandler):
    _url = r"/upload/(.+)"
    def initialize(self):
        StaticFileHandler.initialize(self, UPLOAD_PATH)

    def get(self, filename):
        StaticFileHandler.get(self, filename)

class ErrorHandler(WebHandler):
    def get(self, path):
        self.send_error(404, info=u"您当前访问的页面不存在(可能由于博客迁移,您访问的还是旧链接)")
