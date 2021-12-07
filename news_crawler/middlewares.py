# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/spider-middleware.html

from random import choice
from scrapy import signals
from scrapy.exceptions import NotConfigured


class RotateUserAgentMiddleware(object):
    """ Middleware for rotating user-agent for each request. """

    def __init__(self, user_agents):
        self.enabled = False
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        """"Get the uer aegnts from settings.py"""
        user_agents = crawler.settings.get('USER_AGENT_CHOICES', [])
        if not user_agents:
            raise NotConfigured('USER_AGENT_CHOICES not set or empty.')
        s = cls(user_agents)
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def spider_opened(self, spider):
        self.enabled = getattr(spider, 'rotate_user_agent', self.enabled)

    def process_request(self, request, spider):
        """Select user agent on request"""
        if not self.enabled or not self.user_agents:
            return 
        request.headers['user-agent'] = choice(self.user_agents)
