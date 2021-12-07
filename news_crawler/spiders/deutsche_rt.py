
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


class DeutscheRT(BaseSpider):
    """Spider for DeutscheRT"""
    name = 'deutsche_rt'
    rotate_user_agent = True
    allowed_domains = ['de.rt.com']
    start_urls = ['https://de.rt.com/']

    # Exclude pages without relevant articles
    rules = (
            Rule(
                LinkExtractor(
                    allow=(r'de\.rt\.com\/\w.*'),
                    deny=(r'de\.rt\.com\/video\/',
                        r'de\.rt\.com\/spezial\/',
                        r'de\.rt\.com\/programme\/',
                        r'de\.rt\.com\/strippenzieher\/',
                        r'de\.rt\.com\/dokumentation\/',
                        r'de\.rt\.com\/impressum\/',
                        r'de\.rt\.com\/jobs\/',
                        r'de\.rt\.com\/privacy\-policy\/',
                        r'de\.rt\.com\/uber\-uns\/',
                        r'de\.rt\.com\/terms\-of\-use\/',
                        r'de\.rt\.com\/nutzungsbedingungen\-fuer\-die\-kommentarfunktion\-bei\-rt\-deutsch\/'
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
        creation_date = response.xpath('//meta[@name="publish-date"]/@content').get()
        if not creation_date:
            return
        creation_date = datetime.fromisoformat(creation_date.split('+')[0])
        if self.is_out_of_date(creation_date):
            return

        # Extract the article's paragraphs
        paragraphs = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="Text-root Text-type_5 ArticleView-text ViewText-root "]/p[not(descendant::strong)] | //div[@class="Text-root Text-type_5 ArticleView-text ViewText-root "]/blockquote/p')]
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

        item['news_outlet'] = 'deutsche_rt'
        item['provenance'] = response.url
        item['query_keywords'] = self.get_query_keywords()

        # Get creation, modification, and crawling dates
        item['creation_date'] = creation_date.strftime('%d.%m.%Y')
        data_json = response.xpath('//script[@type="application/ld+json"]/text()')[1].get()
        data_json = json.loads(data_json)
        last_modified = data_json["dateModified"]
        item['last_modified'] = datetime.fromisoformat(last_modified.split('+')[0]).strftime('%d.%m.%Y')
        item['crawl_date'] = datetime.now().strftime('%d.%m.%Y')

        # Get authors
        item['author_person'] = list()
        item['author_organization'] = [data_json['publisher']['name']]

        # Extract keywords, if available
        news_keywords = response.xpath('//div/ul[@class="Tags-list Tags-default"]/li/a/text()').getall()
        item['news_keywords'] = news_keywords if news_keywords else list()

        # Get title, description, and body of article
        title = response.xpath('//meta[@name="twitter:title"]/@content').get().strip()
        description = response.xpath('//meta[@name="twitter:description"]/@content').get().strip()

        # Body as dictionary: key = headline (if available, otherwise empty string), values = list of corresponding paragraphs
        body = dict()

        if response.xpath('//div[@class="Text-root Text-type_5 ArticleView-text ViewText-root "]/p/strong[not(contains(text(), "Mehr zum Thema"))] | //h4'):
            # Extract headlines
            headlines = [h.xpath('string()').get().strip() for h in response.xpath('//div[@class="Text-root Text-type_5 ArticleView-text ViewText-root "]/p/strong[not(contains(text(), "Mehr zum Thema"))] | //h4')]

            # Extract the paragraphs and headlines together
            text = [node.xpath('string()').get().strip() for node in response.xpath('//div[@class="Text-root Text-type_5 ArticleView-text ViewText-root "]/p[not(descendant::strong)] | //div[@class="Text-root Text-type_5 ArticleView-text ViewText-root "]/blockquote/p | //div[@class="Text-root Text-type_5 ArticleView-text ViewText-root "]/p/strong[not(contains(text(), "Mehr zum Thema"))] | //h4')]
          
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
        recommendations = response.xpath('//p/a[preceding-sibling::strong[contains(text(), "Mehr zum Thema")]]/@href').getall()
        if recommendations:
            if len(recommendations) > 5:
                recommendations = recommendations[:5]
            item['recommendations'] = recommendations
        else:
            item['recommendations'] = list()

        item['response_body'] = response.body

        yield item
