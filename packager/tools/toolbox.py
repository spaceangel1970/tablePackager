import logging
import re
import mmap
import os
import stat
import shutil
import zipfile
import threading
import sys
import hashlib
import time
import math
import datetime
import json
from pathlib import Path

def clean_dir(dir_path: str):
    try:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path, ignore_errors=False)
        os.makedirs(dir_path, exist_ok=True)
    except Exception as err:
        print(f"Error cleaning directory {dir_path}: {err}")


def setReadOnlyFile(file):
    if os.path.exists(file):
        os.chmod(file, stat.S_IREAD)


def setReadWriteFile(file):
    if os.path.exists(file):
        fileAtt = os.stat(file).st_mode
        if not fileAtt & stat.S_IWRITE:
            os.chmod(file, stat.S_IWRITE)


def is_read_only_file(file):
    if os.path.exists(file):
        fileAtt = os.stat(file).st_mode
        return not fileAtt & stat.S_IWRITE
    return False


def copytree(logger, src: str, dst: str, symlinks: bool = False, ignore: bool = None):
    if not os.path.exists(dst):
        os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        dst_path = os.path.join(dst, item)
        logger.info(f"+ deploy {dst_path}")
        if os.path.isdir(src_path):
            copytree(logger, src_path, dst_path, symlinks, ignore)
        else:
            if not os.path.exists(dst_path) or os.stat(src_path).st_mtime - os.stat(dst_path).st_mtime > 1:
                shutil.copy2(src_path, dst_path)


def extract_string_from_binary_file(vpx_file: str, pattern: str) -> list:
    roms = []
    p = re.compile(pattern.encode('ascii') if isinstance(pattern, str) else pattern)
    if not os.path.exists(vpx_file) or os.path.getsize(vpx_file) == 0:
        return []
    with open(vpx_file, 'rb') as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
            m = p.findall(s)
            for rom in m:
                roms.append(rom.decode('ascii', errors='ignore'))
    return list(set(roms))  # Deduplicate findings cleanly


