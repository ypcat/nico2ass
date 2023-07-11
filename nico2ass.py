#!/usr/bin/env python3

import datetime
import glob
import html
import json
import math
import os
import random
import re
import string
import sys
import urllib
from pprint import pprint as pp

import attrdict
import requests
try:
    from tqdm import tqdm
except:
    tqdm = lambda x: x

from credentials import FORM

SESSION_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'session')
SESSION_COOKIE = 'user_session='+open(SESSION_PATH).read().strip()+';'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0',
    "X-Frontend-Id": "6",
    "X-Frontend-Version": "0",
    'Cookie': SESSION_COOKIE,
}
#LOGIN = 'https://account.nicovideo.jp/api/v1/login'

#s = requests.Session()
#s.mount('https://', requests.adapters.HTTPAdapter(max_retries=100))

def main():
    if len(sys.argv) < 2:
        print(f'usage: {os.path.basename(sys.argv[0])} url')
        return 1
    for url in sys.argv[1:]:
        if re.match(r'https://ch.nicovideo.jp/\w+', url):
            get_channel(url)
        elif re.match(r'https://www.nicovideo.jp/watch/\w+', url):
            get_comments(url)
        elif os.path.exists(url):
            get_comments_from_file(url)
        elif re.match(r'sm\d+', url):
            get_comments('https://www.nicovideo.jp/watch/' + url)
        elif url.endswith('.live_chat.json') and os.path.exists(url):
            get_youtube_comments(url)
        else:
            print('invalid url', url)
    else:
        return 1
    return 0

def get_meta(url):
    m = re.match(r'https://www.nicovideo.jp/watch/(\w+)', url)
    vid = m.group(1)
    actionTrackId = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(10)) + "_" + str(random.randrange(10**(12),10**13))
    url = 'https://www.nicovideo.jp/api/watch/v3/' + vid + '?actionTrackId=' + actionTrackId
    meta = requests.post(url, headers=HEADERS).json()
    assert meta['meta']['status'] == 200, meta['meta']
    return meta

def get_threads(meta):
    nvComment = meta["data"]["comment"]["nvComment"]
    params = {
        "params": nvComment["params"],
        "additionals": {},
        "threadKey": nvComment["threadKey"]
    }
    url = nvComment["server"] + "/v1/threads"
    r = requests.post(url, json.dumps(params), headers=HEADERS)
    return r.json()

def convert_threads(threads):
    comments = []
    for t in threads['data']['threads']:
        for c in t['comments']:
            c = {'chat': {'content': c['body'], 'mail': ' '.join(c['commands']), 'vpos': c['vposMs']/10}}
            comments.append(c)
    return comments

def get_comments(url):
    meta = get_meta(url)
    title = meta['data']['video']['title']
    threads = get_threads(meta)
    comments = convert_threads(threads)
    filename = title + '.ass'
    get_ass(filename, comments)

def get_comments_from_file(fn):
    threads = json.load(open(fn))
    comments = convert_threads(threads)
    filename = os.path.splitext(fn)[0] + '.ass'
    get_ass(filename, comments)

def get_youtube_comments(fn):
    comments = []
    for line in tqdm(open(fn)):
        try:
            replayChatItemAction = json.loads(line)['replayChatItemAction']
            vpos = int(replayChatItemAction['videoOffsetTimeMsec']) / 10
            for action in replayChatItemAction['actions']:
                for action_key in ['addChatItemAction']: #addLiveChatTickerItemAction
                    if action_key not in action:
                        continue
                    for item_value in action[action_key]['item'].values():
                        parts = []
                        mail = ''
                        for run in item_value.get('message', {}).get('runs', []):
                            if 'text' in run:
                                parts.append(run['text'])
                            if 'emoji' in run:
                                parts.append(run['emoji']['emojiId'])
                        if 'authorBadges' in item_value:
                            mail = 'green'
                        if 'purchaseAmountText' in item_value:
                            mail = 'yellow small ue $'
                            parts.append(item_value['purchaseAmountText']['simpleText'])
                            if 'authorName' in item_value:
                                author = item_value['authorName']['simpleText']
                                parts.append(author)
                        text = ' '.join(parts).strip()
                        while text:
                            c = {'chat': {'content': text[:36], 'mail': mail, 'vpos': vpos}}
                            comments.append(c)
                            text = text[36:]
                            vpos += 100
        except:
            print(line)
            raise
    get_ass(fn.replace('.live_chat.json', '.ass'), comments)

def dedup(items):
    return list(dict.fromkeys(items))

def get_channel(url):
    r = requests.get(url, headers=HEADERS)
    for url in dedup(re.findall(r'https://www.nicovideo.jp/watch/\w+', r.text)):
        get_comments(url)

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

def rgb2bgr(rgb):
    return rgb[0:2] + rgb[6:8] + rgb[4:6] + rgb[2:4]

def get_ass(filename, comments):
    print(f'convert {len(comments)} comments')
    comments = [attrdict.AttrDict(c) for c in comments]
    chats = []
    for c in tqdm(comments):
        attr = c.chat
        text = attr.content
        styles = attr.get('mail', '').split()
        size = find_first(styles, SIZES, DEF_SIZE)
        pos = find_first(styles, POSES, DEF_POS)
        is_naka = (pos == 'naka')
        dur = (5 if is_naka else 3)
        dur = (30 if '$' in styles else dur)
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
    for chat in tqdm(sorted(chats, key=lambda c:c.start_time)):
        time0 = format_time(chat.start_time)
        time1 = format_time(chat.start_time + chat.duration)
        size = (f'\\fs{chat.size}' if chat.size != DEF_SIZE else '')
        color = (f'\\c&H{rgb2bgr(f"{chat.color:#08x}")}&' if chat.color != DEF_COLOR else '')
        anim = update_buf(buf[chat.pos], chat)
        if not anim:
            continue
        text = f'{{{anim}{size}{color}}}{chat.text}'
        dialog = f'Dialogue: 2,{time0},{time1},style1,,0000,0000,0000,,{text}'
        lines.append(dialog)
    print(f'save {filename}')
    with open(filename.replace('/', ' '), 'w') as f:
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
