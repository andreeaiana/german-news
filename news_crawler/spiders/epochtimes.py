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


class Epochtimes(BaseSpider):
    """Spider for The Epoch Times"""
    name = 'epochtimes'
    rotate_user_agent = True
    allowed_domains = ['www.epochtimes.de']
    start_urls = ['https://www.epochtimes.de/']

    # Exclude paid articles and pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.epochtimes\.de\/\w.*\.html'),
                    deny=(r'www\.epochtimes\.de\/newsticker',
                        r'www\.epochtimes\.de\/premium',
                        r'www\.epochtimes\.de\/abo',
                        r'www\.epochtimes\.de\/datenschutzerklaerung',
                        r'www\.epochtimes\.de\/epoch\-times\/impressum',
                        r'www\.epochtimes\.de\/epoch\-times\/epoch\-times\-epochtimes\-a4717\.html'
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
        creation_date = response.xpath('//meta[@name="article:published_time"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@id="news-content"]//p[not(preceding-sibling::h2[@*])] | //div[@id="news-content"]//blockquote/p[not(preceding-sibling::h2[@*])]')]
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

        item['news_outlet'] = 'epochtimes'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@name="article:modified_time"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if data_json:
            data = json.loads(data_json)
            item['author_person'] = [data['author']['name']] if data['author']['name']!='Epoch Times' else list()
            item['author_organization'] = [data['author']['name']] if data['author']['name']=='Epoch Times' else list()
        else:
            item['author_person'] = list()
            item['author_organization'] = list()

        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h2[not(@*)]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[not(@*)]')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@id="news-content"]//p[not(preceding-sibling::h2[@*])] | //div[@id="news-content"]//blockquote/p[not(preceding-sibling::h2[@*])] | //h2[not(@*)]')]
          
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
        recommendations = response.xpath('//ul[@class="mu-related"]/li[@class="related-article"]/a/@href').getall()
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendati ons'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
