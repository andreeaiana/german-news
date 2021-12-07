# -*- coding: utf-8 -*-

import re
import os
import sys
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class SternSpider(BaseSpider):
    """Spider for Stern"""
    name = 'stern'
    rotate_user_agent = True
    allowed_domains = ['www.stern.de']
    start_urls = ['https://www.stern.de/']

    # Exclude paid and English articles, and pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'stern\.de\/\w.*\.html$'),
                    deny=(r'stern\.de\/p\/plus\/\w.*\.html$',
                        r'stern\.de\/\w.*\/english-version-\w.*\.html$',
                        r'www\.stern\.de\/gutscheine\/',
                        r'www\.stern\.de\/\w.*\/themen\/\w.*\.html$'
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
        creation_date = response.xpath('//meta[@name="date"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div/p[@class="text-element u-richtext u-typo u-typo--article-text article__text-element text-element--context-article"] | //div[@class="text-element text-element--list u-richtext u-typo u-typo--list article__text-element article__text-element--list text-element--context-article"]/ul/li')]
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
        
        item['news_outlet'] = 'stern'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@name="last-modified"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        # Check if there are persons authors
        author_person = response.xpath('//div[@class="authors__text u-typo u-typo--author"]/a/text()').getall()
        if author_person:
            item['author_person'] = author_person 
            item['author_organization'] = list()
        else:
            # Check if the author is an organization
            author_organization = response.xpath('//div/span[@class="credits-author-source__item"]/text()').getall()
            item['author_person'] = list()
            item['author_organization'] = author_organization if author_organization else list()

        # Extract keywords, if available
        body_text = response.body.decode('utf-8') 
        pattern = re.compile('keywords\: \[\"\w.+\,.+\"\]')
        match = pattern.search(body_text)
        if match:
            news_keywords = body_text[match.start():match.end()]
            news_keywords = news_keywords.split('[')[1].rsplit(']')[0].split(',')
            item['news_keywords'] = [keyword.strip('"') for keyword in news_keywords]
        else:
            item['news_keywords'] = list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h2[contains(@class, "subheadline-element")]'):
           # Extract headlines
           headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[contains(@class, "subheadline-element")]')]
           
           # Extract paragraphs with headlines
           text = [node.xpath('string()').get().strip() for node in response.xpath('//div/p[@class="text-element u-richtext u-typo u-typo--article-text article__text-element text-element--context-article"] | //div[@class="text-element text-element--list u-richtext u-typo u-typo--list article__text-element article__text-element--list text-element--context-article"]/ul/li | //h2[contains(@class, "subheadline-element")]')]

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
        recommendations = response.xpath('//div/article/a[@class="teaser__link "]/@href').getall()
        if recommendations:
            recommendations = ['www.stern.de' + rec for rec in recommendations if not ('/p/plus' in rec or '/noch-fragen' in rec)]
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
