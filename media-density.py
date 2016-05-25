#!/usr/bin/env python

import argparse
import json
import subprocess as sp
import sys
from datetime import timedelta

import os
import re


def alphanum_key(key):
    return [int(text) if text.isdigit() else text for text in re.split('([0-9]+)', key)]


def sorted_nicely(l):
    """ Sort the given iterable in the way that humans expect."""
    return sorted(l, key=alphanum_key)


def media_bytes(media_path):
    return os.stat(media_path).st_size


def ffprobe(media_path):
    """ Give a json from ffprobe command line

    @vid_file_path : The absolute (full) path of the video file, string.
    """
    if type(media_path) != str:
        raise Exception('Gvie ffprobe a full file path of the video')
    command = ["ffprobe",
               "-loglevel", "quiet",
               "-print_format", "json",
               "-show_format",
               "-show_streams",
               media_path
               ]
    pipe = sp.Popen(command, stdout=sp.PIPE, stderr=sp.STDOUT)
    out, err = pipe.communicate()
    return json.loads(out)


def media_duration(media_path):
    """ Video's duration in seconds, return a float number
    """
    _json = ffprobe(media_path)
    if 'format' in _json:
        if 'duration' in _json['format']:
            return float(_json['format']['duration'])
    if 'streams' in _json:
        # commonly stream 0 is the video
        for s in _json['streams']:
            if 'duration' in s:
                return float(s['duration'])
    raise Exception('no duration found')


def walk_dir(media_path):
    if os.path.isfile(media_path):
        try:
            return process_file(media_path)
        except Exception:
            return 0, 0
    else:
        path_bytes = 0
        path_duration = 0
        for root, dirs, files in os.walk(media_path):
            dirs[:] = sorted(dirs, key=alphanum_key)
            for f in sorted(files, key=alphanum_key):
                try:
                    file_bytes, file_duration = process_file(os.path.join(root, f))
                except Exception as e:
                    continue
                path_bytes += file_bytes
                path_duration += file_duration
                if args.first_only:
                    return path_bytes, path_duration
        return path_bytes, path_duration


def process_file(media_path):
    file_secs = media_duration(media_path)
    file_bytes = media_bytes(media_path)
    if not args.summary:
        print_stat(media_path, file_bytes, file_secs)
    return file_bytes, file_secs


def print_stat(item_path, stat_bytes, stat_duration):
    if 0 == stat_duration:
        return
    if args.csv:
        delim = ','
        item_path = item_path.replace(',', '_')
    else:
        delim = ': '
    print delim.join(map(str, ["{0:7.2f} kBps".format(stat_bytes / stat_duration / 1024),
                               stat_bytes,
                               timedelta(seconds=stat_duration),
                               item_path
                               ]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate "density" (bitrate) of media files')
    parser.add_argument('-t', '--totals', dest='total', action='store_true', default=False,
                        help='generate a summary entry from the duration and size totals')
    parser.add_argument('-f', '--first', dest='first_only', action='store_true', default=False,
                        help='only scan the first episode found for a series')
    parser.add_argument('-s', '--summary', dest='summary', action='store_true', default=False,
                        help='report only the summary for each argument')
    parser.add_argument('-c', '--csv', dest='csv', action='store_true', default=False,
                        help='output results as CSV')
    parser.add_argument('items', metavar='I', type=str, nargs='+',
                        help='files and folders to scan')

    args = parser.parse_args()

    total_bytes = 0
    total_duration = 0

    for item in args.items:
        item_bytes, item_duration = walk_dir(item)
        total_bytes += item_bytes
        total_duration += item_duration
        if 0 == item_duration:
            continue
        if args.summary:
            print_stat(item, item_bytes, item_duration)
    if 0 == total_duration:
        sys.exit(0)
    if args.total:
        print_stat('', total_bytes, total_duration)
