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


class JungleSpider(BaseSpider):
    """Spider for jungle.world"""
    name = 'jungle'
    rotate_user_agent = True
    allowed_domains = ['jungle.world']
    start_urls = ['https://jungle.world/']

    # Exclude pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'jungle\.world\/artikel\/.*'),
                    deny=(r'jungle\.world\/abo')
                    ),
                callback='parse_item',
                follow=True
                ),
            )

    def parse_item(self, response):
        """
        Checks article validity. If valid, it parses it.
        """
        
        if 'Anmeldung erforderlich' in response.xpath('//meta[@name="dcterms.title"]/@content').get():
            return

        # Check if page is duplicate
        if '?page=' in response.url:
            return

        # Check date validity 
        creation_date = response.xpath('//div/span[@class="date"]/text()').get()
        if not creation_date:
            return
        creation_date = creation_date.strip()
        if creation_date == '':
            return
        creation_date = datetime.strptime(creation_date, '%d.%m.%Y')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="lead"] | //p[not(ancestor::div[@class="caption"]) and not(descendant::a[@class="btn btn-default scrollTop"])]')]
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
        
        item['news_outlet'] = 'jungle'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        authors = response.xpath('//meta[@name="dcterms.publisher"]/@content').get()
        item['author_person'] = authors.split(', ') if authors else list()
        item['author_organization'] = list()

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get().split(' • ')[0]

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        # The articles have no headlines, just paragraphs
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}
      
        # No recommendations related to the current article available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
