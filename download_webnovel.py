from os import listdir
import os
from os.path import isfile, join
from parsel import Selector
import urllib
import sys, re
import tempfile
import time
import zipfile
import uuid
from tqdm import tqdm

# --- Functions

def help():
    print('# - Usage:')
    print('# -    python download_webnovel.py [-t epub,html] <URL-OF-SERIES>')
    print('# - Arguments:')
    print('# -    -t       output format, e.g. html, epub. can contain multiple values, seperated by comma')
    print('# -    --help   Displays this help')
    exit()
    

def get_novel_metadata(website_data, source_url):
    title = None
    author = 'Unknown'
    book = Selector(website_data)
    if 'royalroad' in source_url:
        try:
            title = book.xpath('/html/body/div[3]/div/div/div/div[1]/div/div[1]/div[2]/div/h1/text()').getall()[0]
        except Exception:
            pass
        try:
            author = book.xpath('/html/body/div[3]/div/div/div/div[1]/div/div[1]/div[2]/div/h4/span[2]/a/text()').getall()[0]
        except Exception:
            pass
    elif 'novelhall' in source_url:
        try:
            title = book.xpath('/html/body/section[1]/div/div[1]/div[2]/h1/text()').getall()[0]
        except Exception:
            pass
        try:
            author = book.xpath('/html/body/section[1]/div/div[1]/div[2]/div[1]/span[1]/text()').getall()[0].replace('Author：', '')
        except Exception:
            pass
        
    return {'title': title, 'author': author}

def get_chapters(website_data, source_url):
    chapters = None
    book = Selector(website_data)
    if 'royalroad' in source_url:
        chapters = book.xpath('//*[@id="chapters"]/tbody/tr/td/a/@href').getall()
    elif 'novelhall' in source_url:
        cont = book.xpath('//*[@id="morelist"]').getall()
        for entry in cont:
            chapters = Selector(entry).xpath('//div/ul/li/a/@href').getall()
    return chapters
    
def get_chapter(source_url, chapter_path):
    url = source_url + chapter_path
    chapter_title = ''
    chapter_content = None
    req = urllib.request.Request(
        url, 
        data=None, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
    )
    f = urllib.request.urlopen(req)
    chapter_data = f.read().decode('utf-8')
    chapter_selector = Selector(chapter_data)
    if 'royalroad' in source_url:
        chapter_title = chapter_selector.xpath('/html/body/div[3]/div/div/div/div/div[1]/div/div[2]/h1/text()').getall()[0]
        cont = chapter_selector.xpath("//div[contains(@class, 'chapter-inner chapter-content')]").getall()
        for chapter_part in cont:
            if chapter_content is None:
                chapter_content = ''
            chapter_part = re.sub(r'\<\/p\>\<p.*\<\/p\>', '</p>\r\n', chapter_part)
            chapter_content = '\r\n' + chapter_part
    elif 'novelhall' in source_url:
        chapter_title = chapter_selector.xpath('//article/div[1]/h1/text()').getall()[0]
        cont = chapter_selector.xpath('//*[@id="htmlContent"]').getall()
        for chapter_part in cont:
            if chapter_content is None:
                chapter_content = ''
            chapter_content = chapter_content + '\r\n' + chapter_part
    return chapter_title, chapter_content

