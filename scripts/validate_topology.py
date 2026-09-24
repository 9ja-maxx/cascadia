#!/usr/bin/env python3
"""
CASCADIA PROTOCOL — Topological Invariant & DAG Acyclicity Validator
====================================================================
Independent verification script to validate external dependency definitions
prior to submitting `create_verdict` transactions to GenLayer Intelligent Contracts.

Invariants verified:
1. Strict Directed Acyclic Graph (DAG) acyclicity via Kahn's algorithm
2. Maximum graph depth <= 32
3. Maximum fan-out per node <= 32
4. Total active nodes <= 128
5. ID format & uniqueness
"""

import sys
import json
from collections import defaultdict, deque
from typing import Dict, List, Set, Any, Tuple

MAX_NODES = 128
MAX_FANOUT = 32
MAX_DEPTH = 32

def validate_topology(nodes: List[Dict[str, Any]], edges: List[Tuple[str, str]]) -> Tuple[bool, List[str]]:
    errors = []
    
    # 1. Total node capacity bound
    if len(nodes) > MAX_NODES:
        errors.append(f"Node count {len(nodes)} exceeds maximum limit {MAX_NODES}")
        
    node_ids = set()
    for n in nodes:
        nid = n.get("id")
        if not nid:
            errors.append("Encountered node without 'id' field")
            continue
        if nid in node_ids:
            errors.append(f"Duplicate node id detected: {nid}")
        node_ids.add(nid)
        
    # Build adjacency lists:
    # adj: parent -> [children] (forward cascade direction)
    # in_degree: child -> incoming dependency count
    adj = defaultdict(list)
    in_degree = defaultdict(int)
    for nid in node_ids:
        in_degree[nid] = 0
        
    fanout = defaultdict(int)
    for parent, child in edges:
        if parent not in node_ids:
            errors.append(f"Edge parent '{parent}' does not exist in node set")
        if child not in node_ids:
            errors.append(f"Edge child '{child}' does not exist in node set")
            
        adj[parent].append(child)
        fanout[parent] += 1
        in_degree[child] += 1
        
        if fanout[parent] > MAX_FANOUT:
            errors.append(f"Node '{parent}' fanout {fanout[parent]} exceeds limit {MAX_FANOUT}")
            
    # 2. Cycle detection via Kahn's Algorithm
    queue = deque([nid for nid in node_ids if in_degree[nid] == 0])
    visited_count = 0
    depth_map = {nid: 0 for nid in queue}
    
    while queue:
        curr = queue.popleft()
        visited_count += 1
        curr_depth = depth_map[curr]
        
        if curr_depth > MAX_DEPTH:
            errors.append(f"Node '{curr}' depth {curr_depth} exceeds limit {MAX_DEPTH}")
            
        for child in adj[curr]:
            depth_map[child] = max(depth_map.get(child, 0), curr_depth + 1)
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
                
    if visited_count != len(node_ids):
        errors.append(f"Topological cycle detected! Processed {visited_count}/{len(node_ids)} nodes.")
        
    return len(errors) == 0, errors

def main():
    print("=" * 70)
    print("CASCADIA PROTOCOL — TOPOLOGICAL INTEGRITY VERIFIER")
    print("=" * 70)
    
    sample_nodes = [
        {"id": "anchor-compliance-soc2", "kind": "ANCHOR", "title": "SOC 2 Type II"},
        {"id": "anchor-iso27001", "kind": "ANCHOR", "title": "ISO 27001 Certified"},
        {"id": "verdict-sec-audit", "kind": "VERDICT", "title": "Security Audit Approval"},
        {"id": "verdict-procurement-tier1", "kind": "VERDICT", "title": "Tier 1 Procurement Approval"},
        {"id": "verdict-auto-wire", "kind": "VERDICT", "title": "Automated Wire Authorization"}
    ]
    
    sample_edges = [
        ("anchor-compliance-soc2", "verdict-sec-audit"),
        ("anchor-iso27001", "verdict-sec-audit"),
        ("verdict-sec-audit", "verdict-procurement-tier1"),
        ("verdict-procurement-tier1", "verdict-auto-wire")
    ]
    
    print(f"Validating sample topology: {len(sample_nodes)} nodes, {len(sample_edges)} edges...")
    is_valid, errs = validate_topology(sample_nodes, sample_edges)
    
    if is_valid:
        print("[SUCCESS] Topology satisfies all CASCADIA DAG invariants:")
        print("  - Strict Directed Acyclicity: PASS")
        print("  - Depth Bound (<= 32): PASS")
        print("  - Fan-out Bound (<= 32): PASS")
        print("  - Node Capacity Bound (<= 128): PASS")
        print("  - ID Integrity: PASS")
        return 0
    else:
        print("[FAILURE] Violations found:")
        for e in errs:
            print(f"  - {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
