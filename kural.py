
import sqlite3, sys
import codecs
from unicodedata import normalize

conn = sqlite3.connect('./src/kural.db')

cur = conn.cursor()
cur.execute("SELECT cast(kurals.id as int) as id, kural, title, content FROM kurals join vilakams WHERE kurals.id = vilakams.id order by kurals.id")
#cur.execute("SELECT cast(id as int) as id, kural, title FROM kurals order by id")

rows = cur.fetchall()

kural_id = '''
    <div class="sl-block k_id" data-block-type="text">
        kural_id
    </div>
'''

kural_title = '''
    <div class="sl-block k_t" data-block-type="text">
        kural_title
    </div>
'''

kural_explaination = '''
    <div class="sl-block k_e" data-block-type="text">
        <span style="position: absolute; left: -25px; top: 5px;">-</span><span style="font-size:0.7em">kural_explaination</span>
    </div>
'''

kural_template = '''
    <section data-background-color="#222222" data-transition="convex">
        <div class="sl-block" data-block-type="text" style="height: auto; width: 666px; left: 134px; top: 240px;z-index: 10; color: rgb(255, 255, 255);">
            kural            
        </div>
        kural_id
        kural_title
        kural_explaination
    </section>
'''

kurals = []

for row in rows:
   output = ""
   if row[0] % 10 == 1:
       output = "<section>" + kural_template.replace("kural_id", "").replace("kural_title", "").replace("kural_explaination", "").replace('data-transition="convex"', 'data-autoslide="4000"').replace("kural" , "<p>" + normalize('NFC', row[2]) + "</p>")
   x = row[1].split("<br/>")
   x[1] = x[1].strip().rstrip(".") + "."
   x = ["<p>" + normalize('NFC', line) + "</p>" for line in x]
   k_id = kural_id.replace("kural_id", str(row[0]))
   k_title = kural_title.replace("kural_title", row[2])
   k_explaination = kural_explaination.replace("kural_explaination", row[3])
   output += kural_template.replace("kural_id", k_id).replace("kural_title", k_title).replace("kural_explaination", k_explaination).replace("kural",  "".join(x))
   if row[0] % 10 == 0:
       output += "</section>"
   kurals.append(output)

output = "\n".join(kurals)

reading_file = codecs.open("./src/template.html", "r", encoding='utf8')

new_file_content = ""
for line in reading_file:
  stripped_line = line.strip()
  new_line = stripped_line.replace("kural_list", output)
  new_file_content += new_line +"\n"
reading_file.close()

writing_file = codecs.open("./docs/index.html", "w", encoding='utf8')
writing_file.write(new_file_content)
writing_file.close()

conn.commit()
    
