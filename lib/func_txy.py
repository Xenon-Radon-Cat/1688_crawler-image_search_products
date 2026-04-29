# !/usr/bin/python
# -*- coding: utf-8 -*-

import contextlib
import random
import string
import time
import requests
import hashlib
import base64

from PIL import Image
from io import BytesIO
from pathlib import Path

def calculate_md5_hash(text: str):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def request_post(
    url, params=None, data=None, files=None, headers=None, timeout=10, cookies=None
):
    with contextlib.closing(
        requests.post(
            url=url,
            params=params,
            data=data,
            files=files,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
        )
    ) as req:
        return req


def request_get(url, params=None, headers=None, timeout=10, cookies=None):
    with contextlib.closing(
        requests.get(
            url=url, params=params, headers=headers, cookies=cookies, timeout=timeout
        )
    ) as req:
        return req


def get_random_str(k):
    return "".join(random.choices(string.ascii_letters, k=k))


def get_random_digits(k):
    return "".join(random.choices(string.digits, k=k))


def now():
    return int(time.time() * 1000)


def get_headers():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    return headers


def fileb64_encode(path):
    with open(path, "rb") as f:
        b64_str = base64.b64encode(f.read()).decode("ascii")
        return b64_str

def check_image_with_pillow(image_path):
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception as e:
        print(f"Error occurred while checking image {image_path}: {e}")
        return False

def compress_image(image_path):
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            if img.width > 400 or img.height > 400:
                img.thumbnail((400, 400))

            buffer = BytesIO()
            img.save(buffer, format="JPEG", optimize=True, quality=85)
            buffer.seek(0)
            return buffer.read()
    except Exception as e:
        print(f"Error occurred while processing image {image_path}: {e}")
        return None

def compress_and_encode_image(image_path):
    try:
        compressed_data = compress_image(image_path)
        if compressed_data is None:
            return None
        b64_str = base64.b64encode(compressed_data).decode("ascii")
        return b64_str
    except Exception as e:
        print(f"Error occurred while processing image {image_path}: {e}")
        return None

def filter_image_paths(image_dir):
    image_dir_path_obj = Path(image_dir)
    image_paths = []

    for item in image_dir_path_obj.iterdir():
        if item.is_file():
            image_path = str(item)
            if check_image_with_pillow(image_path):
                image_paths.append(image_path)

    return image_paths