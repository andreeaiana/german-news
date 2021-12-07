# -*- coding: utf-8 -*-
# Utils for news_crawler project

from typing import List


def remove_empty_paragraphs(paragraphs: List[str]) -> List[str]:
    """ 
    Removes empty paragraphs from a list of paragraphs. 
    
    Args:
        paragraphs (:obj:`List[str]`):
            A list of paragraphs.

    Returns:
        :obj:`List[str]`:
            The list of paragraphs without empty paragraphs.
    """
    return [para for para in paragraphs if para != ' ' and para != '']
