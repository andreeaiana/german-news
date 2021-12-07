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


class CompactOnline(BaseSpider):
    """Spider for Compact Online"""
    name = 'compact_online'
    rotate_user_agent = True
    allowed_domains = ['www.compact-online.de']
    start_urls = ['https://www.compact-online.de/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.compact\-online\.de\/\w.*'),
                    deny=(r'abo\.compact\-shop\.de\/',
                        r'www\.compact\-shop\.de\/',
                        r'www\.compact\-online\.de\/kontakt\/',
                        r'www\.compact\-online\.de\/spenden\/',
                        r'www\.compact\-online\.de\/digital\-pass\/',
                        r'www\.compact\-online\.de\/compact\-tv\/',
                        r'www\.compact\-online\.de\/compact\-live\/',
                        r'www\.compact\-online\.de\/newsletter\-anmeldung\/',
                        r'www\.compact\-online\.de\/werben\-in\-compact\/'
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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[contains(@class, "post-content description")]/p | //div[contains(@class, "post-content description")]/blockquote/p')]
        paragraphs = paragraphs[1:]
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

        item['news_outlet'] = 'compact_online'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        item['author_person'] = list()
        item['author_person'].append(response.xpath('//span[@class="posted-by"]/span/a/text()').get())
        item['author_organization'] = list()

        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@property="article:tag"]/@content').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # Extract first 5 recommendations towards articles from the same news outlet, if available
        recommendations = response.xpath('//section[@class="related-posts"]//article/a/@href').getall()
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
