# renewrs_corpora
<!-- Topic-specific news corpus collection from German media outlets for the ReNewRS project. -->

renewrs-corpora offers utilities building topic-specific news corpus collections from online German media outlets. Articles relevant for a given topic are retrieved based on keywords stems. New topics or customized spiders for additional media outlets can easily be added to the current implementation.

## Features
- It is built using the standard Scrapy project setup and layout.
- It provides spiders for 42 German media outlets.
- It can be extended with new spiders for other outlets, customed pipelines, extension, and middlewares.

## Extracted information
renewrs-corpora extracts the following attributes from news articles:
- headline
- abstract (lead paragraph)
- body (main text)
- URL
- name(s) of author(s)
- publication date
- modification date
- news keyords
- recommendations (i.e. links to other articles suggested by the outlet)
- query keywords (i.e. keywords used for determing whether the article is relevant for the topic)

## Usage

### Crawling an outlet:
Set configuration for the desired spider in [settings.py](./news_crawler/settings.py). Run the code: 

```python
scrapy crawl $OUTLET
```

### Creating a dataset from scraped articles:
```
python preprocess_data 

optional arguments:
--topic                                     Topic for which the dataset should be created (default: refugees_migration)
--create_processed                          Indicate whether to create the processed or the raw data (default: True)
--drop_duplicates                           Indicate whether to drop duplicates from the dataset (default: True)
--drop_non_german_articles                  Indicate whether to drop non-German articles from the (default: True)
--dop_outliers                              Indicate whether to drop outlier articles (e.g. too long, too short) (default: True)
--drop_news_ticker                          Indicate whether to drop news tickers (i.e. articles with more than a predefined number of subheaders) from the dataset (default: True)
--subheaders_threshold                      Minimum number of subheaders an article should have to be considered a news ticker (default: 10)
--drop_articles_with_forbidden_patterns     Indicate whether to drop articles containing a predefined regular expression from the dataset (default: True)
```

## Data
A sample of the news corpus constructed for the topic *refugees and migration* is available in [datasets](./data/datasets). Due to copyright policies, this sample does not contain the abstract an bodies of the articles. 

A full version of the news corpus is available [upon request](mailto:andreea@informatik.uni-mannheim.de).

## Requirements
This code is implemented in Python 3. The requirements can be installed from requirements.txt


```python
pip3 install -r requirements.txt
```

## License
Licensed under the MIT license.

## Contact
**Author**: Andreea Iana

**Affiliation**: University of Mannheim

**E-mail**: andreea@informatik.uni-mannheim.de
