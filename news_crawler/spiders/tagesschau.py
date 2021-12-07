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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[@class="text small" and not(descendant::strong)] | //blockquote[@class="zitat"]/p')]
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
        data_authors = data['author']['name']

        # Check if the author is an organization
        if data_authors:
            if data_authors == 'tagesschau':
                item['author_person'] = list()
                item['author_organization'] = [data_authors]
            else:
                # Check if authors are persons
                author_person = data_authors.split(', ')[0]
                author_person = author_person.split(' und ') if ' und ' in author_person else [author_person]
                item['author_person'] = [author.strip(' Von ') for author in author_person]
                author_organization = data_authors.split(', ')[1:]
                item['author_organization'] = [' '.join(elem for elem in author_organization)]
        else:
            item['author_person'] = list()
            item['author_organization'] = list()

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()
       
        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h2[@class="subtitle small "]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[@class="subtitle small "]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[@class="text small" and not(descendant::strong)] | //blockquote[@class="zitat"]/p | //h2[@class="subtitle small "]')]

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
        
        # Extract from categories "Mehr zum Thema"
        mehr_zum_thema_h3 = response.xpath('//div[preceding-sibling::h3[contains(text(), "Mehr zum Thema")]]/div/ul/li/a/@href').getall() 
        if mehr_zum_thema_h3:
            mehr_zum_thema_h3 = ['https://www.tagesschau.de' + rec for rec in mehr_zum_thema_h3]

        mehr_zum_thema_h4 = response.xpath('//div[preceding-sibling::h4[contains(text(), "Mehr zum Thema")]]/ul/li/a/@href').getall() 
        if mehr_zum_thema_h4:
            mehr_zum_thema_h4 = ['https://www.tagesschau.de' + rec for rec in mehr_zum_thema_h4]
        
        # Extract from categories "Aus dem Archiv"
        aus_dem_archiv = response.xpath('//div[preceding-sibling::h3[contains(text(), "Aus dem Archiv")]]/div/ul/li/a/@href').getall() 
        if aus_dem_archiv:
            aus_dem_archiv = ['https://www.tagesschau.de' + rec for rec in aus_dem_archiv]

        recommendations = mehr_zum_thema_h3 + mehr_zum_thema_h4 + aus_dem_archiv
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
