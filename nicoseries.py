#!/usr/bin/env python3

import argparse
import json
import re

import pyquery
import requests

def series(url):
    q = pyquery.PyQuery(url)
    d = json.loads(q('#js-initial-userpage-data').attr('data-initial-data'))
    for i in d['nvapi'][0]['body']['data']['items']:
        yield i['video']

def mylist(url):
    mylist_id = re.findall(r'https://www.nicovideo.jp/user/\d+/mylist/(\d+)', url)[0]
    url = 'https://nvapi.nicovideo.jp/v2/mylists/' + mylist_id
    params = {'pageSize': '100', 'page': '1', 'sensitiveContents': 'mask'}
    headers = {'X-Frontend-Id': '6'}
    r = requests.get(url, params=params, headers=headers)
    for i in r.json()['data']['mylist']['items']:
        yield i['video']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('-v', action='store_true')
    args = parser.parse_args()
    if re.match(r'https://www.nicovideo.jp/user/\d+/series/\d+', args.url):
        g = series(args.url)
    elif re.match(r'https://www.nicovideo.jp/user/\d+/mylist/\d+', args.url):
        g = mylist(args.url)
    for v in g:
        url = 'https://www.nicovideo.jp/watch/' + v['id']
        if args.v:
            print(f"{url} - {v['title']}")
        else:
            print(url)

if __name__ == '__main__':
    main()
