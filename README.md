# Spyder - simple python site crawler

Spyder is another simple crawler in python. Subclass Spider and you have your own crawler.

    from spyder import Scraper

    # example
    if __name__ == "__main__":
        sp = Scraper("http://mywebsite.com/")
        sp.scrap()

Save under scrap.py and then execute:

    $ python scrap.py
    Start scrapping domain website.local.ch
    Fetching url: /
    Fetching url: /toto
    Fetching url: /toto?cat=1
    Fetching url: /toto?cat=2
    ...
    Finished

The content is save under the data directory