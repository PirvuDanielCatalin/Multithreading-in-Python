import asyncio
import aiohttp
import re

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
        print('\nRequest on: {}'.format(url))

        async with self.semaphore:
            tries = 3
            while True:
                if tries == 0:
                    break

                tries = tries - 1

                try:
                    async with self.session.get(url, timeout=30, ssl=False) as response:

                        first_chunk_was_taken = False
                        data = None
                        list_of_found_urls = []

                        while True:
                            chunk = await response.content.read(2000)

                            if not first_chunk_was_taken:
                                data = chunk.decode().replace('\n', ' ').replace('\r', '')
                                first_chunk_was_taken = True

                            if not chunk:
                                break

                            decoded = chunk.decode().replace('\n', ' ').replace('\r', '')

                            regex_pattern = r'<a[ ]+href="(.+?)".+?>.*?<\/a>'
                            anchors = re.findall(regex_pattern, decoded)

                            if anchors != []:
                                for href in anchors:
                                    url = urljoin(self.base_url, href)

                                    if url not in self.seen_urls and url.startswith(self.base_url):
                                        list_of_found_urls.append(url)
                                    
                                    print("*************************")
                                    print(url)
                                    print("*************************")
                                    print(self.seen_urls)
                                    print(url not in self.seen_urls)
                                    print(url.startswith(self.base_url))
                                    print("*************************")
                                    print(list_of_found_urls)
                                    print("*************************")

                        page_code = await response.read()
                        return page_code 

                        return data, list_of_found_urls
                except Exception as e:
                    print(
                        'An exception was caught when trying to get HTML data from the URL {}: {}'.format(url, e))

    async def single_extract(self, url):
        data, list_of_found_urls = await self.request_on_url(url)

        if data:
            for url in list_of_found_urls:
                list_of_found_urls.add(url)

        print(list_of_found_urls)
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
        regex_pattern = r'<title>(.*?)<\/title>'
        title = re.findall(regex_pattern, data)[0]
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

    # loop.close()

    result = future.result()

    print("\n##########################")
    print('Length of the result is {}'.format(len(result)))
    print('A sample of the result is ')
    for res in result[: 20]:
        print(res)
    print("##########################")
