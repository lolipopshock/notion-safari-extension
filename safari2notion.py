import sys, os
import argparse

from notion.client import NotionClient
from notion.block import *
from notion.collection import NotionDate

from lib.processor import * 
from lib.utils import *

parser = argparse.ArgumentParser()
parser.add_argument('--page_selection', type=str, default='default', help='desc')
parser.add_argument('--titles',         type=str, nargs='+')
parser.add_argument('--urls',           type=str, nargs='+')
args = parser.parse_args()

CONFIG_PATH = '<your/notion/config/file/path>'

def iterate_items(page_urls, page_titles, page, Processor):

    for page_url, page_title in zip(page_urls, page_titles): 
        proc = Processor(page_url, page_title)
        row = proc.add_to_notion(page)
        if proc.name == 'Paper':
            proc.download_paper(os.path.expanduser('~/Downloads/'))
            proc.upload_thumbnail(client, row)
        
def create_notion_page(url):
    if is_notion_database(url):
        page = client.get_collection_view(url)
    else:
        page = client.get_block(url)
    return page

conf = load_json_record(CONFIG_PATH)
client = NotionClient(token_v2=conf['token'])
    
if __name__ == "__main__":
    
    page_selection = args.page_selection
    page_urls = args.urls
    page_titles = args.titles
    
    _url = conf['pages'].get(page_selection, page_selection)
    page = create_notion_page(_url)
    
    if page_selection == 'Paper':
        iterate_items(page_urls, page_titles, page, Paper)
    elif is_notion_database(_url):
        iterate_items(page_urls, page_titles, page, Article)
    else:
        iterate_items(page_urls, page_titles, page, Bookmark)
    
    client.session.close()