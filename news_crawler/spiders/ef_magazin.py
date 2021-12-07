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


class EfMagazin(BaseSpider):
    """Spider for EfMagazin"""
    name = 'ef_magazin'
    rotate_user_agent = True
    allowed_domains = ['ef-magazin.de']
    start_urls = ['https://ef-magazin.de/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'ef-magazin\.de\/\d+\/\d+\/\d+\/\w.*'),
                    deny=(r'ef-magazin\.de\/webwarum\-ef\/',
                        r'ef-magazin\.de\/accounts\/',
                        r'ef-magazin\.de\/autoren\/',
                        r'ef-magazin\.de\/archiv\/',
                        r'ef-magazin\.de\/adverts\/',
                        r'ef-magazin\.de\/impressum\/'
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
        url = response.xpath('//meta[@property="og:url"]/@content').get()
        try:
            creation_date = url[url.index("de")+3:url.rindex('/')]
            creation_date = datetime.strptime(creation_date, "%Y/%m/%d")
        except:
            return

        if not creation_date:
            return
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath("//article[@class='col-md-7']/p[not(@*) and not(descendant::strong)]")]
        paragraphs = [para.replace('\r\n', ' ') for para in paragraphs]
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

        item['news_outlet'] = 'ef_magazin'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        item['author_person'] = response.xpath("//em[@class='author']/a/text()").getall()
        item['author_organization'] = list()

        # Extract keywords, if available
        item['news_keywords'] = list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().strip()
        description = response.xpath('//meta[@property="og:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        body[''] = paragraphs[1:]

        item['content'] = {'title': title, 'description': description, 'body':body}
        
        # Extract first 5 recommendations towards articles from the same news outlet, if available
        item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
