# Due to the very nature of webscraping, this will be highly fragile.
# Let's hope CSE does not change their stuff too much.
#
# Licensed under the BSD 2-Clause License.
#
# This file can really use some generalisation of functions.

import bs4
from datetime import datetime
import email.message as msg
import email.utils
import mailbox
import json
from html2text import html2text
import os
import re
import multiprocessing as multiproc
import urllib.request as req

UA = { "User-Agent": "Chrome/96.0.4664.110" }
PROCS = []
MESSAGES = []
MAILDIR = mailbox.Maildir(dirname="/home/viz/mail/rss2email/scimag")
REPORT_PDF_RE = re.compile(".*/downloadreports/.*")
DB = {}
if os.path.exists("./DB"):
    with open("./DB") as f:
        DB = json.loads(f.read())
if not DB.get("press-release"):
    DB["press-release"] = []
if not DB.get("reports"):
    DB["reports"] = []

# Mail utils
def msg_to_addr():
    return "<" + os.getenv("USER") + "@" + os.uname()[1] + ">"



# Request utils

def request(url):
    """Request URL."""
    return req.urlopen(req.Request(url, headers=UA))

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

def subpage(page, mailbox, article_fun, push_fun):
    """PAGE maybe be a soup object or a string representing a URL.
    Return the number of article fetched and the total number of
    articles.

    """
    n = 0
    tot = 0
    if isinstance(page, str):
        page = bs4.BeautifulSoup(request(page), "html.parser")
    for i in article_fun(page):
        tot += 1
        if i["url"] in DB.get(mailbox, []):
            continue
        p = multiproc.Process(target=push_fun, args=(i,), name="article fetch " + i["url"])
        PROCS.append(p)
        p.start()
        n += 1
    return n, tot


# Press releases

def articles_in_press_release(soup):
    return [
        { "topic": i.find("ul", class_="article-meta").a.text,
          "url": i.find("h4").a["href"] }
        for i in soup.find_all("article")
    ]

def push_press_release(article):
    m = msg.EmailMessage()
    m.add_header("From", "CSE Press Release <press-release@cse>")
    m.add_header("To", msg_to_addr())
    m.add_header("Topic", article["topic"])
    m.add_header("Newsgroups", "CSE-Press-Release")
    m.add_header("Url", article["url"])
    c = content(article["url"])
    m.add_header("Subject", c[0])
    # Poor man's date.
    m.add_header("Date", email.utils.formatdate())
    m.set_content(str(c[1]), subtype="html")
    m.add_alternative(html2text(str(c[1])))
    MESSAGES.append(("press-release", m))
    # print(MAILDIR.add(m), article["url"])
    # DB["press-release"].append(article["url"])



# Reports
def articles_in_report(soup):
    return [
        { "date": i.find(class_="date").text.strip(),
          "topic": i.find(class_="small-heading").text.strip(),
          "url": i.find("p", class_="amplitude").a["href"],
          "pdf": i.find("a", href=REPORT_PDF_RE)["href"] }
        for i in soup.find_all("div", class_="info")
    ]

def push_report(report):
    m = msg.EmailMessage()
    m.add_header("From", "CSE Reports <reports@cse>")
    m.add_header("To", msg_to_addr())
    m.add_header("Topic", report["topic"])
    m.add_header("Newsgroups", "CSE-Reports")
    m.add_header("Url", report["url"])
    m.add_header("Pdf", report["pdf"])
    m.add_header("Date", email.utils.format_datetime(datetime.strptime(report["date"], "%d %B, %Y")))
    c = content(report["url"])
    m.add_header("Subject", c[0])
    m.set_content(str(c[1]) + "\nPDF: " + report["pdf"], subtype="html")
    m.add_alternative(html2text(str(c[1])) + "\nPDF: " + report["pdf"])
    MESSAGES.append(("reports", m))
    # print(MAILDIR.add(m), report["url"])
    # DB["reports"].append(report["url"])



def do(url, cat, article_fun, push_fun):
    main = bs4.BeautifulSoup(request(url), "html.parser")
    # Try the mainpage first.
    n, tot = subpage(main, cat, article_fun, push_fun)
    # If no article fetched or if no. articles fetched is less than
    # the number in page, bail.
    if not (n == 0 or n < tot):
        p = pages(main)
        for i in p:
            print("Trying...", i)
            p = multiproc.Process(target=subpage, args=(i, cat, article_fun, push_fun),
                                  name=f"subpage {i}")
            PROCS.append(p)
            p.start()

if __name__ == "__main__":
    with multiproc.Manager() as manager:
        MESSAGES = manager.list()
        do("https://www.cseindia.org/press-releases", "press-release", articles_in_press_release, push_press_release)
        do("https://www.cseindia.org/reports", "reports", articles_in_report, push_report)
        for p in PROCS: p.join()
        for m in MESSAGES:
            print(MAILDIR.add(m[1]), m[1].get("Url"))
            DB[m[0]].append(m[1].get("Url"))
        with open("./DB", "w") as f:
            f.write(json.dumps(DB, indent=4))
