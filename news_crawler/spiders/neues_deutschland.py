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


class NeuesDeutschlandSpider(BaseSpider):
    """Spider for neues-deutschland"""
    name = 'neues_deutschland'
    rotate_user_agent = True
    allowed_domains = ['www.neues-deutschland.de']
    start_urls = ['https://www.neues-deutschland.de/']
    
    # Exclude pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.neues\-deutschland\.de\/artikel\/\d+\.\w.*\.html'),
                    deny=(r'www\.neues\-deutschland\.de\/shop\/',
                        r'www\.neues\-deutschland\.de\/leserreisen\/',
                        r'www\.neues\-deutschland\.de\/termine\/',
                        r'www\.neues\-deutschland\.de\/anzeigen\/',
                        r'www\.neues\-deutschland\.de\/jobs\/',
                        r'www\.neues\-deutschland\.de\/abo\/',
                        r'www\.neues\-deutschland\.de\/newsletter\/',
                        r'www\.neues\-deutschland\.de\/nd-ticker\/',
                        r'www\.neues\-deutschland\.de\/redaktion\/',
                        r'www\.neues\-deutschland\.de\/gastautoren\/',
                        r'www\.neues\-deutschland\.de\/kontakt\/',
                        r'www\.neues\-deutschland\.de\/tag\/',
                        r'www\.neues\-deutschland\.de\/nd_extra\/',
                        r'www\.neues\-deutschland\.de\/\w.*\.php'
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
        # Check if page is duplicate
        if 'html?' in response.url:
            return
        
        # Check date validity 
        creation_date = response.xpath('//meta[@name="date"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.strptime(creation_date, '%Y-%m-%d')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//h2[preceding-sibling::h1] | //div[@class="Content"]/p')]
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

        item['news_outlet'] = 'neues_deutschland'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        authors = response.xpath('//meta[@name="author"]/@content').get()
        if 'neues deutschland' in authors:
            item['author_person'] = list()
            item['author_organization'] = authors.split(', ')
        elif authors:
            item['author_person'] = authors.split(', ')
            item['author_organization'] = list()
        else:
            item['author_person'] = list()
            item['author_organization'] = list()

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        if '(neues deutschland)' in title:
            title = title.split(' (neues deutschland)')[0]
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h4[not(ancestor::div[@class="Wrap" or @class="ndPLUS-Abowerbung"])] | //h3[not(descendant::*)]'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//h4[not(ancestor::div[@class="Wrap" or @class="ndPLUS-Abowerbung"])] | //h3[not(descendant::*)]')]

            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//h2[preceding-sibling::h1] | //div[@class="Content"]/p | //h4[not(ancestor::div[@class="Wrap" or @class="ndPLUS-Abowerbung"])] | //h3[not(descendant::*)]')]

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
      
        # Extract the first 5 recommendations related to the article
        recommendations = response.xpath('//div[@id="List-Similar-Articles"]//a/@href').getall()
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            recommendations = ['https://www.neues-deutschland.de' + rec for rec in recommendations]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
