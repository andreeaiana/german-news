# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class NewsCrawlerItem(Item):
    """ Model for the scraped items. """
    news_outlet = Field()
    provenance = Field() # url
    author_person = Field()
    author_organization = Field()
    creation_date = Field()
    last_modified = Field()
    crawl_date = Field() 
    content = Field() # title, description, body
    news_keywords = Field()
    recommendations = Field()
    query_keywords = Field()
    response_body = Field() # Stores response body to be saved as html
