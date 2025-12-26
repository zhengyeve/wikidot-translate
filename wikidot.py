#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib.request, urllib.parse, urllib.error
import json
import os
import argparse
import io
import logging
import time
import sys
import pprint
from datetime import datetime
from xmlrpc.client import Fault

from utility.util import compare_dict_values, zip_file
from convert.sc_to_tc import convert_to_tc, replace_token_by_dict
from api.wikidot_api import WikidotAPI
from api.slack import notify_status
from api.const import KEEP_FILE, KEEP_TITLE, SKIP_FILE_COPY, CONTENT_BROKEN_PAGES, CONST_FILE_PREFIX, \
    FROM_SITE, TO_SITE, PATH_CONVERT_EXCEPTION, LOGGING_FORMAT

__author__ = 'eve'

"""
Documentation:
http://developer.wikidot.com/doc:api
http://www.wikidot.com/doc:api
XML-RPC api is limited to 240 req/min (per user). --> 4 req/sec

Usage:



supported commands:

Update one page:
python wikidot.py convert_site --page <page_name> [--debug]

Update pages within one or multiple category:
python wikidot.py convert_site --category <category_name> [<category_name> <category_name>]

Update all pages:
python wikidot.py convert_site [--debug]

Copy file for one page:
python wikidot.py copy_files --page <page_name>

Copy file for one or multiple category::
python wikidot.py copy_files --category <category_name> [<category_name> <category_name>]

Copy file for all site:
python wikidot.py copy_files

"""

LOG = logging.getLogger()


# retrieve archived files
def save_archive_files(s, site, categories, local_dir, upload_site=None):
    # categories: list

    # pages = s.pages.select({'site': site, 'categories': categories})
    pages = s.get_pages(site=site, categories=categories)
    os.chdir(local_dir)
    for page_name in pages:
        img_name = s.files.select({'site': site, 'page': page_name})[0]
        img_url = '{}/{}/{}'.format(CONST_FILE_PREFIX, page_name, img_name)
        local_name = '{}.{}'.format(page_name, img_name)
        local_name = local_name.replace(":", "_")
        LOG.info('Getting "{}" to "{}/{}"'.format(img_url, local_dir, local_name))
        urllib.request.urlretrieve(img_url, local_name)

# opencc -i test.in -o test.out -c s2twp.json


@notify_status(job_name='Copy one page')
def copy_one_page(s, from_site, to_site, from_page, convert=True, expt={}):
    """

    Args:
        s: authorized WikidotAPI instance
        from_site: site to copy from
        to_site: site to copy to
        from_page: page name to copy from
        convert: True if convert from simplified Chinese to Traditional Chinese
        expt:

    Returns: dictionary of option report

    """
    res = {
        "converted": False,
        "saved": False,
        "log_text_lines": []
    }

    # if for some pages we know the content is broken/incomplete,
    # skip automation and do it manually.
    if from_page in CONTENT_BROKEN_PAGES:
        lt = "{}: Known page with incomplete content. Not copying.".format(from_page)
        LOG.info(lt)
        res["log_text_lines"].append(lt)
        return res

    page_from = s.get_single_page(from_site, from_page)
    parent_fullname = page_from['parent_fullname']
    if not parent_fullname:
        parent_fullname = '-'

    if convert:
        # handle content
        from_content = page_from['content']
        content = convert_to_tc(from_content, except_dict=expt)
        LOG.debug("content after conversion:\n{}".format(content.encode('utf-8')))
        res["converted"] = True
        if len(from_content) and from_content == content:
            LOG.debug("{}: content not converted.".format(from_page))
            res["converted"] = False

        # handle title
        if from_page.split(":")[0] in KEEP_TITLE and from_page.split(":")[1][0] != "_":
            title = page_from['title']
        else:
            title = convert_to_tc(page_from['title'], except_dict=expt)

        # handle tags
        tags = convert_to_tc(",".join(page_from['tags']), except_dict=expt).split(",")
        if '' in tags:
            tags.remove('')
        tags.sort()

    else:
        LOG.info("Not converting.")
        LOG.debug("Exception dict is {}".format(expt))
        content = replace_token_by_dict(page_from['content'], expt)
        title = replace_token_by_dict(page_from['title'], expt)
        tags = replace_token_by_dict(page_from['tags'], expt)

    page_to_save = {
        'site': to_site,
        'page': page_from['fullname'],
        'title': title,
        'content': content,
        'parent_fullname': parent_fullname,
        'tags': tags
    }
    LOG.debug("Page to save:\n{}".format(page_to_save))

    # if nothing is going to change, do not do the save.
    page_to = None
    try:
        page_to = s.get_single_page(to_site, from_page)
        LOG.debug("Page existing:\n{}".format(page_to))
    except Fault:
        lt = "{}: does not exists in {}.  Proceed with saving.".format(from_page, to_site)
        LOG.info(lt)
        res["log_text_lines"].append(lt)

    if page_to and content == page_to['content'] and title == page_to['title'] and tags == page_to['tags']:
        lt = "{}: same content as original site, not saving.".format(from_page)
        LOG.info(lt)
        res["log_text_lines"].append(lt)
        res["saved"] = False
        return res

    if page_to:
        no_change = True
        # compare parent_fullname
        for k in ['parent_fullname']:
            if page_to[k] and page_to[k] != page_to_save[k]:
                no_change = False
                LOG.debug("Changes detected in {}:\nFROM:\n{}\nTO:\n{}\n".format(
                    k, page_to[k], page_to_save[k]
                ))

        no_change = no_change and compare_dict_values(page_to, page_to_save,
                                                      keys=['content', 'title', 'tags'])

        if no_change:
            LOG.info("{}: No change detected compared to existing page.".format(from_page))
            res["saved"] = False
            return res

    try:
        r = s.save_one_page(page_to_save)
        res["saved"] = True
        LOG.debug("Saved page:\n{}".format(r))
    except Fault as e:
        LOG.error('{}: failed save with exception: {}. Trying with removed tags...'.format(from_page, e))
        page_to_save.pop('tags')
        try:
            r = s.save_one_page(page_to_save)
            res["saved"] = True
            LOG.debug("Saved page:\n{}".format(r))
        except:
            LOG.error('{}: failed save with exception: {}. Skipping'.format(from_page, e))
            LOG.debug("Page data:\n{}".format(page_to_save))
    return res
    # pass


