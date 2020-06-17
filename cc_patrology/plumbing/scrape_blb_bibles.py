
import time
import os
import json

import requests
from bs4 import BeautifulSoup

books = [
    "Gen", "Exo", "Lev", "Num", "Deu", "Jos", "Jdg", "Rth", "1Sa",
    "2Sa", "1Ki", "2Ki", "1Ch", "2Ch", "Ezr", "Neh", "Est", "Job", "Psa", "Pro", "Ecc",
    "Sng", "Isa", "Jer", "Lam", "Eze", "Dan", "Hos", "Joe", "Amo", "Oba", "Jon", "Mic",
    "Nah", "Hab", "Zep", "Hag", "Zec", "Mal", "Mat", "Mar", "Luk", "Jhn", "Act", "Rom",
    "1Co", "2Co", "Gal", "Eph", "Phl", "Col", "1Th", "2Th", "1Ti", "2Ti", "Tit", "Phm"]


def get_verses(url, lxx=False):
    soup = BeautifulSoup(requests.get(url).content)
    table = soup.find("div", {'id': "bibleTable"})
    verses = []
    for div in table.find_all("div"):
        if div.attrs.get('id', '').startswith('verse'):
            _, v_id, text = div.find_all('div', {'class': 'columns'})
            v_id = v_id.text.strip()
            text = text.find('div').text
            verses.append((v_id, text))

    return verses


if __name__ == '__main__':
    url_builder = "https://www.blueletterbible.org/{}/{}/{}/1".format
    last = None

    done = set()
    if os.path.isfile('output/blb.json'):
        with open('output/blb.json') as f:
            for line in f:
                line = json.loads(line.strip())
                done.add(line['url'])

    print("{} already done".format(len(done)))

    with open('output/blb.json', 'a+') as f:
        for bible in ['vul', 'lxx']:
            for book in books:
                chapter = 1
                repeats = 0
                while repeats < 3:
                    print(bible, book, chapter)
                    try:
                        url = url_builder(bible, book, chapter)
                        if url in done:
                            chapter += 1
                            continue
                    except Exception as e:
                        print(url, e)
                        chapter += 1
                        continue
                    verses = get_verses(url, lxx=bible == 'lxx')
                    if verses == last:
                        repeats += 1
                    else:
                        f.write(json.dumps({"url": url, "verses": verses},
                                           ensure_ascii=False) + '\n')
                    last = verses
                    chapter += 1
                # print("sleeping 10")
                # time.sleep(10)
