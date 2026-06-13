import json
import time
from naver_commerce_api import NaverCommerceAPI

def update_category_tree():
    api = NaverCommerceAPI()
    flat_list = []
    queue = []

    print(">>> Fetching root categories...")
    roots = api.get_root_categories()
    if not isinstance(roots, list):
        print(f"Error: Expected list but got {type(roots)}. Response: {roots}")
        return

    for root in roots:
        node = {
            'id': root.get('id'),
            'name': root.get('name'),
            'path': root.get('name'),
            'parentId': None,
            'last': root.get('last', False)
        }
        flat_list.append(node)
        if not node['last']:
            queue.append(node)

    print(f"[*] Found {len(roots)} root categories. Total nodes to expand: {len(queue)}")

    idx = 0
    start_time = time.time()
    while idx < len(queue):
        parent = queue[idx]
        idx += 1
        
        # Rate limit safety: 0.1s delay between calls (~10 requests/sec)
        time.sleep(0.1)
        
        if idx % 50 == 0:
            elapsed = time.time() - start_time
            print(f"[*] Progress: {idx}/{len(queue)} nodes processed, total categories so far: {len(flat_list)}, Elapsed: {elapsed:.1f}s")

        try:
            subs = api.get_sub_categories(parent['id'])
            if isinstance(subs, list):
                for sub in subs:
                    node = {
                        'id': sub.get('id'),
                        'name': sub.get('name'),
                        'path': f"{parent['path']} > {sub.get('name')}",
                        'parentId': parent['id'],
                        'last': sub.get('last', False)
                    }
                    flat_list.append(node)
                    if not node['last']:
                        queue.append(node)
            else:
                # API might return error or {} for sub-categories
                pass
        except Exception as e:
            print(f"  [!] Error fetching sub-categories for {parent['id']}: {e}")
            time.sleep(1)

    # Save to JSON
    data = {
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_count': len(flat_list),
        'flat_list': flat_list
    }
    
    filename = 'njob_category_tree.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully updated {len(flat_list)} categories to {filename}")

if __name__ == "__main__":
    update_category_tree()
