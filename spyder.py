import html5lib
from html5lib import treewalkers
walker = treewalkers.getTreeWalker("dom")
import urlparse
import urllib2
import httplib
import socket
import logging
import pdb

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
        self.all_urls = []
        self.visited_urls = []
        self.urls_to_visit = []
        self.html_urls = []
        self.exclude = exclude

    def get_absolute_url(self, current_url, node):

        if current_url.startswith("/"):
            current_url = current_url[1:]

        href = node.attributes.get('href', None)
        if href is None:
            return
            
        href = href.value.strip()
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

        return href

    def cleanup_href(self, href):
        # Normalize URLs even more. Eg:
        # directory/toto/../tata/" -> directory/tata/
        parse = urlparse.urlparse(href)
        url = parse.path
        new_bits = []
        for bits in url.split('/'):
            if bits=='..' and new_bits:
                new_bits.pop()
            else:
                new_bits.append(bits)

        url = "/".join(new_bits)
        if parse.query:
            return url + '?' + parse.query
        return url
            
    def fetch(self, url):
        total = self.http_root + url
        if not url.startswith('/'):
            logging.warn("Invalid URL %s on ?" % total)
        try:
            fh = urllib2.urlopen(total, None, 3)
            content_type = fh.info()['content-type']
            content = fh.read()

        except (urllib2.URLError, httplib.HTTPException, socket.timeout), err:
            logging.warn("Cannot fetch url:%s %s" % (total, err))
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
            logging.info("Fetching url:%s" % url)
            content_type, content = self.fetch(url)
        except (urllib2.HTTPError), err:
            logging.warn("Cannot fetch url:%s %s" % (self.http_root + '/' + url, err))
            return

        if content_type.startswith("text/html"):
            self.html_urls.append(url)
            self.new_page(url, content)
        else:
            return self.new_content(url, content_type, content)

        from html5lib import treebuilders
        parser = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))
        dom_tree = parser.parse(content)
        for node in walk(dom_tree):
            if node.nodeType == 1 and node.nodeName == 'a':
                parse_result = urlparse.urlparse(url)
                href = self.get_absolute_url(parse_result.path, node)
                query = urlparse.parse_qs(parse_result.query)
                if href:
                    href = self.cleanup_href(href)
                    if href not in self.all_urls:
                        self.all_urls.append(href)
                        if query:
                            print query
                        self.urls_to_visit.append(href)

    def scrap(self, start='/'):
        result = self.scrap_page(start)
        while len(self.urls_to_visit):
            for url in self.urls_to_visit:
                self.scrap_page(url)
        return self.visited_urls


    def new_page(self, url, content):
        print url
    
    def new_content(self, url, content_type, content):
        print url, content_type
   
# example
if __name__ == "__main__":
    sp = Scraper("http://www.microsoft.com", exclude=["/dont/not/want/"])
    print sp.scrap()

