# NCBI-SuppMat-Spider

a web spider to search and download suppmat with specific keywords from NCBI.

input: keywords  
output: related papers and related Supplementary Materials.

## usage

**config** NCBI_analysis.py, and **run** it

## dependency

`pip install requests urlllib bs4 xlrd python-docx`

## TODO

- features
  - [ ] speed speed speed
  - [ ] Ouput exact positions of keywords
  - [ ] retry after code 429

- support more formats
  - [x] csv, txt, tsv  
  - [ ] pdf  
  - [ ] doc, docx  
  - [ ] xls, xlsx  

<!-- ### speed

[ ]  -->
