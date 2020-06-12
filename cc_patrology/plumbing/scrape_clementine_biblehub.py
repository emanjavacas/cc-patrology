
import re
import requests
import os
from bs4 import BeautifulSoup

from cc_patrology import utils

ROOT = "https://biblehub.com/vul/"
START = "https://biblehub.com/vul/genesis/1.htm"
STOP = "https://biblehub.com/vul/revelation/22.htm"

if __name__ == '__main__':

    url = START
    n_urls = 0
    verses = {}
    while n_urls < 40000:
        print(url)
        print(len(verses))
        res = requests.get(url)
        soup = BeautifulSoup(res.content)
        for verse in soup.find_all('span', {'class': 'reftext'}):
            text = str(verse.next_sibling).strip()
            if not text:
                print("oops: no text")
                print(verse)
            verse_id = verse.next_element.attrs['href']
            verses[verse_id] = text
        _, post = soup.find('div', {'id': 'topheading'}).find_all('a')
        url = os.path.join(ROOT, post.attrs['href'][3:])
        if url == STOP:
            break
        n_urls += 1

    mapping = utils.read_mapping('clementine.mapping')

    with open('output/clementine.raw.csv', 'w') as f:
        for verse, text in verses.items():
            book, chapter, verse = re.match(
                r'/multi/([^/]+)/([0-9]+)-([0-9]+).*', verse).groups(1)
            book = mapping[book]
            f.write('\t'.join([book, chapter, verse, ' '.join(text.split())]) + '\n')


import collections
collections.Counter(
    [w for l in verses.values() for w in l.strip().split() if 'j' in w])
