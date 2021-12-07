# -*- coding: utf-8 -*-

import os
import sys
import json
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class MerkurSpider(BaseSpider):
    """Spider for Merkur"""
    name = 'merkur'
    rotate_user_agent = True
    allowed_domains = ['www.merkur.de']
    start_urls = ['https://www.merkur.de/']

    # Exclude pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.merkur\.de\/\w.*\.html$'),
                    deny=(r'www\.merkur\.de\/maerkte\/',
                        r'www\.merkur\.de\/wetter\/',
                        r'www\.merkur\.de\/ueber-uns\/',
                        r'www\.merkur\.de\/videos-fotostrecken\/',
                        r'www\.merkur\.de\/abo\/',
                        r'www\.merkur\.de\/auto\/verkehrsmeldungen\/'
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
        
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if not data_json:
            return
        data = json.loads(data_json)

        # Check date validity 
        if not 'datePublished' in data.keys():
            return
        creation_date = data['datePublished']
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[contains(@class, "id-Article-content-item") and not(contains(@class, "summary")) and not(contains(@class, "copyright"))]')]
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
        
        item['news_outlet'] = 'merkur'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = data['dateModified']
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y') 
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        # Check if the authors are persons
        author_person = response.xpath('//meta[@property="lp.article:author"]/@content').getall()
        if author_person:
            item['author_person'] = author_person
            item['author_organization'] = list()
        else:
            # Check if the author is an organization
            author_organization = data['author']['name']
            author_organization = remove_empty_paragraphs(author_organization)
            item['author_person'] = list()
            item['author_organization'] = author_organization if author_organization else list()

        # No keywords available
        item['news_keywords'] = list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3/span[contains(@class, "id-Article-content-item-headline-text")]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3/span[contains(@class, "id-Article-content-item-headline-text")]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[contains(@class, "id-Article-content-item") and not(contains(@class, "summary")) and not(contains(@class, "copyright"))] | //h3/span[contains(@class, "id-Article-content-item-headline-text")]')]

            # Extract paragraphs between the abstract and the first headline
            body[''] = remove_empty_paragraphs(text[:text.index(headlines[0])])

            # Extract paragraphs corresponding to each headline, except the last one
            for i in range(len(headlines)-1):
                body[headlines[i]] = remove_empty_paragraphs(text[text.index(headlines[i])+1:text.index(headlines[i+1])])

            # Extract the paragraphs belonging to the last headline
            body[headlines[-1]] = remove_empty_paragraphs(text[text.index(headlines[-1])+1:])

        else:
            # The article has no headlines, just paragraphs
            body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}
      
        # No recommendations related to the article are available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
