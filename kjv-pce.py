from sqlite3 import connect
import re

block_rgx = re.compile(r"<<[^>]+>>")

conn = connect("kjv-pce.db")
cur = conn.cursor()

def chapters(book_id):
    sql = """select max(chapter) 
from text
where book_id = ?"""
    cur.execute(sql, (book_id,))
    return cur.fetchone()[0]

def replace_special(content):
    out = content
    extras = []

    blocks = block_rgx.findall(content)

    for b in blocks:
        if "THE END" in b:
            extras.append('<blockquote style="text-align: center;">THE END</blockquote>')
        elif b.startswith("<<[") and b.endswith("]>>"):
            extras.append("<blockquote>%s</blockquote>" %
                          b[3:-3])
        else:
            psh, _ = replace_special(b[2:-2])
            extras.append('<div class="psalm-header">%s</div>' %
                          psh)

    out = block_rgx.sub("", content)
    
    out = out.replace("[", "<em>").replace("]", "</em>")

    return out, extras
    
def book_name(book_id):
    cur.execute("select name from book where id = ?", (book_id,))
    return cur.fetchone()[0]

def books():
    cur.execute("select id, name, testament from book order by id")
    return [{"id": row[0],
             "name": row[1],
             "testament": row[2]}
            for row in cur.fetchall()]

def book_list():
    cur.execute("select id, name, testament from book order by id")

    cur_testament = None
    html = "<h1>Holy Bible</h1>\n<h2>King James Version</h2><hr />\n"
    
    
    for row in cur.fetchall():
        id, name, testament = row

        if testament != cur_testament:
            html += "<h2>%s Testament</h2>\n" % testament.title()
            cur_testament = testament
            

        html += '<h3><a href="%(name)s.html">%(name)s</a></h3><h3>' % {"id": id,
                                                                      "name": name}

        for chap in range(1, chapters(id) + 1):
            html += '<a href="%(name)s.html#%(chap)s">%(chap)s</a> ' % {"name": name,
                                                                       "chap": chap}
            
    return html
        
def verse_html(book_id, chapter, verse):
    cur.execute("select name, content from book b inner join text t on b.id = t.book_id where book_id = ? and chapter = ? and verse = ?",
                (book_id, chapter, verse))
    row = cur.fetchone()
    name, content = row
    html = '<span class="verse">%s</span>' % replace_special(content)
    return html

def chapter_html(book_id, chapter):
    cur.execute("select name, chapter, verse, content from book b inner join text t on b.id = t.book_id where book_id = ? and chapter = ? order by verse",
                (book_id, chapter))

    html = None
    for row in cur.fetchall():
        book, chapter, verse, content = row

        if not html:
            html = "<h2>%s %s</h2>" % (book, chapter)

        content, extras = replace_special(content)

        for e in extras:
            if "psalm" in e:
                html += e + "\n"
        
        html += """
<p class="verse-block">
<span class="verse">
<span class="verse-num">%(verse)s</span>
<span class="verse-text">%(content)s</span>
</span>
</p>""" % {"book": book,
           "chapter": chapter,
           "verse": verse,
           "content": content}

        for e in extras:
            if not "psalm" in e:
                html += e + "\n"

    return html

def book_html(book_id):
    if 1 < book_id < 66:
        cur.execute("select a.name, b.name from book a left outer join book b on a.id = (b.id - 2) where a.id = ?", (book_id - 1,))
        prev_book, next_book = cur.fetchone()
        prev_book_link = '<a href="%s.html">&lt;&lt %s</a>' % (prev_book, prev_book)
        next_book_link = '<a href="%s.html">%s &gt;&gt;</a>' % (next_book, next_book)
        
    elif book_id == 1:
        prev_book_link = ''
        next_book_link = '<a href="Exodus.html">Exodus</a>'
    else:
        prev_book_link = '<a href="Jude.html">Jude</a>'
        next_book_link = ''
        
    cur.execute("""select name,
cast(chapter as integer) as chapter,
cast(verse as integer) as verse,
content
from book b
inner join text t
on b.id = t.book_id
where book_id = ?
order by chapter, verse""", (book_id,))

    cur_chapter = 0
    html = None
    
    for row in cur.fetchall():
        book, chapter, verse, content = row

        if not html:
            html = "<h2>%s</h2>" % book
            
        if chapter > cur_chapter:
            html += "<h3 id=\"%s\">%s</h3>\n" % (chapter, chapter)
            cur_chapter = chapter

        content, extras = replace_special(content)

        for e in extras:
            if "psalm" in e:
                html += e + "\n"
        
        html += """
<p class="verse-block">
<span class="verse">
<span class="verse-num">%(verse)s</span>
<span class="verse-text">%(content)s</span>
</span>
</p>""" % {"book": book,
           "chapter": chapter,
           "verse": verse,
           "content": content}

        for e in extras:
            if not "psalm" in e:
                html += e + "\n"
        
    html += ("""
<hr />
<table style="width: 100%%;">
<tr>
<td style="width: 33%%" align="left">
%(prev)s
</td>
<td style="width: 33%%" align="center">
<a href="index.html">Contents</a>
</td>
<td style="width: 33%%" align="right">
%(next)s
</td>
</tr>
</table>\n""" %
             {"prev": prev_book_link,
              "next": next_book_link})
            
    return html

def wrap_page(title, content):
    return """<html>
<head>
<title>%(title)s</title>
<link rel="stylesheet" media="only screen and (max-width: 480px)" href="bible-mobile.css" />
<link rel="stylesheet" media="only screen and (min-width: 481px)" href="bible.css" />
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
%(content)s
</body>
</html>""" % {"title": title,
              "content": content}

if __name__ == "__main__":
    with open("index.html", "w") as f:
        f.write(wrap_page("Holy Bible (KJV)", book_list()))

    books = books()

    for book in books:
        with open("%s.html" % book["name"], "w") as f:
            f.write(wrap_page(book["name"],
                              book_html(book["id"])))

