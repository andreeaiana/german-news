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


class TagesspiegelSpider(BaseSpider):
    """Spider for Tagesspiegel"""
    name = 'tagesspiegel'
    rotate_user_agent = True
    allowed_domains = ['www.tagesspiegel.de']
    start_urls = ['https://www.tagesspiegel.de/']
    
    # Exclude paid articles and pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.tagesspiegel\.de\/\w.*\/\d+\.html$'),
                    deny=(r'plus\.tagesspiegel\.de',
                        r'tagesspiegel\.de\/service\/\w.*\.html$',
                        r'tagesspiegel\.de\/\w+\-\w+\/\d+\.html$',
                        r'tagesspiegel\.de\/dpa\/\d+\.html$',
                        r'tagesspiegel\.de\/mediacenter\/fotostrecken\/\w.*\/\d+\.html$'
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
        creation_date = response.xpath('//div/time[@itemprop="datePublished"]/@datetime').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get() for node in response.xpath('//div[@itemprop="articleBody"]/p[not(descendant::strong and descendant::span)]')]
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

        item['news_outlet'] = 'tagesspiegel'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        # No last-modified date available 
        item['last_modified'] = creation_date.strftime('%d.%m.%Y') 
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        # Check if authors are persons
        author_person = response.xpath('//address/span/a[@rel="author"]/text()').getall()
        if author_person:
            item['author_person'] = author_person 
            item['author_organization']= list()
        else:
            # Check if any news organization is mentioned at the end of the article (e.g. dpa)
            last_paragraph = [node.xpath('string()').get() for node in response.xpath('//div[@itemprop="articleBody"]/p[descendant::em]')]
            if last_paragraph:
                last_paragraph = last_paragraph[-1] if len(last_paragraph) > 1 else last_paragraph
                last_paragraph = last_paragraph[0] if type(last_paragraph) == list else last_paragraph
                last_paragraph = last_paragraph.split('. ')[-1].lstrip('(').rstrip(')')
                author_organization = last_paragraph.split(', ') if ', ' in last_paragraph else [last_paragraph]
                item['author_person'] = list()
                item['author_organization'] = author_organization if author_organization else list()
            else:
                item['author_person'] = list()
                item['author_organization'] = list()

        # Extract keywords, if available (from javascript)
        body_text = response.body.decode('utf-8') 
        pattern = re.compile('keywords\: \[\"\w.+\,.+\"\]')
        match = pattern.search(body_text)
        if match:
            news_keywords = body_text[match.start():match.end()]
            news_keywords = news_keywords.split('["')[1].rsplit('"]')[0].split(',')
            item['news_keywords'] = news_keywords
        else:
            item['news_keywords'] = list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get() 
        description = response.xpath('//meta[@property="og:description"]/@content').get()
       
        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3[not(contains(@class, "ts-title"))]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[not(contains(@class, "ts-title"))]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@itemprop="articleBody"]/p[not(descendant::strong and descendant::span)] | //h3[not(contains(@class, "ts-title"))]')]

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
        recommendations = response.xpath('//article[@class="ts-teaser ts-type-article "]/a/@href').getall()
        if recommendations:
            recommendations = ['https://www.tagesspiegel.de' + rec for rec in recommendations]
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
