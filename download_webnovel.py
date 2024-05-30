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
import math
from pathlib import Path
import json
import re

# --- Functions

cache_dir = os.path.join(str(Path.home()), ".webnove_downloader", "cache")
book_dir = os.path.join(str(Path.home()), ".webnove_downloader", "books")

cache_enabled = True

def get_cached_chapter(novel, chapter_name):
    if cache_enabled:
        cached_chapter = os.path.join(cache_dir, re.sub(r'[^\w_. -]', '_', novel), re.sub(r'[^\w_. -]', '_', chapter_name) + '.json')
        if os.path.isfile(cached_chapter):
            with open(cached_chapter, 'r', encoding='utf-8') as cached_file:
                return json.load(cached_file)
    return None

def write_cached_chapter(novel, chapter_name, content):
    if cache_enabled:
        cached_chapter = os.path.join(cache_dir, re.sub(r'[^\w_. -]', '_', novel), re.sub(r'[^\w_. -]', '_', chapter_name) + '.json')
        os.makedirs(os.path.join(cache_dir, re.sub(r'[^\w_. -]', '_', novel)), exist_ok=True)
        with open(cached_chapter, 'w', encoding='utf-8') as cached_file:
            cached_file.write(json.dumps(content))
    return content

def write_book_metadata(novel_metadata):
    book_metadata_file = os.path.join(book_dir, re.sub(r'[^\w_. -]', '_', novel_metadata['title']) + '.json')
    os.makedirs(book_dir, exist_ok=True)
    with open(book_metadata_file, 'w', encoding='utf-8') as cached_file:
        cached_file.write(json.dumps(novel_metadata, indent=4))

def files(path):
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            yield file
            
def get_saved_books():
    os.makedirs(book_dir, exist_ok=True)
    books = []
    for book_metadata_file in files(book_dir):
       with open(os.path.join(book_dir, book_metadata_file), 'r', encoding='utf-8') as book_metadata:
         books.append(json.load(book_metadata))
    return books


def help(exit_code=0):
    print('# - Usage:')
    print('# -    python download_webnovel.py [-t epub,html] [-s 100] [-o <PATH>] <URL-OF-SERIES>')
    print('# -')
    print('# - Arguments:')
    print('# -    -t          Output format, e.g. html, epub. can contain multiple values, seperated by comma')
    print('# -    -s <NUMBER> Split the novel into parts, the number after the parameter defines how many chapters each part has')
    print('# -    -o <PATH>   Outputs novel to a specific path, use %i in the path when splitting the novel in seperate parts')
    print('# -    --help      Displays this help')
    print('# -    --no-cache  Diables caching')
    print('# -')
    print('# - Example:')
    print('# -')
    print('# -   python download_webnovel.py -s 100 -t epub -o "test\\Test Part %i.epub" https://www.royalroad.com/fiction/12345/test')
    print('# -')
    print('# - Example 2, providing no url will show the already downlaoded books and provide the possibillity to update/redownload them:')
    print('# -')
    print('# -   python download_webnovel.py -s 100 -t epub')
    print()
    exit(exit_code)
    
