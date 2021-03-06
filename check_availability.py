# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.crawler import CrawlerProcess
from twisted.internet import reactor
from twisted.internet.task import deferLater
import json
import logging


class CheckAvailabilitySpider(CrawlSpider):
    name = 'check_availability'
    allowed_domains = ['www.supremenewyork.com']
    start_urls = ['https://www.supremenewyork.com/shop/all/']

    rules = (
        Rule(LinkExtractor(
            restrict_xpaths='//*[@id="container"]/article/div/a'), callback='parse_item', follow=True),
    )

    # once opened spider read old data from file
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.data = {}
        try:
            with open('items.json', 'r') as f:
                self.old_data = json.load(f)
        except:
            self.old_data = {}

    # once closed spider write new data to file
    def closed(self, spider):
        with open('items.json', 'w') as f:
            f.write(str(self.data).replace('\'', '\"'))

    # parse and collect new data
    def parse_item(self, response):
        name = response.xpath('//*[@id="details"]/h1/text()').get().replace('"', ' inches')
        color = response.xpath('//*[@id="details"]/p[1]/text()').get().replace('"', ' inches')
        url = response.url
        image = response.urljoin(response.xpath('//*[@id="img-main"]/@src').get())
        price = response.xpath('//span[@itemprop = "price"]/text()').get()

        if response.xpath('//*[@id="add-remove-buttons"]/b[@class="button sold-out"]'):
           sizes = "all sold out"
        else:
            sizes = {}
            for option in response.xpath('//*[@id="size"]/option'):
                size = option.xpath('.//text()').get()
                sizes[size] = 'available'

            if sizes == {}:
                sizes = 'monosize'
                
        # create new dataset
        try:
            self.data[name][color] = {
                    "url": url,
                    "image": image,
                    "price": price,
                    "available sizes": sizes,
                }
        except:
            self.data[name] = {}
            self.data[name][color] = {
                "url": url,
                "image": image,
                "price": price,
                "available sizes": sizes,
            }

        # look for restocks or new items
        if self.old_data != {} and sizes != 'all sold out':
            try:
                old_sizes = self.old_data.get(name).get(color).get("available sizes")
                if sizes != old_sizes:  # restocked size
                    if sizes == 'monosize':
                        logging.info(f'RESTOCK: {name} color {color} just restocked at {price}. Link: {url}')
                    else:
                        different_sizes = { k : sizes[k] for k in set(sizes) - set(old_sizes) }.keys()
                        for s in different_sizes:
                            logging.info(f'RESTOCK: {name} color {color} just restocked in size {s} at {price}. Link: {url}')
            except:  # new item
                if sizes == 'monosize':
                    logging.info(f'NEW ITEM ADDED: {name} color {color} at {price}. Link: {url}')
                else:
                    for s in sizes:
                        logging.info(f'NEW ITEM ADDED: {name} color {color} in size {s} at {price}. Link: {url}')



# ***** SPIDER EXECUTION HERE *****

def sleep(self, *args, seconds):
    return deferLater(reactor, seconds, lambda: None)


def crawl(result, spider):
    d = process.crawl(spider)

    # if uncommented will add delay between each time the spider runs (change seconds to increase or reduce delay between operations)
    # d.addCallback(lambda results: print('waiting 10 seconds before restart...'))
    # d.addCallback(sleep, seconds=10)

    # if uncommented will loop forever and live monitor the availability
    d.addCallback(crawl, spider)
    return d


if __name__ == '__main__':
    # all the spider settings go here
    process = CrawlerProcess({
            'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
            })

    crawl(None, CheckAvailabilitySpider)
    process.start()
