
import sqlite3, sys
from unicodedata import normalize

conn = sqlite3.connect('./src/kural.db')

cur = conn.cursor()
cur.execute("SELECT cast(id as int) as id, kural, title FROM kurals order by 1")
rows = cur.fetchall()

a = '''
    <section data-background-color="#222222" data-transition="concave">
        <div class="sl-block" data-block-type="text" style="height: auto; width: 666px; left: 134px; top: 280px;"
            data-name="text-a5a325">
            <div class="sl-block-style" style="z-index: 10; transform: rotate(0deg);">
                <div class="sl-block-content" data-placeholder-tag="p" data-placeholder-text="Text"
                    style="z-index: 10; color: rgb(255, 255, 255);">
                    kural
                </div>
            </div>
        </div>
        <div class="sl-block" data-block-type="text" style="height: auto; width: 80px; left: 880px; top: 661px;"
            data-name="text-bc8060" data-block-id="1b90fe705627eebc1cc89bada8d942e4">
            <div class="sl-block-content" data-placeholder-tag="p" data-placeholder-text="Text"
                style="z-index: 11; color: rgb(102, 102, 102); text-align: center;">
                kural_id
            </div>
        </div>
        <div class="sl-block" data-block-type="text" style="height: auto; width: 480px; left: 480px; top: 0px;"
            data-block-id="7e9a36c7becaa9a0ef90b199a3b5faea" data-name="text-4a48b5">
            <div class="sl-block-style" style="z-index: 12; transform: rotate(0deg);">
                <div class="sl-block-content" data-placeholder-tag="p" data-placeholder-text="Text"
                    style="z-index: 12; color: rgb(102, 102, 102); text-align: right;">
                    kural_title
                </div>
            </div>
        </div>
    </section>
'''

kurals = []

for row in rows:
   output = ""
   if row[0] % 10 == 1:
       output = "<section>" + a.replace('data-transition="concave"', 'data-transition="zoom" data-autoslide="4000"').replace("kural_id", "").replace("kural_title", "").replace("kural" , "<p>" + normalize('NFC', row[2]) + "</p>")
   x = row[1].split("<br/>")
   x[1] = x[1].strip().rstrip(".") + "."
   x = ["<p>" + normalize('NFC', line) + "</p>" for line in x]
   output += a.replace("kural_id", str(row[0])).replace("kural_title", row[2]).replace("kural" ,  "".join(x))
   if row[0] % 10 == 0:
       output += "</section>"
   kurals.append(output)

output = "\n".join(kurals)

reading_file = open("./src/template.html", "r")

new_file_content = ""
for line in reading_file:
  stripped_line = line.strip()
  new_line = stripped_line.replace("kural_list", output)
  new_file_content += new_line +"\n"
reading_file.close()

writing_file = open("./docs/index.html", "w")
writing_file.write(new_file_content.encode('UTF-8'))
writing_file.close()

conn.commit()
    
