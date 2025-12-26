#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging
import zipfile
from api.const import CONST_IMG_URL_PATTERN


__author__ = 'eve'

LOG = logging.getLogger(__name__)


def unique_content_list(l):
    """
    Docstring for unique_content_list
    
    :param l: list of content with 'id' field
    :return: Description
    :rtype: Any
    """
    # l: list of content
    new_list = {}
    for d in l:
        if d['id'] not in new_list:
            new_list[d['id']] = d
    return list(new_list.values())


def url_is_image(url):
    """
    return true if the url is an wikidot image url
    
    :param url: Description
    """
    l = re.findall(CONST_IMG_URL_PATTERN, url)
    LOG.debug("Findall result is {} for findall({},{})".format(l,CONST_IMG_URL_PATTERN,url))
    return len(l) > 0


def compare_dict_values(from_dict, to_dict, keys=None, keep_list_order=False):
    """
    Utility to compare values of two dicts. Each dict represents data for a wikidot page.
    
    :param from_dict: Data of source site
    :param to_dict: Data of target site
    :param keys: specific keys to compare. If None, compare all keys.
    :param keep_list_order: whether to keep list order when comparing list values.
    :return: True if all values for the given keys are the same in both dicts; False otherwise
    """
    if not keys:
        keys = list(set(from_dict.keys()).intersection(set(to_dict.keys())))
    for k in keys:
        from_v = from_dict[k]
        to_v = to_dict[k]

        if isinstance(from_v, str):
            from_v = str(from_v)
        if isinstance(to_v, str):
            to_v = str(to_v)

        if not isinstance(from_v, type(to_v)):
            LOG.debug("Different data type: {} vs. {}".format(type(from_v), type(to_v)))
            return False

        if isinstance(from_v, list):
            if not keep_list_order:
                from_v = set(from_v)
                to_v = set(to_v)
                LOG.debug("converting list to set: {} vs. {}".format(from_v, to_v))
            if from_v != to_v:
                LOG.debug("Different value for list: {} vs. {}".format(from_v, to_v))
                return False
        elif from_v != to_v:
            LOG.debug("Different value: {} vs. {}".format(from_v, to_v))
            return False

    return True


def zip_file(input_file, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zip_file_out:
        zip_file_out.write(input_file)
        if zip_file_out.testzip() is None:
            LOG.info('Successfully zipped to {}'.format(output_file))

### jq utilities
# jq 'sort_by(.id) | .[] | {user: .user.name, time: .created_at, text:.text}'  _archive/BUNNYONOFFICIAL/BUNNYONOFFICIAL_625961229027119105-649161253584154624.json
