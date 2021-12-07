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


class Rationalgalerie(BaseSpider):
    """Spider for Rationalgalerie"""
    name = 'rationalgalerie'
    rotate_user_agent = True
    allowed_domains = ['www.rationalgalerie.de']
    start_urls = ['https://www.rationalgalerie.de/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.rationalgalerie\.de\/\w.*'),
                    deny=(r'www\.rationalgalerie\.de\/weiteres\/kontakt',
                        r'www\.rationalgalerie\.de\/informationen\/impressum',
                        r'www\.rationalgalerie\.de\/informationen\/datenschutz'
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
        creation_date = response.xpath('//meta[@property="article:published_time"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.strptime(creation_date,'%d.%m.%Y')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="aticle-text"]/p[not(descendant::strong) and not(descendant::span[@class="txt-c-r"])]')]
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

        item['news_outlet'] = 'rationalgalarie'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        item['last_modified'] = datetime.strptime(last_modified,'%d.%m.%Y').strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//meta[@name="author"]/@content').getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()

        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//div[@class="aticle-text"]/p[not(descendant::span[@class="txt-c-r"]) and descendant::strong]'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//div[@class="aticle-text"]/p[not(descendant::span[@class="txt-c-r"]) and descendant::strong]')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="aticle-text"]/p[not(descendant::strong) and not(descendant::span[@class="txt-c-r"])] | //div[@class="aticle-text"]/p[not(descendant::span[@class="txt-c-r"]) and descendant::strong]')]
          
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

        item['content'] = {'title': title, 'description': description, 'body': body}

        # Extract first 5 recommendations towards articles from the same news outlet, if available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
