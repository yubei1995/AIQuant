import os
import xml.etree.ElementTree as ET

def load_stock_list(xml_path=None):
    if xml_path is None:
        # Default to project root data/stock_list.xml
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        xml_path = os.path.join(project_root, "data", "stock_list.xml")
    
    if not os.path.exists(xml_path):
        print(f"Warning: Stock list not found at {xml_path}")
        return []

    tree = ET.parse(xml_path)
    root = tree.getroot()
    stocks = []
    for block in root.findall('Block'):
        for stock in block.findall('Stock'):
            code = stock.get('code')
            name = stock.text.strip()
            stocks.append({'code': code, 'name': name, 'block': block.get('name')})
    return stocks

NATIONAL_TEAM_ETFS = [
    {'code': '510300', 'name': '沪深300ETF'},
    {'code': '510050', 'name': '上证50ETF'},
    {'code': '510500', 'name': '中证500ETF'},
    {'code': '512100', 'name': '中证1000ETF'},
    {'code': '588000', 'name': '科创50ETF'},
    {'code': '159915', 'name': '创业板ETF'}
]
