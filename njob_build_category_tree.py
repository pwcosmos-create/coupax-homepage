import json
import urllib.request
import time
from dotenv import load_dotenv

load_dotenv()

with open('njob_session.json', 'r', encoding='utf-8') as f:
    session = json.load(f)
COOKIES = '; '.join([c['name'] + '=' + c['value'] for c in session.get('cookies', [])])

def api(ca=''):
    url = f'https://www.njobapp.com/getCategoryNjobPc?ca={ca}'
    req = urllib.request.Request(url, headers={
        'Cookie': COOKIES,
        'User-Agent': 'Mozilla/5.0',
        'X-Requested-With': 'XMLHttpRequest'
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))

def build_tree():
    tree = {}

    # ── sort1 ─────────────────────────────────────────────────────────────────
    r1 = api('')
    sort1 = r1['data']  # {code: name}
    tree['sort1'] = [{'id': k, 'name': v} for k, v in sort1.items()]
    print(f'sort1: {len(tree["sort1"])}개')

    # ── sort2 ~ sort4 ─────────────────────────────────────────────────────────
    all_nodes = {}  # id -> node

    queue = [item['id'] for item in tree['sort1']]

    for code in queue:
        r = api(code)
        children = r.get('data', [])
        if not isinstance(children, list) or not children:
            continue

        for item in children:
            item_id = item['id']
            if item_id not in all_nodes:
                all_nodes[item_id] = {
                    'id': item_id,
                    'depth': item['depth'],
                    'name': item['ca_name'],
                    'seId': item.get('seId', ''),
                    'children': []
                }
            # 부모에 자식 연결
            if item_id not in all_nodes.get(code, {}).get('children', []):
                if code not in all_nodes:
                    all_nodes[code] = {'id': code, 'depth': 1, 'name': sort1.get(code, ''), 'seId': '', 'children': []}
                if item_id not in all_nodes[code]['children']:
                    all_nodes[code]['children'].append(item_id)

        # depth 3 이하면 재귀 조회
        for item in children:
            if item['depth'] < 4:
                queue.append(item['id'])

        time.sleep(0.1)

    # 중복 제거를 위해 set으로 처리 후 queue 정리 (이미 조회한 코드 제외)
    print(f'전체 노드: {len(all_nodes)}개')

    # ── 평면 카테고리 목록 생성 (경로 포함) ───────────────────────────────────
    flat_list = []

    def get_name(code):
        if code in all_nodes:
            return all_nodes[code]['name']
        return sort1.get(code, code)

    def build_path(node_id, visited=None):
        if visited is None:
            visited = set()
        if node_id in visited:
            return
        visited.add(node_id)
        node = all_nodes.get(node_id)
        if not node:
            return

        if not node['children']:
            # 리프 노드 - 전체 경로 구성
            parts = [node_id]
            cur = node_id
            # 부모 역추적
            for s1 in tree['sort1']:
                if node_id in all_nodes.get(s1['id'], {}).get('children', []):
                    path = f"{s1['name']} > {node['name']}"
                    flat_list.append({'id': node_id, 'seId': node['seId'], 'path': path, 'depth': node['depth']})
                    return

            flat_list.append({'id': node_id, 'seId': node['seId'], 'path': node['name'], 'depth': node['depth']})
        else:
            for child_id in node['children']:
                build_path(child_id, visited)

    # 간단한 평면 리스트: 모든 노드를 경로와 함께 저장
    # 부모 맵 구성
    parent_map = {}
    for nid, node in all_nodes.items():
        for child_id in node.get('children', []):
            parent_map[child_id] = nid
    for s1 in tree['sort1']:
        for child_id in all_nodes.get(s1['id'], {}).get('children', []):
            parent_map[child_id] = s1['id']

    def get_full_path(node_id):
        parts = []
        cur = node_id
        visited = set()
        while cur and cur not in visited:
            visited.add(cur)
            node = all_nodes.get(cur)
            name = node['name'] if node else sort1.get(cur, cur)
            parts.insert(0, name)
            cur = parent_map.get(cur)
            if cur and cur not in all_nodes:
                # sort1
                s1_name = sort1.get(cur, cur)
                parts.insert(0, s1_name)
                break
        return ' > '.join(parts)

    for nid, node in all_nodes.items():
        path = get_full_path(nid)
        flat_list.append({
            'id': nid,
            'seId': node['seId'],
            'depth': node['depth'],
            'name': node['name'],
            'path': path
        })

    # sort1도 추가
    for s1 in tree['sort1']:
        flat_list.append({
            'id': s1['id'],
            'seId': '',
            'depth': 1,
            'name': s1['name'],
            'path': s1['name']
        })

    # 저장
    result = {
        'sort1': tree['sort1'],
        'all_nodes': all_nodes,
        'flat_list': flat_list
    }
    with open('njob_category_tree.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'[완료] 총 {len(flat_list)}개 카테고리 -> njob_category_tree.json')
    return result

if __name__ == '__main__':
    build_tree()
