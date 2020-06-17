
import re
import requests
import os
from bs4 import BeautifulSoup

from cc_patrology import utils

ROOT = "https://biblehub.com/vul/"
START = "https://biblehub.com/vul/genesis/1.htm"

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
            text = str(verse.next_sibling)
            text = re.sub(r"<[^>]+", "", text).strip()
            text = ' '.join(text.split())
            if not text:
                print("oops: no text")
                print(verse)
            verse_id = verse.next_element.attrs['href']
            verses[verse_id] = text
        _, post = soup.find('div', {'id': 'topheading'}).find_all('a')
        url = os.path.join(ROOT, post.attrs['href'][3:])
        if url == START:
            break
        n_urls += 1

    mapping = utils.read_mapping('clementine.mapping')

    with open('output/clementine.raw.csv', 'w') as f:
        for verse, text in verses.items():
            book, chapter, verse = re.match(
                r'/multi/([^/]+)/([0-9]+)-([0-9]+).*', verse).groups(1)
            book = mapping[book]
            f.write('\t'.join([book, chapter, verse, ' '.join(text.split())]) + '\n')