def sha1sum(filename: str) -> str:
    h = hashlib.sha1()
    b = bytearray(128 * 1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def zip_dir(path: str, ziph: zipfile.ZipFile) -> None:
    # 1. Force the root collection anchor to be an absolute, fully resolved path
    base_anchor = Path(path).resolve()
    parent_anchor = base_anchor.parent

    for root, dirs, files in os.walk(path):
        # 2. Convert directories to absolute paths before finding the relative layout path
        for dir_name in dirs:
            full_dir_path = Path(os.path.join(root, dir_name)).resolve()
            archive_name = full_dir_path.relative_to(parent_anchor).as_posix()
            ziph.write(str(full_dir_path), archive_name)
            
        # 3. Convert files to absolute paths before finding the relative layout path
        for file_name in files:
            full_file_path = Path(os.path.join(root, file_name)).resolve()
            archive_name = full_file_path.relative_to(parent_anchor).as_posix()
            ziph.write(str(full_file_path), archive_name)


def zip_file(src: str) -> None:
    with zipfile.ZipFile(src + '.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(src, os.path.basename(src))


def pack(src: str, dest: str, pack_name: str) -> None:
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(os.path.join(dest, pack_name), 'w', zipfile.ZIP_DEFLATED) as zipf:
        zip_dir(src, zipf)


def unpack(src: str, dest: str) -> None:
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(src, 'r') as zipf:
        zipf.extractall(dest)


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def utcTime2IsoStr():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def strIsoUTCTime2DateTime(strIsoTime):
    """
    Converts an ISO UTC time string to a datetime object.
    Heals malformed timestamps missing a colon between minutes and seconds.
    """
    if isinstance(strIsoTime, str):
        if 'T' in strIsoTime and '.' in strIsoTime:
            date_part, time_remainder = strIsoTime.split('T', 1)
            time_part, micro_part = time_remainder.split('.', 1)
            
            if time_part.count(':') == 1:
                parts = time_part.split(':')
                hour = parts[0]
                min_sec = parts[1]
                if len(min_sec) == 4:  # MMSS
                    corrected_time_part = f"{hour}:{min_sec[:2]}:{min_sec[2:]}"
                    strIsoTime = f"{date_part}T{corrected_time_part}.{micro_part}"

    # Fixed NameError by referencing nested datetime namespace module directly
    stime = time.strptime(strIsoTime, "%Y-%m-%dT%H:%M:%S.%f%z")
    return datetime.datetime.fromtimestamp(time.mktime(stime), datetime.timezone.utc)


def mtime2IsoStr(mtime):
    date = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)
    return date.isoformat()


def utcTime2Str(utcTime: datetime.datetime) -> str:
    return utcTime.strftime("%Y-%m-%d %H:%M:%S")


def try_str_2_struct_time(str_date: str, time_format: str) -> time.struct_time:
    try:
        return time.strptime(str_date, time_format)
    except ValueError:
        fallbacks = {
            '%Y-%m-%d': '%m-%d-%Y',
            '%m-%d-%Y': '%Y-%m',
            '%Y-%m': '%B, %Y',
            '%B, %Y': '%Y',
            '%Y': '%B %d, %Y',
            '%B %d, %Y': '%b %d %Y %I:%M %p',
            '%b %d %Y %I:%M %p': '%Y-%m-%dT%H:%M:%SZ'
        }
        next_format = fallbacks.get(time_format)
        if next_format:
            return try_str_2_struct_time(str_date, next_format)
        return None
    except OverflowError:
        print(f"Overflow {str_date}/{time_format}")
        return None


def str_2_struct_time(str_date: str) -> time.struct_time:
    return try_str_2_struct_time(str_date, '%Y-%m-%d')


def struct_time_2_datetime(date: time.struct_time) -> datetime.datetime:
    if date is None:
        return None
    if date.tm_year <= 1970:
        return datetime.datetime(date.tm_year, date.tm_mon, date.tm_mday, tzinfo=datetime.timezone.utc)
    return datetime.datetime.fromtimestamp(time.mktime(date), datetime.timezone.utc)


def extract_text(title: str, txt: str) -> str:
    pos = txt.find(title, 0) + len(title)
    return txt[pos:].strip('\n\t ')


def searchSentenceInString(string, sentence):
    if not sentence:
        return 0.0
    score = 0.0
    words = sentence.split(' ')
    for word in words:
        if string.find(word) >= 0:
            score = score + 1.0
    return score / len(words)


def unsuffix(path):
    path_obj = Path(path)
    return path_obj.name.split('.')[0]


def is_suffix(filename: str, suffix: str) -> bool:
    return suffix in Path(filename).suffixes


def iterative_levenshtein(s, t, costs=(1, 1, 1)):
    rows = len(s) + 1
    cols = len(t) + 1
    deletes, inserts, substitutes = costs
    dist = [[0 for _ in range(cols)] for _ in range(rows)]

    for row in range(1, rows):
        dist[row][0] = row * deletes
    for col in range(1, cols):
        dist[0][col] = col * inserts

    for col in range(1, cols):
        for row in range(1, rows):
            if s[row - 1] == t[col - 1]:
                cost = 0
            else:
                cost = substitutes
            dist[row][col] = min(dist[row - 1][col] + deletes,
                                 dist[row][col - 1] + inserts,
                                 dist[row - 1][col - 1] + cost)
    return dist[rows - 1][cols - 1]


def save_data(filepath: str, data: object) -> None:
    try:
        with open(filepath, 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, indent=4, separators=(',', ': '), default=str)
    except IOError as e:
        raise Exception(f"Database write error {e}")


def load_data(filepath: str) -> object:
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return json.load(file)
    except IOError as e:
        raise Exception(f"Database read error {e}")


def safe_save_json(filepath: str, data: object) -> None:
    # Fixed: Prevent FileNotFoundError if running for the first time
    if os.path.exists(filepath):
        if os.path.exists(filepath + '.back'):
            os.remove(filepath + '.back')
        os.rename(filepath, filepath + '.back')
    
    save_data(filepath, data)
    
    if os.path.exists(filepath + '.back'):
        os.remove(filepath + '.back')


def safe_load_json(filepath: str) -> object:
    if not os.path.exists(filepath + '.back'):
        return load_data(filepath)
    else:
        data = load_data(filepath + '.back')
        if os.path.exists(filepath):
            os.remove(filepath)
        os.rename(filepath + '.back', filepath)
        return data


def justify_text(text: str, tab: int = 0, max_col: int = 30) -> list:
    result = []
    size = len(text)
    nb_col = max_col - tab
    if nb_col <= 0:
        return [text]
    nb_line = int(size / nb_col)
    for line in range(0, nb_line):
        result.append(text[line * nb_col:(line * nb_col) + nb_col])
    if size % nb_col != 0:
        result.append(text[nb_line * nb_col:])
    return result


class AsynRun(threading.Thread):
    def __init__(self, method_begin, method_end, context=None):
        threading.Thread.__init__(self)
        self.context = context
        self.method_begin = method_begin
        self.method_end = method_end

    def run(self):
        result = self.method_begin(self.context)
        self.method_end(self.context, result)