@notify_status(job_name='Convert Site')
def copy_pages(s, from_site, to_site, categories=None, page=None, convert=True, exception={}):
    """

    Args:
        s: Authorized WikidotAPI instance
        from_site:
        to_site:
        categories:
        page:
        convert:
        exception:

    Returns:

    """
    r = {
        "pages_updated": [],
        "pages_converted": [],
    }

    process_count = 0

    pages = s.get_pages(from_site, categories=categories)

    # convert one single page
    if page:
        pages = [page]

    LOG.info("Retrieved {} pages in categories: {}".format(len(pages), categories))

    LOG.info("Pages to process: {}".format(pages))
    start_time = time.time()
    for p in pages:
        LOG.debug("{}: start processing...".format(p))
        process_count += 1
        response = {
            "converted": False,
            "saved": False
        }
        try:
            response = copy_one_page(s, from_site, to_site, p, convert=convert, expt=exception)
        except Exception as e:
            LOG.error("{}: Failed processing due to exception: {}".format(p, e))

        if response["converted"]:
            r["pages_converted"].append(p)
        if response["saved"]:
            r["pages_updated"].append(p)

        if process_count % 100 == 0:
            LOG.info("PROCESSED {} pages in {} sec.".format(
                process_count, time.time() - start_time
            ))

    r["pages_unconverted"] = list(set(pages) - set(r["pages_converted"]))

    r["log_text"] = """
        Finished processing. [category: {} page: {}]
        {}/{} pages are updated: {}
        {}/{} pages are not converted: {}
        Entire process took {} sec.
    """.format(
        ','.join(categories) if categories else None, page,
        len(r["pages_updated"]), len(pages), r["pages_updated"],
        len(r["pages_unconverted"]), len(pages), r["pages_unconverted"],
        time.time() - start_time
    )

    LOG.info(r["log_text"])
    r["end_time"] = str(datetime.utcnow())
    return r


