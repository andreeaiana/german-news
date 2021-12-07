# -*- coding: utf-8 -*-

import os
import sys
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class KritischesNetzwerk(BaseSpider):
    """Spider for Kritisches Netzwerk"""
    name = 'kritisches_netzwerk'
    rotate_user_agent = True
    allowed_domains = ['kritisches-netzwerk.de']
    start_urls = ['https://kritisches-netzwerk.de/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'kritisches-netzwerk\.de\/\w.*'),
                    deny=(r'kritisches-netzwerk\.de\/content\/',
                        r'kritisches-netzwerk\.de\/user'
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
        creation_date = response.xpath('//meta[@property="article:published_time"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[@class="rtejustify"]')]
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

        item['news_outlet'] = 'kritisches_netzwerk'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        author = response.xpath('//meta[@name="dcterms.creator"]/@content').get()
        item['author_person'] = [author.strip(' - ADMIN')] if author else list()
        item['author_organization'] = list()

        # Extract keywords, if available
        news_keywords = response.xpath('//div[@class="field field-name-field-tags field-type-taxonomy-term-reference field-label-inline clearfix"]//a/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        body[''] = paragraphs
        
        item['content'] = {'title': title, 'description': description, 'body':body}

        # Extract first 5 recommendations towards articles from the same news outlet, if available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
