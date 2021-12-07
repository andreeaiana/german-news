# -*- coding: utf-8 -*-

import os
import sys
import dateparser
from datetime import datetime
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class NachdenkseitenSpider(BaseSpider):
    """Spider for NachDenkSeiten"""
    name = 'nachdenkseiten'
    rotate_user_agent = True
    allowed_domains = ['www.nachdenkseiten.de']
    start_urls = ['https://www.nachdenkseiten.de/']
    
    # Exclude pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.nachdenkseiten\.de\/\?p=\d+$'),
                    deny=(r'www\.nachdenkseiten\.de\/foerdermitgliedschaft\/',
                        r'www\.nachdenkseiten\.de\/spenden\/',
                        r'www\.nachdenkseiten\.de\/\?page_id\=\d+',
                        r'www\.nachdenkseiten\.de\/\?cat\=\d+',
                        r'www\.nachdenkseiten\.de\/\?feed\=podcast',
                        r'www\.nachdenkseiten\.de\/\?p\=60958',
                        r'www\.nachdenkseiten\.de\/\?tag\=\w.*',
                        r'www\.nachdenkseiten\.de\/\?p\=\d+\&pdf\=\d+',
                        r'www\.nachdenkseiten\.de\/\?p=\d+\%.*'
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
        creation_date = response.xpath('//span[@class="postMeta"]/text()').get()
        if not creation_date:
            return
        creation_date = creation_date.split(' um')[0]
        creation_date = dateparser.parse(creation_date)
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="articleContent" or @class="footnote"]/p[not(contains(@class, "powerpress_links"))] | //blockquote/p')]
        # Remove irrelevant paragraphs
        paragraphs = [para for para in paragraphs if not 'Dieser Beitrag ist auch als Audio-Podcast' in para and not 'Titelbild: ' in para]
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

        item['news_outlet'] = 'nachdenkseiten'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        authors = response.xpath('//span[@class="author"]/a/text()').getall()
        item['author_person'] = [author for author in authors if len(author.split()) >= 2] if authors else list()
        item['author_organization'] = [author for author in authors if len(author.split()) == 1] if authors else list()

        # Extract keywords
        news_keywords = response.xpath('//a[@rel="tag"]/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        # The article has no headlines, just paragraphs
        body[''] = paragraphs

        item['content'] = {'title': title, 'description': description, 'body':body}
      
        # No recommendations related to the article are available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
