
import os
import re
import urllib.request
from lxml import etree
from bs4 import BeautifulSoup

TOC = "http://www.perseus.tufts.edu/hopper/xmltoc?doc=Perseus%3Atext%3A1999.02.0060"


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='output/vulgate/source')
    args = parser.parse_args()

    toc = etree.fromstring(urllib.request.urlopen(TOC).read()).getroottree()

    targets = []
    for chunk in toc.findall("chunk"):
        targets.append(chunk.attrib['ref'])

    if not os.path.isdir(args.target):
        os.makedirs(args.target)

    for target in targets:
        url = 'http://www.perseus.tufts.edu/hopper/text?doc=' + target
        try:
            html = BeautifulSoup(urllib.request.urlopen(url).read(), 'html.parser')
        except Exception as e:
            print("oops at ", url, str(e))
            continue
        name = html.find(name='span', attrs={'class': 'title'}).text
        name = '_'.join(name.split())

        for idx, chapter in enumerate(html.findAll('a', title=re.compile("chapter .*"))):
            filename = os.path.join(args.target, '{}.{}.xml'.format(name, idx + 1))
            if os.path.isfile(filename):
                print("skipping", filename)
                continue
            url = re.sub('%[^%]*verse.*', '', chapter.get('href'))
            url = 'http://www.perseus.tufts.edu/hopper/xmlchunk' + url
            try:
                urllib.request.urlretrieve(url, filename=filename)
            except Exception as e:
                print("oops at " + filename, url, str(e))
