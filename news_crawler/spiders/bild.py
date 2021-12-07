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


class BildSpider(BaseSpider):
    """Spider for Bild"""
    name = 'bild'
    rotate_user_agent = True
    allowed_domains = ['www.bild.de']
    start_urls = ['https://www.bild.de/']
    
    # Exclude paid and English articles and pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.bild\.de\/\w.*\.bild\.html$'),
                    deny=(r'www\.bild\.de\/\w+\/international\/\w.*\.bild\.html$',
                        r'www\.bild\.de\/bild-plus\/\w.*\.bild\.html$',
                        r'www\.bild\.de\/video\/mediathek\/\w.*',
                        r'www\.bild\.de\/video\/clip\/dokumentation\/\w.*',
                        r'www\.bild\.de\/bild-mobil\/audio\/podcast\/\w.*',
                        r'www\.bild\.de\/\w.*\-doku\-\w.*'
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
        if creation_date == '':
            return
        if 'Z' in creation_date:
            if '.' in creation_date:
                creation_date = datetime.fromisoformat(creation_date.split('.')[0])
            else:
                creation_date = datetime.fromisoformat(creation_date[:-1])
        else:
            creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get() for node in response.xpath('//div[@class="txt" or @class="article-body"]/p')]
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
        
        item['news_outlet'] = 'bild'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = data['dateModified']
        if 'Z' in last_modified:
            if '.' in last_modified:
                item['last_modified'] = datetime.fromisoformat(last_modified.split('.')[0]).strftime('%d.%m.%Y')
            else:
                item['last_modified'] = datetime.fromisoformat(last_modified[:-1]).strftime('%d.%m.%Y')
        else:
             item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        author_person = response.xpath('//div[@class="authors"]//span[@class="authors__name"]/text()').get()
        if author_person:
            author_person = author_person.split(' UND ') if 'UND' in author_person else [author_person]
        else:
            author_person = response.xpath('//div[@class="author"]//span[@class="author__name"]/text()').get()
            author_person = [author_person] if author_person else list()
        item['author_person'] = author_person
        data_author = data['author']
        if type(data_author) != list:
            data_author = [data_author]
        item['author_organization'] = [author['name'] for author in data_author if author['@type']=='Organization'] 

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        if news_keywords:
            item['news_keywords'] = news_keywords.split(', ') if ', ' in news_keywords else news_keywords.split(',')
        else:
            item['news_keywords'] = list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h2[@class="crossheading"]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[@class="crossheading"]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="txt" or @class="article-body"]/p | //h2[@class="crossheading"]')]

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
      
        # Extract first 5 recommendations towards articles from the same news outlet, if available
        recommendations = response.xpath('//div[@class="related-topics__container"]/article/a/@href').getall()
        if not recommendations:
            recommendations = response.xpath('//div[descendant::h3[contains(text(), "Lesen Sie auch")]]/ul/li//a/@href').getall()
            recommendations = ['https://www.bild.de' + rec for rec in recommendations]
        if recommendations:    
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
