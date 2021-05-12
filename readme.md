# NCBI-SuppMat-Spider

a web spider to search and download suppmat with specific keywords from NCBI.

input: keywords  
output: related papers and related Supplementary Materials.

Basic perf test:
 - search 1000 related papers in about 15 mins (0.5 GB supplementary materials)

## usage

**config** searcher.py, and **run** it

## dependency

`pip install requests urlllib bs4 xlrd python-docx tqdm`

## TODO

- features
  - [x] progress bar
  - [ ] speed speed speed
  - [ ] ouput exact positions of keywords


- support more formats
  - [x] csv, txt, tsv  
  - [x] xls, xlsx  
  - [ ] pdf  
  - [ ] doc, docx  
  
