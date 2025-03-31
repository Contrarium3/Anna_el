import os
import json

def count_scraped_jsons(folder_path):
    scraped_count = 0
    not_scraped_count = 0

    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):  # Process only JSON files
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r") as file:
                data = json.load(file)
                for book in data.values():
                    if book["scraped"]:
                        scraped_count += 1
                    else:
                        not_scraped_count += 1

    # Calculate ratio
    ratio = scraped_count / not_scraped_count if not_scraped_count != 0 else float('inf')
    return scraped_count, not_scraped_count, ratio


folder_path = "Dicts"  
scraped_count, not_scraped_count, ratio = count_scraped_jsons(folder_path)

def projected(ratio):
    unscraped = 30000 / (ratio+1)
    scraped = ratio * unscraped
    print(f'Projecetd scraped: {scraped} , Projected unscraped: {unscraped}')

print(f"Scraped: {scraped_count}, Not Scraped: {not_scraped_count}, Ratio: {ratio}")
projected(ratio)