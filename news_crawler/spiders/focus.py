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


class FocusSpider(BaseSpider):
    """Spider for Focus"""
    name = 'focus'
    rotate_user_agent = True
    allowed_domains = ['www.focus.de']
    start_urls = ['https://www.focus.de/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.focus\.de\/\w.*\.html$'),
                    deny=(r'www\.focus\.de\/service\/',
                        r'www\.focus\.de\/focustv\/',
                        r'www\.focus\.de\/videos\/',
                        r'www\.focus\.de\/\w+\/videos\/',
                        r'www\.focus\.de\/shopping\/',
                        r'www\.focus\.de\/schlagzeilen\/',
                        r'www\.focus\.de\/deals\/',
                        r'www\.focus\.de\/panorama\/lotto\/',
                        r'www\.focus\.de\/gesundheit\/lexikon\/',
                        r'www\.focus\.de\/gesundheit\/testcenter\/',
                        r'www\.focus\.de\/wissen\/natur\/meteorologie\/',
                        r'www\.focus\.de\/finanzen\/boerse\/robo',
                        r'www\.focus\.de\/intern\/',
                        r'www\.focus\.de\/finanzen\/focus\-online\-kooperationen\-services\-vergleiche\-rechner\_id'
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
    
        json_data = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if not json_data:
            return
        data = json.loads(json_data)

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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="textBlock"]/p[not(contains(@class, "noads")) and not(descendant::em[contains(text(), "Lesen Sie auch")])]')]
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
        
        item['news_outlet'] = 'focus'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = data['dateModified']
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        author_person = response.xpath('//div[@class="authorMeta"]/span/a/text()').getall()
        item['author_person'] = author_person if author_person else list()
        # Check if the author is an organization
        author_organization = response.xpath('//div[@class="textBlock "]/span[@class="created"]/text()').get()
        if author_organization:
            author_organization = author_organization.split('/')
            author_organization = remove_empty_paragraphs(author_organization)
            item['author_organization'] = author_organization
        else:
            item['author_organization'] = list()

        # No keywords available
        item['news_keywords'] = list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()
       
        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h2[not(contains(@class, "mm-h2"))]'):

           # Extract headlines
           headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[not(contains(@class, "mm-h2"))]')]

           # Extract the paragraphs and headlines together
           text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="textBlock"]/p[not(contains(@class, "noads")) and not(descendant::em[contains(text(), "Lesen Sie auch")])] | //h2[not(contains(@class, "mm-h2"))]')]
          
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
      
        # No article-related recommendations
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
