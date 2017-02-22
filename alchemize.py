#!/usr/bin/env python
"""
This script generates web-pages from the html fragments contained in grist/posts/
 and the templates in grist/templates
It generates the index.html to contain an aggregation of some number of recent posts.
It generates an individual page for each post in pages/{date-title}.html
This script also attempts to make sure the resulting pages contain nicely formatted html
"""

import os
import re
import datetime
from collections import namedtuple
import itertools


def safe_filename(s):
    s = s.replace(' ', '_')
    return ''.join(c for c in s if c.isalpha() or c.isdigit() or c in '_-')


def ff(s, vals):
    """
    For use around doc-string style strings
    This removes a leading newline,
    Replaces all {var}-format expressions inside the string.
    """
    s = s.format(**vals)
    # Strip first and last line if empty
    lines = s.split('\n')
    first = 0
    last = len(lines)
    if lines[0].strip() == '':
        first = 1
    if lines[last-1].strip() == '':
        last -= 1
    s = '\n'.join(lines[first:last])
    # Add additional newline to end of new string
    s += '\n'
    return s


def indent(s, depth):
    """
    Indents each line of the string to the given depth using 4 spaces
    Already indented lines will be indented more
    However, if all the lines are already at least indented some amount,
     then that common indentation will be removed from all lines before indenting
    """

    def get_indent(line):
        return sum(1 for _ in itertools.takewhile(lambda c: c in ' \t', line))

    lines = s.split('\n')
    # Detect common indentation 
    common_indentation = min(get_indent(line) for line in lines)
    # Apply indentation
    for i, line in enumerate(lines):
        lines[i] = ' '*depth*4 + line[common_indentation:]
    return '\n'.join(lines)


def strip_empty_lines(s):
    """
    Removes empty lines from the beginning and end of the given paragraph
    """
    lines = s.split('\n')
    for first, line in enumerate(lines):
        if line.strip():
            break
    for last, line in reversed(list(enumerate(lines))):
        if line.strip():
            break
    return '\n'.join(lines[first:last+1])


def main():
    # Read in templates
    with open('grist/templates/header.html', 'rb') as f:
        header = f.read()
    with open('grist/templates/footer.html', 'rb') as f:
        footer = f.read()

    post_filenames = []
    # Gather all posts in grist/posts/ and subdirectories
    for path, dirnames, filenames in os.walk('grist/posts'):
        post_filenames += (os.path.join(path, filename) for filename in filenames if
                filename[0] != '.')

    # How many recent posts to show on the homepage
    number_of_recent_posts = 5
    recent_posts = list()
    posts = list()
    Post = namedtuple('Post', ('title', 'date', 'body', 'filename'))

    # Read in data and metadata from post files
    for filename in post_filenames:
        with open(filename, 'rb') as f:
            # read metadata
            print('parsing ' + filename + '...')
            title = re.match(r'^<title>([^<]*)</title>$', f.readline()).group(1)
            date = re.match(r'^<date>([^<]*)</date>$', f.readline()).group(1)
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            body = f.read().strip()
            # Remove starting and ending body tags
            body = body[len('<body>'):-len('</body>')]
            # Format body so that the html looks good (This is a site for programmers, not robots)
            body = strip_empty_lines(body)
            body = indent(body, 4)
            post_filename = date.strftime('%Y-%m-%d') + '-' + safe_filename(title) + '.html'
            posts.append(Post(title, date, body, post_filename))

    # Generate header side post links
    side_posts = list()
    for post in sorted(posts, key=lambda p: p.date, reverse=True):
        side_posts.append('            <a class="side side_post" href="/pages/{}">{}</a><br/>'.format(post.filename, post.title))
    side_posts = '\n'.join(side_posts)
    header = header.format(side_posts=side_posts)

    # Generate page for post
    for post in sorted(posts, key=lambda p: p.date, reverse=True):
        with open(os.path.join('pages/', post.filename), 'wb') as w:
            w.write(header)
            w.write(ff("""
        <h1>{post.title}</h1>
        <div style="width:auto; height:1px; background-color:#00ff00; margin-bottom:10px;"></div><br/>
        <div class="article">
{post.body}
        </div>
                """, locals()))
            w.write(footer)

        # Remember for homepage
        if len(recent_posts) < number_of_recent_posts:
            recent_posts.append(post)
        elif post.date > min(recent.date for recent in recent_posts):
            # replace oldest post
            oldest_index = min((recent.date, i) for i, recent in enumerate(recent_posts))[1]
            recent_posts[oldest_index] = post

    # Generate index.html
    with open('index.html', 'wb') as homepage:
        homepage.write(header)
        homepage.write(ff("""
            <h1>News</h1>
            <div style="width:auto; height:1px; background-color:#00ff00; margin-bottom:10px;"></div><br/>
            """, locals()))
        for post in sorted(recent_posts, key=lambda p: p.date, reverse=True):
            body = indent(post.body, 4)
            homepage.write(ff("""
            <div class="article">
            <h2><a href=pages/{post.filename}>{post.title}</a></h2>
            <div>
{body}
            </div>
                """, locals()))
        homepage.write(footer)

    # Read images.meta
    Image = namedtuple('Image', ('filename', 'alt_text', 'gallery_title'))
    images = list()
    print('Reading grist/images.meta...')
    with open('grist/images.meta', 'r') as image_manifest:
        for line in image_manifest:
            line = line.strip()
            if not line or line[0] == '%':
                continue
            filename, alt_text, gallery_title = (s.strip()
                    for s in line.split(':'))
            images.append(Image(filename, alt_text, gallery_title))
    
    # Warn about files in images/ which do not exist in images.meta
    image_filenames = set(image.filename for image in images)
    for path, dirnames, filenames in os.walk('images'):
        for filename in filenames:
            if filename[0] != '.':
                if filename not in image_filenames:
                    print('WARNING: {} not found in images.meta'.format(filename))

    # Generate gallery.html
    print('Generating gallery.html...')
    with open('gallery.html', 'wb') as gallery:
        gallery.write(header)
        gallery.write(ff("""
            <h1>Gallery</h1>
            <div style="width:auto; height:1px; background-color:#00ff00; margin-bottom:10px;"></div><br/>
            <div class="gallery">
            """, locals()))
        # All the images
        for filename, alt_text, gallery_title in images:
            filename = os.path.join('images/', filename)
            gallery.write(ff("""
                <a class="gallery_frame" href="{filename}">
                    <img class="gallery_image" src="{filename}" alt="{alt_text}"/>
                    <div class="gallery_title">{gallery_title}</div>
                </a>
            """, locals()))
        # Trailer
        gallery.write(ff("""
            </div>
            """, locals()))
        gallery.write(footer)


if __name__ == '__main__':
    main()

