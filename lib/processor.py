from abc import ABC
import io
import re

from notion.block import *
from markdownify import markdownify as md
from md2notion.upload import upload
import arxiv
from newspaper import Article as _Article

from .utils import * 

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

class BaseProcessor(ABC):
    
    def __init__(self, link, title):
        self.link = link
        self.title = title

    def add_to_notion(self, notion_page):
        pass


class Paper(BaseProcessor):
    
    def __init__(self, link, title):    
        super().__init__(link, title)        
        
    def extract_info_from_link(self):
        if "arxiv" in self.link:
            return self.arxiv_extractor()
        else:
            return self.plain_extractor()
    
    def arxiv_extractor(self):
        
        paper_id = _extract_arixv_paper_id(self.link)
        entry = arxiv.query(id_list=[paper_id])[0]
        
        return {'title': entry['title'],
                'authors': ', '.join(entry['authors']),
                'url': entry['pdf_url']}
        
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
        row.set_property("Paper Name", paper_info['title'])
        
        if enable_template_page:
            self.template_page(row)
    

class Article(BaseProcessor):

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