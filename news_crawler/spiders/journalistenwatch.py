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


class Journalistenwatch(BaseSpider):
    """Spider for journalistenwatch"""
    name = 'journalistenwatch'
    rotate_user_agent = True
    allowed_domains = ['journalistenwatch.com']
    start_urls = ['https://journalistenwatch.com/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'journalistenwatch\.com\/\w.*'),
                    deny=(r'journalistenwatch\.com\/impressum\/',
                        r'journalistenwatch\.com\/datenshutzerklaerung\/',
                        r'journalistenwatch\.com\/kontakt\/',
                        r'journalistenwatch\.com\/downloads\/',
                        r'journalistenwatch\.com\/spenden\/',
                        r'journalistenwatch\.com\/category\/video\/',
                        r'journalistenwatch\.com\/freie\-medien\/',
                        r'journalistenwatch\.com\/auf\-jouwatch\-werben\/'
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
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="td-post-content td-pb-padding-side"]//p[not(descendant::strong)]')]
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

        item['news_outlet'] = 'journalistenwatch'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@property="article:modified_time"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        item['author_person'] = response.xpath('//meta[@itemprop="author"]/@content').getall()
        item['author_organization'] = list()

        # Extract keywords, if available
        item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().split(' \u203a Jouwatch')[0]
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//div[@class="td-post-content td-pb-padding-side"]//p/strong'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//div[@class="td-post-content td-pb-padding-side"]/p/strong')]
            headlines = headlines[1:]
            if headlines:
                # Extract the paragraphs and headlines together
                text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="td-post-content td-pb-padding-side"]//p[not(descendant::strong)] | //div[@class="td-post-content td-pb-padding-side"]/p/strong')]
                text = text[1:]

                # Extract paragraphs between the abstract and the first headline
                body[''] = remove_empty_paragraphs(text[:text.index(headlines[0])])

                # Extract paragraphs corresponding to each headline, except the last one
                for i in range(len(headlines)-1):
                    body[headlines[i]] = remove_empty_paragraphs(text[text.index(headlines[i])+1:text.index(headlines[i+1])])

                # Extract the paragraphs belonging to the last headline
                body[headlines[-1]] = remove_empty_paragraphs(text[text.index(headlines[-1])+1:])
            else:
                body[''] = paragraphs
        else:
            # The article has no headlines, just paragraphs
            body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}

        # Extract first 5 recommendations towards articles from the same news outlet, if available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
