#!/usr/bin/env python3

import argparse
import json

import pyquery

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('-v', action='store_true')
    args = parser.parse_args()
    for i in json.loads(pyquery.PyQuery(args.url)('script[type="application/ld+json"]').text())['itemListElement']:
        if args.v:
            print(f"{i['url']} - {i['name']}")
        else:
            print(i['url'])

if __name__ == '__main__':
    main()
