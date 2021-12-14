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


class TagesschauSpider(BaseSpider):
    """Spider for Tagesschau"""
    name = 'tagesschau'
    rotate_user_agent = True
    allowed_domains = ['www.tagesschau.de']
    start_urls = ['https://www.tagesschau.de/']
    
    # Exclude pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.tagesschau\.de\/\w+\/\w.*\.html$'),
                    deny=(r'www\.tagesschau\.de\/multimedia\/\w.*\.html$',
                        r'wetter\.tagesschau\.de\/',
                        r'meta\.tagesschau\.de\/',
                        r'www\.tagesschau\.de\/mehr\/\w.*',
                        r'www\.tagesschau\.de\/hilfe\/\w.*',
                        r'www\.tagesschau\.de\/impressum\/',
                        r'www\.tagesschau\.de\/kontakt_und_hilfe\/\w.*',
                        r'www\.tagesschau\.de\/sitemap\/',
                        r'www\.tagesschau\.de\/app\/',
                        r'www\.tagesschau\.de\/atlas\/',
                        r'www\.tagesschau\.de\/allemeldungen\/'
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
        if 'datePublished' not in data.keys():
            return
        creation_date = data['datePublished']
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[contains(@class, "m-ten")]')]
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

        item['news_outlet'] = 'tagesschau'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = data['dateModified']
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        authors_list = response.xpath('//div[@class="authorline__author"]/text() | //div[@class="authorline__author"]/em/text()').get()

        item['author_person'] = list()
        item['author_organization'] = list()

        if authors_list:
            authors_list = authors_list.split(', sowie ')
            for authors in authors_list:
                authors = authors.strip('Von ')
                authors = authors.split(', ')

                author_organization = authors[-1]
                item['author_organization'].extend(author_organization.split('/'))

                author_person = authors[:-1]
                for author in author_person:
                    item['author_person'].extend(author.split(' und '))

        # Extract keywords
        news_keywords = [node.xpath('text()').get() for node in response.xpath('//ul[@class="taglist"]/li/a')]
        item['news_keywords'] = news_keywords if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()
       
        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h2[contains(@class, "meldung__subhead")]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[contains(@class, "meldung__subhead")]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[contains(@class, "m-ten")] | //h2[contains(@class, "meldung__subhead")]')]

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
        recommendations = response.xpath('//div[preceding-sibling::div//h2[contains(text(), "Mehr zum Thema")]]/ul/li/a/@href').getall()
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
