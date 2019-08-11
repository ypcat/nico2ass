#!/usr/bin/env python3

import datetime
import glob
import html
import json
import math
import os
import re
import sys
import urllib
from pprint import pprint as pp

import attrdict
import requests

from credentials import FORM

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0'}
LOGIN = 'https://account.nicovideo.jp/api/v1/login'

def main():
    s = requests.Session()
    s.mount('https://', requests.adapters.HTTPAdapter(max_retries=100))
    if len(sys.argv) < 2:
        print(f'usage: {os.path.basename(sys.argv[0])} url')
        return 1
    url = sys.argv[1]
    if re.match(r'https://ch.nicovideo.jp/\w+', url):
        get_channel(s, url)
    elif re.match(r'https://www.nicovideo.jp/watch/\w+', url):
        get_comments(s, url)
    else:
        print('invalid url')
        return 1
    return 0

def get_channel(s, url):
    r = s.get(url, headers=HEADERS)
    processed = []
    for url in re.findall(r'https://www.nicovideo.jp/watch/\w+', r.text):
        if url not in processed:
            get_comments(s, url)
            processed.append(url)

def get_comments(s, url):
    m = re.match(r'https://www.nicovideo.jp/watch/(\w+)', url)
    vid = m.group(1)
    g = glob.glob(f'*{vid}*.json')
    if g:
        print(f'load from cache {g[0]}')
        return get_ass(g[0], json.load(open(g[0])))
    def get_api_data():
        print(f'get api data {url}')
        r = s.get(url, headers=HEADERS)
        m = re.search(r'data-api-data="([^"]*)"', r.text)
        if m:
            return attrdict.AttrDict(json.loads(html.unescape(m.group(1))))
    d = get_api_data()
    if not d:
        print('cannot get api data, login and try again')
        s.post(LOGIN, data=FORM, headers=HEADERS)
        d = get_api_data()
    q = [{'ping': {'content': 'rs:0'}}]
    n = 0
    for t in d.commentComposite.threads:
        if not t.isActive:
            continue
        if t.isThreadkeyRequired:
            print(f'get thread key {t.id}')
            url = 'https://flapi.nicovideo.jp/api/getthreadkey'
            r = s.get(url, params={'thread': t.id}, headers=HEADERS)
            k = dict(urllib.parse.parse_qsl(r.text))
        else:
            k = {'userkey': d.context.userkey}
        user_id = d.viewer.id or ''
        q += [{'ping': {'content': f'ps:{n}'}},
              {'thread': {
                  'fork': 0,
                  'thread': f'{t.id}',
                  'version': '20090904',
                  'language': 0,
                  'user_id': f'{user_id}',
                  'with_global': 1,
                  'scores': 1,
                  'nicoru': 0,
                  **k}},
              {'ping': {'content': f'pf:{n}'}}]
        n += 1
        if t.isLeafRequired:
            duration = math.ceil(d.video.duration / 60)
            q += [{'ping': {'content': f'ps:{n}'}},
                  {'thread_leaves': {
                      'thread': f'{t.id}',
                      'language': 0,
                      'user_id': f'{user_id}',
                      'content': f'0-{duration}:100,1000',
                      'scores': 1,
                      'nicoru': 0,
                      **k}},
                  {'ping': {'content': f'pf:{n}'}}]
            n += 1
    q += [{'ping': {'content': 'rf:0'}}]
    print('get comments')
    url = 'https://nmsg.nicovideo.jp/api.json/'
    r = s.post(url, json=q, headers=HEADERS)
    comments = [c for c in r.json() if c.get('chat', {}).get('content', '')]
    fn = f'{d.video.title}_{vid}.json'
    with open(fn, 'w') as f:
        print(f'save json comments {fn}')
        json.dump(comments, f, indent=2)
    return get_ass(fn, comments)

