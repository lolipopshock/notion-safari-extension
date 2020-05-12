import json
import notion

def load_json_record(filepath):
    
    with open(filepath, 'r') as fp:
        res = json.load(fp)
    return res

def is_notion_link(link):
    return link.startswith("https://www.notion.so/")

def is_notion_database(link):
    if isinstance(link, str):
        return '?v=' in link.split('/')[-1]
    elif isinstance(link, notion.collection.TableView):
        return True
    else:
        return False