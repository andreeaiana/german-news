# -*- coding: utf-8 -*-
""" Data loading and preprocessing utilities """

import os
import re 
import pickle
import argparse
import numpy as np
import pandas as pd
from typing import List, Dict 
from pathlib import Path
from langdetect import detect
from util import setup_logging

# DISCLAIMER:
# This code file is adapted from https://github.com/alexandergrote/otree_experiment/blob/main/renewrs/fetch_data.py

PATTERN_LIST = ['Die Woche COMPACT (Video)', 'Dieser Beitrag ist gesperrt und nur für Onlineabonnenten lesbar.']

logger = setup_logging(name=Path(__file__).name, log_level='info')


def format_content(title: str, body: Dict[str, List[str]]) -> str:
    """ 
    Formats an article's content by adding HTML tags and joining the paragraphs. 
    
    Args:
        title (:obj:`str`): 
            The title of an article.
        body (:obj:`Dict[str, List[str]]`): 
            The body of an article. This is  dictionary that maps headlines to lists of corresponding paragraphs.

    Returns:
        :obj:`str`: 
            Article content with HTML tags and joined paragraphs. 
    
    """
    text = _add_html_tag(title, 'h1')

    for header, paragraphs in body.items():
        # Avoid empty paragraphs:
        if not paragraphs:
            continue

        # Reformat header
        header_html = _add_html_tag(header, 'h2') if header != '' else ''

        # Get paragraphs
        paragraphs = _get_paragraphs(paragraphs)

        # Reformat paragraphs
        paragraphs_html = ''.join(paragraphs)

        text += header_html + paragraphs_html

    return text


def _add_html_tag(text: str, tag:str) -> str:
    """ 
    Annotates a text with HTML tags. 

    Args: 
        text (:obj:`str`): 
            Text to be processed.
        tag (:obj:`str`): 
            Tag to add to text.

    Returns:
        :obj:`str`: 
            The text annotated with HTML tags.
    """

    return f'<{tag}>{text}</{tag}>'


def _get_paragraphs(paragraphs: List[str]) -> List[str]:
    """ 
    Returns the paragraphs of an article's body, annotated with HTML tags. 

    Args:
        paragraphs (:obj:`List[str]`): 
            List of strings denoting paragraphs.

    Returns:
        :obj:`List[str]`:
            List of paragraphs annotated with HTML tags.
    """
    paragraphs = [_add_html_tag(paragraph, 'p') for paragraph in paragraphs if not re.findall('trends.embed.renderExploreWidget', paragraph)]
    return paragraphs


def check_if_article_contains_forbidden_pattern(article: str) -> bool:
    """ Checks if an article contains a predefined forbidden pattern. """
    for pattern in PATTERN_LIST:
        if re.findall(pattern, article):
            return True
    return False


def annotate_raw_data(data: pd.DataFrame) -> pd.DataFrame:
    """ 
    Annotates the raw dataset of news articles. 
    
    Args:
        data (:obj:`pd.DataFrame`): 
            A dataframe of news articles.

    Returns:
        :obj:`pd.DataFrame`:
            The annotated dataset.
    """
    logger.info('Annotating raw dataset.')
    
    # Format article' content
    data['formatted_content'] = data.apply(lambda row: format_content(row['title'], row['body']), axis=1)

    # Detect article's language
    data['language'] = data.apply(lambda row: detect(row['formatted_content']), axis=1)

    # Article length
    data['article_length'] = data.apply(lambda row: len(row['formatted_content']), axis=1)

    # Number of subheaders
    data['number_subheaders'] = data.apply(lambda row: len(re.findall('<h2>', row['formatted_content'])), axis=1)

    # Mark articles with forbidden patterns
    data['forbidden_pattern'] = data.apply(lambda row: check_if_article_contains_forbidden_pattern(row['formatted_content']), axis=1)

    logger.info('Finished annotating raw dataset.\n')
    return data


def _get_outlier_bound(series: pd.Series) -> tuple:
    """ Computes the outlier bounds of a series of observations. """

    # Calculate statistics
    quantile_25 = series.quantile(0.25)
    quantile_75 = series.quantile(0.75)
    iqr = quantile_75 - quantile_25

    # Calculate lower and upper bounds 
    lower_bound = quantile_25 - 1.5 * iqr
    upper_bound = quantile_75 + 1.5 * iqr

    return lower_bound, upper_bound


