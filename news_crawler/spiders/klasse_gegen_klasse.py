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


class KlasseGegenKlasseSpider(BaseSpider):
    """Spider for Klasse Gegen Klasse"""
    name = 'klasse_gegen_klasse'
    rotate_user_agent = True
    allowed_domains = ['www.klassegegenklasse.org']
    start_urls = ['https://www.klassegegenklasse.org/']
    
    # Exclude pages without relevant articles and articles in Turkish 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.klassegegenklasse\.org\/\w.*\/'),
                    deny=(r'www\.klassegegenklasse\.org\/\w.*\/\?replytocom=\d+',
                        r'www\.klassegegenklasse\.org\/kategorie\/turkce\/'
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

        # Check if page is duplicate (same article with 2 URLs, with 'http' and 'https')
        if not response.url.startswith('https:'):
            return

        # Check date validity 
        creation_date = response.xpath('//time/@datetime').get()
        if not creation_date:
            return
        creation_date = datetime.strptime(creation_date, '%Y-%m-%d')
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@*) and not(ancestor::div[@class="article-content"])]')]
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
        
        item['news_outlet'] = 'klasse_gegen_klasse'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        authors = response.xpath('//div/a/p[preceding-sibling::img[@class="author-img"]]/text()').getall()
        organizations = ['Left Voice'] # Organizations that cannot be distinguished otherwise from author names
        persons = ['Juan Cruz Ferre', 'René Amado Lehmann'] # Author names that cannot be distinguished otherwise from organizations
        if authors:
            item['author_person'] = [author for author in authors if len(author.split()) == 2 and not author in organizations or author in persons]
            item['author_organization'] = [author for author in authors if len(author.split()) != 2 and not author in persons or author in organizations]
        else:
            # Check if authors appear in a different format
            authors = response.xpath('//div[@class="text-center bottom-space"]/a/p/text()').getall()
            item['author_person'] = [author for author in authors if len(author.split()) == 2 and not author in organizations or author in persons] if authors else list()
            item['author_organization'] = [author for author in authors if len(author.split()) != 2 and not author in persons or author in organizations] if authors else list()
            
        # No keywords available
        item['news_keywords'] = list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h2[not(@*)]'):
            # Extract headlines
            headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2[not(@*)]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[not(@*) and not(ancestor::div[@class="article-content"])] | //h2[not(@*)]')]

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
      
        # No recommendations related to the article are available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
