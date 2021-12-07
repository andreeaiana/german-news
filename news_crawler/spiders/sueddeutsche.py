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

class SueddeutscheSpider(BaseSpider):
    """Spider for Sueddeutsche"""
    name = 'sueddeutsche'
    rotate_user_agent = True
    allowed_domains = ['www.sueddeutsche.de']
    start_urls = ['https://www.sueddeutsche.de/']
 
    # Exclude paid articles and pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.sueddeutsche\.de\/\w.*\.\d+$'),
                    deny=(r'www\.sueddeutsche\.de\/\w.*\.\d+\?reduced=true.*$', 
                        r'www\.sueddeutsche\.de\/thema\/Spiele',
                        r'www\.sueddeutsche\.de\/app\/spiele\/\w.*',
                        r'www\.sueddeutsche\.de\/service\/\w.*',
                        r'www\.sueddeutsche\.de\/autoren'
                        )
                    ),
                callback='parse',
                follow=True
                ),
            )


    def parse(self, response):
        """
        Checks article validity. If valid, it parses it.
        """
       
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if not data_json:
            # The page does not contain an article
            return
        data = json.loads(data_json)
        
        # Check date validity
        if 'datePublished' not in data:
            return
        creation_date = data['datePublished']
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get() for node in response.xpath('//p[@class=" css-0"]')]
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

        item['news_outlet'] = 'sueddeutsche_zeitung'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
       
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = data['dateModified']
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        data_authors = data['author']
        item['author_person'] = [author['name'] for author in data_authors if author['@type']=='Person']
        item['author_organization'] = [author['name'] for author in data_authors if author['@type']=='Organization']

        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(',') if news_keywords else list()
       
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get() 
        description = response.xpath('//meta[@property="og:description"]/@content').get()
         # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3[not(@*)]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[not(@*)]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[@class=" css-0"] | //h3[not(@*)]')]

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

        # Extract first 5 recommendations towards articles from the same news outlet
        recommendations = response.xpath('//aside[@id="more-on-the-subject"]//a/@href').getall()
        if recommendations:
            recommendations = [rec for rec in recommendations if not '?reduced=true' in rec]
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
