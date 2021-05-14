# from multiprocessing.dummy import Pool as ThreadPool
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


# multi-thread
def add_paperdata(link):
    tmp_data = get_data(link.split("PMC")[-1])  # parse xml from API
    if tmp_data is not None:
#         print(link)
        return (tmp_data,None)
    else:
        return (None, link)


# get title
def get_papertitle(root_xml):
    for item in root_xml.iter():
        if item.tag == 'title-group':
            for j in item.iter():
                if j.tag == 'article-title':
                    if len(j) == 0:
                        return j.text
                    else:
                        tmp = '' if j.text is None else j.text
                        for i in range(len(j)):
                            tmp += '' if j[i].text is None else j[i].text
                            tmp += '' if j[i].tail is None else j[i].tail

                        return tmp

# concurrently get paper data from pid
def get_data(pid):
    data = {}
    data_link = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id="+str(pid)+"&api_key="+api_key
    r = requests.get(data_link)
    
    # retry to get paper data
    while r.status_code != 200:
        time.sleep(1)
        r = requests.get(data_link)

    root_paper = ET.fromstring(r.text)
    data['title'] = get_papertitle(root_paper).replace("\n","")  # del \n
    data['id'] = str(pid)
#     data['pdf'] =  "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC"+str(pid)+"/pdf/"+ get_pdf_fname(root_paper) # e.g. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6851703/pdf/MMI-112-1284.pdf
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

# search for related paper links from given keywords
def search_links(key_encoded):
    prefix_eutils = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc"
    count = 1000000  # a big number
    search_link = "{prefix}&RetMax={ret}&term={keywords}".format(prefix=prefix_eutils,ret=str(count),keywords=key_encoded)
    print(search_link)
    
    r = requests.get(search_link)
    while r.status_code != 200:
        time.sleep(1)
        r = requests.get(data_link)
    
    # make sure grep all data!
    root = ET.fromstring(r.text)
    pmcids = []
    flag = grep_all_paper(root,count)
    if flag != -1:
        count = flag
        search_link = "{prefix}&RetMax={ret}&term={keywords}".format(prefix=prefix_eutils,ret=str(count),keywords=key_encoded)
        root = ET.fromstring(r.text)
        
    for item in root.iter():
        if item.tag == 'Id':
            pmcids.append(item.text)
    
    print("related papers:",len(pmcids))
    paper_links = []
    for pid in pmcids:
        paper_links.append("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC"+pid)
    return paper_links

api_key = ''

# fetch paper details
def search(keywords, api_key, max_workers = 3, ret = 0):
    print("searching from NCBI PMC.......")
    api_key = api_key
    data = []
    key_encoded = quote(keywords)
    paper_links = search_links(key_encoded)
    data = []
    failed_index = []
    try:
        if ret == 0:
            results = thread_map(add_paperdata, paper_links, max_workers=max_workers)
        else:
            results = thread_map(add_paperdata, paper_links[:ret], max_workers=max_workers)

    except Exception as e:
        print(">"*50, e)
        raise

    return results

text_type = ['csv', 'tsv', 'txt', 'html']
excel_type = ['xls','xlsx']
useful_names = []

# for name, link in download:
def down4check(name_link):
    useful_names = []
    name, link = name_link
#     print("check",name)
    suffix = name.split(".")[-1].lower()
    if not os.path.exists(name):  # download and check file
        r = requests.get(link)
        while r.status_code != 200:
            time.sleep(0.5)
            r = requests.get(link)
        
        # pure text!
        if suffix in text_type:
            flag = True
            for key in k_word_list:
                if key not in r.text:
                    flag = False
            with open(name, 'w') as f: # save it as tmp file
                f.write(r.text)
            if flag:
#                 print(name)
                useful_names.append(name, link)
        
        # ms excel
        if suffix in excel_type:
            with open(name, 'wb') as f:
                f.write(r.content)
            excel_handler(name, link)
        
    else: # check local file
        # pure text
        if suffix in text_type:
            with open(name) as f:
                data = f.readlines()
            flag = True

            for key in k_word_list:
                if key not in data:
                    flag = False
            if flag:  # contain!
#                 print(name)
                useful_names.append(name)
        
        if suffix in excel_type:
            excel_handler(name, link)
            
# must be xls or xlsx
def excel_handler(name, link):
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
        print(name,"is broken!")
        return None
        
    sheet_names = workbook.sheet_names()

    flags = [False for _ in range(len(k_word_list))]

    for sname in sheet_names:
        worksheet = workbook.sheet_by_name(sname)
        for i in range(worksheet.nrows):
            for item in worksheet.row_values(i):
                for k in range(len(k_word_list)):
                    key = k_word_list[k]
                    if key in str(item):
                        flags[k] = True
    if False not in flags:
        return name

# file type stats
def print_type_stat(result):
    type_stat = {}
    for item,_ in result:
        if item is not None:
            for k,v in item['suppmats'].items():
                t = k.split(".")[-1].lower()
                if t in type_stat.keys():
                    type_stat[t] += 1
                else:
                    type_stat[t] = 1
    print("type_stat: ",type_stat)


def collect_related_files(result):
    related_file = []
    # match_type = ['xls', 'xlsx', 'csv', 'tsv', 'txt', 'html', 'doc', 'docx', 'pdf']   # TODO: future work here
    match_type = ['csv', 'tsv', 'txt', 'html', 'xls', 'xlsx']  # pure text..

    for item,_ in result:
        if item is None:
            continue
        subpath = item['title'] if "/" not in item['title'] else item['title'].replace("/","-")
        directory = os.path.join('data', subpath)
        if not os.path.exists(directory):
            # create
            os.makedirs(directory)

        if not os.path.exists(os.path.join(directory, "info.txt")):
            with open(os.path.join(directory, "info.txt"), "w") as f:
                f.write(str(item))

        for name, link in item['suppmats'].items():
            name = name.lower()
            suffix = name.split(".")[-1]
            if suffix in match_type:
                related_file.append((os.path.join(directory, name), link))
    
    return related_file

    
if __name__ == '__main__':
    keywords = "propionyl-CoA CANCER"
    api_key = '1cb4976dd163905feedacce5da0f10552309'
    k_word_list = keywords.split(" ")
    thread_num = 10
    result = search(keywords,api_key,max_workers=thread_num, ret=0)
    # print(result)

    print_type_stat(result)  # show types
    
    related_file = collect_related_files(result)

    try:
        results = thread_map(down4check, related_file, max_workers=10)
    except Exception as e:
        print(">"*50, e)
        raise

    with open(keywords+".result", "w") as f:
        if len(useful_names) != 0:
            f.writelines("\n".join(useful_names))
        else:
            f.writelines("None!")

    print(useful_names)

    print("results show in the root path")