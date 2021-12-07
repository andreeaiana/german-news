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


class FazSpider(BaseSpider):
    """Spider for Frankfurter Allgemeine Zeitung"""
    name = 'faz'
    rotate_user_agent = True
    allowed_domains = ['www.faz.net']
    start_urls = ['https://www.faz.net/']

    # Exclude English articles and pages without relevant articles (i.e. sports) 
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'www\.faz\.net\/\w+\/\w.*\.html$'),
                    deny=(r'www\.faz\.net\/english\/\w.*\.html$',
                        r'www\.faz\.net\/asv\/\w.*\.html$',
                        r'www\.faz\.net\/\w.*\/routenplaner\/\w+\-\d+\.html$',
                        r'www\.faz\.net\/\w+\/finanzen\/boersen-maerkte\/',
                        r'www\.faz\.net\/faz-net-services\/sport-live-ticker\/\w.*',
                        r'www\.faz\.net\/aktuell\/sport\/sport-in-zahlen\/\w.*',
                        r'www\.faz\.net\/faz-live',
                        r'www\.faz\.net\/podcasts\/\w.*'
                        )
                    ),
                callback='parse_item',
                process_links = 'process_links',
                follow=True
                ),
            )

    def process_links(self, links):
        """ 
        Modifies the original URLs such that articles expanding over multiple pages are instead displayed on one page. 
        """
        for link in links:
            link.url = link.url + '?printPagedArticle=true' 
        return list(set(links)) # Avoid duplicates

    def parse_item(self, response):
        """
        Checks article validity. If valid, it parses it.
        """

        # Exclude paid articles
        if response.xpath('//div[contains(@class, "PaywallInfo")]').get():
            return

        # Check date validity 
        creation_date = response.xpath('//time/@datetime').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//p[@class="First atc-TextParagraph"]')]
        paragraphs.extend([node.xpath('string()').get().strip() for node in response.xpath('//p[@class="atc-TextParagraph"]')])
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
        
        item['news_outlet'] = 'faz'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()
        
        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        item['last_modified'] = creation_date.strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')
        
        # Get authors
        data_json = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        if data_json:
            data = json.loads(data_json[-1])
            authors = data['author'] if type(data['author'])==list else [data['author']]
            item['author_person'] = [author['name'].strip() for author in authors if author['@type']=='Person']
            author_organization = [author['name'].strip() for author in authors if author['@type']=='Organization']
            item['author_organization'] = author_organization[0].split('/') if len(author_organization) == 1 else author_organization
        else:
            item['author_person'] = list()
            item['author_organization'] = list()

        # Extract keywords
        news_keywords = response.xpath('//meta[@name="news_keywords"]/@content').get()
        item['news_keywords'] = news_keywords.split(', ') if news_keywords else list()
        
        # Get title, description, and body of article
        title = response.xpath('//meta[@property="og:title"]/@content').get()
        description = response.xpath('//meta[@property="og:description"]/@content').get()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()
        if response.xpath('//h3[@class="atc-SubHeadline"]'):
            # Extract headlines
            headlines = [h3.xpath('string()').get().strip() for h3 in response.xpath('//h3[@class="atc-SubHeadline"]')]
            
            # Extract paragraphs with headlines
            text = [node.xpath('string()').get().strip() for node in response.xpath('//p[@class="First atc-TextParagraph"]')]
            text.extend([node.xpath('string()').get().strip() for node in response.xpath('//p[@class="atc-TextParagraph"] | //h3[@class="atc-SubHeadline"]')])

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
        recommendations = response.xpath('//div[@class="tsr-Base_TextWrapper  " and ancestor::article[@class="js-tsr-Base tsr-Base tsr-More tsr-Base-has-no-text-border-line  tsr-Base-has-border     "]]/div/div/a/@href').getall() 
        if recommendations:    
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body
        
        yield item
