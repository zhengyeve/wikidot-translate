# !/usr/bin/env python
# -*- coding: utf-8 -*-

from xmlrpc.client import ServerProxy, Fault
from api.const import PATH_CREDENTIAL, KEEP_FILE, SKIP_FILE_COPY, FROM_SITE, TO_SITE
from api.slack import notify_status
import logging
import json
import time
import os.path


LOG = logging.getLogger(__name__)


# logging.basicConfig()

class WikidotAPI(object):
    API_PATH_TEMPLATE = 'https://{user}:{key}@www.wikidot.com/xml-rpc-api.php'
    LOG_COUNT = 100


    # rate limit: 240 req per min per user
    WAIT = 0.2

    def __init__(self,
                 credential_file=PATH_CREDENTIAL,
                 permission='ro',
                 from_site=FROM_SITE,
                 to_site=TO_SITE
                 ):
        credential = json.load(open(credential_file))
        self.user = credential['user']
        self.permission = permission
        self.ro_key = credential['ro_key']
        self.rw_key = credential['rw_key']
        self.from_site = from_site
        self.to_site = to_site

        self.s = self.authorize()

    def authorize(self):
        key = self.ro_key
        if self.permission == 'rw':
            key = self.rw_key

        api_path = self.API_PATH_TEMPLATE.format(user=self.user, key=key)
        LOG.info('Authorizing {} {} ...'.format(self.user, api_path))
        return ServerProxy(api_path)

    # all categories (list of str: category name)
    def get_categories(self, site):
        return self.s.categories.select({'site': site})

        # all pages (list of str: page name)

    def get_pages(self, site, categories=None, page=None):
        data = {'site': site}

        if page is not None:
            data['page'] = page

        if categories:
            data['categories'] = categories
        return self.s.pages.select(data)

    # all files of a specific page
    def get_files(self, site, page):
        data = {'site': site, 'page': page}
        time.sleep(self.WAIT)
        return self.s.files.select(data)

    # file content of a specific file of a page
    def get_file_content(self, site, page, filename):
        data = {'site': site, 'page': page, 'file': filename}
        return self.s.files.get_one(data)

    # single page (dictionary)
    def get_single_page(self, site, page):
        time.sleep(self.WAIT)
        return self.s.pages.get_one({'site': site, 'page': page})

    def save_one_page(self, page_to_save):
        r = self.s.pages.save_one(page_to_save)
        return r

    def copy_one_file(self, from_page, from_file, to_page=None, to_file=None):
        to_upload = False
        from_file_path = u'{}/{}'.format(from_page, from_file)

        if not to_page:
            to_page = from_page
        if not to_file:
            to_file = from_file
        to_file_path = u'{}/{}'.format(to_page, to_file)

        LOG.debug(u'Processing {}/{} to {}/{}'.format(self.from_site, from_file_path, self.to_site, to_file_path))

        try:
            file_from = self.get_file_content(self.from_site, from_page, from_file)
        except Fault:
            LOG.error(u"Fail to retrieve {}. Copy manually.".format(from_file_path))
            return

        # avoid extra uploads
        try:
            file_to = self.get_file_content(self.to_site, to_page, to_file)
        except Fault:
            LOG.info(u"File {} does not exist in {}. Uploading...".format(to_file_path, self.to_site))
            to_upload = True

        if not to_upload:
            LOG.debug(u"File {} already exist in {}. Comparing...".format(to_file_path, self.to_site))
            if from_file_path in KEEP_FILE:
                LOG.debug(u"File {} in no-change list. Not uploading.".format(to_file_path))
                return
            elif file_to['content'] == file_from['content']:
                LOG.debug(u"File {} already exists with no change. Not uploading.".format(to_file_path))
                return

        file_to_save = {
            'site': self.to_site,
            'page': to_page,
            'file': file_from['filename'],
            'content': file_from['content'],
        }
        LOG.debug("File to save:\n{}".format(file_to_save))

        try:
            r = self.s.files.save_one(file_to_save)
            LOG.debug(u"Saved file: \n{}".format(to_file_path, r))
        except Fault as e:
            LOG.error(u'Failed to save {} in {} with exception: {}'.format(to_file_path, from_page, e))

    def copy_files(self, categories=None, page=None):
        pages = self.get_pages(self.from_site, categories=categories)

        c = 0

        for p in pages:
            file_list = self.get_files(self.from_site, p)
            if file_list:
                LOG.info(u"Retrieving {} files in page {}: {}".format(len(file_list), p, file_list))
                for f in file_list:
                    c += 1
                    if c % self.LOG_COUNT == 0:
                        LOG.info('Processed {} files'.format(c))
                    self.copy_one_file(p, f)
        LOG.info('Processed {} files'.format(c))

    ## Compare site: copy over files if different
    ## reports error if the page that files need to be copied to does not exist
    @notify_status('Compare Sites')
    def compare_sites(self, update_pages=False, update_files=True):
        LOG.info("Comparing {} to {}".format(self.to_site, self.from_site))

        # page: detect removed / changed / added
        from_site_pages = self.get_pages(site=self.from_site)
        to_site_pages = self.get_pages(site=self.to_site)

        r = {
            # page
            "from_site_pages": from_site_pages,
            "to_site_pages": to_site_pages,
            "removed_pages": list(set(to_site_pages) - set(from_site_pages)),
            "added_pages": list(set(from_site_pages) - set(to_site_pages)),

            # file
            "removed_files": [],
            "added_files": [],
            "from_site_files": [],
            "to_site_files": [],
            "skipped_pages": [],

            # log
            "log_text_lines": []
        }

        lt = """
        {} pages in {},
        {} pages in {},
        {} unhandled added pages: {},
        {} unhandled removed pages: {}
        """.format(len(from_site_pages), self.from_site, len(to_site_pages), self.to_site,
                   len(r["added_pages"]), r["added_pages"],
                   len(r["removed_pages"]), r["removed_pages"])
        LOG.info(lt)
        r["log_text_lines"].append(lt)

        # file
        c = 0
        for p in from_site_pages:
            c += 1
            if c % self.LOG_COUNT == 0:
                LOG.info("Processed {} Pages ...".format(c))

            if p.split(':')[0] in SKIP_FILE_COPY:
                r["skipped_pages"].append(p)
                continue

            flist_from = self.get_files(self.from_site, p)
            if flist_from:
                LOG.debug("processing {} files in {}".format(len(flist_from), p))
                r["from_site_files"] += [u'{}/{}'.format(p, f) for f in flist_from]
                if p in to_site_pages:
                    flist_to = self.get_files(self.to_site, p)
                    r["to_site_files"] += [u'{}/{}'.format(p, f) for f in flist_to]
                else:
                    flist_to = []
                r["removed_files"] += [u'{}/{}'.format(p, f) for f in list(set(flist_to) - set(flist_from))]
                r["added_files"] += [u'{}/{}'.format(p, f) for f in list(set(flist_from) - set(flist_to))]
        LOG.info("Processed {} Pages ...".format(c))

        lt = """
        {} files in {},
        {} files in {},
        {} unhandled added files: {},
        {} unhandled removed files: {},
        {} pages skipped due to config: {}
        """.format(len(r["from_site_files"]), self.from_site,
                   len(r["to_site_files"]), self.to_site,
                   len(r["added_files"]), r["added_files"],
                   len(r["removed_files"]), r["removed_files"],
                   len(r["skipped_pages"]), r["skipped_pages"])
        LOG.info(lt)
        r["log_text_lines"].append(lt)

        if update_files:
            LOG.info("Copying {} files ...".format(len(r["added_files"])))
            for f in r["added_files"]:
                page = f.split('/')[0]
                filename = f.split('/')[-1]
                self.copy_one_file(page, filename)
            r["log_text_lines"].append("Copied {} files.".format(len(r["added_files"])))

        return r

    def archive_site(self, site, json_out_fh):
        """
        Wite site json data to file handler.
        Args:
            site:
            json_out_fh:

        Returns:

        """
        all_page_data = []
        count_appended_page = 0
        all_pages = self.get_pages(site)
        LOG.info('Found {} pages.'.format(len(all_pages)))

        for page in all_pages:
            page_data = {page: self.get_single_page(site, page)}
            # all_page_data.append(page_data)
            # json.dump(page_data, json_out_file)
            json_out_fh.write(str(json.dumps(page_data, ensure_ascii=False)))
            json_out_fh.write('\n')
            count_appended_page += 1
            LOG.info('Wrote page ({}/{}): {}'.format(
                count_appended_page, len(all_pages), page))
            LOG.debug('page_data: {}'.format(page_data))
            # if  count_appended_page == 10: break

        # json_out_file.write(unicode(json.dumps(all_page_data, ensure_ascii=False)))
        # LOG.info('Wrote {} page_data to file: {}'.format(len(all_page_data), json_out))
        json_out_fh.close()
