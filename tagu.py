#!python

import alp
import subprocess
import re
import sqlite3

DB = "db"

def init_db():
    conn = sqlite3.connect(alp.local(join=DB))
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY, url_id NUMERIC, tag TEXT);''')
    c.execute('''CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, url TEXT UNIQUE);''')

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

def save(tags):
    conn = sqlite3.connect(alp.local(join=DB))
    c = conn.cursor()

    url = subprocess.check_output('pbpaste')

    # existed
    c.execute('SELECT * FROM urls WHERE url = ?', (url, ))
    row = c.fetchone()

    url_id = None

    if not row:
        c.execute('INSERT INTO urls VALUES (NULL, ?)', (url, ))
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

    question_marks = ','.join('?'*len(tags))

    rows = []

    for tag in tags:
        c.execute('''
            SELECT urls.* FROM urls
            JOIN tags ON tags.url_id = urls.id
            WHERE tags.tag LIKE ?
        ''', ('%'+tags[0]+'%', ))

        rows += c.fetchall()

    indexed = {}
    for row in rows:
        indexed[row['id']] = row['url']

    items = []
    for (_id, url) in indexed.items():
        c.execute('SELECT * FROM tags WHERE url_id = ?', (_id,))
        url_tags = c.fetchall()
        item = alp.Item(
                title=url,
                subtitle=" ".join(map(lambda tag: tag['tag'], url_tags)),
                valid=True,
                arg=url
                )
        items.append(item)

    alp.feedback(items)


init_db()

fun = alp.args()[0]
tags = alp.args()[1:]

if fun == "tag":
    tag(tags)
elif fun == "save":
    save(tags)
elif fun == "search":
    search(tags)

