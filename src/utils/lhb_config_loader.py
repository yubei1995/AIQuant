import pandas as pd
import os
import xml.etree.ElementTree as ET

def load_lhb_config(file_path):
    """
    Load LHB analysis configuration.
    Returns a tuple (exact_map, fuzzy_rules).
    
    exact_map: dict {branch_name: {'category': ..., 'alias': ...}}
    fuzzy_rules: list [{'pattern': ..., 'match': 'contains', 'category': ..., 'alias': ...}]
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")

    if file_path.endswith('.xml'):
        return _load_from_xml(file_path)
    elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        # Legacy support: wrap dict in tuple
        return _load_from_excel(file_path), []
    else:
        raise ValueError("Unsupported file format. Use .xml or .xlsx")

def _load_from_xml(file_path):
    exact_map = {}
    fuzzy_rules = []
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        seat_mappings = root.find('SeatMappings')
        if seat_mappings is None:
            return exact_map, fuzzy_rules
            
        for category in seat_mappings.findall('Category'):
            cat_name = category.get('name')
            
            for alias in category.findall('Alias'):
                alias_name = alias.get('name')
                
                for branch in alias.findall('Branch'):
                    branch_name = branch.text
                    match_mode = branch.get('match')
                    
                    if branch_name:
                        info = {
                            'category': cat_name,
                            'alias': alias_name
                        }
                        
                        if match_mode == 'contains':
                            fuzzy_rules.append({
                                'pattern': branch_name.strip(),
                                'match': 'contains',
                                **info
                            })
                        else:
                            # Default is exact match
                            exact_map[branch_name.strip()] = info
                            
    except Exception as e:
        print(f"Error parsing XML config: {e}")
        
    return exact_map, fuzzy_rules

def _load_from_excel(file_path):
    # READ Excel logic (Moved from original function)
    df = pd.read_excel(file_path)
    
    mapping = {}
    current_category = None
    current_alias = None
    
    # Iterate from row 2 to end
    for i in range(2, len(df)):
        row = df.iloc[i]
        
        col_cat = row.iloc[1] # Category
        col_alias = row.iloc[2] # Alias
        col_branch = row.iloc[3] # Branch
        
        # Update Category
        if pd.notna(col_cat):
            val = str(col_cat).strip()
            # Stop if we hit metadata rows like "游资净买入变化" (Row 77+)
            if "变化" in val or "成交额" in val:
                break
            current_category = val
            
        # Update Alias
        if pd.notna(col_alias):
            current_alias = str(col_alias).strip()
        elif pd.notna(col_cat) and pd.isna(col_alias):
            current_alias = current_category
            
        # If Branch is present
        if pd.notna(col_branch):
            branch_name = str(col_branch).strip()
            if branch_name:
                mapping[branch_name] = {
                    'category': current_category,
                    'alias': current_alias
                }
    return mapping

if __name__ == "__main__":
    # Test
    try:
        # base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # xml_path = os.path.join(base_dir, "data", "lhb_config.xml") 
        # m = load_lhb_config(xml_path)
        # print(f"Loaded {len(m)} branch mappings from XML.")
        pass
    except Exception as e:
        print(e)
