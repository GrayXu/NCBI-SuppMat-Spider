# NCBI-SuppMat-Spider

![lincense](https://img.shields.io/badge/license-MIT-green)

A web spider to search and download supplementary materials (*SuppMat*) with specific keywords from NCBI PubMed Central® (PMC) .

***input*: keywords of titles and abstracts to search papers, and the keywords to search supplementary materials**  
***output*: all related supplementary materials.**

## Usage

```
git clone https://github.com/GrayXu/NCBI-SuppMat-Spider.git
pip install -r requirements.txt
python3 main.py
```
1. Use pip to install dependencies.  
2. **config** main.py, and directly **run** it  

*note: pls make sure xlrd's version, otherwise it won't handle xlsx files*

## TO-DO

- features
  - [x] progress bar
  - [x] optional keywords for searching in files
  - [x] ouput coordinates of keywords in xls&xlsx
  - [x] create soft links to related suppmats
  - [x] optionally keep un-related files as cache
  - [x] optional case sensitivity
  - [ ] more account keys and proxy IPs to speed up (after scaling seacher to millions level, waiting time will be a disaster, so it's urgent)
  

- support more formats
  - [x] csv, txt, tsv, html, xml  
  - [x] xls, xlsx  
  - [ ] zip  
  - [ ] pdf  
  - [ ] doc, docx  
  

- some trival bugs
  - [x] can't handle csv or tsv files with wrong suffix (e.g. a \*.xls file but in csv formats, which is a bug from NCBI DB)   
  - [ ] download and check progress bar depends on the number of files instead of the size of files, and the estimated time from `tqdm` is not stable (*hard to fix*)
  - [ ] downloading and parsing need times, so actually the size of thread pool be larger than limits
  
## some notes

1. if you need to use proxy, edit `proxies` variable in the head of searcher.py
2. one IP is allowed to send 3 requests to NCBI PMC in 1 seconds If you register an accout and use its api_key, the number can be increased to 10.

...