def main():
    """
    A series of command line actions to perform wikidot site operations.
    Suppoprt site archive, site copy, site translation from simplified Chinese to Traditional Chinese.

    Supported actions:
    - archive_site: archive site to a json file locally
    - save_files: save archived files from one site to a json file locally 
    - convert_site: convert pages from one site to another (zh-cn to zh-tw)
    - compare_sites: compare two sites and update different pages/files
    - get_page: get one single page content
    - copy_files: copy files from one site to another
    - test: test overall functionality
    - test_convert: test convert one single page content
    Returns: exit code 0 if success; 1 otherwise
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('action', action='store', help='action to perform')
    parser.add_argument('--debug', action='store_true', default=False, help='debug flag')
    parser.add_argument('--log', action='store', default=None, help='log file')

    parser.add_argument('--input', action='store',  required=False, help='input file path')
    parser.add_argument('--output', action='store',  required=False, help='output file path')
    parser.add_argument('--zip', action='store_true', default=False, help='whether to zip output file')

    parser.add_argument('--update_files', action='store_true', default=False, help='whether to update files')
    parser.add_argument('--update_pages', action='store_true', default=False, help='whether to update pages')

    parser.add_argument('--site', action='store', help='site to perform action on', default=FROM_SITE)
    parser.add_argument('--category', action='store', help='convert categories', nargs='*')
    parser.add_argument('--page', action='store', help='test convert page')

    args = parser.parse_args()

    # log handling
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    handlers = [stdout_handler]
    if args.log:
        file_handler = logging.FileHandler(filename=args.log)
        handlers.append(file_handler)

    logging.basicConfig(format=LOGGING_FORMAT, handlers=handlers)

    # debug
    if args.debug:
        LOG.info("DEBUGGING.")
        LOG.setLevel(logging.DEBUG)

    action = args.action

    if action == 'archive_site':
        to_zip = args.zip
        site_to_archive = args.site

        if args.output:
            json_out = args.ouput
        else:
            today = datetime.strftime(datetime.today(), "%Y-%m-%d")
            json_out = '{}_{}.json'.format(site_to_archive, today)

        json_out_file = io.open(json_out, 'w', encoding='utf-8')

        wa = WikidotAPI()
        wa.archive_site(site_to_archive, json_out_file)

        if to_zip:
            zip_file(json_out, json_out+'.zip')

    elif action == 'save_files':
        wa = WikidotAPI()
        save_archive_files(wa, args.site, ['cover'], '/tmp', upload_site='horizon-test')

    elif action == 'convert_site':
        cat = args.category
        page = args.page
        
        expt = json.load(io.open(PATH_CONVERT_EXCEPTION, 'r', encoding='utf-8'))

        wa = WikidotAPI(permission='rw')

        copy_pages(wa, FROM_SITE, TO_SITE,
                   categories=cat, page=page,
                   convert=True, exception=expt)


    elif action == 'compare_sites':
        wa = WikidotAPI()
        wa.compare_sites(
            update_files=args.update_files,
            update_pages=args.update_pages)
        # pass

    elif action == 'get_page':

        wa = WikidotAPI()
        res = wa.get_single_page('horizon-wiki', args.page)
        pprint.pprint(res)
        LOG.debug("Page content:\n{}".format(res['content']))
        LOG.debug("Page html:\n{}".format(res['html']))

    elif action == 'copy_files':
        cat = args.category
        page = args.page
        wa = WikidotAPI(permission='rw')
        wa.copy_files(FROM_SITE, TO_SITE, categories=cat, page=page)

    elif action == 'test':

        cat = args.category
        page = args.page or 'laurant:faq'

        wa = WikidotAPI()
        print(wa.get_categories(FROM_SITE))
        print(os.environ)
        # wa.copy_files(from_site, to_site, categories=cat, page=page)
        expt = json.load(io.open(PATH_CONVERT_EXCEPTION, 'r', encoding='utf-8'))
        copy_pages(wa, FROM_SITE, TO_SITE,
                   categories=cat, page=page,
                   convert=True, exception=expt)


    elif action == 'test_convert':
        # all_pages_sc = s2.pages.select({'site': sc, "order": "created_at desc desc"})
        # print len(all_pages_sc), all_pages_sc
        # all_pages_tc = s2.pages.select({'site': tc})
        # print len(all_pages_tc), all_pages_tc
        expt = json.load(io.open(PATH_CONVERT_EXCEPTION, 'r', encoding='utf-8'))
        # print(expt)
        # tctest="video:tc-test"
        tctest="play:ousama-kun-to-ryoufuku-kun-no-bouken"
        # tctest = "play:revo-meets-noel"
        if args.page:
            tctest = args.page
        wa = WikidotAPI()
        page_from = wa.get_single_page(site=FROM_SITE, page=tctest)
        # print(page_from)
        content = page_from['content']
        # contentc = opencc.convert(content, config='s2twp.json')
        contentc = convert_to_tc(content,  except_dict=expt)

        if args.input:
            content = io.open(args.input, 'r', encoding='utf-8')
        print(content)
        print("{} --> {}".format(len(content), len(contentc)))
        print(contentc)
    
    else:
        LOG.error("Unrecognized action: {}".format(action))
        return 1
        

if __name__ == "__main__":
    # LOG = logging.getLogger(__name__)
    LOG.setLevel(logging.INFO)
    main()

