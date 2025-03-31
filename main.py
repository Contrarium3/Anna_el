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
from utils import *
from torrentool.api import Torrent
import re
import libtorrent as lt 
import os
import hashlib
import html
from datetime import datetime


import concurrent.futures
from typing import List

def scrape_year(year: int, q:str) -> int:
    """
    Scrape books for a specific year
    
    Args:
        year (int): Year to scrape books from
    
    Returns:
        Total number of books scraped for the year
    """
    books_taken = 0
    
    print(f"Scraping year {year}..... \n")
    page = 1
    
    while True:
        soup = safe_main_scrape(year=year, page=page, q=q)
        books_in_page = safe_scrape_page( soup, year)
        
        page += 1
        books_taken += books_in_page
        
        # print(f"\n Added {books_taken} books so far...... \n")
        
        # Break conditions
        if page > 100 or books_in_page < 88:
            break
    
    return books_taken

def main():
    q = ""
    # Define the range of years to scrape
    start_year = 2024
    end_year = 1990
    
    # Number of worker threads
    num_workers = 3
    
    # Total books tracked across all years
    total_books = 0
    
    # Use ThreadPoolExecutor for concurrent scraping
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Create futures for each year
        futures = [
            executor.submit(scrape_year, year, q) 
            for year in range(start_year, end_year - 1, -1)
        ]
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                year_books = future.result()
                total_books += year_books
                print(f"✅ ✅ ✅ Completed scraping a year. Total books so far: {total_books}")
            except Exception as e:
                print(f"❌ ❌ ❌ ❌ Error scraping: a year in the threads!!!!!!")
    
    # Final total of books
    print(f"✅ ✅ ✅ Finished Scraping: Total books scraped across all years: {total_books} ✅ ✅ ✅ ")
    return total_books

if __name__ == "__main__":

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S \n")
    print(current_time)
    

    main()

