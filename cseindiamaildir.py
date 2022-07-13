# Due to the very nature of webscraping, this will be highly fragile.
# Let's hope CSE does not change their stuff too much.
#
# Licensed under the BSD-2 Clause License, written by Visuwesh.

import bs4
import urllib.request as req

UA = { "User-Agent": "Chrome/96.0.4664.110" }
def request(url):
    """Request URL."""
    return req.urlopen(req.Request(url, headers=UA))

def articles_in_soup(soup):
    return [
        { "topic": i.find("ul", class_="article-meta").a.text,
          "url": i.find("h4").a["href"] }
        for i in soup.find_all("article")
    ]

def pages(soup):
    return [
        "https://www.cseindia.org" + i["href"]
        for i in soup.find_all("a", attrs={"data-page":True})[1:]
    ]

def content(article):
    """Return the title and content of the URL ARTICLE."""
    soup = bs4.BeautifulSoup(request(page), "html.parser")
    return (soup.find("title").text,
            soup.find("div", class_="content-page"))

# https://www.cseindia.org/press-releases
