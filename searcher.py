from re import T
from tqdm.contrib.concurrent import thread_map
from tqdm.contrib.concurrent import process_map
import os
import requests
import xlrd
import sys
import time
import random
from urllib.parse import quote
from bs4 import BeautifulSoup
from xml.etree.ElementTree import parse
import xml.etree.ElementTree as ET
import json  # to format results outputs

import logging
logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] %(name)s:%(levelname)s: %(message)s"
)


def get_paperdata(link_api_key):
    # multi-thread
    ''' 
    return: [(data_dict,link)]
    '''
    try:
        link, api_key = link_api_key
        # parse xml from API
        tmp_data = get_data(link.split("PMC")[-1], api_key)
        if tmp_data is not None:
            return (tmp_data, None)
        else:
            return (None, link)
    except:
        logging.exception("get_paperdata exception "+link)
        return (None, link)


# get title (bad formatting..)
def get_papertitle(root_xml):
    for item in root_xml.iter():
        if item.tag == 'title-group':
            for j in item.iter():
                if j.tag == 'article-title':
                    if len(j) == 0:
                        # mv multi-space to one space
                        title = ' '.join(j.text.split())
                        return title[:200] if len(title) > 200 else title
                    else:
                        tmp = '' if j.text is None else j.text
                        for i in range(len(j)):
                            tmp += '' if j[i].text is None else j[i].text
                            tmp += '' if j[i].tail is None else j[i].tail

                        # mv multi-space to one space
                        title = ' '.join(tmp.split())
                        return title[:200] if len(title) > 200 else title
    return None


def get_data(pid, api_key):
    '''
    concurrently get paper data from pid
    input: pmc_id, api_key
    return: a data dict with title, id, pdf, suppmat_links info
    '''
    data = {}
    data_link = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=" + \
        str(pid)+"&api_key="+api_key
    r = requests.get(data_link)

    # retry to get paper data
    while r.status_code != 200:
        time.sleep(1)
        logging.debug("status code failed: "+data_link)
        r = requests.get(data_link)

    root_paper = ET.fromstring(r.text)
    paper_result = get_papertitle(root_paper)
    if paper_result is None:
        data['title'] = str(pid)  # del \n
        logging.error("title failed: "+pid)
    else:
        data['title'] = paper_result.replace("\n", "")  # del \n
    data['id'] = str(pid)
    data['pdf'] = "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC" + \
        str(pid)+"/pdf/"
    sms = {}
    for item in root_paper.iter():
        if item.tag == 'supplementary-material':
            for j in item.iter():
                if j.tag == 'media':
                    for k, v in j.attrib.items():
                        if 'href' in k:
                            sms[v] = "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC" + \
                                str(pid) + "/bin/" + v
    data['suppmats'] = sms
    return data


def grep_all_paper(root, count):
    for item in root.iter():
        if item.tag == 'Count':
            if int(item.text) > count:  # need re-try to catch all!
                return int(item.text)
    return -1


def search_links(key_encoded, ret):
    # search for related paper links from given keywords
    prefix_eutils = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc"
    count = 1000000 if ret == 0 else ret  # a big number
    search_link = "{prefix}&RetMax={ret}&term={keywords}".format(
        prefix=prefix_eutils, ret=str(count), keywords=key_encoded)
    logging.warning(search_link)
    r = requests.get(search_link)
    while r.status_code != 200:
        time.sleep(1)
        logging.debug("status code failed: "+search_link)
        r = requests.get(search_link)

    # make sure grep all data!
    root = ET.fromstring(r.text)
    pmcids = []
    flag = grep_all_paper(root, count)
    if flag != -1:
        count = flag
        search_link = "{prefix}&RetMax={ret}&term={keywords}".format(
            prefix=prefix_eutils, ret=str(count), keywords=key_encoded)
        root = ET.fromstring(r.text)

    for item in root.iter():
        if item.tag == 'Id':
            pmcids.append(item.text)

    logging.warning("related papers: "+str(len(pmcids)))
    paper_links = []
    for pid in pmcids:
        paper_links.append("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC"+pid)
    return paper_links


