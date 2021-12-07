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


class Jungefreiheit(BaseSpider):
    """Spider for jungefreiheit"""
    name = 'jungefreiheit'
    rotate_user_agent = True
    allowed_domains = ['jungefreiheit.de']
    start_urls = ['https://jungefreiheit.de/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'jungefreiheit\.de\/\w.*'),
                    deny=(r'jungefreiheit\.de\/archiv\/',
                        r'jungefreiheit\.de\/informationen\/',
                        r'jungefreiheit\.de\/service\/',
                        r'jungefreiheit\.de\/faq\/',
                        r'jungefreiheit\.de\/aktuelle\-jf\/',
                        r'jungefreiheit\.de\/datenschutzerklaerung\/',
                        r'jungefreiheit\.de\/kategorie\/pressemitteilung\/'
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
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        data = json.loads(data_json)['@graph']
        creation_date = data[4]['datePublished']
        if not creation_date:
            return
        if 'CEST' in creation_date:
            creation_date = creation_date.split('CEST')[0]
            creation_date = datetime.fromisoformat(creation_date)
        else:
            creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="elementor-widget-container"]/p[not(@*)]')]
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

        item['news_outlet'] = 'jungefreiheit'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')

        last_modified = data[4]['dateModified']
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = data[4]['author']
        item['author_person'] = [authors['name']] if authors['name']!='Online Redaktion' else list()
        item['author_organization'] = [authors['name']] if authors['name']=='Online Redaktion' else list()

        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@property="article:tag"]/@content').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3[not(@*)]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[not(@*)]')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="elementor-widget-container"]/p[not(@*)] | //h3[not(@*)]')]
          
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
        recommendations = response.xpath("//a[@class='ee-media ee-post__media ee-post__media--content']/@href").getall()
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
