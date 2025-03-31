import json
import os
import requests
import time
import requests

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
from torrentool.api import Torrent
import re
import libtorrent as lt 
import os
import hashlib
import html
import socket

from torrents import *
from loggers import * 


def load_books(year, FILE_PATH):
    """Loads the existing books from the JSON file."""
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)  # Attempt to load the JSON data
            except json.JSONDecodeError:
                # In case the file is empty or corrupted, return an empty dictionary
                log_info(year , "⚠️ The file is empty or corrupted, initializing a new one.")
                return {}
    
    return {}  # Return an empty dictionary if the file doesn't exist

def save_books(year,  books, FILE_PATH):
    """Saves the books data to the JSON file."""
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=4)

def add_book(**book_data):
    FILE_PATH = f"Dicts/{book_data['year']}_downloaded_books.json"
    
    try:
        data = load_books(book_data['year'], FILE_PATH)
                
        book_entry = {k: v for k, v in book_data.items() if k != 'link'}
        data[book_data['link']] = book_entry

        save_books(book_data['year'] , data, FILE_PATH)
        log_info(book_data['year'] , f"Book added: {book_data['link']} - {book_data['book_name']} , scraped: {book_data['scraped']}")
    
        if book_data['link'] not in data:
            pass
        else:
            log_info(book_data['year'] , f"⚠️ Book {book_data['link']} already exists, skipping...")

    except Exception as e: 
        log_error(book_data['year'], 'Failed to add_book : {e}')



def is_internet_available():
    """Check if internet is available by resolving a common domain (Google)."""
    try:
        socket.gethostbyname("google.com")
        return True
    except socket.gaierror:
        return False
    

