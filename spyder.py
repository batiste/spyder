import html5lib
from html5lib import treewalkers
walker = treewalkers.getTreeWalker("dom")
import urlparse
import urllib2
import httplib
import socket
import logging

def walk(node):
    yield node
    if hasattr(node, 'childNodes'):
        for n in node.childNodes:
            for m in walk(n):
                yield m

def node_is(node, name):
    return node.type == 5 and node.name == name

class Scraper(object):

    def __init__(self, uri, exclude=[]):
        self.uri = uri
        self.domain = urlparse.urlparse(uri)[1]
        self.http_root = "http://%s" % self.domain
        self.start_url = self.uri[len(self.http_root):]
        self.all_urls = []
        self.visited_urls = []
        self.urls_to_visit = []
        self.html_urls = []
        self.exclude = exclude

    def get_relative_url(self, current_url, node):

        if current_url.startswith("/"):
            current_url = current_url[1:]

        href = node.attributes.get('href', None)
        if href is None:
            return
        href = href.strip()
        if len(href) == 0:
            href = current_url

        if href.startswith('#'):
            return None

        if href.startswith('./'):
            return current_url + href[1:]

        if href.startswith(self.http_root):
            href =  href[len(self.http_root):]

        if "://" in href:
            return None

        if href.startswith("mailto:"):
            return None

        if href.startswith("javascript:"):
            return None

        # relative urls
        if not href.startswith("/"):
            return current_url + href

        if not href.startswith("/"):
            return "/" + href

        return href

    def cleanup_href(self, href):
        # Normalize URLs even more. Eg:
        # directory/toto/../tata/" -> directory/tata/
        url = urlparse.urlparse(href).path
        new_bits = []
        for bits in url.split('/'):
            if bits=='..' and new_bits:
                new_bits.pop()
            else:
                new_bits.append(bits)

        return "/".join(new_bits)

    def fetch(self, url):
        try:
            fh = urllib2.urlopen(self.http_root + '/' + url, None, 3)
            content_type = fh.info()['content-type']
            content = fh.read()

        except (urllib2.URLError, httplib.HTTPException, socket.timeout), err:
            logging.warn("Cannot fetch url:%s %s" % (self.http_root + '/' + url, err))
            return "error", ""

        return content_type, content

    def scrap_page(self, url):
        if url in self.visited_urls:
            return

        for ex in self.exclude:
            if ex in url:
                return

        self.visited_urls.append(url)
        if url in self.urls_to_visit:
            self.urls_to_visit.remove(url)
        try:
            content_type, content = self.fetch(url)
        except (urllib2.HTTPError), err:
            logging.warn("Cannot fetch url:%s %s" % (self.http_root + '/' + url, err))
            return

        if content_type.startswith("text/html"):
            self.html_urls.append(url)
            self.new_page(url, content)
        else:
            return self.new_content(url, content_type, content)

        parser = html5lib.HTMLParser()
        dom_tree = parser.parse(content)
        for node in walk(dom_tree):
            if node.type == 5 and node.name == 'a':
                href = self.get_relative_url(url, node)
                if href:
                    href = self.cleanup_href(href)
                    if href not in self.all_urls:
                        self.all_urls.append(href)
                        self.urls_to_visit.append(href)

    def scrap(self):
        result = self.scrap_page(self.start_url)
        while len(self.urls_to_visit):
            for url in self.urls_to_visit:
                self.scrap_page(url)
        return self.visited_urls


    def new_page(self, url, content):
        print url
    
    def new_content(self, url, content_type):
        print url, content_type
   
# example
#def __main__():
sp = Scraper("http://d8.opera.com:8001/", exclude=["/dont/want/"])
print sp.scrap()

