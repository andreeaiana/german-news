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


class PiNews(BaseSpider):
    """Spider for pi-news"""
    name = 'pi_news'
    rotate_user_agent = True
    allowed_domains = ['www.pi-news.net']
    start_urls = ['http://www.pi-news.net/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.pi\-news\.net\/\d+\/\d+\/\w.*'),
                    deny=(r'www\.pi\-news\.net\/pi\-wants\-you\/',
                        r'www\.pi\-news\.net\/support\-pi\/',
                        r'www\.pi\-news\.net\/pi\-tv\/',
                        r'www\.pi\-news\.net\/kontakt\/',
                        r'www\.pi\-news\.net\/leitlinien\/',
                        r'www\.pi\-news\.net\/videothek\/'
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
        creation_date = response.xpath('//meta[@itemprop="datePublished"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="td-post-content"]/p[not(descendant::strong)] | //div[@class="td-post-content"]/blockquote/p[not(descendant::strong)]')]
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

        item['news_outlet'] = 'pi_news'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@itemprop="dateModified"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        authors = response.xpath('//div[@class="td-author-name vcard author"]//a/text()').getall()
        item['author_person'] = list()
        item['author_organization'] = authors if authors else list()

        # Extract keywords, if available
        news_keywords = response.xpath('//div[@class="td-post-source-tags"]/ul/li/a/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//title/text()').get().split(' | PI-NEWS')[0]
        description = ''

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//div[@class="td-post-content"]/p[descendant::strong]'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//div[@class="td-post-content"]/p[descendant::strong]')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="td-post-content"]/p[not(descendant::strong)] | //div[@class="td-post-content"]/blockquote/p[not(descendant::strong)] | //div[@class="td-post-content"]/p[descendant::strong]')]
          
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
        recommendations = list(set(response.xpath("//div[@class='td_module_mega_menu td_mod_mega_menu']//a/@href").getall()))
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
