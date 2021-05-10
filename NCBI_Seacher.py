# pip install requests urlllib bs4

from multiprocessing.dummy import Pool as ThreadPool
import requests
import time
import random
from urllib.parse import quote
from bs4 import BeautifulSoup
from xml.etree.ElementTree import parse
import xml.etree.ElementTree as ET

# parse web, deprecated.. bad concurrency
def get_links_from_paperlink(paper_link):
    prefix = "https://www.ncbi.nlm.nih.gov"
    try:
        r_p = requests.get(paper_link)
        soup_p = BeautifulSoup(r_p.text)

        title = soup_p.find_all(name='h1', attrs={'class': 'content-title'})[0]
        title = title.get_text().replace("\n", "").replace(
            "<em>", "").replace("</em>", "")
        pdf_link = None

        pdf = soup_p.find_all(name='link', attrs={
                              'type': 'application/pdf'})[0]
        pdf_link = prefix + pdf.get_attribute_list('href')[0]

        sm_links = {}  # fname:link
        suppmats = soup_p.find_all(name='div', attrs={'class': 'sec suppmat'})
        for sm in suppmats:
            link_element = sm.find_all(
                name='a', attrs={'data-ga-action': 'click_feat_suppl'})[0]
            sm_link = link_element.get_attribute_list('href')[0]
            sm_links[sm_link.split("/")[-1]] = prefix + sm_link

        time.sleep(0.5)
        return {'title': title, 'id': paper_link.split("PMC")[-1], 'pdf': pdf_link, 'suppmats': sm_links}
    except:
        return None


# multi-thread
def add_paperdata(link):
    tmp_data = get_data(link.split("PMC")[-1])  # parse xml from API
    if tmp_data is not None:
        print(link)
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
                        tmp = ''
                        for i in range(len(j)):
                            tmp += j[i].text
                            if j[i].tail is not None:
                                tmp += j[i].tail

                        return tmp

# deprecated because of auto-redirect
# # get paper
# def get_pdf_fname(root_xml):
#     for item in root_paper.iter():
#         if item.tag == 'self-uri':
#             for k,v in item.attrib.items():
#                 if 'href' in k:
#                     return v.split(":")[-1]
#             break
#     return ''


failed_rs = []

# concurrently get paper data from pid
def get_data(pid):
    data = {}
    r = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id="+str(pid)+"&api_key="+api_key)
    if r.status_code != 200:
        print(pid, "status code", r.status_code)
        failed_rs.append(r)
        return None

    root_paper = ET.fromstring(r.text)
    data['title'] = get_papertitle(root_paper)
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

# search for related paper links from given keywords
def search_links(key_encoded):
    prefix_eutils = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc"
    count = 999999  # a big number
    search_link = "{prefix}&RetMax={ret}&term={keywords}".format(prefix=prefix_eutils,ret=str(count),keywords=key_encoded)
    print(search_link)
    r = requests.get(search_link)
    root = ET.fromstring(r.text)
    pmcids = []
    count = 10000000000
    for item in root.iter():
        if item.tag == 'Count':
            if int(item.text) > count:  # need re-try to catch all!
                print(item.text)
                count = int(item.text)
                print(item.text, "too large, and retry")
                break
        if item.tag == 'Id':
            pmcids.append(item.text)
            
    print("related papers:",len(pmcids))
    paper_links = []
    for pid in pmcids:
        paper_links.append("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC"+pid)
    return paper_links

api_key = ''

# fetch paper details
def search(key, api_key, thread_num = 3, ret = 0):
    api_key = api_key
    data = []
    key_encoded = quote(keywords)
    paper_links = search_links(key_encoded)
    pool = ThreadPool(thread_num)
    data = []
    failed_index = []
    try:
    #     results = pool.map(add_paperdata, [x for x in range(len(paper_links))])
        if ret == 0:
            results = pool.map(add_paperdata, [x for x in paper_links])
        else:
            results = pool.map(add_paperdata, [x for x in paper_links[:ret]])

    except Exception as e:
        print(">"*50, e)
        raise

    pool.close()
    pool.join()
    return results


if __name__ == '__main__':
    # config
    keywords = "propionyl-CoA CANCER "
    api_key = '1cb4976dd163905feedacce5da0f10552309'  # this key is only for testing, you can easily get one from your NCBI account!
    thread_num = 10
    
    print(search(keywords,api_key,thread_num))
