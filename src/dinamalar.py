import requests
from bs4 import BeautifulSoup
import sqlite3, sys


conn = sqlite3.connect('kural.db')
#conn.text_factory = str #lambda x: unicode(x, "utf-8", "ignore")

c = conn.cursor()
#c.execute('''PRAGMA encoding="UTF-8";''')

c.execute('''CREATE TABLE IF NOT EXISTS kurals
             (id, kural, title)''')

c.execute('''CREATE TABLE IF NOT EXISTS vilakams(id, author, content)''')

conn.commit()

c = conn.cursor()

for x in range(1, 1331):
    URL = "https://m.dinamalar.com/kural_detail.php?kural_no=" + str(x)
    page = requests.get(URL)

    soup = BeautifulSoup(page.content, 'html.parser')
    k = soup.find_all('p', class_='clsMaink')
    title = soup.select('#citylist > option[selected]')
    kvs = soup.select('div > p > b')
    
    kural = k[0].encode_contents()
    title = title[0].encode_contents().strip()
    print(title)

    #kural = unicode(kural, "utf-8")
    c.execute('INSERT INTO kurals(id, kural, title) VALUES(?, ?, ?)', (x, kural.decode('utf-8'), title.decode('utf-8')));
    for v in kvs:
        v = v.find_parent('div')
        author = v.find('span').encode_contents().strip().replace(":", "").strip()
        v.find('b').decompose()
        content = v.find('p').encode_contents().strip()
        #author = unicode(author, "utf-8") 
        #content = unicode(content, "utf-8")
        print(author)
        print(content)
        c.execute('INSERT INTO vilakams(id, author, content) VALUES(?, ?, ?)', (x, author.decode('utf-8'), content.decode('utf-8')))

conn.commit()
    
