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


class Opposition24(BaseSpider):
    """Spider for Opposition24"""
    name = 'opposition24'
    rotate_user_agent = True
#    allowed_domains = ['opposition24.com/']
    start_urls = ['https://opposition24.com/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'opposition24\.com\/\w.*'),
                    deny=(r'opposition24\.com\/datenschutz\/',
                        r'opposition24\.com\/impressum\/',
                        r'opposition24\.com\/leitbild\/',
                        r'opposition24\.com\/spenden\/',
                        r'opposition24\.com\/podcasts\/',
                        r'opposition24\.com\/youtube\/',
                        r'opposition24\.com\/regeln\-fuer\-kommentare\/',
                        r'opposition24\.com\/werben\-und\-partnerangebote\/'
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
        creation_date = data['datePublished']
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[starts-with(@class, "post-content")]/p')]
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

        item['news_outlet'] = 'opposition24'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = data['dateModified']
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        author = data['author']['name']
        item['author_person'] = [author] if author  and not (author == 'Redaktion' or author == 'Gastbeitrag') else list()
        item['author_organization'] = [author] if author and (author == 'Redaktion' or author == 'Gastbeitrag') else list()

        # Extract keywords, if available
        item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip().replace('\n\n', ' ')

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//div[starts-with(@class, "post-content")]/h4/strong | //h3[not(@*)]'):
            # Extract headlines
            headlines = [node.xpath('string()').get().strip() for node in response.xpath('//div[starts-with(@class, "post-content")]/h4/strong | //h3[not(@*)]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[starts-with(@class, "post-content")]/p | //div[starts-with(@class, "post-content")]/h4/strong | //h3[not(@*)]')]

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
        recommendations = list(set(response.xpath('//section[@class="related-posts"]//a/@href').getall()))
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