def search_from_web_sub(keywords, api_key, max_workers=3, ret=0):
    ''' 
    fetch paper details
    input:
    return: [(data_dict,link)]
    '''
    logging.warning("searching from NCBI PMC.......")
    key_encoded = quote(keywords)
    paper_links = search_links(key_encoded, ret)

    try:
        if ret == 0:
            results = thread_map(
                get_paperdata, [(x, api_key) for x in paper_links], max_workers=max_workers)
        else:
            results = thread_map(get_paperdata, [
                                 (x, api_key) for x in paper_links[:ret]], max_workers=max_workers)

    except Exception as e:
        logging.exception("search exception (big one)")

    return results


def search_aio_sub(link_kword_api_keep):
    '''
    input: (link, kword_file, api_key, keep_cache)
    return: none
    '''
    try:
        link, keywords_file, api_key, keep_cache = link_kword_api_keep
        k_word_list = keywords_file.split(" ")
        # parse xml from API
        tmp_data = get_data(link.split("PMC")[-1], api_key)
        if tmp_data is not None:
            # download them and check it!
            for name, link in tmp_data['suppmats'].items():
                name = name.lower()
                suffix = name.split(".")[-1].lower()
                if suffix not in text_type + excel_type:  # not match
                    return  # finish

                r = requests.get(link)

                # it's hard to get a trade-off concurrency here
                # speed will be affected here by a static number of threads
                while r.status_code != 200:
                    time.sleep(0.5)
                    r = requests.get(link)

                # init handle_result
                handle_result = {}
                handle_result["name"] = name
                for k in k_word_list:
                    handle_result[k] = []

                if suffix in text_type:  # match!
                    logging.debug(name+","+link)
                    try:
                        data = str(r.content, encoding='utf-8').split("\n")
                    except:
                        data = str(r.content, encoding='gbk').split("\n")

                    for k in k_word_list:
                        find_this_key = False
                        for line_index in range(len(data)):
                            if k in data[line_index]:
                                find_this_key = True
                                handle_result[k].append(line_index+1)

                        if not find_this_key:
                            return None  # no this keyword!

                    # survive, then write to disk and return
                    with open(name, 'wb') as f:
                        f.write(r.content)

                    return handle_result

                elif suffix in excel_type:
                    logging.debug(name+","+link)
                    try:
                        workbook = xlrd.open_workbook(file_contents=r.content)
                        sheet_names = workbook.sheet_names()

                        for k in range(len(k_word_list)):
                            key = k_word_list[k]
                            find_this_key = False
                            for sname in sheet_names:
                                worksheet = workbook.sheet_by_name(sname)
                                for i in range(worksheet.nrows):
                                    for item in worksheet.row_values(i):
                                        item_split = str(item).split(",")
                                        for j in range(len(item_split)):
                                            if key in str(item_split[j]):
                                                find_this_key = True
                                                if (sname, i+1, j+1) not in handle_result[key]:
                                                    handle_result[key].append(
                                                        (sname, i+1, j+1))
                            if not find_this_key:
                                return None  # no this keyword
                        
                        # write to disk and return
                        with open(name, 'wb') as f:
                            f.write(r.content)
                        
                        return handle_result
                    except:
                        logging.error(name+" is broken!")
                        return None
    except:
        logging.exception("get_paperdata exception "+link)
        return None


def search_aio(keywords, keywords_file, api_key, max_workers=3, ret=0):
    # new entrance and save memory
    # fetch paper details
    logging.warning("searching from NCBI PMC.......")
    key_encoded = quote(keywords)
    paper_links = search_links(key_encoded, ret)
    try:
        if ret == 0:
            result = thread_map(search_aio_sub, [(x, keywords_file, api_key, False)
                                        for x in paper_links], max_workers=max_workers)
        else:
            result = thread_map(search_aio_sub, [(x, keywords_file, api_key, False)
                                        for x in paper_links[:ret]], max_workers=max_workers)
        return list(filter(lambda x: x is not None, result))

    except Exception as e:
        logging.exception("search exception (big one)")


