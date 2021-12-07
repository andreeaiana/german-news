# -*- coding: utf-8 -*-

import os
import sys
from news_crawler.spiders import BaseSpider
from scrapy.spiders import Rule
from scrapy.linkextractors import LinkExtractor
from datetime import datetime
import dateutil.parser as date_parser

sys.path.insert(0, os.path.join(os.getcwd(), "..",))
from news_crawler.items import NewsCrawlerItem
from news_crawler.utils import remove_empty_paragraphs


class Achgut(BaseSpider):
    """Spider for Achgut"""
    name = 'achgut'
    rotate_user_agent = True
    allowed_domains = ['www.achgut.com']
    start_urls = ['https://www.achgut.com/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.achgut\.com\/artikel\/\w.*$'),
                    deny=(r'www\.achgut\.com\/podcast',
                        r'www\.achgut\.com\/presseschau',
                        r'www\.achgut\.com\/suche',
                        r'www\.achgut\.com\/autoren',
                        r'www\.achgut\.com\/seite\/\w.*',
                        r'newsletter\.achgut\.com\/',
                        r'paten\.achgut\.com\/',
                        r'shop\.achgut\.com\/',
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
        dates = response.xpath("//div[@class='column full']//div[@class='teaser_text_meta']/text()").getall()
        try:
            dates = [date.strip() for date in dates if len(date.strip())!=0]
            creation_date = dates[0]
            creation_date = creation_date.replace('/','').strip()
            creation_date = date_parser.parse(creation_date)
        except:
            return
        if not creation_date:
            return
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@id="article_maincontent"]/p')]
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

        item['news_outlet'] = 'achgut'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@id="author_header"]/text()').getall()
        item['author_person'] = authors if authors else list() 
        item['author_organization'] = list()

        # Extract keywords, if available
        item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()

        if response.xpath('//div[@id="article_content"]//h3[not(@*)]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//div[@id="article_content"]//h3[not(@*)]')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@id="article_maincontent"]/p | //div[@id="article_content"]//h3[not(@*)]')]
          
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
        recommendations = [response.urljoin(link) for link in response.xpath("//div[@class='teaser_blog_text']/h3/a/@href").getall()]
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
