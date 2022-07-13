# Due to the very nature of webscraping, this will be highly fragile.
# Let's hope CSE does not change their stuff too much.
#
# Licensed under the BSD-2 Clause License, written by Visuwesh.
#
# Currently this only handles press releases.

import bs4
import email.message as msg
from email.utils import formatdate as msgdate
import mailbox
import json
from html2text import html2text
import os
import threading
import urllib.request as req

UA = { "User-Agent": "Chrome/96.0.4664.110" }
THREADS = []
MAILDIR = mailbox.Maildir(dirname="./test/cse")
DB = {}
if os.path.exists("./DB"):
    with open("./DB") as f:
        DB = json.loads(f.read())
if not DB.get("press-release"):
    DB["press-release"] = []

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
    soup = bs4.BeautifulSoup(request(article), "html.parser")
    return (soup.find("title").text,
            soup.find("div", class_="content-para"))

def push_message(article):
    m = msg.EmailMessage()
    m.add_header("From", "CSE Press Release <press-release@cse>")
    m.add_header("To", "<" + os.getenv("USER") + "@" + os.uname()[1] + ">")
    m.add_header("Topic", article["topic"])
    m.add_header("Newsgroups", "CSE-Press-Release")
    m.add_header("Url", article["url"])
    c = content(article["url"])
    m.add_header("Subject", c[0])
    # Poor man's date.
    m.add_header("Date", msgdate())
    m.set_content(str(c[1]), subtype="html")
    m.add_alternative(html2text(str(c[1])))
    print(MAILDIR.add(m))
    DB["press-release"].append(article["url"])


def subpage(page):
    """PAGE maybe be a soup object or a string representing a URL.
    Return the number of article fetched.

    """
    n = 0
    if isinstance(page, str):
        page = bs4.BeautifulSoup(request(page), "html.parser")
    for i in articles_in_soup(page):
        if i["url"] in DB.get("press-release", []):
            continue
        t = threading.Thread(target=push_message, args=(i,), name="article fetch " + i["url"])
        THREADS.append(t)
        t.run()
        n += 1
    return n

def do():
    main = bs4.BeautifulSoup(request("https://www.cseindia.org/press-releases"), "html.parser")
    # Try the mainpage first.
    n = subpage(main)
    # If no article fetched or if no. articles fetched is less than
    # the number in page, bail.
    if not (n == 0 or n < len(articles_in_soup(main))):
        p = pages(main)
        for i in p:
            t = threading.Thread(target=subpage, args=(i,), name=f"subpage {i}")
            THREADS.append(t)
            t.run()

if __name__ == "__main__":
    do()
    with open("./DB", "w") as f:
        f.write(json.dumps(DB, indent=4))
