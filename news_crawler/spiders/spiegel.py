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


class SpiegelSpider(BaseSpider):
    """Spider for Spiegel"""
    name = 'spiegel'
    rotate_user_agent = True
    allowed_domains = ['www.spiegel.de']
    start_urls = ['https://www.spiegel.de/']
    
    # Exclude articles in English and pages without relevant articles 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'spiegel\.de\/\w.*$'),
                    deny=(r'spiegel\.de\/international\/\w.*$',
                        r'www\.spiegel\.de\/audio\/',
                        r'www\.spiegel\.de\/plus\/',
                        r'www\.spiegel\.de\/thema\/mobilitaet-videos\/',
                        r'www\.spiegel\.de\/thema\/podcasts',
                        r'www\.spiegel\.de\/thema\/audiostorys\/',
                        r'www\.spiegel\.de\/thema\/spiegel-update\/',
                        r'www\.spiegel\.de\/thema\/spiegel-tv\/',
                        r'www\.spiegel\.de\/thema\/bundesliga_experten\/',
                        r'www\.spiegel\.de\/video\/',
                        r'www\.spiegel\.de\/newsletter',
                        r'www\.spiegel\.de\/services',
                        r'www\.spiegel\.de\/lebenundlernen\/schule\/ferien-schulferien-und-feiertage-a-193925\.html',
                        r'www\.spiegel\.de\/dienste\/besser-surfen-auf-spiegel-online-so-funktioniert-rss-a-1040321\.html',
                        r'www\.spiegel\.de\/gutscheine\/',
                        r'www\.spiegel\.de\/impressum',
                        r'www\.spiegel\.de\/kontakt',
                        r'www\.spiegel\.de\/nutzungsbedingungen',
                        r'www\.spiegel\.de\/datenschutz-spiegel',
                        r'www\.spiegel-live\.de\/'
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
       
        # Exclude paid articles (i.e. SpiegelPlus)
        if response.xpath('//span[@class="flex-shrink-0 leading-none"]').get():
            return

        # Check date validity
        creation_date = response.xpath('//meta[@name="date"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[contains(@class, "RichText RichText--iconLinks")]/p')]
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

        item['news_outlet'] = 'spiegel'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        last_modified = response.xpath('//meta[@name="last-modified"]/@content').get()
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').get()
        if data_json:
            data = json.loads(data_json)
            data_authors = data[0]['author']
            if type(data_authors) != list:
                data_authors = [data_authors]
            item['author_person'] = [author['name'] for author in data_authors if author['@type']=='Person']
            item['author_organization'] = [author['name'] for author in data_authors if author['@type']=='Organization']
        else:
            item['author_person'] = list()
            item['author_organization'] = list()

        # Extract keywords, if available 
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get().split(' - DER SPIEGEL')[0]
        description = response.xpath('//meta[@property="og:description"]/@content').get()
       
        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[contains(@class, "RichText RichText--iconLinks")]/p | //h3')]
          
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
        recommendations = response.xpath('//ul[@class="flex flex-col" and preceding-sibling::span[contains(text(), "Mehr zum Thema")]]//a[@class="text-black block" and not(../descendant::span[@data-flag-name="sponpaid"])]/@href').getall()
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item 
