import asyncio
import aiohttp

import re

from lxml import html as html_util

from urllib.parse import urljoin, urlparse


class Crawler:

    def __init__(self, initial_url, depth, no_more_then_y_in_parallel=20):
        self.initial_url = initial_url
        self.base_url = '{}://{}'.format(urlparse(self.initial_url).scheme,
                                         urlparse(self.initial_url).netloc)
        self.depth = depth
        self.seen_urls = set()
        self.session = aiohttp.ClientSession()
        self.semaphore = asyncio.BoundedSemaphore(no_more_then_y_in_parallel)

    async def request_on_url(self, url):
        print(
            "##############################################################################")
        print('Request on: {}'.format(url))
        print(
            "##############################################################################")

        async with self.semaphore:
            tries = 3
            while True:
                tries = tries - 1
                if tries == 0:
                    break

                try:
                    async with self.session.get(url, timeout=30, ssl=False) as response:
                        while True:
                            chunk = await response.content.read(2000)
                            if not chunk:
                                break

                            print("##########################")
                            decoded = chunk.decode().replace('\n', ' ').replace('\r', '')
                            print(decoded)
                            print("##########################")
                            anchors = re.match(
                                r'<a[ ]+href="(.+?)".+?>.*?<\/a>', decoded)
                                
                            if anchors != None:
                                print(anchors.groups())
                            print("##########################\n")

                            print("##########################")
                            De pus primul chunk in ceva pt ca de acolo voi lua titlul
                            De facut Regexul sa mearga si sa preiau paginile din href-uri -> Formez urlurile tot in functia asta si le pun in list_iterator
                            Returnez lista de variabile : primu chunk, list
                            print("##########################")

                            # page_code = await response.content.read(2000)
                            # return page_code

                        page_code = await response.read()
                        return page_code
                except Exception as e:
                    print(
                        'An exception was caught when trying to get HTML data from the URL {}: {}'.format(url, e))

    def find_urls(self, html):
        list_of_found_urls = []

        dom = html_util.fromstring(html)

        for href in dom.xpath('//a/@href'):
            url = urljoin(self.base_url, href)
            if url not in self.seen_urls and url.startswith(self.base_url):
                list_of_found_urls.append(url)

        return list_of_found_urls

    async def single_extract(self, url):
        data = await self.request_on_url(url)

        list_of_found_urls = set()

        if data:
            for url in self.find_urls(data):
                list_of_found_urls.add(url)

        return url, data, list_of_found_urls

    async def multiple_extract(self, go_through):
        futures = []
        results = []

        for url in go_through:
            if url in self.seen_urls:
                continue

            self.seen_urls.add(url)
            futures.append(self.single_extract(url))

        for future in asyncio.as_completed(futures):
            try:
                results.append((await future))
            except Exception as e:
                print(
                    'An exception was caught when trying to wait for the future to finish: {}'.format(e))

        return results

    def parser(self, data):
        dom = html_util.fromstring(data)

        title = dom.xpath('//title')

        # print(title[0].text)

        if title:
            title = title[0].text

        return {'title': title}

    async def crawl_start(self):
        search_area = [self.initial_url]

        results = []

        for depth in range(self.depth + 1):
            load = await self.multiple_extract(search_area)

            search_area = []

            for url, data, found_urls in load:
                data = self.parser(data)
                results.append((depth, url, data))
                search_area.extend(found_urls)

        await self.session.close()

        return results


if __name__ == '__main__':
    url = 'https://a1.ro'

    crawler = Crawler(url, 3)

    future = asyncio.Task(crawler.crawl_start())

    loop = asyncio.get_event_loop()

    loop.run_until_complete(future)

    loop.close()

    result = future.result()

    print("##########################")
    print('Length of the result is {}'.format(len(result)))
    print('A sample of the result is ')
    for res in result[: 20]:
        print(res)
    print("##########################")
