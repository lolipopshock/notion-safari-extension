from abc import ABC
import io
import re

from notion.block import *
from markdownify import markdownify as md
from md2notion.upload import upload
import arxiv
from newspaper import Article as _Article
import pandas as pd
from .utils import * 
import os 
import mimetypes

from urllib.parse import urlparse
import urllib.request

_cvf_path = os.path.join(os.path.abspath(__file__.replace('processor.py', '')), 'data/cvf_all.csv')
CVF_Data = pd.read_csv(_cvf_path)

def _process_paper_title(name):
    #ref https://stackoverflow.com/a/295466
    value = re.sub(r'[^\w\s-]', ' ', name)
    value = re.sub(r'[-\s]+', '-', value)
    return value

def _extract_arixv_paper_id(url):
    return url.split('/')[-1].replace('.pdf', '')    

def _newspaper3k_extract(link):
    article = _Article(link, keep_article_html=True)
    article.download()
    article.parse()
    return article

def _upload_file_to_row_property(client, row, path, property_name):
    mimetype = mimetypes.guess_type(path)[0] or "text/plain"
    filename = os.path.split(path)[-1]
    data = client.post("getUploadFileUrl", {"bucket": "secure", "name": filename, "contentType": mimetype}, ).json()
    # Return url, signedGetUrl, signedPutUrl
    mangled_property_name = [e["id"] for e in row.schema if e["name"] == property_name][0]

    with open(path, "rb") as f:
        response = requests.put(data["signedPutUrl"], data=f, headers={"Content-type": mimetype})
        response.raise_for_status()
    simpleurl = data['signedGetUrl'].split('?')[0]
    op1 = build_operation(id=row.id, path=["properties", mangled_property_name], args=[[filename, [["a", simpleurl]]]], table="block", command="set")
    file_id = simpleurl.split("/")[-2]
    op2 = build_operation(id=row.id, path=["file_ids"], args={"id": file_id}, table="block", command="listAfter")
    client.submit_transaction([op1, op2])

class BaseProcessor(ABC):
    
    def __init__(self, link, title):
        self.link = link
        self.title = title

    def add_to_notion(self, notion_page):
        pass

class Paper(BaseProcessor):
    
    @property
    def name(self):
        return "Paper"
    
    def __init__(self, link, title):    
        super().__init__(link, title)        
        
    def extract_info_from_link(self):
        if "arxiv" in self.link:
            return self.arxiv_extractor()
        elif 'thecvf' in self.link:
            return self.cvf_extractor()
        else:
            return self.plain_extractor()
    
    def arxiv_extractor(self):
        
        paper_id = _extract_arixv_paper_id(self.link)
        entry = arxiv.query(id_list=[paper_id])[0]
        self.download_link = entry['pdf_url']
        self.title = entry['title']
        return {'title': entry['title'],
                'authors': ', '.join(entry['authors']),
                'url': entry['pdf_url']}
    
    def cvf_extractor(self):
        res = urlparse(self.link)
        paper_info = CVF_Data[CVF_Data.pdf_link==res.path[1:]]
        if paper_info.shape[0]==1:
            paper_info = paper_info.iloc[0]
            self.download_link = self.link
            self.title = paper_info['name']
            return {'title': paper_info['name'],
                    'authors': paper_info['authors'],
                    'url': self.link,
                    'ref': paper_info['bibref']}
        else:
            return self.plain_extractor()
    
    def plain_extractor(self):
        return {'title': self.title,
                'authors': '',
                'url': self.link}

    def template_page(self, row):
        row.children.add_new(DividerBlock)
        tb = row.children.add_new(ToggleBlock, title='**Summary**')
        tb.children.add_new(BulletedListBlock, title='')
        #row.children.add_new(TextBlock, title='\n')
        row.children.add_new(DividerBlock)
        tb = row.children.add_new(ToggleBlock, title='**Contribution**')
        tb.children.add_new(BulletedListBlock, title='')    
        row.children.add_new(DividerBlock)
        
    def add_to_notion(self, notion_page, enable_template_page=True):
                
        row = notion_page.collection.add_row()
        paper_info = self.extract_info_from_link()
        
        row.set_property("name", paper_info['title'])
        row.set_property("Authors", paper_info['authors'])
        row.set_property("URL", paper_info['url'])
        row.set_property("Bibtex", paper_info.get('ref', ''))
        
        if enable_template_page:
            self.template_page(row)
        return row
    
    def download_paper(self, save_path):
        save_path = os.path.join(save_path, f"{_process_paper_title(self.title)}.pdf")
        urllib.request.urlretrieve(self.download_link, save_path)
        self.save_path = save_path
    
    def upload_thumbnail(self, client, row, quality=40):
        if hasattr(self, "save_path"):
            
            cache_dir = os.path.expanduser('~/.cache/paper-img')
            
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            
            from pdf2image import convert_from_path
            pages = convert_from_path(self.save_path)
            tmp_image_save_path = os.path.join(cache_dir, 'tmp.png')
            pages[0].save(tmp_image_save_path, quality=quality)
        
            _upload_file_to_row_property(client, row, tmp_image_save_path, 'Thumbnail')
            os.remove(tmp_image_save_path)


class Article(BaseProcessor):

    @property
    def name(self):
        return "Article"
    
    def __init__(self, link, title, text=''):    
        super().__init__(link, title)
        self.text = text
    
    def extract_article(self, article_parser):
        pass
    
    def add_to_notion(self, notion_page):
        
        article = _newspaper3k_extract(self.link)
        
        mdFile = io.StringIO(md(article.article_html))
        mdFile.__dict__["name"] = '/'
        
        if is_notion_database(notion_page):
            page = notion_page.collection.add_row(title=article.title)
            page.set_property("url", self.link)
        else:
            page = notion_page.children.add_new(PageBlock, title=article.title)
            page.add_new(TextBlock, title=self.link)

        if article.top_image != '':    
            block = page.children.add_new(ImageBlock, link=article.top_image)
            block.source = article.top_image
        
        upload(mdFile, page)
    

class Bookmark(BaseProcessor):

    @property
    def name(self):
        return "Bookmark"
    
    def __init__(self, link, title):    
        super().__init__(link, title)
    
    def add_to_notion(self, notion_page): 
        
        if not is_notion_database(notion_page):
            block = notion_page.children.add_new(BookmarkBlock, link=self.link, title=self.title)
            article = _newspaper3k_extract(self.link)
            if article.top_image != '':
                block.bookmark_cover = article.top_image
            if article.meta_description != '':
                block.description = article.meta_description
        else:
            page = notion_page.collection.add_row(title=self.title)
            page.set_property("url", self.link)