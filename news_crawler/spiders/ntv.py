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


class NtvSpider(BaseSpider):
    """Spider for NTV"""
    name = 'ntv'
    rotate_user_agent = True
    allowed_domains = ['www.n-tv.de']
    start_urls = ['https://www.n-tv.de/']

    # Excude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.n\-tv\.de\/\w.*\-article\d+\.html'),
                    deny=(r'www\.n-tv\.de\/mediathek\/videos\/\w.*',
                        r'www\.n-tv\.de\/mediathek\/livestream\/\w.*',
                        r'www\.n-tv\.de\/mediathek\/tvprogramm\/',
                        r'www\.n-tv\.de\/mediathek\/magazine\/',
                        r'www\.n-tv\.de\/mediathek\/moderatoren\/',
                        r'www\.n-tv\.de\/mediathek\/teletext\/',
                        r'www\.tvnow\.de\/',
                        r'www\.n-tv\.de\/wetter\/',
                        r'www\.n-tv\.de\/boersenkurse\/',
                        r'www\.n-tv\.de\/wirtschaft\/der_boersen_tag\/',
                        r'www\.n-tv\.de\/sport\/der_sport_tag\/',
                        r'www\.n-tv\.de\/der_tag\/'
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
        paragraphs = [node.xpath('string()').get() for node in response.xpath('//div/p[not(contains(@class, "article__source")) and not(descendant::strong)]')]
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

        item['news_outlet'] = 'ntv'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@name="last-modified"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        author_person = response.xpath('//div//span[@class="article__author"]/text()').getall()
        if author_person:
            author_person = [author.strip().split('Von ')[-1].rsplit(',')[0] for author in author_person]
            author_person = remove_empty_paragraphs(author_person)
            if author_person:
                item['author_person'] = author_person
            else:
                author_person = response.xpath('//div//span[@class="article__author"]/a/text()').getall()
                if author_person:
                    author_person = [author.split('von ')[-1].split(',')[0] for author in author_person]
                    author_person = [author.split('Von ')[-1].split(',')[0] for author in author_person]
                    item['author_person'] = author_person
                else:
                    item['author_person'] = list()
        else:
            item['author_person'] = list()

        author_organization = response.xpath('//p[@class="article__source"]/text()').get()
        item['author_organization'] = author_organization.split('Quelle: ')[-1].split(', ') if author_organization else list()

        # Extract keywords, if available
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get() 
        description = response.xpath('//meta[@property="og:description"]/@content').get()
       
        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h2'):
           # Extract headlines
           headlines = [h2.xpath('string()').get().strip() for h2 in response.xpath('//h2')]

           # Extract paragraphs with headlines
           text = [node.xpath('string()').get().strip() for node in response.xpath('//div/p[not(contains(@class, "article__source")) and not(descendant::strong)] | //h2')]

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
      
        # No article-related recommendations
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
