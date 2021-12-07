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


class TonlineSpider(BaseSpider):
    """Spider for t-online"""
    name = 'tonline'
    rotate_user_agent = True
    allowed_domains = ['www.t-online.de']
    start_urls = ['https://www.t-online.de/']
    
    # Exclude pages without relevant articles  
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.t-online\.de\/\w.*'),
                    deny=(r'www\.t-online\.de\/spiele\/',
                        r'www\.t-online\.de\/wetter\/',
                        r'www\.t-online\.de\/tv\/',
                        r'www\.t-online\.de\/podcasts\/',
                        r'www\.t-online\.de\/sport\/live-ticker\/',
                        r'www\.t-online\.de\/computer\/browser\/',
                        r'www\.t-online\.de\/\w.*\/quiz\-\w.*',
                        r'www\.t-online\.de\/\w.*\-lottozahlen\-\w.*'
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
        creation_date = response.xpath('//meta[@itemprop="datePublished"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@itemprop="articleBody"]/p[not(preceding-sibling::h2[@itemprop="alternativeHeadline"]) and not(descendant::span[@class="Tiflle"])]')]
        paragraphs = remove_empty_paragraphs(paragraphs[1:]) # First paragraph is the article's description
        text = ' '.join([para for para in paragraphs])

        # Check article's length validity
        if not self.has_min_length(text):
            return

        # Check keywords validity
        if not self.has_valid_keywords(text):
            return

        # Parse the valid article
        item = NewsCrawlerItem()

        item['news_outlet'] = 'tonline'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        data = json.loads(data_json)
        data_authors = data['author']
        if data_authors:
            author_person = [data_authors[i]['name'] for i in range(len(data_authors)) if data_authors[i]['@type'] == 'Person']
            item['author_person'] = [author for author in author_person if author != ""] 
            author_organization = [data_authors[i]['name'] for i in range(len(data_authors)) if data_authors[i]['@type'] == 'Organization']
            item['author_organization'] = [author for author in author_organization if author != ""] 

        else:
            item['author_person'] = list()
            item['author_organization'] = list()

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3[not(@*)]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[not(@*)]')]
           
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@itemprop="articleBody"]/p[not(preceding-sibling::h2[@itemprop="alternativeHeadline"]) and not(descendant::span[@class="Tiflle"])] | //h3[not(@*)]')]
            text = text[1:] # First paragraph is the article's description

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
        recommendations = response.xpath('//ul[preceding-sibling::p[contains(text(), "Mehr zum Thema")]]/li/a/@href').getall()
        if recommendations:    
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
