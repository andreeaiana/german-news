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


class Antispiegel(BaseSpider):
    """Spider for Antispiegel"""
    name = 'anti_spiegel'
    rotate_user_agent = True
    allowed_domains = ['www.anti-spiegel.ru']
    start_urls = ['https://www.anti-spiegel.ru/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.anti\-spiegel\.ru\/\d+\/\w.*'),
                    deny=(r'www\.anti\-spiegel\.ru\/dokus\-vortraege\/',
                        r'www\.anti\-spiegel\.ru\/newsletter\/',
                        r'www\.anti\-spiegel\.ru\/kontakt\/',
                        r'www\.anti\-spiegel\.ru\/dokus\-vortraege\/',
                        r'www\.anti\-spiegel\.ru\/werbung\-auf\-anti\-spiegel\/'
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
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div//div[@class="article__content"]/p | //div/blockquote/p')]
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

        item['news_outlet'] = 'anti_spiegel'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        item['author_person'] = list()
        item['author_organization'] = list()
        author = response.xpath('//div[@class="authors article-meta__authors "]/text()').get().strip()
        if 'von' in author:
            author = author.split('von')[-1].strip()
        if 'Anti-Spiegel' in author:
            item['author_organization'].append(author)
        else:
            item['author_person'].append(author)

        # Extract keywords, if available
        data_json = response.xpath("//script[@class='yoast-schema-graph']/text()").get()
        data_json = json.loads(data_json)
        news_keywords = data_json['@graph'][5]['keywords']
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().split(' | Anti-Spiegel')[0]
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()

        if response.xpath('//h2[not(@*)] | //h3[not(@*)]'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//h2[not(@*)] | //h3[not(@*)]')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div//div[@class="article__content"]/p |  //div/blockquote/p | //h2[not(@*)] | //h3[not(@*)]')]

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
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
