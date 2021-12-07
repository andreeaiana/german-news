# -*- coding: utf-8 -*-

import os
import sys
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule
from scrapy.linkextractors import LinkExtractor
from datetime import datetime
import dateparser

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class DeSott(BaseSpider):
    """Spider for DeSott"""
    name = 'de_sott'
    rotate_user_agent = True
    allowed_domains = ['de.sott.net']
    start_urls = ['https://de.sott.net/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                        allow=(r'de\.sott\.net\/article\/\w.*$'),
                    deny=(r'de\.sott\.net\/page\/1\-Uber\-Sott\-net',
                        r'de\.sott\.net\/page\/3\-Unterstutzen\-Sie\-SOTT\-net',
                        r'de\.sott\.net\/page\/2\-Sott\-net\-Archiv',
                        r'de\.sott\.net\/pics\-of\-day',
                        r'de\.sott\.net\/quirks'
                        )
                    ),
                callback='parse_item',
                follow=True
                ),
            )

    def parse_item(self, response):
        """
        Checks article validity. If valid, it parses it.
        """
        
        # Check date validity
        creation_date = response.xpath('string(//div[@class="article-info"]//div[@class="m-bar"])').get()
        if not creation_date:
            return
        creation_date = creation_date.split(', ')[-1].split(' UTC')[0]
        creation_date = dateparser.parse(creation_date)
        if not creation_date:
            return
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="article-body"]')]
        paragraphs = paragraphs[0].split('\n')
        paragraphs = [para.strip() for para in paragraphs]
        paragraphs = remove_empty_paragraphs(paragraphs)
        text = ' '.join([para for para in paragraphs])
        
        # Check article's length validity
        if not self.has_min_length(text):
            return

        # Check keywords validity
        if not self.has_valid_keywords(text):
            return

        # Parse the valid article
        item = NewsCrawlerItem()

        item['news_outlet'] = 'de_sott'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        author_person = response.xpath('//div[@class="article-info"]//div[@class="m-bar"]/text()').get()
        author_organization = response.xpath('//div[@class="article-info"]//div[@class="m-bar"]/a/text()').get() 
        item['author_person'] = [author_person] if (author_person and not 'UTC' in author_person) else list()
        item['author_organization'] = [author_organization] if author_organization else list()

        # Extract keywords, if available
        item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().split(' -- Sott.net')[0]
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # Extract first 5 recommendations towards articles from the same news outlet, if available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
