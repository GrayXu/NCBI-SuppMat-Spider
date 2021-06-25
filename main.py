from searcher import NCBI_searcher


# this api_key is only for testing. So pls use your api_key from ur NCBI accounts, otherwise it will effect your speed
api_key = '1cb4976dd163905feedacce5da0f10552309'

keywords = "metabolomics"
keywords_file = "propanoyl-CoA"

searcher = NCBI_searcher(api_key=api_key, len_limit=0)

# just search them
searcher.search_from_all(keywords, keywords_file, thread_num=10, keep_cache=False, case_sensitive=False)

print("finished!")
