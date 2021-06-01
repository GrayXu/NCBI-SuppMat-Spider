from searcher import NCBI_searcher

api_key = '1cb4976dd163905feedacce5da0f10552309'
keywords = "cancer"
keywords_file = "propionyl-CoA"

keywords = "propionyl-CoA CANCER glyoxylate methylcitrate"
keywords_file = "Rv1220c"

searcher = NCBI_searcher(api_key=api_key, len_limit=0)

# just search them
searcher.search_from_all(keywords, keywords_file, thread_num=10, keep_cache=False)

print("finished!")
