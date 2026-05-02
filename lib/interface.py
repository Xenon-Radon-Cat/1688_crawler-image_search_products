from lib.ali1688 import ali1688
from lib import alibaba
import time
import json
from playwright.sync_api import sync_playwright, TimeoutError
from playwright_stealth import Stealth
import random

needCount = 3

ali1688_upload = ali1688.Ali1688Upload()
alibaba_upload = alibaba.Upload()
alibaba_image_search = alibaba.ImageSearch()

ali1688_selector = "span[data-extra]"
alibaba_selector = "a[href^='//www.alibaba.com/product-detail'][href$='.html']"

ali1688_example_url = "https://s.1688.com/youyuan/index.htm?tab=imageSearch"
alibaba_example_url = "https://www.alibaba.com/picture/search.htm"

def block_resources(route):
    if route.request.resource_type in ["image", "stylesheet", "font", "media"]:
        route.abort()
    else:
        route.continue_()

def ali1688_core_image_search(image_path):
    try:
        res = ali1688_upload.upload(image_path)
        image_id = res.json().get("data", {}).get("imageId", "")
        if not image_id:
            print(f"fail to upload image to ali1688: {image_path}")
            return None
        else:
           image_search_url = ali1688_upload.image_search_url(image_id)
           return image_search_url
    except Exception as e:
        print(f"error occurs when uploading image to ali1688: {image_path} {e}")
        return None

def alibaba_core_image_search(image_path):
    try:
        image_key = alibaba_upload.upload(image_path)
        req = alibaba_image_search.search(image_key=image_key)
        image_search_url = req.url
        return image_search_url
    except Exception as e:
        print(f"error occurs when uploading image to alibaba: {image_path} {e}")
        return None
    
def ali1688_similar_offer_urls(page):
    offerIds = []
    similar_offer_urls = []
    span_locators = page.locator(ali1688_selector).all()

    for span_locator in span_locators:
        data_extra_str = span_locator.get_attribute("data-extra")
        
        if data_extra_str:
            try:
                data_extra_json = json.loads(data_extra_str)
                offerId = data_extra_json.get("offerId")
                if offerId not in offerIds:
                    offerIds.append(offerId)
                    if len(offerIds) >= needCount:
                        break
            except Exception as e:
                print(f"Error occurred while extracting offerIds: {e}")

    for offerId in offerIds:
        similar_offer_url = f"https://detail.1688.com/offer/{offerId}.html"
        similar_offer_urls.append(similar_offer_url)

    return similar_offer_urls

def alibaba_similar_offer_urls(page):
    similar_offer_urls = []
    a_locators = page.locator(alibaba_selector).all()

    for a_locator in a_locators:
        href = a_locator.get_attribute("href")

        if href.startswith("//www.alibaba.com/product-detail") and href.endswith(".html"):
            similar_offer_url = href.replace("//", "https://")

            if similar_offer_url not in similar_offer_urls:
                similar_offer_urls.append(similar_offer_url)
                if len(similar_offer_urls) >= needCount:
                    break
    
    return similar_offer_urls

def ali1688_multi_image_search(image_paths, progress_callback, popup_callback):
    return multi_image_search(image_paths, ali1688_example_url, ali1688_core_image_search, ali1688_selector, ali1688_similar_offer_urls, progress_callback, popup_callback)

def alibaba_multi_image_search(image_paths, progress_callback, popup_callback):
    return multi_image_search(image_paths, alibaba_example_url, alibaba_core_image_search, alibaba_selector, alibaba_similar_offer_urls, progress_callback, popup_callback)

def multi_image_search(image_paths, example_url, core_image_search_method, selector, core_similar_offer_urls_method, progress_callback, popup_callback):
    result_dict = {} # image_path -> (image_search_url, [offer_url]) | None
    success = 0
    fail = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,
            #user_data_dir = r"C:\Users\XenonRadonCat\AppData\Local\Microsoft\Edge\User Data\Default",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        page = browser.new_page()
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        try:
            page.goto(example_url, wait_until="domcontentloaded", timeout=10000)
        except Exception as e:
            print(f"ignore example page exception {e}")

        popup_callback()

        # page.route("**/*", block_resources)

        for image_path in image_paths:
            try:
                start = time.time()
                image_search_url = core_image_search_method(image_path)
                mid = time.time()
                print(f"{image_path} get image search url {image_search_url} costs {mid - start} seconds")

                if image_search_url:
                    page.goto(image_search_url, wait_until="domcontentloaded", timeout=10000)
                    page.wait_for_selector(selector, timeout=10000)
                    simillar_offer_urls = core_similar_offer_urls_method(page)
                    end = time.time()
                    print(f"{image_search_url} get similar offer urls {simillar_offer_urls} costs {end - mid} seconds")
                    result_dict[image_path] = (image_search_url, simillar_offer_urls)
                    success += 1
                else:
                    fail += 1
            except TimeoutError as e:
                print(f"wait for selector too long, maybe redirect to login or verify page {e}")
                popup_callback("提取相似商品链接超时，可能重定向到登录或者滑块认证，先帮忙处理")

                if 'image_search_url' in locals() and image_search_url:
                    try:
                        mid = time.time()
                        page.wait_for_selector(selector, timeout=20000)
                        simillar_offer_urls = core_similar_offer_urls_method(page)
                        end = time.time()
                        print(f"{image_search_url} get similar offer urls {simillar_offer_urls} costs {end - mid} seconds")
                        result_dict[image_path] = (image_search_url, simillar_offer_urls)
                        success += 1
                    except Exception as e:
                        print(f"only retry once {e}")
                        result_dict[image_path] = (image_search_url, None)
                        fail += 1
                else:
                    print(f"fail to get image search url")
                    result_dict[image_path] = None
            except Exception as e:
                print(f"Error occurred while searching image {image_path}: {e}")
                result_dict[image_path] = (image_search_url, None) if 'image_search_url' in locals() else None
                fail += 1

            progress_callback(success, fail)

            time.sleep(random.uniform(1, 3))

        browser.close()

    return result_dict