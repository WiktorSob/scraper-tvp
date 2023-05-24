from utils import get_content
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from time import time
import pickle
import argparse
from time import sleep
from random import random, randint
from tqdm import tqdm
from os import cpu_count
import os
import pathlib
import pandas as pd
import json
from loguru import logger
import os




def file_processor(in_path = '../results', out_path = '../articles_metadata'):
    file_list = []
    dfs=[]
    if os.path.exists(in_path):
        if os.path.exists(out_path) == False:
            os.makedirs(out_path)
            
        for file in os.listdir(in_path):
            if file.endswith(".csv"):
                file_list.append(file)
                file_list.sort()
                
        for f in file_list:
            path = in_path + '/' + f
            data = pd.read_csv(path)
            dfs.append(data)
        df = pd.concat(dfs)
        df = df[['link', 'title', 'lead']]
        df.to_csv(out_path+ '/' + 'articles_metadata.csv', index=False)
        return df
    
 
    
def batch(batch_size, n_workers, metadata_df):
    """
    calls function for obtaining content from given link.
    """
    
    links = metadata_df.link
    titles = metadata_df.title
    headlines = metadata_df.lead

    with open("../obtained_content/logs.json", "r") as f:
        log = json.load(f)
    #open file with already obtained content for appending new pages
    
    try:
        full_content = pd.read_csv('../obtained_content/full_content.csv', header=0)
    except FileNotFoundError:
        full_content = pd.DataFrame({'link' : [],
                                     'title' : [],
                                     'headline' : [],
                                     'content' : [] })


    logger.info(f'current len of content: {len(full_content)}')
    checkpoint = log['last_page']
    logger.info(f'starting from page: {checkpoint}')
    
    start = time()

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        res = list(tqdm(executor.map(get_content,
                                links[checkpoint : checkpoint + batch_size],
                                titles[checkpoint : checkpoint + batch_size],
                                headlines[checkpoint : checkpoint + batch_size]),
                        total = batch_size))
    
    res = pd.DataFrame(res)
    full_content = pd.concat([full_content, res], axis = 0, ignore_index=True)    
    
    end = time()
    
    logger.info(f'last obtained page: {checkpoint + batch_size}')
    
    # save last obtained page id to logs as a starting point for another call
    log['last_page'] = checkpoint + batch_size 
    
    with open("../obtained_content/logs.json","w") as f:
        json.dump(log, f)

    full_content.to_csv('../obtained_content/full_content.csv', index=False, header=True)    
    
    logger.info(f'exec time: {end-start:.3f}s')



def main():
    
    parser = argparse.ArgumentParser(description="Scrape articles from tvpinfo")
    parser.add_argument("-bs",
                        "--batch_size",
                        type = int,
                        default = 32,
                        help = 'number of pages to download in one batch')
    parser.add_argument("-nb",
                        "--n_batches",
                        type = int,
                        default = 8,
                        help = 'number of batches')
    parser.add_argument("-nw",
                        "--n_workers",
                        type = int,
                        default = cpu_count(),
                        help = 'number of workers/separate processes')
    args = parser.parse_args()   

    batch_size = args.batch_size
    n_batches = args.n_batches
    n_workers = args.n_workers
    
    df = file_processor()
    
    for progress, i in enumerate(range(1, n_batches+1)):
        
        batch(batch_size = batch_size, n_workers = n_workers, metadata_df = df)
        logger.info(f'finished batch: {i}/{n_batches} ({100*i/n_batches:.2f}%)')
        
        if i < n_batches: 
            sleep_time = randint(1,30) * random()
            logger.info(f'Cooldown time: {sleep_time:.3f}s')
            sleep(sleep_time)
            
            
            
if __name__ == '__main__':
    main()