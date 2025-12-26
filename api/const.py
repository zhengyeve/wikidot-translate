# !/usr/bin/env python
# -*- coding: utf-8 -*-


# site related
FROM_SITE = 'horizon-wiki'
TO_SITE = 'horizon-wiki-tc'


# file and images related
CONST_FILE_PREFIX = 'http://www.horizon-wiki.cn/local--files'
CONST_IMG_URL_PATTERN = 'https?://[^/]+\.(?:jpg|gif|png|jpeg)'


PATH_CREDENTIAL = 'api/credential.json'
PATH_CONVERT_EXCEPTION = 'convert_exception.json'


# pages need special handling
KEEP_TITLE = [
    # 'twitter',
 # 'repo',
 # 'pic-stage',
 # 'news-archive',
 # 'news',
 # 'line',
 'goods',
 # 'community',
 # 'widget',
 'co',
 # 'site',
 # 'search',
 # 'system', #-\/
 # 'forum',
 # 'nav',
 # 'about', #-\/
 'stage',
 'actor',
 # '_default',
 'collabo', #-\/
 'event',
 'exhibition',
 'neta',
 # 'talk',
 'bandman',
 'character',
 # 'cover',
 'discography',
 'featured',
 # 'laurant', #-\/
 # 'media', #-\/
 # 'pic-character',
 # 'pic-song',
 # 'play', #-\/
 'pv',
 'reference',
 # 'snippet',
 'song',
 # 'timer',
 # 'update',
 'video',
 'vo'
]

# file to keep (skip overwrite and copy)
# naming convention: page_name/file_name
KEEP_FILE = [
    "goods:_index/noimage.jpg"
]

SKIP_FILE_COPY = [
    "special"
]

CONTENT_BROKEN_PAGES = [
    'line:2015',
    'play:bunnyonofficial'
]


# logging
LOGGING_FORMAT = '[%(levelname)s %(asctime)s |%(module)s] %(message)s'