def htmlescape(text):
    return text.replace('[', ' ').replace(']', ' ')

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
        print('# - Creating epub...')
        for root, dirs, files in os.walk(directory_path):
            for i in tqdm(range(len(files)), desc='    Compressing files'):
                file = files[i]
                if file == 'mimetype':
                    continue
                archive.write(os.path.join(root, file), 
                           os.path.relpath(os.path.join(root, file), os.path.join(directory_path)), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

def output_epub(metadata, chapters):
    print('# - Publishing epub...')
    uuid_str = str(uuid.uuid4())
    temp_dir = tempfile.TemporaryDirectory()
    os.mkdir(temp_dir.name + os.sep + 'META-INF')
    with open(temp_dir.name + os.sep + 'META-INF' + os.sep + 'container.xml', 'w', encoding='utf-8') as container_xml:
        container_xml.write('''<?xml version="1.0"?>\n''')
        container_xml.write('''<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n''')
        container_xml.write('''<rootfiles>\n''')
        container_xml.write('''      <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>\n''')
        container_xml.write('''   </rootfiles>\n''')
        container_xml.write('''</container>\n''')
    with open(temp_dir.name + os.sep + 'mimetype', 'w', encoding='utf-8') as container_xml:
        container_xml.write('''application/epub+zip''')
    toc = []
    padding = len(str(len(chapters)))
    ch_idx = 1
    for i in tqdm(range(len(chapters)), desc='# - Processing Chapters'):
        chapter = chapters[i]
        chapter_title = htmlescape(chapter['title'])
        chapter_content = chapter['content']
        toc.append(str(ch_idx).zfill(padding) + '.html')
        # Write Chapter HTML
        with open(temp_dir.name + os.sep + str(ch_idx).zfill(padding) + '.html', 'w', encoding='utf-8') as chapter_html:
            chapter_html.write('''<?xml version='1.0' encoding='utf-8'?>\n''')
            chapter_html.write('''<html xmlns="http://www.w3.org/1999/xhtml">\n''')
            chapter_html.write('''  <head>\n''')
            chapter_html.write('''    <title>''' + chapter_title + '''</title>\n''')
            chapter_html.write('''    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n''')
            chapter_html.write('''<body>\n''')
            chapter_html.write('''<div>''')
            chapter_html.write('''<h1>''' + str(chapter_title) + '''</h1>\r\n''');
            chapter_html.write(str(chapter_content.replace('<br>', '<br/>')))
            chapter_html.write('''\n''')
            chapter_html.write('''</div></body></html>''')
        ch_idx = ch_idx + 1
    # Wirte ncx file
    with open(temp_dir.name + os.sep + 'toc.ncx', 'w', encoding='utf-8') as toc_ncx:
            toc_ncx.write('''<?xml version='1.0' encoding='UTF-8'?>\n''')
            toc_ncx.write('''<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n''')
            toc_ncx.write('''<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="de">\n''')
            toc_ncx.write('''    <head>\n''')
            toc_ncx.write('''        <meta name="dtb:uid" content="''' + uuid_str + '''" />\n''')
            toc_ncx.write('''        <meta content="0" name="dtb:totalPageCount" />\n''')
            toc_ncx.write('''        <meta content="0" name="dtb:maxPageNumber" />\n''')
            toc_ncx.write('''    </head>\n''')
            toc_ncx.write('''    <docTitle>\n''')
            toc_ncx.write('''        <text>''' + htmlescape(metadata['title']) + '''</text>\n''')
            toc_ncx.write('''    </docTitle>\n''')
            toc_ncx.write('''    <docAuthor>\n''')
            toc_ncx.write('''        <text>''' + htmlescape(metadata['author']) + '''</text>\n''')
            toc_ncx.write('''    </docAuthor>\n''')
            toc_ncx.write('''    <navMap>\n''')
            ch_idx = 1
            padding = len(str(len(chapters)))
            for chapter in chapters:
                chapter_title = htmlescape(chapter['title'])
                chapter_content = chapter['content']
                toc_ncx.write('''        <navPoint id="kapitel_''' + str(ch_idx) + '''" playOrder="''' + str(ch_idx) + '''">\n''')
                toc_ncx.write('''            <navLabel>\n''')
                toc_ncx.write('''                <text>''' + chapter_title + '''</text>\n''')
                toc_ncx.write('''            </navLabel>\n''')
                toc_ncx.write('''            <content src="''' + str(ch_idx).zfill(padding) + '.html' + '''"/>\n''')
                toc_ncx.write('''        </navPoint>\n''')
                ch_idx = ch_idx + 1
            toc_ncx.write('''    </navMap>\n''')
            toc_ncx.write('''</ncx>''')
            
    content_opf =               "<?xml version='1.0' encoding='utf-8'?>\n"
    content_opf = content_opf + '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="uuid_id">\n'
    content_opf = content_opf + '  <metadata xmlns:opf="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:calibre="http://calibre.kovidgoyal.net/2009/metadata">\n'
    content_opf = content_opf + '    <dc:language>en</dc:language>\n'
    content_opf = content_opf + '    <dc:title>' + htmlescape(metadata['title']) + '</dc:title>\n'
    content_opf = content_opf + '    <dc:contributor opf:role="bkp">download_webnovel.py</dc:contributor>\n'
    content_opf = content_opf + '    <meta name="calibre:timestamp" content="2024-02-19T21:28:09.816300+00:00"/>\n'
    content_opf = content_opf + '    <dc:identifier id="uuid_id" opf:scheme="uuid">' + uuid_str + '</dc:identifier>\n'
    content_opf = content_opf + '    <dc:creator opf:role="aut">' + htmlescape(metadata['author']) + '</dc:creator>\n'
    content_opf = content_opf + '    <meta name="calibre:title_sort" content="' + htmlescape(metadata['title']) + '"/>\n'
    if 'series_index' in metadata:
        content_opf = content_opf + '    <<meta name="calibre:series_index" content="' + htmlescape(metadata['series_index']) + '"/>\n'
    if 'series' in metadata:
        content_opf = content_opf + '    <<meta name="calibre:series" content="' + htmlescape(metadata['series']) + '"/>\n'
    content_opf = content_opf + '    <dc:date>0101-01-01T00:00:00+00:00</dc:date>\n'
    content_opf = content_opf + '    <meta name="cover" content="cover"/>\n'
    content_opf = content_opf + '  </metadata>\n'
    content_opf = content_opf + '  <manifest>\n'
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
    #print(metadata)
    epub_file = re.sub(r'[^\w_. -]', '_', metadata['file_name']['epub'])
    zip_directory(temp_dir.name, epub_file)
    temp_dir.cleanup()
    print('# - Epub created: ' + epub_file)

def output_html(metadata, chapters):
    print('# - Publishing html...')
    html_file = re.sub(r'[^\w_. -]', '_', metadata['file_name']['html'])
    with open( html_file, 'w', encoding='utf-8') as book_file:
        book_file.write('<html><body>\r\n');
        for i in tqdm(range(len(chapters)), desc='# - Processing Chapters'):
            chapter = chapters[i]
            book_file.write('<div>\r\n');
            book_file.write('<h1>' + str(chapter['title']) + '</h1>\r\n');
            book_file.write(str(chapter['content']))
            book_file.write('</div>\r\n');
        book_file.write('</body></html>\r\n');  
    print('# - HTML created: ' + html_file)  

# --- Main Programm

output = 'epub'

print('# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #')
print('#                  Webnovel Downloader v0.2                      #')
print('#              Supports royalroad and novelhall                  #')
print('# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #')

segmentate = False
chapter_per_segment = 100
output_override = False
output = 'epub'

if '--help' in sys.argv:
    help()

if '--no-cache' in sys.argv:
    cache_enabled = False
    sys.argv.remove('--no-cache')

# Change the output type
if '-t' in sys.argv:
    output = sys.argv[sys.argv.index('-t')+1]

# Split Novel into Segments of Chapters
if '-s' in sys.argv:
    try:
        segmentate = True
        chapter_per_segment = int(sys.argv[sys.argv.index('-s')+1])
    except ValueError as valErr:
        print('# - Argument after -s must be an integer (you provided: {arg})'.format(arg=sys.argv[sys.argv.index('-s')+1]))
        print('# - exiting...')
        exit(2)
    sys.argv.remove(sys.argv[sys.argv.index('-s')+1])
    sys.argv.remove('-s')
        
# Change the output destination
if '-o' in sys.argv:
    output_override = True
    output = sys.argv[sys.argv.index('-o')+1]
    sys.argv.remove(sys.argv[sys.argv.index('-o')+1])
    sys.argv.remove('-o')

print('# - Output(s) selected: ' + output)

link = sys.argv[len(sys.argv)-1]       
source_url = 'https://www.royalroad.com' if 'www.royalroad.com' in link else 'https://www.novelhall.com' if 'https://www.novelhall.com' in link else None
     
if source_url is None:
    books = get_saved_books()
    if len(books) == 0:
        print('# - Unknown site: ' + link)
        help(1)
    else:
        print('# - No valid URL provided')
        print('# - Known books: ')
        counter = 0
        for book in books:
            print(('#   * {:0' + str(len(str(len(books)))) + 'd} - ').format(counter) + book['title'])
            counter = counter + 1
        print('# - Choos from 0 to ' + str(len(books)) + ' to update one of the books, type c for cancel')
        choice = input('# > ')
        if 'c' == choice:
            help(1)
        else:
            try:
                book_no = int(choice)
            except ValueError as valErr:
                print('# - Input not a number or c')
                print('# - exiting...')
                exit(2)
            if book_no < 0 or book_no > len(books):
                print('# - Input outside of range')
                print('# - exiting...')
                exit(2)
            link = books[book_no]['novel_url']
        
source_url = 'https://www.royalroad.com' if 'www.royalroad.com' in link else 'https://www.novelhall.com' if 'https://www.novelhall.com' in link else None
        
        
 
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
novel_metadata['novel_url'] = link
chapter_links = get_chapters(website_data, source_url)
novel_metadata['file_name'] = dict(
    epub = (novel_metadata['title'] if not output_override else output) + '.epub',
    html = (novel_metadata['title'] if not output_override else output) + '.html'
)

print('# - Book Title:         ' + novel_metadata['title']) 
print('# - Author:             ' + novel_metadata['author']) 

write_book_metadata(novel_metadata)

# --- Read Chapters

read_chapters = []
chapters = []
chapter_links_dedup = []
[chapter_links_dedup.append(x) for x in chapter_links if x not in chapter_links_dedup]
for i in tqdm(range(len(chapter_links_dedup)), desc='# - Downloading Chapters', unit='Ch'):
    link = chapter_links_dedup[i]
    if link in read_chapters:
        continue
    read_chapters.append(link)
    chapter = get_cached_chapter(novel_metadata['title'], link)
    if chapter is not None:
        chapter_title, chapter_content = [chapter['title'], chapter['content']]
    else:
        chapter_title, chapter_content = get_chapter(source_url, link)
        write_cached_chapter(novel_metadata['title'], link, {'title': chapter_title, 'content': chapter_content})
    chapters.append({'title': chapter_title, 'content': chapter_content})

# --- Split chapters fur segmentation
parts = []
if segmentate:
    segment = []
    part = 1
    part_padding = len(str(math.ceil((len(chapters)+0.0)/chapter_per_segment)))
    for i in range(len(chapters)):
        if len(segment) < chapter_per_segment:
            segment.append(chapters[i])
        else:
            part_name = novel_metadata['title'] + ' Part ' + str(part).zfill(part_padding)
            file_names = dict(
                epub = (part_name if not output_override else output.replace('%i', str(part).zfill(part_padding))) + '.epub',
                html = (part_name if not output_override else output.replace('%i', str(part).zfill(part_padding))) + '.html'
            )
            file_names['epub'] = file_names['epub'].replace('.epub.epub', '.epub')
            file_names['epub'] = file_names['epub'].replace('.html.epub', '.epub')
            file_names['html'] = file_names['html'].replace('.html.html', '.html')
            file_names['html'] = file_names['html'].replace('.epub.html', '.html')
            file_names['epub'] = re.sub(r'[^\w_. -]', '_', file_names['epub'])
            file_names['html'] = re.sub(r'[^\w_. -]', '_', file_names['html'])
            part_metadata = dict(
                title = part_name,
                author = novel_metadata['author'],
                series = novel_metadata['title'],
                series_index = str(part),
                file_name = file_names
            )
            parts.append({'metadata': part_metadata, 'chapters': segment})
            part = part + 1
            segment = []
            segment.append(chapters[i])
    if len(segment) > 0:
        file_names = dict(
            epub = (part_name if not output_override else output.replace('%i', str(part).zfill(part_padding))) + '.epub',
            html = (part_name if not output_override else output.replace('%i', str(part).zfill(part_padding))) + '.html'
        )
        file_names['epub'] = file_names['epub'].replace('.epub.epub', '.epub')
        file_names['epub'] = file_names['epub'].replace('.html.epub', '.epub')
        file_names['html'] = file_names['html'].replace('.html.html', '.html')
        file_names['html'] = file_names['html'].replace('.epub.html', '.html')
        file_names['epub'] = re.sub(r'[^\w_. -]', '_', file_names['epub'])
        file_names['html'] = re.sub(r'[^\w_. -]', '_', file_names['html'])
        part_metadata = dict(
            title = novel_metadata['title'] + ' Part ' + str(part).zfill(part_padding),
            author = novel_metadata['author'],
            series = novel_metadata['title'],
            series_index = str(part),
            file_name = file_names
        )
        parts.append({'metadata': part_metadata, 'chapters': segment})
else:
    parts.append({'metadata': novel_metadata, 'chapters': chapters})


# --- Output
for part in parts:
    if 'epub' in output:
        output_epub(part['metadata'], part['chapters'])
    if 'html' in output:
        output_html(part['metadata'], part['chapters'])
    