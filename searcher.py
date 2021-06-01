import re
from tqdm.contrib.concurrent import thread_map
from tqdm.contrib.concurrent import process_map
import os
import requests
import xlrd
import time
from urllib.parse import quote
import xml.etree.ElementTree as ET
import json  # to format results outputs

import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s:%(levelname)s: %(message)s"
)

proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890", }


def get_papertitle(root_xml):
    # get title (bad formatting..), and limit its size to 200
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
    get paper data from pid
    input: pmc_id, api_key
    return: a data dict with title, id, pdf, suppmat_links info
    '''
    data = {}
    data_link = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=" + \
        str(pid)+"&api_key="+api_key
    r = requests.get(data_link, proxies=proxies)

    # retry to get paper data
    while r.status_code != 200:
        time.sleep(0.818)
        logging.info("status code failed: "+data_link)
        r = requests.get(data_link, proxies=proxies)

    root_paper = ET.fromstring(r.text)
    paper_result = get_papertitle(root_paper)
    if paper_result is None:
        data['title'] = str(pid)  # del \n
        logging.error("title failed: "+pid)
    else:
        data['title'] = paper_result.replace("\n", "").replace(
            "/", "-").replace(":", "").replace("*", "")  # del \n
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
    count = 9000000 if ret == 0 else ret  # a big number
    search_link = "{prefix}&RetMax={ret}&term={keywords}".format(
        prefix=prefix_eutils, ret=str(count), keywords=key_encoded)
    logging.info(search_link)
    r = requests.get(search_link, proxies=proxies)
    while r.status_code != 200:
        time.sleep(1)
        logging.info("status code failed: "+search_link)
        r = requests.get(search_link, proxies=proxies)

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

    logging.info("related papers: "+str(len(pmcids)))
    paper_links = []
    for pid in pmcids:
        paper_links.append("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC"+pid)
    return paper_links

# hard code here
text_type = ['csv', 'tsv', 'txt', 'html', 'xml']
excel_type = ['xls', 'xlsx']

def search_aio_sub(link_kword_api_keep):
    '''
    input: (link, kword_file, api_key, keep_cache)
    return: none
    '''

    link, keywords_file, api_key, keep_cache = link_kword_api_keep
    k_word_list = keywords_file.split(" ")
    try:
        # parse xml from API
        tmp_data = get_data(link.split("PMC")[-1], api_key)
    except:
        logging.error("get_data error: "+link)
        return None

    if tmp_data is not None:
        # download them and check it!
        directory = os.path.join('data', tmp_data['title'])

        res = []
        for name, link in tmp_data['suppmats'].items():
            fname = os.path.join(directory, name)
            name = name.lower()
            suffix = name.split(".")[-1].lower()
            if suffix not in text_type + excel_type:  # not match
                continue
            
            # init handle_result, this result will be written to disk as a json file
            handle_result = {}
            handle_result["name"] = fname
            for k in k_word_list:
                handle_result[k] = []

            exist_flag = True
            if not os.path.exists(name):
                exist_flag = False
                try:
                    r = requests.get(link, proxies=proxies)
                    # it's hard to get a trade-off concurrency here
                    # speed will be affected here by a static number of threads
                    while r.status_code != 200:
                        time.sleep(0.5)
                        r = requests.get(link, proxies=proxies)
                except:
                    logging.error("download files error: "+fname)
                    return None

            if suffix in text_type:  # match!
                re = plain_text_handler(r, fname, k_word_list, handle_result, exist_flag)
                if re is None and keep_cache:  # keep it as cache
                    with open(fname, 'wb') as f:
                        f.write(r.content)
                if re is not None:
                    res.append(re)

            elif suffix in excel_type:
                re = excel_handler(r, fname, k_word_list, handle_result, exist_flag)
                if re is None and keep_cache:  # keep it as cache
                    with open(fname, 'wb') as f:
                        f.write(r.content)
                if re is not None:
                    res.append(re)

    return res if len(res) != 0 else None

def search_aio(keywords, keywords_file, api_key, max_workers=3, ret=0, keep_cache=False):
    # new entrance and save memory
    # fetch paper details
    logging.info("searching from NCBI PMC.......")
    key_encoded = quote(keywords)
    paper_links = search_links(key_encoded, ret)
    try:
        if ret == 0:
            result = thread_map(search_aio_sub, [(x, keywords_file, api_key, keep_cache)
                                                 for x in paper_links], max_workers=max_workers)
        else:
            result = thread_map(search_aio_sub, [(x, keywords_file, api_key, keep_cache)
                                                 for x in paper_links[:ret]], max_workers=max_workers)

        return list(filter(lambda x: x is not None, result))

    except Exception as e:
        logging.exception("search exception (big one)")


def plain_text_handler(result_request, fname, k_word_list, handle_result, exist_flag):
    logging.debug(fname)
    data = None

    if exist_flag:
        with open(fname) as f:
            data = f.read()
    else:
        try:
            try:
                data = str(result_request.content, encoding='utf-8').split("\n")
            except:
                data = str(result_request.content, encoding='gbk').split("\n")
        except:
            logging.error(fname+" encoding error")
        return None

    for k in k_word_list:
        find_this_key = False
        for line_index in range(len(data)):
            if k in data[line_index]:
                find_this_key = True
                handle_result[k].append(line_index+1)

        if not find_this_key:
            return None  # no this keyword!

    # survive, then write to disk and return
    if not exist_flag:
        directory = os.path.split(fname)[0]
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(fname, 'w') as f:
            f.write(data)

    return handle_result


def excel_handler(result_request, fname, k_word_list, handle_result, exist_flag):
    logging.debug(fname)

    try:
        if exist_flag:
            workbook = xlrd.open_workbook(filename=fname)
        else:
            workbook = xlrd.open_workbook(file_contents=result_request.content)
    except:
        logging.error(fname+" is broken!")
        # try to parse broken excel files as plain text
        return plain_text_handler(result_request, fname, k_word_list, handle_result, exist_flag)

    sheet_names = workbook.sheet_names()
    for key in k_word_list:
        find_this_key = False
        for sname in sheet_names:
            worksheet = workbook.sheet_by_name(sname)
            for i in range(worksheet.nrows):
                for item in worksheet.row_values(i):
                    item_split = str(item).split(",")
                    for j in range(len(item_split)):
                        if key in item_split[j]:
                            find_this_key = True
                            if (sname, i+1, j+1) not in handle_result[key]:
                                handle_result[key].append(
                                    (sname, i+1, j+1))
        if not find_this_key:
            return None  # no this keyword

    # write to disk and return
    directory = os.path.split(fname)[0]
    if not exist_flag:
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(fname, 'wb') as f:
            f.write(result_request.content)

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
    logging.info("type_stat: "+str(type_stat))


def process_result(results, path):
    '''
    gen human-readable results
    path is like keywords+" "+keywords_file...
    '''
    if not os.path.exists(path):
        # create
        os.makedirs(path)

    # write summary info
    with open(os.path.join(path, "result.json"), "w") as f:
        f.write(str(json.dumps(results, sort_keys=True,
                               indent=2, separators=(',', ': '))))
    # create soft link with paper naming path
    for item in results:
        src = item['name']
        prefix, fname = os.path.split(item['name'])
        directory = os.path.join(path, prefix)
        if not os.path.exists(directory):
            os.makedirs(directory)
        dst = os.path.join(directory, fname)  # absolute path
        try:
            os.symlink(os.path.abspath(src), os.path.abspath(dst))
        except:
            pass


class NCBI_searcher(object):

    def __init__(self, api_key='', len_limit=0):
        self.api_key = api_key
        self.len_limit = len_limit

    # search all in one, this method saves memory
    def search_from_all(self, keywords_web, keywords_file, thread_num=9, keep_cache=False):
        self.keywords_web = keywords_web
        self.keywords_file = keywords_file
        results_tmp = search_aio(keywords_web, keywords_file, self.api_key,
                             max_workers=thread_num, ret=self.len_limit, keep_cache=keep_cache)
        
        # join results!
        results = []
    
        for r in results_tmp:
            results += r
        
        process_result(results, "results/" +
                       keywords_web+"+"+keywords_file)
