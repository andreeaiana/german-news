# -*- coding: utf-8 -*-

import os
import sys
import dateparser
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class CiceroSpider(BaseSpider):
    """Spider for Cicero"""
    name = 'cicero'
    rotate_user_agent = True
    allowed_domains = ['www.cicero.de']
    start_urls = ['https://www.cicero.de/']

    # Exclude paid articles and pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.cicero\.de\/\w.*'),
                    deny=(r'www\.cicero\.de\/cicero\-plus',
                        r'www\.cicero\.de\/newsletter\-anmeldung',
                        r'www\.cicero\.de\/rss\.xml$',
                        r'www\.cicero\.de\/comment\/\w.*'
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
    
        # Exclude paid articles
        if response.xpath('//div[@class="paywall-text"]').get():
            return

        # Check date validity 
        metadata = response.xpath('//div[contains(@class, "teaser-small__metadata")]/p/text()').getall()
        if not metadata:
            return
        creation_date = metadata[-1].strip()
        if not creation_date:
            return
        creation_date = creation_date.split('am ')[-1]
        creation_date = dateparser.parse(creation_date)
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="field field-name-field-cc-body"]/p')]
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
        
        item['news_outlet'] = 'cicero'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors       
        item['author_person'] = list()
        item['author_organization'] =  list()

        authors = response.xpath('//div[@class="row author-box"]//p[contains(text(), "So erreichen Sie")]/text()').getall()
        if authors:
            authors = [author.lstrip('So erreichen Sie ').rstrip(':') for author in authors]
            if 'Cicero-Redaktion' in authors:
                item['author_organization'].extend(authors)
            else:
                item['author_person'].extend(authors)

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3[not(contains(text(), "Kommentare"))]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[not(contains(text(), "Kommentare"))]')]
            headlines.remove('Mehr lesen über')
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="field field-name-field-cc-body"]/p | //h3[not(contains(text(), "Kommentare"))]')]

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
