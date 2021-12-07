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


class JungeweltSpider(BaseSpider):
    """Spider for Junge Welt"""
    name = 'jungewelt'
    rotate_user_agent = True
    allowed_domains = ['www.jungewelt.de']
    start_urls = ['https://www.jungewelt.de/']

    # Exclude paid articles and pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.jungewelt\.de\/artikel\/\d+\.\w.*'),
                    deny=(r'www\.jungewelt\.de\/\w.*\/leserbriefe\.php$',
                        r'www\.jungewelt\.de\/verlag',
                        r'www\.jungewelt\.de\/ueber_uns\/',
                        r'www\.jungewelt\.de\/blogs\/',
                        r'www\.jungewelt\.de\/aktion\/',
                        r'www\.jungewelt\.de\/ladengalerie\/',
                        r'www\.jungewelt\.de\/termine\/',
                        r'www\.jungewelt\.de\/unterstuetzen\/',
                        r'www\.jungewelt\.de\/rlk\/',
                        r'www\.jungewelt\-shop\.de\/',
                        r'www\.jungewelt\.de\/loginFailed\.php\?\w.*'
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
        pay_message = 'Dieser Beitrag ist am Erscheinungstag gesperrt und nur für Onlineabonnenten lesbar.'
        if pay_message in response.body.decode('utf-8'):
            return

        # Check date validity 
        creation_date = response.xpath('//meta[@name="dcterms.date"]/@content').get()
        if not creation_date or creation_date == '':
            return
        creation_date = datetime.strptime(creation_date, '%Y-%m-%d')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(ancestor::div[@class="col-md-8 mx-auto mt-4 bg-light"]) and not(descendant::strong[contains(text(), "Unverzichtbar!")]) and not(ancestor::div[@id="Infobox"])]')]
        paragraphs = remove_empty_paragraphs(paragraphs)
        text = ' '.join([para for para in paragraphs])

        # Check article's length validity
        if not self.has_min_length(text):
            return

        # Check keywords validity
        if not self.has_valid_keywords(text):
            return

        # Parse the article
        item = NewsCrawlerItem()
        
        item['news_outlet'] = 'jungewelt'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        authors = response.xpath('//meta[@name="Author"]/@content').get()
        # Check if authors are persons
        if authors:
            authors = authors.split(', ') 
            # Remove location from the author's name, if included
            item['author_person'] = [author for author in authors if len(author.split())>=2]
            item['author_organization'] = list()
        else:
            # Check if the author is an organization (mentioned at the end of the last paragraph)
            author_organization = paragraphs[-1].split('. ')[-1].lstrip('(').rstrip(')').split('/')
            item['author_organization'] = author_organization if author_organization else list()
            item['author_person'] = list()

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get().split(' • ')[0]

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3[not(@*) and not(ancestor::footer)]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[not(@*) and not(ancestor::footer)]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(ancestor::div[@class="col-md-8 mx-auto mt-4 bg-light"]) and not(descendant::strong[contains(text(), "Unverzichtbar!")]) and not(ancestor::div[@id="Infobox"])] | //h3[not(@*) and not(ancestor::footer)]')]

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
        recommendations = response.xpath('//div[@id="similars"]/ul/li[not(contains(@class, "protected"))]//a[not(ancestor::h3)]/@href').getall()
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