def zip_directory(directory_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w') as archive:
        if os.path.exists(directory_path + os.sep + 'mimetype'):
            archive.write(directory_path + os.sep + 'mimetype', "mimetype")
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file == 'mimetype':
                    continue
                archive.write(os.path.join(root, file), 
                           os.path.relpath(os.path.join(root, file), os.path.join(directory_path)))

def output_epub(metadata, chapters):
    print('# - Publishing epub...')
    uuid_str = str(uuid.uuid4())
    temp_dir = tempfile.TemporaryDirectory()
    os.mkdir(temp_dir.name + os.sep + 'META-INF')
    with open(temp_dir.name + os.sep + 'META-INF' + os.sep + 'container.xml', 'w', encoding='utf-8') as container_xml:
        container_xml.write('''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
   <rootfiles>
      <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
      
   </rootfiles>
</container>
    ''')
    with open(temp_dir.name + os.sep + 'mimetype', 'w', encoding='utf-8') as container_xml:
        container_xml.write('''application/epub+zip''')
    toc = []
    padding = len(str(len(chapters)))
    ch_idx = 1
    for i in tqdm(range(len(chapters)), desc='# - Processing Chapters'):
        chapter = chapters[i]
        chapter_title = chapter['title']
        chapter_content = chapter['content']
        toc.append(str(ch_idx).zfill(padding) + '.html')
        # Write Chapter HTML
        with open(temp_dir.name + os.sep + str(ch_idx).zfill(padding) + '.html', 'w', encoding='utf-8') as chapter_html:
            chapter_html.write('''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>''' + chapter_title + '''</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
</head>
<body>
<div>''')
            chapter_html.write('<h1>' + str(chapter_title) + '</h1>\r\n');
            chapter_html.write(str(chapter_content.replace('<br>', '<br/>')))
            chapter_html.write('''
</div></body></html>''')
        ch_idx = ch_idx + 1
    # Wirte ncx file
    with open(temp_dir.name + os.sep + 'toc.ncx', 'w', encoding='utf-8') as toc_ncx:
            toc_ncx.write('''<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="de">
    <head>
        <!-- Hier kommt die Buchidentifikation aus content.opf hinein. -->
        <meta name="dtb:uid" content="''' + uuid_str + '''" />
        <meta content="0" name="dtb:totalPageCount" />
        <meta content="0" name="dtb:maxPageNumber" />
    </head>
    <!-- Hier kommt der Buchtitel hinein. -->
    <docTitle>
        <text>''' + metadata['title'] + '''</text>
    </docTitle>
    <!-- Hier kommt der Autorenname hinein. -->
    <docAuthor>
        <text>Unknown</text>
    </docAuthor>
    <navMap>''')
            ch_idx = 1
            padding = len(str(len(chapters)))
            for chapter in chapters:
                chapter_title = chapter['title']
                chapter_content = chapter['content']
                toc_ncx.write('''        <navPoint id="kapitel_''' + str(ch_idx) + '''" playOrder="''' + str(ch_idx) + '''">
            <navLabel>
                <text>''' + chapter_title + '''</text>
            </navLabel>
            <content src="''' + str(ch_idx).zfill(padding) + '.html' + '''"/>
        </navPoint>
''')
                ch_idx = ch_idx + 1
            toc_ncx.write('''        </navMap>
</ncx>''')
            
    content_opf = '''<?xml version='1.0' encoding='utf-8'?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uuid_id">
  <metadata xmlns:opf="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:calibre="http://calibre.kovidgoyal.net/2009/metadata">
    <dc:language>en</dc:language>
    <dc:title>''' + metadata['title'] + '''</dc:title>
    <dc:contributor opf:role="bkp">calibre (5.35.0) [https://calibre-ebook.com]</dc:contributor>
    <meta name="calibre:timestamp" content="2024-02-19T21:28:09.816300+00:00"/>
    <dc:identifier id="uuid_id" opf:scheme="uuid">''' + uuid_str + '''</dc:identifier>
    <dc:identifier opf:scheme="calibre">67454d07-b70c-4a94-ac60-e797793a2849</dc:identifier>
    <dc:creator opf:role="aut">''' + metadata['author'] + '''</dc:creator>
    <meta name="calibre:title_sort" content="Infrasound Berserker"/>
    <dc:date>0101-01-01T00:00:00+00:00</dc:date>
    <meta name="cover" content="cover"/>
  </metadata>
  <manifest>
'''
    # Generate Manifest
    for entry in toc:
        content_opf = content_opf + '    <item id="html' + entry.replace('.html', '') + '" href="' + entry + '" media-type="application/xhtml+xml"/>\n'
    content_opf = content_opf + '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
    content_opf = content_opf + '  </manifest>\n'
    # Generate toc
    content_opf = content_opf + '  <spine toc="ncx">\n'
    for entry in toc:
        content_opf = content_opf + '    <itemref idref="html' + entry.replace('.html', '') + '"/>\n'
    content_opf = content_opf + '  </spine>\n</package>\n'
    # Write content.opf file
    with open(temp_dir.name + os.sep + 'content.opf', 'w', encoding='utf-8') as container_xml:
        container_xml.write(content_opf)
    # Write mimetype file
    with open(temp_dir.name + os.sep + 'mimetype', 'w', encoding='utf-8') as container_xml:
        container_xml.write('''application/epub+zip''')
    zip_directory(temp_dir.name, metadata['title'] + '.epub')
    temp_dir.cleanup()
    print('# - Epub created: ' + metadata['title'] + '.epub')

def output_html(metadata, chapters):
    print('# - Publishing html...')
    with open( metadata['title'] + '.html', 'w', encoding='utf-8') as book_file:
        book_file.write('<html><body>\r\n');
        for i in tqdm(range(len(chapters)), desc='# - Processing Chapters'):
            chapter = chapters[i]
            book_file.write('<div>\r\n');
            book_file.write('<h1>' + str(chapter['title']) + '</h1>\r\n');
            book_file.write(str(chapter['content']))
            book_file.write('</div>\r\n');
        book_file.write('</body></html>\r\n');  
    print('# - HTML created: ' + metadata['title'] + '.html')  

# --- Main Programm

output = 'epub'

print('# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #')
print('#                  Webnovel Downloader v0.1                      #')
print('#              Supports royalroad and novelhall                  #')
print('# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #')

if '--help' in sys.argv:
    help()

if '-t' in sys.argv:
    output = sys.argv[sys.argv.index('-t')+1]

print('# - Output(s) selected: ' + output)

link = sys.argv[len(sys.argv)-1]

source_url = 'https://www.royalroad.com' if 'www.royalroad.com' in link else 'https://www.novelhall.com' if 'https://www.novelhall.com' in link else None

if source_url is None:
    print('# - Unknown site: ' + link)
    exit(1)
 
print('# - Reading novel from: royalroad' if 'royalroad' in source_url else '# - Reading novel from: novelhall')

print('# - Novel URL:          ' + link) 

req = urllib.request.Request(
    link, 
    data=None, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    }
)
f = urllib.request.urlopen(req)
website_data = f.read().decode('utf-8')
book = Selector(website_data)

# -- Load Metadata

novel_metadata = get_novel_metadata(website_data, source_url)
chapter_links = get_chapters(website_data, source_url)


print('# - Book Title:         ' + novel_metadata['title']) 
print('# - Author:             ' + novel_metadata['author']) 

# --- Read Chapters

read_chapters = []
chapters = []
for i in tqdm(range(len(chapter_links)), desc='# - Downloading Chapters'):
    link = chapter_links[i]
    if link in read_chapters:
        continue
    read_chapters.append(link)
    chapter_title, chapter_content = get_chapter(source_url, link)
    chapters.append({'title': chapter_title, 'content': chapter_content})

# --- Output

if 'epub' in output:
    output_epub(novel_metadata, chapters)
if 'html' in output:
    output_html(novel_metadata, chapters)
    