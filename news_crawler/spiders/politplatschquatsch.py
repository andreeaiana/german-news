# -*- coding: utf-8 -*-

import os
import sys
import dateparser
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule 
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class PolitplatschquatschSpider(BaseSpider):
    """Spider for politplatschquatsch"""
    name = 'politplatschquatsch'
    rotate_user_agent = True
    allowed_domains = ['www.politplatschquatsch.com']
    start_urls = ['https://www.politplatschquatsch.com/']
    
    # Exclude pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.politplatschquatsch\.com\/\d+\/\w.*\.html$')
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
        creation_date = response.xpath('//h2[@class="date-header"]/span/text()').get()
        if not creation_date:
            return
        creation_date = creation_date.split(', ')[-1]
        creation_date = dateparser.parse(creation_date)
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's content
        raw_paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@itemprop="articleBody" and descendant::text()]')]

        if not '\n\n' in raw_paragraphs[0]:
            # Handle non-breaking spaces
            raw_paragraphs = raw_paragraphs[0].replace('.\xa0', '.\n')
            raw_paragraphs = raw_paragraphs.split('.\n')
            raw_paragraphs = [para.replace('\n', '') for para in raw_paragraphs]
            raw_paragraphs = [para.replace('\xa0', '') for para in raw_paragraphs]
            paragraphs = [para.strip() for para in raw_paragraphs]
            paragraphs = remove_empty_paragraphs(paragraphs)
            text = ' '.join([para for para in paragraphs])
 
        else:
            # Split text into paragraphs
            raw_paragraphs = raw_paragraphs[0].split('\n\n')
            raw_paragraphs = [para.strip() for para in raw_paragraphs]

            paragraphs = list()
            for para in raw_paragraphs:
                if '\n' in para:
                    paragraphs.extend(para.split('\n'))
                else:
                    paragraphs.append(para)
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
        
        item['news_outlet'] = 'politplatschquatsch'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # No authors listed
        item['author_person'] = list()
        item['author_organization'] = list()

        # No keywords available
        item['news_keywords'] = list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        
        # Headlines are not handled consistently
        body[''] = paragraphs 

        item['content'] = {'title': title, 'description': description, 'body':body}
      
        # No recommendations related to the article are available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
