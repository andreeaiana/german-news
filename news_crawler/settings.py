# -*- coding: utf-8 -*-

# Scrapy settings for news_crawler project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'news_crawler'

SPIDER_MODULES = ['news_crawler.spiders']
NEWSPIDER_MODULE = 'news_crawler.spiders'

# Run spider until item count or timeout
CLOSESPIDER_ITEMCOUNT = 200 
CLOSESPIDER_TIMEOUT = 3600*24*3 # For topics 'refugees and migration', 'green deal'
#CLOSESPIDER_TIMEOUT = 3600*24*9 # For topic 'Grundeinkommen', 'wind power', 'homeopathy', 'legalization_soft_drugs'


# Project-specific variables
TOPIC = 'refugees_migration'
#TOPIC = 'grundeinkommen'
#TOPIC = 'green_deal'
#TOPIC = 'wind_power'
#TOPIC = 'homeopathy'
#TOPIC = 'legalization_soft_drugs'

START_DATE = "01.01.2019" # For topic 'refugees and migration'
#START_DATE = "01.01.2015" # For topics 'Grundeinkommen', 'wind power', 'homeopathy', 'legalization_soft_drugs'
#START_DATE = "01.12.2019" # For topic 'green deal'

END_DATE = "20.10.2020" # For topic 'refugees and migration'
#END_DATE = "16.12.2020" # For topic 'Grundeinkommen'
#END_DATE = "31.01.2021" # For topics 'green deal', 'wind power', 'homeopathy', 'legalization_soft_drugs'

ARTICLE_LENGTH = 150
KEYWORDS_MIN_FREQUENCY = 2
KEYWORDS_MIN_DISTANCE = 50

KEYWORDS = ['flüchtl', 'geflücht', 'asyl', 'zuwander', 'immigrant', 'immigration', 'migration', 'migrant',  'ausländer', 'einwander', 'refug', 'rapefug', 'invasor'] # For topic 'refugees and migration'
#KEYWORDS = ['grundeinkommen', 'bedingungslos einkommen'] # For topic 'Grundeinkommen'
#KEYWORDS = ['green deal', 'eu green deal', 'eu grüne deal'] # For topic 'green deal'
#KEYWORDS = ['windkraft', 'windenergie', 'windrad', 'windräder'] # For topic 'wind power'
#KEYWORDS = ['homöopathie', 'globuli', 'alternativmedizin', 'alternativ medizin'] # For topic 'homeopathy'
#KEYWORDS = [
#        ['weich droge', 'soft drug', 'soft droge', 'entkriminalisierung'], 
#        ['marihuana', 'cannabis', 'hanf', 'haschisch', 'tetrahydrocannabinol', 'thc', 'weed', 'psilocybin', 'psilocin', 'magic mushroom', 'zauberpilz', 'halluzinogen pilz'], 
#        ['legal', 'entkriminalisierung']
#        ] # For topic 'legalization_soft_drugs'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'news_crawler (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 5
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'news_crawler.middlewares.MyCustomSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'news_crawler.middlewares.RotateUserAgentMiddleware': 110,
}

#User agents used for rotation (most common agents)
USER_AGENT_CHOICES = [
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30',
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/10.10 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/10.10 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30',
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/10.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30',
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30',
        'Mozilla/5.0 (X11; Linux armv7l) AppleWebKit/537.42 (KHTML, like Gecko) Chromium/25.0.1349.2 Chrome/25.0.1349.2 Safari/537.42',
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/65.0.3325.181 Chrome/65.0.3325.181 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/10.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30'
        ]

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
PERSIST_STATS_ENABLED = True
EXTENSIONS = {
        'scrapy.extensions.closespider.CloseSpider': 500,
        'news_crawler.extensions.PersistStatsExtension': 500
}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'news_crawler.pipelines.HtmlWriterPipeline': 100,
    'news_crawler.pipelines.JsonWriterPipeline': 200,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enableand configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage' 
