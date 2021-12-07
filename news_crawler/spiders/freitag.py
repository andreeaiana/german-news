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


class FreitagSpider(BaseSpider):
    """Spider for Freitag"""
    name = 'freitag'
    rotate_user_agent = True
    allowed_domains = ['www.freitag.de']
    start_urls = ['https://www.freitag.de/']
    
    # Exclude pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.freitag\.de\/\w.*'),
                    deny=(r'www\.freitag\.de\/produkt-der-woche\/',
                        r'www\.freitag\.de\/\w.*\/\@\@kommentare\?\w.*'
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
     
        data_json = response.xpath('//script[@class="qa-structured-data" and @type="application/ld+json"]/text()').get()
        if not data_json:
            return
        data = json.loads(data_json)

        # Check date validity 
        if not 'datePublished' in data.keys():
            return
        creation_date = data['datePublished']
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@id="x-article-text"]/p')]
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
        
        item['news_outlet'] = 'freitag'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = data['dateModified']
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        authors = response.xpath('//span[@class="author"]/a/text()').get()
        if authors:
            authors = authors.strip()
            if 'und' in authors:
                authors = authors.split(' und ')
            if ',' in authors:
                authors = authors.split(', ')
            if type(authors) == str:
                authors = [authors]
            item['author_person'] = [author for author in authors if len(author.split())>=2 and author != 'der Freitag']
            item['author_organization'] = [author for author in authors if len(author.split()) == 1 or author == 'der Freitag']
        else:
            item['author_person'] = list()
            item['author_organization'] = list()

        # Extract keywords
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
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@id="x-article-text"]/p | //h2[not(@*)]')]

            # Extract paragraphs between the abstract and the first headline
            body[''] = remove_empty_paragraphs(text[:text.index(headlines[0])])

            # Extract paragraphs corresponding to each headline, except the last one
            for i in range(len(headlines)-1):
                body[headlines[i]] = remove_empty_paragraphs(text[text.index(headlines[i])+1:text.index(headlines[i+1])])

            # Extract the paragraphs belonging to the last headline
            body[headlines[-1]] = remove_empty_paragraphs(text[text.index(headlines[-1])+1:])

        else:
            # The article has no headlines, just paragraphs
            body[''] = [para for para in paragraphs if para != ' ' and para != ""]

        item['content'] = {'title': title, 'description': description, 'body':body}
      
        # No recommendations related to the article are available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
