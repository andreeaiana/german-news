# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import os
import json
from scrapy.utils.project import get_project_settings


class HtmlWriterPipeline(object):
    """ Creates one directory per spider and stores each scraped page as html. """
    def open_spider(self, spider):
        # Create directory for the given spider
        settings = get_project_settings()
        topic = settings.get('TOPIC')
        self.folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', topic, spider.name, 'html')
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)
        
        # Keep track of how many articles have been parsed
        self.article_num = 0

    def process_item(self, item, spider):
        """ Save article's body in HTML format and pass item to the next pipeline. """
        self.article_num += 1
        file = str(self.article_num) + '.html'
        with open(os.path.join(self.folder, file), 'wb') as f:
            f.write(item['response_body'])
        return item
        

class JsonWriterPipeline(object):
    """ Creates one directory per spider and writes each item into a new json file. """
    def open_spider(self, spider):
        # Create directory for the given spider
        settings = get_project_settings()
        topic = settings.get('TOPIC')
        self.folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', topic, spider.name, 'json')
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)

        self.article_num = 0

    def process_item(self, item, spider):
        """ Save item in JSON file. """
        self.article_num += 1
        file = str(self.article_num) + '.json'
        result = dict(item)
        result.pop('response_body')
        with open(os.path.join(self.folder, file), 'w') as f:
            json.dump(result, f)
