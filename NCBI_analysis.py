# pip install xlrd python-docx
from multiprocessing.dummy import Pool as ThreadPool
import NCBI_Seacher
import os
import requests

keywords = "propionyl-CoA CANCER"
k_word_list = keywords.split(" ")
api_key = '1cb4976dd163905feedacce5da0f10552309'
thread_num = 10  # set it 3 if no api_key
result = search(keywords,api_key,thread_num=thread_num, ret=1000)
# print(result)


# file type stats
type_stat = {}
for item,_ in result:
    if item is not None:
        for k,v in item['suppmats'].items():
            t = k.split(".")[-1].lower()
            if t in type_stat.keys():
                type_stat[t] += 1
            else:
                type_stat[t] = 1
print(type_stat)


related_file = []

# match_type = ['xls', 'xlsx', 'csv', 'tsv', 'txt', 'html', 'doc', 'docx', 'pdf']   # TODO: future work here

match_type = ['csv', 'tsv', 'txt', 'html']  # pure text..

for item,_ in result:
    if item is None:
        continue
    
    directory = os.path.join('data', item['title'])
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
            
print("Try",len(related_file),"files")
            
text_type = ['csv', 'tsv', 'txt', 'html']

useful_names = []

# for name, link in download:
def down4check(name_link):
    name, link = name_link
    if not os.path.exists(name):  # download and check file
        r = requests.get(link)
        if r.status_code != 200:
            print("200X", name_link)
            return
        if name.split(".")[-1].lower() in text_type:
            flag = True
            for key in k_word_list:
                if key not in r.text:
                    flag = False
            with open(name, 'w') as f: # save it as tmp file
                f.write(r.text)
            if flag:
                print(name)
                useful_names.append(name)
    else: # check local file
        with open(name) as f:
            data = f.readlines()
        flag = True
        for key in k_word_list:
            if key not in data:
                flag = False
        if flag:  # contain!
            print(name)
            useful_names.append(name)
#     print("--------",link)
            
                       
            
pool = ThreadPool(10)
try:
    results = pool.map(down4check, [(n,l) for n,l in related_file[:]])
except Exception as e:
    print(">"*50, e)
    raise

pool.close()
pool.join()

with open(keywords+".result", "w") as f:
    if len(useful_names) != 0:
        f.writelines("\n".join(useful_names))
    else:
        f.writelines("None!")
            
            