# Count decorator
def log_number_observations(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        logger.info(f'\t\tNumber of observations remaining: {result.shape[0]}')
        return result
    return wrapper


@log_number_observations
def drop_duplicates(data: pd.DataFrame) -> pd.DataFrame:
    """ 
    Drops duplicated articles (i.e. same outlet and content). 

    Args:
        data (:obj:`pd.DataFrame`): 
            A dataframe of news articles.
    
    Returns:
        :obj:`pd.DataFrame`:
            The dataset without duplicated articles.
    """
    duplicates = data[['news_outlet', 'formatted_content']].duplicated()
    data = data[duplicates==False]
    data.reset_index(inplace=True, drop=True)
    return data


@log_number_observations
def drop_non_german_articles(data: pd.DataFrame) -> pd.DataFrame:
    """ 
    Drops articles which are not written in German. 
    
    Args:
        data (:obj:`pd.DataFrame`): 
            A dataframe of news articles.
    
    Returns:
        :obj:`pd.DataFrame`:
            The dataset without non-German articles.
    """
    data.drop(data[data['language'] != 'de'].index, inplace=True)
    data.reset_index(inplace=True, drop=True)
    return data


@log_number_observations
def drop_outliers(data: pd.DataFrame) -> pd.DataFrame:
    """ 
    Drops outlier articles (i.e. too short, too long). 

    Args:
        data (:obj:`pd.DataFrame`): 
            A dataframe of news articles.
    
    Returns:
        :obj:`pd.DataFrame`:
            The dataset without outliers.
    """
    # Log-transform article length distribution so that it resembles a normal distribution
    log_article_length = np.log(data['article_length'])
    
    # Get outlier bounds
    lower_bound, upper_bound = _get_outlier_bound(log_article_length)

    # Get indices of articles to drop
    is_outlier = (log_article_length.between(lower_bound, upper_bound)) == False
    outlier_index = data[is_outlier].index

    # Drop outliers
    data.drop(outlier_index, inplace=True)
    data.reset_index(inplace=True, drop=True)

    return data


@log_number_observations
def drop_news_tickers(data:pd.DataFrame, subheaders_threshold: int = 10) -> pd.DataFrame:
    """ 
    Drops articles that are news or live ticker. 
    Assumption: article contains more than a specified number of subheaders. 
    
    Args:
        data (:obj:`pd.DataFrame`): 
            A dataframe of news articles.
        subheaders_threshold (:obj:`int`, `optional`, defaults to 10):
            The number of subheaders for finding a news ticker.
    
    Returns:
        :obj:`pd.DataFrame`:
            The dataset without news tickers.
    """
    idx2drop = data[data['number_subheaders'] > subheaders_threshold].index
    data.drop(idx2drop, inplace=True)
    data.reset_index(inplace=True, drop=True)
    return data


@log_number_observations
def drop_articles_with_forbidden_pattern(data: pd.DataFrame) -> pd.DataFrame:
    """ 
    Drops articles containing a predefined forbidden pattern in the content. 
    
    Args:
        data (:obj:`pd.DataFrame`): 
            A dataframe of news articles.
    
    Returns:
        :obj:`pd.DataFrame`:
            The dataset without articles containing forbidden patterns.
    """
    idx2drop = data[data['forbidden_pattern'] == True].index
    data.drop(idx2drop, inplace=True)
    data.reset_index(inplace=True, drop=True)
    return data


def process_data(data: pd.DataFrame, bool_drop_duplicates: bool = True, bool_drop_non_german_articles: bool = True, bool_drop_outliers: bool = True, bool_drop_news_ticker: bool = True, subheaders_threshold: int = 10, bool_drop_articles_with_forbidden_pattern: bool = True) -> pd.DataFrame:
    """ 
    Processes the dataset of news articles.

    Args:
        data (:obj:`pd.DataFrame`):
            A dataframe of news articles.
        bool_drop_duplicates (:obj:`bool`, `optional`, defaults to :obj:`True`): 
            Whether to drop duplicates.
        bool_drop_non_german_articles (:obj:`bool`, `optional`, defaults to :obj:`True`):
            Whether to drop non-German articles.
        bool_drop_outliers (:obj:`bool`, `optional`, defaults to :obj:`True`):
            Whether to drop outliers.
        bool_drop_news_ticker (:obj:`bool`, `optional`, defaults to :obj:`True`):
            Whether to drop news tickers.
        subheaders_threshold (:obj:`int`, `optional`, defaults to 10):
            The number of subheaders for finding a news ticker.
        bool_drop_articles_with_forbidden_pattern (:obj:`bool`, `optional`, defaults to :obj:`True`):
            Whether to drop articles wth forbidden pattern.

    Returns:
        :obj:`pd.DataFrame`: 
            The prcessed dataset.
    """
    logger.info(f'Processing raw dataset with {data.shape[0]} news articles.')

    # Drop duplicates
    if bool_drop_duplicates:
        logger.info('\tDropping duplicates.')
        data = drop_duplicates(data)

    # Drop articles not written in German
    if bool_drop_non_german_articles:
        logger.info('\tDropping non-German articles.')
        data = drop_non_german_articles(data)

    # Drop outlier articles
    if bool_drop_outliers:
        logger.info('\tDropping outliers, e.g. too short or too long articles')
        data = drop_outliers(data)

    # Drop news tickers
    if bool_drop_news_ticker:
        logger.info(f'\tDropping articles with more than {subheaders_threshold} subheaders. These are considered news tickers.')
        data = drop_news_tickers(data, subheaders_threshold)

    # Drop articles containign a predefined forbidden pattern
    if bool_drop_articles_with_forbidden_pattern:
        logger.info(f'\tDropping articles that contain a predefined regular expression. In this case, the predefined patterns are: {" & ".join(PATTERN_LIST)}')
        data = drop_articles_with_forbidden_pattern(data)

    # Merge headlines with corresponding paragraphs
    data['body'] = data['body'].apply(lambda x: sum(x.values(), []))
    data['body'] = data['body'].apply(lambda x: ' '.join([para for para in x if para != '' and para != ' ']))

    # Remove empty space from title and description
    data['title'] = data['title'].str.strip()
    data['description'] = data['description'].str.strip()

    # Remove None values and fix formatting of values in certain columns
    data['description'].fillna('', inplace=True)
    data['author_person'] = data['author_person'].apply(lambda authors: [author for author in authors if author is not None])
    data['author_person'] = data['author_person'].apply(lambda authors: authors[0] if len(authors) > 0 and type(authors[0])==list else authors)
    data['author_organization'] = data['author_organization'].apply(lambda authors: [authors] if type(authors)==str else authors)
    data['recommendations'] = data['recommendations'].apply(lambda val: list() if type(val)==float else val)

    # Clean author names
    signs = ['/', ', ', ' und ']
    for sign in signs:
        data['author_person'] = data.apply(lambda row: clean_authors(row['author_person'], sign), axis=1)
        data['author_organization'] = data.apply(lambda row: clean_authors(row['author_organization'], sign), axis=1)

    logger.info(f'Finished processing dataset. Final dataset has {data.shape[0]} news articles.\n')
    
    return data

def clean_authors(authors_list: List[str], sign: str) -> List[str]:
    """
    Cleans a list of author names by splliting them based on a given sign.

    Args: 
        authors_list (:obj:`List[str]`):
            A list of author names.
        sign (:obj:`str`):
            Sign that separates author names in the list.

    Returns:
        :obj:`List[str]`:
            A list of splitted author names.
    """
    if authors_list:
        authors = list()
        for author in authors_list:
            if sign in author:
                authors.extend([name.strip() for name in author.split(sign)])
            else:
                authors.append(author)
        return authors
    return authors_list


def load_raw_data(topic: str = 'refugees_migration') -> pd.DataFrame:
    """ 
    Loads the raw corpus for the desired topic. 

    Args:
        topic: (:obj:`str`, `optional`, defaults to :obj:`refugees_migration`):
            The topic for which to load the news dataset.

    Returns:
        :obj:`pd.DataFrame`:
            A dataset of news articles.
    """
    logger.info('Loading the raw articles.')

    raw_files_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', topic)
    dataframes = list()
    outlets = os.listdir(raw_files_dir)
    for idx, outlet in enumerate(outlets):
        outlet_files_dir = os.path.join(raw_files_dir, outlet, 'json')
        if os.path.isdir(outlet_files_dir):
            outlet_files = os.listdir(outlet_files_dir)
            for json_file in outlet_files:
                filepath = os.path.join(outlet_files_dir, json_file)
                if not os.path.isfile(filepath):
                    raise FileNotFoundError(f'Could not find file for path {filepath}.')
                df = pd.read_json(filepath, orient='index')
                dataframes.append(df.T)
        else:
            logger.info(f'\t\tOutlet {outlet} has no articles.')
        logger.info(f'\tRead files for {idx} of {len(outlets)} outlets.')

    # Concatenate all dataframes into one
    data = pd.concat(dataframes, ignore_index=True)
    data.reset_index(inplace=True, drop=True)
    
    # Split the content column into different coumns for title, description, and body
    data = pd.concat([data.drop(['content'], axis=1), data['content'].apply(pd.Series)], axis=1)

    logger.info(f'Loaded {data.shape[0]} news articles.\n')

    return data


def cache_data(data: pd.DataFrame, filepath: str, dataset_type: str) -> None:
    """ 
    Caches the data to disk as a pickle file at the specified location. 
    
    Args:
        data (:obj:`pd.DataFrame`):
            A dataset of news articles.
        filepath (:obj:`str`):
            The ilepath to the dataset.
        dataset_type (:obj:`str`):
            The type of dataset given by the news topic.
    """
    logger.info(f'Caching {dataset_type} data to disk.')
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)
    logger.info('Data cached.\n')


