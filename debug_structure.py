#!/usr/bin/env python3
from beatport_playlist_scraper import fetch_html, extract_script_json
import json

html = fetch_html("https://www.beatport.com/playlists/share/6326317")
blobs = extract_script_json(html)

if blobs:
    first_blob = blobs[0]
    
    if 'props' in first_blob:
        props = first_blob['props']
        if isinstance(props, dict) and 'pageProps' in props:
            pageProps = props['pageProps']
            
            if 'dehydratedState' in pageProps:
                dehydrated = pageProps['dehydratedState']
                if isinstance(dehydrated, dict) and 'queries' in dehydrated:
                    queries = dehydrated['queries']
                    if isinstance(queries, list) and len(queries) > 1:
                        query1 = queries[1]
                        if isinstance(query1, dict) and 'state' in query1:
                            state = query1['state']
                            if isinstance(state, dict) and 'data' in state:
                                data = state['data']
                                if isinstance(data, dict):
                                    print(f"data keys: {list(data.keys())}")
                                    print(f"count (total tracks): {data.get('count')}")
                                    print(f"per_page: {data.get('per_page')}")
                                    print(f"page: {data.get('page')}")
                                    print(f"results count: {len(data.get('results', []))}")
                                    print(f"next: {data.get('next')}")