def scrape_page(soup, year):
    global books_taken
    books_info = soup.find_all('div', class_='h-[110px] flex flex-col justify-center') 
    books_taken_in_page = 0 
    
    for book_info in books_info:  
        no_internet = False
        
        book_data = {
            'year': year,
            'link': None,
            'book_name': None,
            'author': None,
            'description': None,
            'scraped': False,
            'err_msg': None,
            'description': None,
            'torrent_file': None,
            'inside_torrent': None,
            'zlib': False
            
        }
        
        try:
            x = book_info.find('a')
            if not x: 
                book_data['err_msg'] = 'ERROR Could not find <a>'
                log_error(year, book_data['err_msg'])
                add_book(**book_data)
                continue
                
            link = x.get('href')
            book_data['link'] = link
            log_info(year, f"Link: {link}")
            
            if not link: 
                book_data['err_msg'] = 'ERROR: Could not get link'
                log_error(year, book_data['err_msg'])
                add_book(**book_data)
                continue
            
            book_name = book_info.find('h3').text
            book_data['book_name'] = book_name
            
            author = book_info.find('div', class_='max-lg:line-clamp-[2] lg:truncate leading-[1.2] lg:leading-[1.35] max-lg:text-sm italic').text.strip()
            book_data['author'] = author
            log_info(year, f'Book: {book_name}')
            
            if not book_name or not author: 
                log_info(year, f"Could not scrape book name or author")
                
            
            try:
                response = requests.get(f'https://annas-archive.org' + link)
                if response.status_code != 200:
                    book_data['err_msg'] = f"ERROR: Could not get response: status code {response.status_code}"
                    log_error(year, book_data['err_msg'])
                    add_book(**book_data)
                    continue
            
            except requests.exceptions.RequestException as e:
                while True:
                    if not is_internet_available():
                        book_data['err_msg'] = f"❌ ❌ ❌ ❌ No internet. Waiting for network to come back...."
                        log_error(year, book_data['err_msg'])
                        time.sleep(3)
                        no_internet = True
                        
                    else: 
                        if no_internet:
                            log_error(year, f"✅ ✅ ✅ ✅ Network came back. Continue..✅")
                            
                        else: 
                            book_data['err_msg'] = f'Failed to get response: Error {e}' 
                        break
                    
                add_book(**book_data)
                log_error(year, book_data['err_msg'])
                continue
                
            except Exception as e:
                book_data['err_msg'] = f"ERROR: Could not get response. Error: {e}"
                add_book(**book_data)
                log_error(year, book_data['err_msg'])
                continue
            
            try: 
                soup_2 = BeautifulSoup(response.text, 'html.parser')
                
                parent_div = soup_2.find('div', class_="mt-4 line-clamp-[10] js-md5-top-box-description")
                mb1_div = parent_div.find('div', class_="mb-1") if parent_div else None
                description = mb1_div.text.strip() if mb1_div else None
                book_data['description'] = description
                
                count_torrent_files = 0
                selected_torrent = None
                tar_torrent = None  # Backup option if no other choice

                for link_ in soup_2.find_all('a', href=True):
                    parent_div = link_.find_parent("div", class_="text-sm text-gray-500")
                    if parent_div and parent_div.get("style") == "margin-left: 24px": 
                        pass
                    else: continue
                    href = link_.get('href')
                    if href.endswith('.torrent'):
                        count_torrent_files += 1

                        if href.endswith('.tar.torrent'):
                            tar_torrent = href  # Store .tar.torrent as a backup
                            torrent_link = link_
                        else:
                            # Prioritize a non-tar torrent, especially one starting with 'r'
                            if selected_torrent is None or href.startswith('r'):
                                selected_torrent = href
                                torrent_link = link_
                                continue

                if count_torrent_files > 1:
                    log_info(year, f"More than 1 torrent_files for {link}")

                # If no non-tar torrent was found, fall back to a tar.torrent
                if selected_torrent is None:
                    selected_torrent = tar_torrent
                    

                if selected_torrent:
                    log_info(year, f"Selected torrent file: {selected_torrent}")
                else: 
                    book_data['err_msg'] = 'No selected torrent'
                    add_book(**book_data)
                    log_error(year, book_data['err_msg'])
                    continue
                                    
                if 'tar' in selected_torrent: 
                    book_data['err_msg'] = 'Torrent is tar format'
                    add_book(**book_data)
                    log_error(year, book_data['err_msg'])
                    continue
                    
                file_name = selected_torrent.split('/')[-1]
                book_data['torrent_file'] = file_name
                torrent_file = download_torrent(year, f'https://annas-archive.org' + selected_torrent, 'TORRENT_FILES', file_name)
                info = lt.torrent_info(torrent_file)
                files = info.files()

            except Exception as e:
                while True:
                    if not is_internet_available():
                        book_data['err_msg'] = f"❌ ❌ ❌ ❌ No internet. Waiting for network to come back...."
                        log_error(year, book_data['err_msg'])
                        no_internet = True
                        time.sleep(3)
                    else: 
                        if no_internet:
                            log_error(year, f"✅ ✅ ✅ ✅ Network came back. Continue..✅")
                            
                        else:
                            book_data['err_msg'] = f'Failed to download torrent: Error {e}' 
                            
                        break
                    
                add_book(**book_data)
                log_error(year, book_data['err_msg'])
                continue
            

            try:
                external_txt = soup_2.find('ul', class_=re.compile(r'list-inside.*js-show-external')).text
                if 'Z-Library' in external_txt: book_data['zlib'] = True
            except Exception as e:
                log_info(year , f'Could not get zlib {e}')
    
                
            
            try:
                parent_div = torrent_link.find_parent("div", class_="text-sm text-gray-500", style="margin-left: 24px")
                text_inside_div = parent_div.get_text(strip=True) if parent_div else None
                text_inside_div = html.unescape(text_inside_div)
                match = re.search(r'file[\s\xa0]+[“"]([^”"]+)[”"]?', text_inside_div)
                
                if match:
                    this_torrent = match.group(1)
                    book_data['inside_torrent'] = this_torrent
                else:
                    book_data['err_msg'] = "Could not scrape this_torrent on match"
                    add_book(**book_data)
                    log_error(year, book_data['err_msg'])
                    continue
                    
                log_info(year, this_torrent)
                
            except Exception as e:
                if is_internet_available():
                    book_data['err_msg'] = f"Could not download this_torrent {e}"
                    add_book(**book_data)
                    log_error(year, book_data['err_msg'])
                    continue
                else:
                    while True:
                        if not is_internet_available():
                            log_error(year, f"❌ ❌ ❌ ❌ No internet. Waiting for network to come back....")
                            time.sleep(3)
                        else: 
                            log_error(year, f"✅ ✅ ✅ ✅ Network came back. Continue..✅")
                            break
                    
                    book_data['err_msg'] = 'Error: Lost book cause of no internet connection'
                    add_book(**book_data)
                    log_error(year, book_data['err_msg'])
                    continue
                
            try:
                path  = f"Downloads/{link.split('/')[-1]}"
                download = download_specific_file(year, torrent_file, path , this_torrent)
                if download[0]:
                    books_taken_in_page += 1
                    book_data['scraped'] = True
                    add_book(**book_data)
                    log_info(year, f'Book ADDED SUCCESSFULLY. ✅ ✅ ✅\nTotal books so far in this page: {books_taken_in_page}')
                    # print('ADDED A BOOK ✅ ✅ ✅')
                else:
                    book_data['err_msg'] = download[1]
                    add_book(**book_data)
                    log_error(year, book_data['err_msg'])
                    continue
            
            except Exception as e:
                book_data['err_msg'] = f'Failed to Download the inside torrent file because: {e}'
                add_book(**book_data)
                log_error(year, book_data['err_msg'])
                continue
            
        except Exception as e:
            while True:
                if not is_internet_available():
                    book_data['err_msg'] = f"❌ ❌ ❌ ❌ No internet. Waiting for network to come back...."
                    log_error(year, book_data['err_msg'])
                    no_internet = True
                    time.sleep(3)
                else: 
                    if no_internet:
                        log_error(year, f"✅ ✅ ✅ ✅ Network came back. Continue..✅")
                        
                    else:
                        book_data['err_msg'] = f'Not caught Error {e}' 
                        
                    break
                
            add_book(**book_data)
            log_error(year, book_data['err_msg'])
            continue
                
    print(f"✅ ✅ ✅ Finished scraping a page for year {year} Books taken in page: {books_taken_in_page} ")
    log_info(year, f"✅ ✅ ✅ Finished scraping a page for year {year} Books taken in page: {books_taken_in_page} ")
    
    return books_taken_in_page
    


        #ZLIB
        # try:
            
        #     # # ZLIB 5 daily for ip
        #     # response = requests.get("https://z-lib.gs/md5/27edf0f87e979f1f7c405faae99f025e")
        #     # fake_url = response.url
        #     # download_url = "https://z-lib.gs/" + '/dl/' + fake_url.split('/')[-1] 
        #     # log_error(year , download_url)
        #     # add_book(link , book_name, author)
        #     # books_taken +=1 


        # except Exception as e:
        #     log_error(year , f"Error: {str(e)}")
            