WIDTH = 1280
HEIGHT = 720
WHITE = 0xffffff
DEF_SIZE = 60
DEF_POS = 'naka'
DEF_COLOR = 'white'
SIZES = {'big': DEF_SIZE * 1.44, 'small': DEF_SIZE * 0.64}
POSES = {'ue': 'ue', 'shita': 'shita'}
COLORS = {'red': 0xff0000, 'pink': 0xff8080, 'orange': 0xffcc00,
          'yellow': 0xffff00, 'green': 0x00ff00, 'cyan': 0x00ffff,
          'blue': 0x0000ff, 'purple': 0xc000ff, 'black': 0x000000,
          'niconicowhite': 0xcccc99, 'white2': 0xcccc99, 'truered': 0xcc0033,
          'red2': 0xcc0033, 'passionorange': 0xff6600, 'orange2': 0xff6600,
          'madyellow': 0x999900, 'yellow2': 0x999900,
          'elementalgreen': 0x00cc66, 'green2': 0x00cc66,
          'marineblue': 0x33ffcc, 'blue2': 0x33ffcc, 'nobleviolet': 0x6633cc,
          'purple2': 0x6633cc}
CEIL = attrdict.AttrDict({'upper': -1.0e6, 'lower': 0, 'yield_time': 1.0e6})
FLOOR = attrdict.AttrDict({'upper': HEIGHT, 'lower': 1.0e6, 'yield_time': 1.0e6})

def find_first(keys, values, default):
    for k in keys:
        if k in values:
            return values[k]
    return default

def get_ass(filename, comments):
    filename = filename.replace('.json', '.ass')
    comments = [attrdict.AttrDict(c) for c in comments]
    chats = []
    for c in comments:
        attr = c.chat
        text = attr.content
        styles = attr.get('mail', '').split()
        size = find_first(styles, SIZES, DEF_SIZE)
        pos = find_first(styles, POSES, DEF_POS)
        is_naka = (pos == 'naka')
        dur = (5 if is_naka else 3)
        time = attr.vpos * 0.01
        lines = text.split('\n')
        w = size * max(len(l) for l in lines)
        chats.append(attrdict.AttrDict(
            text = text,
            start_time = (time - dur / 2 if is_naka else time),
            yield_time = (time + dur * (w / (w + WIDTH) - 0.5) if is_naka else time + dur),
            duration = dur,
            size = size,
            height = size * len(lines),
            width = w,
            pos = pos,
            color = find_first(styles, COLORS, DEF_COLOR)))
    lines = ["[Script Info]",
             "ScriptType: v4.00+",
             f"PlayResX: {WIDTH}",
             f"PlayResY: {HEIGHT}",
             f"Aspect Ratio: {WIDTH}:{HEIGHT}",
             "Collisions: Normal",
             "WrapStyle: 2",
             "ScaledBorderAndShadow: yes",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             f"Style: style1, ヒラギノ角ゴ ProN W3, {DEF_SIZE}, &H33FFFFFF, &H33FFFFFF, &H33000000, &H33000000, 0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, 3, 0, 7, 0, 0, 0, 0",
             "[Events]",
             "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    buf = {'naka': [CEIL, FLOOR],
           'ue': [CEIL, FLOOR],
           'shita': [CEIL, FLOOR]}
    for chat in sorted(chats, key=lambda c:c.start_time):
        time0 = format_time(chat.start_time)
        time1 = format_time(chat.start_time + chat.duration)
        size = (f'\\fs{chat.size}' if chat.size != DEF_SIZE else '')
        color = (f'\\c&H{chat.color:#08x}&' if chat.color != DEF_COLOR else '')
        anim = update_buf(buf[chat.pos], chat)
        if not anim:
            continue
        text = f'{{{anim}{size}{color}}}{chat.text}'
        dialog = f'Dialogue: 2,{time0},{time1},style1,,0000,0000,0000,,{text}'
        lines.append(dialog)
    with open(filename, 'w') as f:
        f.writelines(l + '\r\n' for l in lines)

def format_time(t):
    t = max(0.0, t) # XXX correct x if t < 0
    return str(datetime.timedelta(seconds=t))[:10]

def update_buf(buf, c):
    buf[:] = [b for b in buf if b.yield_time > c.start_time]
    for i, b in enumerate(buf):
        if i > 0 and buf[i-1].lower + c.height < b.upper:
            y = buf[i-1].lower
            a = attrdict.AttrDict({'upper': y, 'lower': y + c.height,
                                   'yield_time': c.yield_time })
            buf.insert(i, a)
            if c.pos == 'naka':
                return f'\\move(1280, {y}, -{c.width}, {y})'
            elif c.pos == 'ue':
                return f'\\an2\\pos({WIDTH / 2}, {y + c.height})'
            elif c.pos == 'shita':
                return f'\\an2\\pos({WIDTH / 2}, {HEIGHT - y})'
    # XXX random y and insert

if __name__ == '__main__':
    sys.exit(main())
