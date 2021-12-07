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


class TazSpider(BaseSpider):
    """Spider for Taz"""
    name = 'taz'
    rotate_user_agent = True
    allowed_domains = ['taz.de']
    start_urls = ['https://taz.de/']

    # Exclude English articles and pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'taz\.de\/\w.*\/\!\d+\/',
                        r'taz\.de\/\!\d+\/'
                        ),
                    deny=(r'taz\.de\/English-Version\/\!\d+\/',
                        r'taz\.de\/taz-in-English\/\!\w.*\/',
                        r'taz\.de\/\!p4697\/',
                        r'taz\.de\/\!p4209\/',
                        r'taz\.de\/\!p4791\/',
                        r'taz\.de\/Info\/',
                        r'taz\.de\/Anzeigen\/',
                        r'taz\.de\/Podcast\/',
                        r'taz\.de\/Hilfe\/',
                        r'shop\.taz\.de\/',
                        r'taz\.de\/eKiosk-AGB\/',
                        r'taz\.de\/AGB',
                        r'taz\.de\/Print\-am\-Wochenende.*',
                        r'taz\.de\/FAQ.*'
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
        creation_date = response.xpath('//li[@class="date" and @itemprop="datePublished"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[@xmlns="" and (@class="article first odd Initial" or @class="article first odd" or @class="article odd" or @class="article even" or @class="article last odd" or @class="article last even")]')]
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

        item['news_outlet'] = 'taz'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@itemprop="dateModified"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y') 
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        # Check if authors are persons
        author_person = response.xpath('//div[@itemprop="author"]/a/h4[@itemprop="name"]/text()').getall()
        if author_person:
            item['author_person'] = list(set(author_person))
            item['author_organization'] = list()
        else:
            # Check if the author is an organization (i.e. taz)
            author_organization = response.xpath('//meta[@name="author"]/@content').get()
            item['author_person'] = list()
            item['author_organization'] = author_organization if author_organization else list()

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h6[@xmlns=""]'):
            # Extract headlines
            headlines = [h6.xpath('string()').get().strip() for h6 in response.xpath('//h6[@xmlns=""]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[@xmlns="" and (@class="article first odd Initial" or @class="article first odd" or @class="article odd" or @class="article even" or @class="article last odd" or @class="article last even")] | //h6[@xmlns=""]')]

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