# hard code here
text_type = ['csv', 'tsv', 'txt', 'html', 'xml']
excel_type = ['xls', 'xlsx']


def down4check(name_link_kwordlist_keep_cache):
    try:
        name, link, k_word_list, keep_cache = name_link_kwordlist_keep_cache
        suffix = name.split(".")[-1].lower()
        if not os.path.exists(name):  # download and check file
            r = requests.get(link)
            while r.status_code != 200:
                time.sleep(0.5)
                r = requests.get(link)

            # plain text
            if suffix in text_type:
                with open(name, 'wb') as f:
                    f.write(r.content)
                return plain_text_handler(name, k_word_list, keep_cache)

            # ms excel
            if suffix in excel_type:
                with open(name, 'wb') as f:
                    f.write(r.content)
                return excel_handler(name, link, k_word_list, keep_cache)

        else:  # check local file
            # plain text
            if suffix in text_type:
                return plain_text_handler(name, k_word_list, keep_cache)

            # ms excel
            if suffix in excel_type:
                return excel_handler(name, link, k_word_list, keep_cache)
    except:
        logging.exception("down4check exception "+link)


def plain_text_handler(name, k_word_list, keep_cache):
    # txt..
    handle_result = {}
    handle_result["name"] = name
    for k in k_word_list:
        handle_result[k] = []

    try:
        with open(name) as f:
            data = f.readlines()

        # do n^2 search
        for k in k_word_list:
            find_this_key = False
            for line_index in range(len(data)):
                if k in data[line_index]:
                    handle_result[k].append(line_index+1)
                    find_this_key = True
            if not find_this_key:
                if not keep_cache:
                    os.remove(name)
                return None
    # some unknown issues, e.g. encoding problems...
    except Exception as e:
        logging.error(name+" is broken!")
        return None
    return handle_result


def excel_handler(name, link, k_word_list, keep_cache):
    # must be xls or xlsx
    handle_result = {}
    handle_result["name"] = name
    for k in k_word_list:
        handle_result[k] = []
    workbook = None
    broken_flag = False
    try:
        workbook = xlrd.open_workbook(name)
    except:
        broken_flag = True

    # if file is broken, retry 3 times!
    for _ in range(3):
        if broken_flag:
            time.sleep(0.5)
            r = requests.get(link)
            with open(name, 'wb') as f:
                f.write(r.content)
            try:
                workbook = xlrd.open_workbook(name)
                broken_flag = False
            except:
                pass
        else:
            break

    if broken_flag:
        logging.error(name+" is broken!")
        os.remove(name)
        return None

    sheet_names = workbook.sheet_names()

    flags = [False for _ in range(len(k_word_list))]

    for sname in sheet_names:
        worksheet = workbook.sheet_by_name(sname)
        # n^3 search
        for i in range(worksheet.nrows):
            for item in worksheet.row_values(i):
                for k in range(len(k_word_list)):
                    key = k_word_list[k]
                    item_split = str(item).split(",")
                    for j in range(len(item_split)):
                        if key in str(item_split[j]):
                            flags[k] = True  # mark the flags
                            if (sname, i+1, j+1) not in handle_result[key]:
                                handle_result[key].append((sname, i+1, j+1))

    if False in flags:
        # delete file
        if not keep_cache:
            os.remove(name)
        return None
    else:
        return handle_result


def print_type_stat(result):
    # file type stats
    type_stat = {}
    for item, _ in result:
        if item is not None:
            for k, v in item['suppmats'].items():
                t = k.split(".")[-1].lower()
                if t in type_stat.keys():
                    type_stat[t] += 1
                else:
                    type_stat[t] = 1
    logging.warning("type_stat: "+str(type_stat))


