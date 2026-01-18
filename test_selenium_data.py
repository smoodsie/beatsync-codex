#!/usr/bin/env python3
from beatport_playlist_scraper import fetch_html_with_selenium, extract_script_json

html = fetch_html_with_selenium("https://www.beatport.com/playlists/share/6326317")
blobs = extract_script_json(html)

print(f"Blobs found: {len(blobs)}")
if blobs:
    first_blob = blobs[0]
    if 'props' in first_blob:
        props = first_blob['props']
        if 'pageProps' in props:
            pageProps = props['pageProps']
            if 'dehydratedState' in pageProps:
                queries = pageProps['dehydratedState'].get('queries', [])
                print(f"Queries in dehydratedState: {len(queries)}")
                for i, q in enumerate(queries):
                    if 'state' in q and 'data' in q['state']:
                        data = q['state']['data']
                        if isinstance(data, dict) and 'results' in data:
                            results_count = len(data['results'])
                            page = data.get('page')
                            print(f"Query {i}: {results_count} results (page {page})")
