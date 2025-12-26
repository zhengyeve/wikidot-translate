# !/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
LOG = logging.getLogger(__name__)


def replace_token_by_dict(input_str, exception_dict):
    # given a replace dict with key-value pair of strings, replace value with key.
    output_str = input_str
    for k, v in list(exception_dict.items()):
        if k in output_str:
            LOG.debug("Detected replacement: {} to {}".format(k, v))
        output_str = output_str.replace(k, v)
    return output_str


def convert_to_tc(content, except_dict={}):
    # content: unicode.
    # convert an input str to traditional chinese
    content_utf8 = content
    
    from opencc import OpenCC
    cc = OpenCC('s2twp')
    output_str = cc.convert(content_utf8)
    
    output_str = replace_token_by_dict(output_str, except_dict)

    if not len(content):
        LOG.debug("0 content. Bypassing.")
        return content

    diff = abs(len(output_str) - len(content)) / float(len(content))
    if diff < .5:
        return output_str
    else:
        LOG.warning("Large diff after conversion: {} ({}/{}). Keep old content.".format(
            diff, len(output_str), len(content)))
        print(len(content), content)
        print(len(output_str), output_str)
        return content
