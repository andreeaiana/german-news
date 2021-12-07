# -*- coding: utf-8 -*-

import os
import sys
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule
from scrapy.linkextractors import LinkExtractor
from datetime import datetime
import dateparser 

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class Rubikon(BaseSpider):
    """Spider for Rubikon"""
    name = 'rubikon'
    rotate_user_agent = True
    allowed_domains = ['www.rubikon.news']
    start_urls = ['https://www.rubikon.news/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.rubikon\.news\/artikel\/\w.*'),
                    deny=(r'www\.rubikon\.news\/artikel\/\w.*\.md',
                        r'www\.rubikon\.news\/unterstuetzen',
                        r'www\.rubikon\.news\/autoren',
                        r'www\.rubikon\.news\/beirat',
                        r'www\.rubikon\.news\/newsletter',
                        r'www\.rubikon\.news\/kontakt',
                        r'www\.rubikon\.news\/datenschutz',
                        r'www\.rubikon\.news\/buecher',
                        r'www\.rubikon\.news\/impressum',
                        r'www\.rubikon\.news\/artikel\.atom'
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
        creation_date = response.xpath("//div[@class='article-meta']/text()").getall()
        creation_date = [date for date in creation_date if 'Uhr' in date][0]
        if not creation_date:
            return
        creation_date = creation_date.strip().split(', ')[1]
        creation_date = dateparser.parse(creation_date)
        if not creation_date:
            return
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="article-teaser"]/p | //div[@class="article-content"]//p')]
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

        item['news_outlet'] = 'rubikon'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath("//div[@class='article-author']//strong/text()").getall()
        item['author_person'] = authors if authors else list()
        item['author_organization'] = list()

        # Extract keywords, if available
        item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@name="description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//div[@class="article-content"]/h1 | //div[@class="article-content"]/h2'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//div[@class="article-content"]/h1 | //div[@class="article-content"]/h2')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="article-teaser"]/p | //div[@class="article-content"]//p | //div[@class="article-content"]/h1 | //div[@class="article-content"]/h2')]
          
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
        recommendations = [response.urljoin(link) for link in response.xpath("//div[@class='loop-main']/article/a[@class='article-image']/@href").getall()]
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
