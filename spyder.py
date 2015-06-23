
import urlparse
import urllib2
import httplib
import socket
import pdb
from bs4 import BeautifulSoup
from termcolor import colored
import os

def ensure_dir(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            print path
            raise

class Scraper(object):

    def __init__(self, uri, exclude=[], data_directory='data', assets_domain=None):
        self.uri = uri
        self.domain = urlparse.urlparse(uri)[1]
        self.http_root = "http://%s" % self.domain
        self.all_urls = []
        self.visited_urls = []
        self.urls_to_visit = []
        self.html_urls = []
        self.data_directory = data_directory
        self.exclude = exclude
        if assets_domain and not assets_domain.endswith('/'):
            assets_domain += '/'
        self.assets_domain = assets_domain
        self.assets_urls = []

    def get_absolute_url(self, current_url, href):

        # normalise the current_url to start and end with /
        if not current_url.startswith('/'):
            current_url = '/' + current_url

        if not current_url.endswith('/'):
            current_url = current_url + '/'

        if href is None or len(href) == 0:
            return '/'
            
        href = href.strip()

        if href.startswith("//"):
            return href

        if href.startswith('#'):
            return None

        if href.startswith('./'):
            return current_url + href[2:]

        if href.startswith('../'):
            bits = current_url.split('/')
            if len(bits) < 3:
                return None
            return "/".join(bits[:-3] + [href[3:]])

        if self.assets_domain and href.startswith(self.assets_domain):
            href =  href[len(self.assets_domain)-1:]
            return href

        if href.startswith(self.http_root):
            href =  href[len(self.http_root):]
            return href
        elif href.startswith('http://') or href.startswith('www'):
            return None

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
        try:
            fh = urllib2.urlopen(url, timeout=20)
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
            if not url.startswith('/'):
                self.error("Invalid URL %s on ?" % url)
            content_type, content = self.fetch(self.http_root + url)
        except IOError as error:
            print(colored("Cannot fetch url: %s\nReasons: %s" % (url, error), 'red'))
            return

        if content_type.startswith("text/html"):
            self.html_urls.append(url)
            self.new_page(url, content)
        else:
            return self.new_content(url, content_type, content)

        parse_result = urlparse.urlparse(url)
        soup = BeautifulSoup(content)

        def scarp_if_asset(href):
            if not self.assets_domain:
                return False
            if href in self.assets_urls:
                return True
            if href.startswith(self.assets_domain):
                self.assets_urls.append(href)
                self.scrap_asset(href)
                return True

        for link in soup.find_all(True):

            href = None
            for name in ['href', 'src']:
                if name in link.attrs: 
                    href = link.attrs[name]
                    break

            if href is None:
                continue

            if scarp_if_asset(href):
                continue

            href = self.get_absolute_url(parse_result.path, link.attrs[name])
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
            print('Page scrapped: ' + str(len(self.visited_urls)) + ', Left over: ' + str(len(self.urls_to_visit)))

        print(colored('Finished', 'green'))

    def scrap_asset(self, url):
        try:
            content_type, content = self.fetch(url)
        except (IOError, UnicodeEncodeError) as error:
            print(colored("Cannot fetch url: %s\nReasons: %s" % (url, error), 'red'))
            return
        url = url[len(self.assets_domain):]
        self.new_content(url, content_type, content)
        print(' ---> Asset scrapped: ' + url)

    def transform_links(self, url, content):

        parse_result = urlparse.urlparse(url)
        soup = BeautifulSoup(content)

        for link in soup.find_all(True):

                href = None
                for name in ['href', 'src']:
                    if name in link.attrs: 
                        href = link.attrs[name]
                        break

                if href is None:
                    continue

                new_href = self.get_absolute_url(parse_result.path, link.attrs[name])
                if new_href is not None:
                    link.attrs[name] = new_href

        return soup.encode_contents(formatter='html')


    def new_page(self, url, content):
        path = [self.data_directory] + url.split('/')

        content = self.transform_links(url, content)

        filepath = os.path.join(*path)
        if not filepath.endswith('/'):
            filepath += '/'
        ensure_dir(filepath)
        filepath += 'index.html'
        f = open(filepath, 'w')
        f.write(content)
        f.close()

    def new_content(self, url, content_type, content):
        #parse = urlparse.urlparse(url)
        #url = parse.path
        path = [self.data_directory] + url.split('/')
        filepath = os.path.join(*path)
        if filepath.endswith('/'):
            ensure_dir(filepath)
            return
        path = [self.data_directory] + url.split('/')[:-1]
        parent_filepath = os.path.join(*path)
        ensure_dir(parent_filepath)
        f = open(filepath, 'w')
        f.write(content)
        f.close()
   


import unittest

class ScrapperTest(unittest.TestCase):

    def setUp(self):
        self.sc = Scraper('http://blog.example.com')

    def test_get_absolute_url(self):
        self.assertEqual(self.sc.get_absolute_url('', 'en'), '/en')
        self.assertEqual(self.sc.get_absolute_url('hello/test', '../en'), '/en')
        self.assertEqual(self.sc.get_absolute_url('', '../en'), None)
        self.assertEqual(self.sc.get_absolute_url('', 'http://blog.example.com/test/toto'), '/test/toto')
        self.assertEqual(self.sc.get_absolute_url('hello/test', 'test/toto'), '/hello/test/test/toto')
        self.assertEqual(self.sc.get_absolute_url('hello/test', './test/toto'), '/hello/test/test/toto')
        self.assertEqual(self.sc.get_absolute_url('', './test/toto'), '/test/toto')
        self.assertEqual(self.sc.get_absolute_url('', 'www.google.com'), None)
        self.assertEqual(self.sc.get_absolute_url('', 'http://hello'), None)
        self.assertEqual(self.sc.get_absolute_url('', '//hello'), '//hello')
        self.assertEqual(self.sc.get_absolute_url('/hella/tests', '//hello'), '//hello')
        self.assertEqual(self.sc.get_absolute_url('', '1396340238/fast-food.jpg'), '/1396340238/fast-food.jpg')
        self.assertEqual(self.sc.get_absolute_url('something', '1396340238/fast-food.jpg'), '/something/1396340238/fast-food.jpg')
        self.assertEqual(self.sc.get_absolute_url('/', '1328100363/favicon.ico'), '/1328100363/favicon.ico')
        self.assertEqual(self.sc.get_absolute_url('', ''), '/')
        self.assertEqual(self.sc.get_absolute_url('', '   '), '/')


if __name__ == '__main__':
    unittest.main()
