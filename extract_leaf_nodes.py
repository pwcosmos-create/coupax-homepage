import json

def extract_leaf_nodes():
    try:
        with open('njob_category_tree.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        flat_list = data.get('flat_list', [])
        # 'last': True 인 노드만 추출 (네이버 API에서 수정 가능한 리프 노드)
        leaf_nodes = [node for node in flat_list if node.get('last') is True]
        
        with open('njob_leaf_categories.json', 'w', encoding='utf-8') as f:
            json.dump(leaf_nodes, f, ensure_ascii=False, indent=2)
            
        print(f"[+] Total Categories: {len(flat_list)}")
        print(f"[+] Leaf Categories: {len(leaf_nodes)}")
        print("[+] Saved to njob_leaf_categories.json")
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    extract_leaf_nodes()
