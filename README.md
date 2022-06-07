# german-news

german_news offers utilities for building topic-specific news corpus collections from online German media outlets. Articles relevant for a given topic are retrieved based on keywords stems. 

## Features
- Built using the standard Scrapy project setup and layout.
- Provides spiders for 42 German media outlets.
- Can be extended with new spiders for other outlets, customed pipelines, extension, and middlewares.

## Extracted information
german-news extracts the following attributes from news articles:
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

### Crawling an outlet
Configurations for the desired spider can be set in `settings.py`. 

The following topic-specific conditions are currently supported and need to be specified:
- Stopping condition: item count or timeout
- Topic
- Publication date timeframe
- Minimum article length
- Minimum keyword frequency
- Minimum distance between keywords in text
- Keywords

Run the code
```
scrapy crawl $OUTLET
```

### Creating a dataset from scraped articles
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
A sample of the raw and processed news corpus constructed for the topic *refugees and migration* is available in `data/dataset` folder. Due to copyright policies, this sample does not contain the abstract and body of the articles. 

A full version of the news corpus is available [upon request](mailto:andreea.iana@uni-mannheim.de).

## Requirements
This code is implemented in Python 3. The requirements can be installed from `requirements.txt`.
```python
pip3 install -r requirements.txt
```

## License
The code is licensed under the MIT License. The data files are licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## Contact
**Author**: Andreea Iana

**Affiliation**: University of Mannheim

**E-mail**: andreeaiana@uni-mannheim.de