def load_cache(filepath: str, dataset_type: str) -> pd.DataFrame:
    """ 
    Loads the cached data for the specified topic. 

    Args:
        filepath (:obj:`str`):
            The ilepath to the dataset.
        dataset_type (:obj:`str`):
            The type of dataset given by the news topic.
    
    Returns:
        :obj:`pd.DataFrame`:
            The dataset of news articles.
    """
    logger.info(f'Loading the cached {dataset_type} data')
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    logger.info(f'Loaded {dataset_type} dataset with {data.shape[0]} articles.\n')
    return data
      

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Arguments for data processing.')
    parser.add_argument('--topic', 
            default='refugees_migration',
            choices=['refugees_migration', 'legalization_soft_drugs'],
            type=str,
            help='The topic for which the dataset should be created (default: refugees_migration).'
            )
    parser.add_argument('--create_processed',
            default=True,
            action='store_false',
            help='Whether to create the processed or the raw data (default: processed).' 
            )
    parser.add_argument('--drop_duplicates',
            default=True,
            action='store_false',
            help='Whether to drop duplicates from the dataset (default: True).')
    parser.add_argument('--drop_non_german_articles',
             default=True,
             action='store_false',
             help='Whether to drop non-German articles from the dataset (default: True).')
    parser.add_argument('--drop_outliers',
             default=True,
             action='store_false',
             help='Whether to drop outlier articles (e.g. too long, too short) from the dataset (default: True).')
    parser.add_argument('--drop_news_ticker',
             default=True,
             action='store_false',
             help='Whether to drop articles with more than a predefined number of subheaders (i.e. considered news tickers) from the dataset (default: True).')
    parser.add_argument('--subheaders_threshold',
             default=10,
             type=int,
             help='The minimum number of subheaders an article should have to be considered a news ticker (default: 10).')
    parser.add_argument('--drop_articles_with_forbidden_pattern',
             default=True,
             action='store_false',
             help='Whether to drop articles containing a predefined regular expression from the dataset (default: True).')
    args = parser.parse_args()

    dataset_type = 'processed' if args.create_processed else 'raw'
    filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'dataset', args.topic + '_' + dataset_type + '.p')
    
    if os.path.isfile(filepath):
        logger.info(f'The dataset has already been created and cached.')
    else:
        if args.create_processed:
        # The dataset is not processed. Load the raw, annotated dataset and process it
            logger.info('Dataset is not processed. Processing now..\n')
           
            # Load the cached, raw, annotated dataset, if it exists, or create it otherwise.
            raw_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'dataset', args.topic + '_raw.p')
            if not os.path.isfile(raw_filepath):
                logger.info('Raw dataset does not exist. Creating now..\n')
                data = load_raw_data(args.topic)
                data = annotate_raw_data(data)
                cache_data(data, raw_filepath, dataset_type='raw')
                logger.info('Finished creating raw, annotated dataset.\n')
            else:
                data = load_cache(raw_filepath, dataset_type='raw')

            # Process the raw, annotated dataset
            data = process_data(data, args.drop_duplicates, args.drop_non_german_articles, args.drop_outliers, args.drop_news_ticker, args.subheaders_threshold, args.drop_articles_with_forbidden_pattern)
            logger.info('Finished processing the dataset.')
            cache_data(data, filepath, dataset_type)
            
        else:
            # The raw dataset has not been created. Load the individual aticles and create the annotated dataset.
            logger.info('Raw dataset does not exist. Creating now..\n')
            data = load_raw_data(args.topic)
            data = annotate_raw_data(data)
            cache_data(data, filepath, dataset_type)
            logger.info('Finished creating the raw, annoatated dataset.')
