import html5lib
from html5lib import treewalkers
walker = treewalkers.getTreeWalker("dom")
import urlparse
import urllib2
import httplib
import socket
import pdb
from termcolor import colored
import os

def ensure_dir(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            print path
            raise

def walk(node):
    yield node
    if hasattr(node, 'childNodes'):
        for n in node.childNodes:
            for m in walk(n):
                
                yield m

def node_is(node, name):
    return node.type == 5 and node.name == name

class Scraper(object):

    def __init__(self, uri, exclude=[], data_directory='data'):
        self.uri = uri
        self.domain = urlparse.urlparse(uri)[1]
        self.http_root = "http://%s" % self.domain
        self.all_urls = []
        self.visited_urls = []
        self.urls_to_visit = []
        self.html_urls = []
        self.data_directory = data_directory
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

    def error(self, msg):
        print(colored(msg, 'red'))

    def message(self, msg):
        print(colored(msg))
            
    def fetch(self, url):
        total = self.http_root + url
        if not url.startswith('/'):
            self.error("Invalid URL %s on ?" % total)
        try:
            fh = urllib2.urlopen(total, None, 5)
            content_type = fh.info()['content-type']
            content = fh.read()

        except (urllib2.URLError, httplib.HTTPException, socket.timeout), err:
            raise IOError(err)

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
            print("Fetching url: %s" % url)
            content_type, content = self.fetch(url)
        except IOError as error:
            print(colored("Cannot fetch url: %s\nReasons: %s" % (url, error), 'red'))
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
                        #if query:
                        #    print('Query string', query)
                        self.urls_to_visit.append(href)

    def scrap(self, start='/'):
        print(colored('Start scrapping domain '+self.domain, 'green'))
        result = self.scrap_page(start)
        while len(self.urls_to_visit):
            url = self.urls_to_visit.pop()
            self.scrap_page(url)
        print(colored('Finished', 'green'))


    def new_page(self, url, content):
        path = [self.data_directory] + url.split('/')
        filepath = os.path.join(*path)
        if not filepath.endswith('/'):
            filepath += '/'
        ensure_dir(filepath)
        filepath += 'index.html'
        f = open(filepath, 'w')
        f.write(content)
        f.close()

    def new_content(self, url, content_type, content):
        path = [self.data_directory] + url.split('/')
        filepath = os.path.join(*path)
        if filepath.endswith('/'):
            ensure_dir(filepath)
            return
        ensure_dir(filepath)
        f = open(filepath, 'w')
        f.write(content)
        f.close()
   
# example
if __name__ == "__main__":
    sp = Scraper("http://www.microsoft.com", exclude=["/dont/not/want/"])
    print sp.scrap()