# MAX_RETRIES = 5

def safe_main_scrape(year, page, q):
    log_info(year , f"Scraping page {page}")
    
    while True:
        try:
            return main_scrape(year=year, page=page,q=q)
        
        except (requests.exceptions.ConnectionError, ConnectionError) as ce:
            log_error(year , f"Network error on main_scrape({year}, {page}): {ce} | Retrying until network comes back...")
            time.sleep(5)  # Wait a few seconds before retrying (you can adjust)
        
        except requests.exceptions.RequestException as e:
            if not is_internet_available():
                log_error(year , f"❌ ❌ ❌ ❌ No internet. Waiting for network to come back....")
                time.sleep(3)
                
        except Exception as e:
            # Catch custom "Could not reach host" messages as well
            if not is_internet_available():
                log_error(year , f"❌ ❌ ❌ ❌ No internet. Waiting for network to come back....")
                time.sleep(3)
            
            else:
                log_error(year , f"Error on main_scrape({year}, {page}): {e} |")
                return None


def safe_scrape_page(soup, year):
    
    try:
        return scrape_page(soup, year)

    except Exception as e:
        log_error(year , f"Error caught on safe_scrape_page(): {e} |")
        return 0


def scroll_and_load(driver, wait, scroll_pause_time=2, max_scrolls=15):
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    for i in range(max_scrolls):
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait to load new content
        time.sleep(scroll_pause_time)
        
        # Wait for new elements (optional: you can skip this if the page loads new content automatically)
        try:
            wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".h-\\[110px\\].flex.flex-col.justify-center")
            ))
        except Exception as e:
            print( f"Scroll {i+1}: Warning ")

        # Check new scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            # No more content to load
            break
        
        last_height = new_height




BASE_URL = "https://annas-archive.org/search"

def main_scrape(page=None,  year=None, url=BASE_URL, acc = 'torrents_available', q =""):
    # Set up Chrome options for Selenium
    options = Options()
    options.add_experimental_option(
        "prefs", {
            "profile.managed_default_content_settings.images": 2,
        }
    )
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm -usage")
    # Specify the path to your chromedriver
    service = Service()



    # Initialize the WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 30)

    # Build the URL with parameters (this is the same as you did with requests)
    if q == "":
        full_url = f"{url}?lang=el&termtype_1=year&termval_1={year}&page={page}&acc={acc}"
    else:
        full_url = f"{url}?q={'+'.join(q.split())} "
        
    driver.get(full_url)
    log_info(year, f'URL: {full_url}')
    
    
    log_info(year , f"🔍 Status Code: {driver.execute_script('return document.readyState;')} for {full_url}")    
    

    try:
        try:
            wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".h-\\[110px\\].flex.flex-col.justify-center")
            ))
            scroll_and_load(driver, wait)
            
        except Exception as e:
            log_error(year , "Warning: Could not find spans with h-[110px] flex flex-col justify-center class")      

        # Get the page source after it is fully loaded
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        log_info(year , 'Got response ✅')

    except Exception as e:
        log_error(year, f"❌ Error: {str(e)}")
        soup = None
    finally:
        driver.quit()

    return soup



  

