import json
import graphviz
from collections import defaultdict, deque
from graphviz import Digraph
from dateutil import parser
import re

# Function to parse JSON lines from a file
def parse_json_lines(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return [json.loads(line) for line in lines]

# Function to extract cookieTraceID from attributes
def get_cookie_trace_id(attributes):
    for attribute in attributes:
        if attribute['Key'] == 'cookieTraceID':
            return attribute['Value']['Value']
    return None

# Function to group entries by cookieTraceID
def group_by_cookie_trace_id(entries):
    grouped = defaultdict(list)
    for entry in entries:
        cookie_trace_id = get_cookie_trace_id(entry['attributes'])
        if cookie_trace_id:
            grouped[cookie_trace_id].append(entry)
    return grouped

# Function to sort entries by startTime
def sort_by_start_time(entries):
    return sorted(entries, key=lambda x: parser.isoparse(x['startTime']))

# Load the JSON lines
entries = parse_json_lines('input.json')

# Group entries by cookieTraceID
grouped_entries = group_by_cookie_trace_id(entries)
print(f"Found {len(grouped_entries)} cookieTraceID groups")

# Create a new directed graph
dot = graphviz.Digraph(comment='CookieTraceID Graphs')

# Function to replace 4-digit numbers with an asterisk
def replace_digits_with_asterisk(target):
    target = re.sub(r'/api/livestream/\d{4}/', '/api/livestream/_/', target)
    target = re.sub(r'/api/livestream/\d{4}', '/api/livestream/_', target)
    target = re.sub(r'(/api/user/)[^/]+', r'\1_', target)
    target = re.sub(r'/api/livestream/_/livecomment/\d{4}/', '/api/livestream/_/livecomment/_/', target)

    return target


edge_weights = defaultdict(int)
nodes = defaultdict(int)  # Fix: Changed from string to int


nodes = defaultdict(int)
edge_weights = defaultdict(int)

# Step 1: Edge and Node Processing
edges = []
for cookie_trace_id, trace_entries in grouped_entries.items():
    sorted_entries = sort_by_start_time(trace_entries)
    previous_target = None

    for entry in sorted_entries:
        current_target = entry['attributes'][6]['Value']['Value']  # Assuming http.target is always at index 6
        # ユーザーごとにパスが違う場合にまとめる
        current_target = replace_digits_with_asterisk(current_target)  # Replace digits with asterisk

        nodes[current_target] += 1

        if previous_target:
            edge = (previous_target, current_target)
            edge_weights[edge] += 1
            edges.append(edge)
        previous_target = current_target

# Step 2: Root Node Detection
in_degree = defaultdict(int)
out_degree = defaultdict(int)

for parent, child in edges:
    in_degree[child] += 1
    out_degree[parent] += 1

# 入次数が0または自分からのエッジしかないノードをルートとする
root_nodes = [
    node for node in nodes
    if in_degree[node] == 0 or (in_degree[node] == 1 and out_degree[node] == 1)
]

# Step 3: Distance Calculation Using BFS from Root
node_ranks = {}
for root in root_nodes:
    queue = deque([(root, 0)])  # (node, distance)
    visited = set()

    while queue:
        node, distance = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        node_ranks[node] = distance

        for _, child in filter(lambda x: x[0] == node, edges):
            if child not in visited:
                queue.append((child, distance + 1))

# Step 4: Graphviz Ranks and Node/Edge Addition
dot = Digraph()
dot.attr(rankdir="LR", ranksep="1")

# Create subgraphs for each rank level
rank_groups = defaultdict(list)
for node, rank in node_ranks.items():
    rank_groups[rank].append(node)

# Apply rank=same for nodes with the same distance
for rank, rank_nodes in rank_groups.items():
    with dot.subgraph() as s:
        s.attr(rank="same")
        for node in rank_nodes:
            dot.node(node, label=f"{node}\n{nodes[node]} times")

# Add edges with labels for their weights
for (parent, child), count in edge_weights.items():
    dot.edge(parent, child)

print(f"Finish adding edges and nodes")

# Render the graph
dot.render('output_graph', format='png', cleanup=True)

print("Graph has been generated as 'output_graph.png'")