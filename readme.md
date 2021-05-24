# NCBI-SuppMat-Spider

a web spider to search and download suppmat with specific keywords from NCBI.

**input: keywords to search NCBI, and the keywords to search files**  
**output: related Supplementary Materials.**

Basic perf test:
 - search 1000 related papers in about 14 mins and it will download about 0.5 GB supplementary material files.

## usage

**config** searcher.py, and directly **run** it

## dependency

`pip install requests urllib3 bs4 xlrd==1.2.0 python-docx tqdm`

*note: pls make sure xlrd's version*

## TO-DO

- features
  - [x] progress bar
  - [x] optional keywords for searching in files
  - [x] ouput exact positions of keywords
  - [x] create links to related suppmats
  - [ ] optional case sensitivity
  - [ ] more account keys and proxy IPs to speed up
  

- support more formats
  - [x] csv, txt, tsv, html, xml  
  - [x] xls, xlsx  
  - [ ] zip  
  - [ ] pdf  
  - [ ] doc, docx  
  

- some trival bugs
  - [ ] download nad check progress bar depends on the number of files instead of the size of files (hard to fix)
  - [ ] can't handle csv or tsv files with wrong suffix (e.g. a \*.xls file but in csv formats, which is a bug from NCBI DB)   
  
## some warning notes

...
