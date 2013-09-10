#!python

import alp
import subprocess
import re
import sqlite3
import urllib
import hashlib
import os
import SocketServer
import sys
import atexit
from StringIO import StringIO

DB = "db"

def init_db():
    conn = sqlite3.connect(alp.local(join=DB))
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, url_id NUMERIC, tag TEXT);''')
    c.execute('''CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, url TEXT UNIQUE, icon BLOB);''')

    conn.commit()
    conn.close()

def tag(tags):
    url = subprocess.check_output('pbpaste')

    # borrow from django
    regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if re.match(regex, url):
        description = alp.Item(title="Tag " + " ".join(tags), subtitle=url, valid=True, arg=" ".join(tags))
        alp.feedback(description)
    else:
        notice = alp.Item(title="Please Copy URL to Clipboard", valid=False)
        alp.feedback(notice)

def save(tags):
    conn = sqlite3.connect(alp.local(join=DB))
    c = conn.cursor()

    url = subprocess.check_output('pbpaste')

    # existed
    c.execute('SELECT * FROM urls WHERE url = ?', (url, ))
    row = c.fetchone()

    url_id = None

    if not row:
        # fetch favicon
        google_favicon_service = 'http://www.google.com/s2/favicons?%s'
        params = urllib.urlencode({'domain_url': url})
        icon = ""
        try:
            icon = urllib.urlopen(google_favicon_service % params).read()
        except:
            pass
        c.execute('INSERT INTO urls VALUES (NULL, ?, ?)', (url, sqlite3.Binary(icon)))
        url_id = c.lastrowid
    else:
        url_id = row[0]

    for tag in tags:
        c.execute('INSERT INTO tags VALUES (NULL, ?, ?)', (url_id, tag))

    conn.commit()
    conn.close()

    # for notification
    print url

def search(tags):
    conn = sqlite3.connect(alp.local(join=DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    rows = []

    for tag in tags:
        c.execute('''
            SELECT DISTINCT urls.* FROM urls
            JOIN tags ON tags.url_id = urls.id
            WHERE tags.tag LIKE ?
        ''', ('%'+tag+'%', ))

        rows += c.fetchall()

    items = []
    for row in rows:
        icon = row['icon']

        sha224 = hashlib.sha224(icon).hexdigest()
        icon_path = alp.local(join=os.path.join('icon_cache', sha224))

        if not os.path.exists(icon_path):
            with open(icon_path, 'w') as f:
                f.write(icon)

        c.execute('SELECT * FROM tags WHERE url_id = ?', (row['id'],))
        url_tags = c.fetchall()
        item = alp.Item(
                title=row['url'],
                subtitle=" ".join(map(lambda tag: tag['tag'], url_tags)),
                valid=True,
                icon=icon_path,
                arg=row['url']
                )
        items.append(item)

    alp.feedback(items)


class RequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        # redirect stdout to string
        sys.stdout = buf = StringIO()

        data = self.rfile.readline().strip().split(' ')

        if data:
            command = data[0]
            tags = data[1:]

            if command == "tag":
                tag(tags)
            elif command == "save":
                save(tags)
            elif command == "search":
                search(tags)

        self.wfile.write(buf.getvalue())
        buf.close()

if __name__ == '__main__':

    def cleanup():
        sys.stdout = sys.__stdout__
        os.remove('./socket')

    atexit.register(cleanup)

    if os.path.exists('./socket'):
        os.remove('./socket')

    init_db()
    server = SocketServer.UnixStreamServer("./socket", RequestHandler)
    server.serve_forever()