def collect_related_files(result):
    '''
    input:
    return: [(fname, link)]
    '''
    related_file = []
    # match_type = ['xls', 'xlsx', 'csv', 'tsv', 'txt', 'html', 'doc', 'docx', 'pdf']   # TODO: future work here
    # pure text..
    match_type = text_type + excel_type

    for item, _ in result:
        if item is None:
            continue
        item['title'] = item['title'].replace(
            "/", "-").replace(":", "").replace("*", "")
        subpath = item['title']
        directory = os.path.join('data', subpath)
        if not os.path.exists(directory):
            # create
            os.makedirs(directory)

        # write info
        if not os.path.exists(os.path.join(directory, "info.txt")):
            with open(os.path.join(directory, "info.txt"), "w", encoding="utf-8") as f:
                f.write(str(item))

        for name, link in item['suppmats'].items():
            name = name.lower()
            suffix = name.split(".")[-1]
            if suffix in match_type:
                related_file.append([os.path.join(directory, name), link])

    return related_file


def process_result(results, path):
    '''
    gen human-readable results
    keywords+" "+keywords_file
    '''
    if not os.path.exists(path):
        # create
        os.makedirs(path)
    # write summary info

    with open(os.path.join(path, "result.json"), "w") as f:
        f.write(str(json.dumps(results, sort_keys=True,
                               indent=2, separators=(',', ': '))))
    # create soft link
    for item in results:
        src = item['name']
        prefix, fname = os.path.split(item['name'])
        dst = os.path.join(path, prefix[5:10]+"-"+fname)  # absolute path
        os.symlink(os.path.abspath(src), os.path.abspath(dst))


class NCBI_searcher(object):

    def __init__(self, api_key, len_limit=0):
        self.api_key = api_key
        self.len_limit = len_limit

    def search_from_web(self, keywords_web, thread_num=10):
        self.keywords = keywords_web
        result = search_from_web_sub(keywords_web, self.api_key,
                                     max_workers=thread_num, ret=self.len_limit)
        print_type_stat(result)
        return result

    # results save in root path
    # if keep_cache, useless files for now won't be deleted to accelerate future search
    def search_from_file(self, result, keywords_file, keep_cache=False):
        self.keywords_file = keywords_file
        related_file = collect_related_files(result)
        # some magic number...
        logging.warning("Estimated time: " +
                        str(len(related_file)*(4.26/100)) + " mins")
        k_word_list = keywords_file.split(" ")
        try:
            results = thread_map(
                down4check, [x+[k_word_list, keep_cache] for x in related_file], max_workers=9)
            useful_results = list(filter(lambda x: x is not None, results))

            process_result(useful_results, "results/" +
                           self.keywords+"+"+self.keywords_file)
        except Exception as e:
            logging.exception("search_from_file exception (big one)")

        logging.debug("results show in the root path")

    # search all in one, this method saves memory
    def search_from_all(self, keywords_web, keywords_file, thread_num=9, keep_cache=False):
        self.keywords_web = keywords_web
        self.keywords_file = keywords_file
        results = search_aio(keywords_web, keywords_file, self.api_key, max_workers=9, ret=self.len_limit)
        process_result(results, "results/" +
            keywords_web+"+"+keywords_file)



if __name__ == '__main__':

    api_key = '1cb4976dd163905feedacce5da0f10552309'
    keywords = "propionyl-CoA CANCER glyoxylate methylcitrate"
    keywords_file = "Rv1220c"

    searcher = NCBI_searcher(api_key, len_limit=0)

    # just search them
    searcher.search_from_all(keywords, keywords_file)


    # or you can do this.. it's deprecated now, since it will use too much memory!

    # re = searcher.search_from_web(keywords)
    # print(re)
    # searcher.search_from_file(re, keywords_file)

    print("finished!")
