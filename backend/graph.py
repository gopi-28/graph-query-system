"""
graph.py — Graph Builder
========================
PURPOSE:
    This file builds an in-memory graph from the SQLite database.
    Think of it like a web of connected business entities.

WHY A GRAPH?
    A relational database stores data in separate tables.
    A graph shows HOW those tables connect to each other.

    Example:
        Customer "Cardenas Inc"
            → placed Sales Order "80001"
                → delivered via Delivery "70001"
                    → billed as Invoice "90001"
                        → payment received "PAY001"

    This chain is the "Order-to-Cash flow" the task asks you to trace.

WHY NetworkX?
    NetworkX is a Python library for building and analyzing graphs.
    - Easy to use (just add nodes and edges)
    - Works in memory (fast)
    - Can be converted to JSON for the frontend
    - No database server needed

KEY CONCEPTS:
    Node = a business entity (Customer, Order, Delivery, etc.)
    Edge = a relationship between two entities (Customer PLACED Order)

    Each node has:
        - id: unique identifier (e.g. "order_80001")
        - type: what kind of entity it is (e.g. "SalesOrder")
        - label: human-readable name shown in the UI
        - data: all the raw fields from the database

    Each edge has:
        - source: the "from" node id
        - target: the "to" node id
        - label: the relationship name (e.g. "PLACED", "DELIVERED_VIA")
"""

import networkx as nx
from db import get_connection

# ─── GLOBAL GRAPH ─────────────────────────────────────────────────────────────

# We keep one graph in memory for the whole app lifetime
# It's rebuilt once when the server starts
_graph = None


def build_graph():
    """
    Reads from SQLite and constructs the full NetworkX graph.

    Returns: nx.DiGraph (directed graph — edges have a direction)

    HOW IT WORKS:
        1. Load each entity type from SQLite
        2. Add each record as a node with its data as attributes
        3. Add edges between nodes based on foreign key relationships
    """
    global _graph

    print("Building graph from database...")
    G = nx.DiGraph()  # DiGraph = Directed Graph (edges have direction)

    conn = get_connection()

    # ── 1. CUSTOMERS (Business Partners) ──────────────────────────────────────
    # Source: business_partners table
    # Why: Customers are the starting point of every O2C flow
    rows = conn.execute("SELECT * FROM business_partners").fetchall()
    for row in rows:
        r = dict(row)
        node_id = f"customer_{r['customer']}"
        G.add_node(
            node_id,
            type="Customer",
            label=r.get("businessPartnerFullName") or r["customer"],
            entity_id=r["customer"],
            data=r
        )
    print(f"  Added {len(rows)} Customer nodes")

    # ── 2. SALES ORDERS ───────────────────────────────────────────────────────
    # Source: sales_order_headers table
    # Why: Sales orders are created by customers — core of the O2C process
    rows = conn.execute("SELECT * FROM sales_order_headers").fetchall()
    for row in rows:
        r = dict(row)
        node_id = f"order_{r['salesOrder']}"
        G.add_node(
            node_id,
            type="SalesOrder",
            label=f"Order {r['salesOrder']}",
            entity_id=r["salesOrder"],
            data=r
        )

        # Edge: Customer → SalesOrder (PLACED)
        # soldToParty is the customer who placed this order
        customer_node = f"customer_{r['soldToParty']}"
        if G.has_node(customer_node):
            G.add_edge(customer_node, node_id, label="PLACED")

    print(f"  Added {len(rows)} SalesOrder nodes")

    # ── 3. SALES ORDER ITEMS ──────────────────────────────────────────────────
    # Source: sales_order_items table
    # Why: Each order has line items — each item is for a specific product
    rows = conn.execute("SELECT * FROM sales_order_items").fetchall()
    for row in rows:
        r = dict(row)
        node_id = f"orderitem_{r['salesOrder']}_{r['salesOrderItem']}"
        G.add_node(
            node_id,
            type="SalesOrderItem",
            label=f"Item {r['salesOrderItem']} of Order {r['salesOrder']}",
            entity_id=f"{r['salesOrder']}-{r['salesOrderItem']}",
            data=r
        )

        # Edge: SalesOrder → SalesOrderItem (HAS_ITEM)
        order_node = f"order_{r['salesOrder']}"
        if G.has_node(order_node):
            G.add_edge(order_node, node_id, label="HAS_ITEM")

    print(f"  Added {len(rows)} SalesOrderItem nodes")

    # ── 4. PRODUCTS ───────────────────────────────────────────────────────────
    # Source: products + product_descriptions tables
    # Why: Products are what customers order
    # We join products with descriptions to get readable names
    rows = conn.execute("""
        SELECT p.*, pd.productDescription
        FROM products p
        LEFT JOIN product_descriptions pd 
            ON p.product = pd.product AND pd.language = 'EN'
    """).fetchall()

    for row in rows:
        r = dict(row)
        node_id = f"product_{r['product']}"
        G.add_node(
            node_id,
            type="Product",
            label=r.get("productDescription") or r["product"],
            entity_id=r["product"],
            data=r
        )
    print(f"  Added {len(rows)} Product nodes")

    # Edge: SalesOrderItem → Product (IS_PRODUCT)
    # Now connect order items to products
    item_rows = conn.execute(
        "SELECT salesOrder, salesOrderItem, material FROM sales_order_items"
    ).fetchall()
    edge_count = 0
    for row in item_rows:
        r = dict(row)
        item_node = f"orderitem_{r['salesOrder']}_{r['salesOrderItem']}"
        product_node = f"product_{r['material']}"
        if G.has_node(item_node) and G.has_node(product_node):
            G.add_edge(item_node, product_node, label="IS_PRODUCT")
            edge_count += 1
    print(f"  Added {edge_count} IS_PRODUCT edges")

    # ── 5. DELIVERIES ─────────────────────────────────────────────────────────
    # Source: outbound_delivery_headers table
    # Why: After an order is placed, it gets delivered
    rows = conn.execute("SELECT * FROM outbound_delivery_headers").fetchall()
    for row in rows:
        r = dict(row)
        node_id = f"delivery_{r['deliveryDocument']}"
        G.add_node(
            node_id,
            type="Delivery",
            label=f"Delivery {r['deliveryDocument']}",
            entity_id=r["deliveryDocument"],
            data=r
        )
    print(f"  Added {len(rows)} Delivery nodes")

    # Edge: SalesOrder → Delivery (DELIVERED_VIA)
    # outbound_delivery_items links deliveries back to sales orders
    # via referenceSdDocument (= salesOrder number)
    del_items = conn.execute(
        "SELECT DISTINCT deliveryDocument, referenceSdDocument FROM outbound_delivery_items"
    ).fetchall()
    edge_count = 0
    for row in del_items:
        r = dict(row)
        order_node = f"order_{r['referenceSdDocument']}"
        delivery_node = f"delivery_{r['deliveryDocument']}"
        if G.has_node(order_node) and G.has_node(delivery_node):
            G.add_edge(order_node, delivery_node, label="DELIVERED_VIA")
            edge_count += 1
    print(f"  Added {edge_count} DELIVERED_VIA edges")

    # ── 6. BILLING DOCUMENTS (Invoices) ───────────────────────────────────────
    # Source: billing_document_headers table
    # Why: After delivery, the customer is billed (invoiced)
    rows = conn.execute("SELECT * FROM billing_document_headers").fetchall()
    for row in rows:
        r = dict(row)
        node_id = f"billing_{r['billingDocument']}"
        G.add_node(
            node_id,
            type="BillingDocument",
            label=f"Invoice {r['billingDocument']}",
            entity_id=r["billingDocument"],
            data=r
        )

        # Edge: Customer → BillingDocument (BILLED_TO)
        # soldToParty = the customer being billed
        customer_node = f"customer_{r['soldToParty']}"
        if G.has_node(customer_node):
            G.add_edge(customer_node, node_id, label="BILLED_TO")

    print(f"  Added {len(rows)} BillingDocument nodes")

    # Edge: SalesOrder → BillingDocument (BILLED_AS)
    # billing_document_items links billing docs back to sales orders
    # via referenceSdDocument (= salesOrder number)
    bill_items = conn.execute(
        "SELECT DISTINCT billingDocument, referenceSdDocument FROM billing_document_items"
    ).fetchall()
    edge_count = 0
    for row in bill_items:
        r = dict(row)
        order_node = f"order_{r['referenceSdDocument']}"
        billing_node = f"billing_{r['billingDocument']}"
        if G.has_node(order_node) and G.has_node(billing_node):
            G.add_edge(order_node, billing_node, label="BILLED_AS")
            edge_count += 1
    print(f"  Added {edge_count} BILLED_AS edges")

    # ── 7. PAYMENTS ───────────────────────────────────────────────────────────
    # Source: payments_accounts_receivable table
    # Why: Final step — customer pays the invoice
    rows = conn.execute("SELECT * FROM payments_accounts_receivable").fetchall()
    for row in rows:
        r = dict(row)
        node_id = f"payment_{r['accountingDocument']}_{r['accountingDocumentItem']}"
        G.add_node(
            node_id,
            type="Payment",
            label=f"Payment {r['accountingDocument']}",
            entity_id=r["accountingDocument"],
            data=r
        )

        # Edge: BillingDocument → Payment (SETTLED_BY)
        # clearingAccountingDocument links payment to the billing doc
        billing_node = f"billing_{r['clearingAccountingDocument']}"
        if G.has_node(billing_node):
            G.add_edge(billing_node, node_id, label="SETTLED_BY")

    print(f"  Added {len(rows)} Payment nodes")

    # ── 8. JOURNAL ENTRIES ────────────────────────────────────────────────────
    # Source: journal_entry_items_accounts_receivable
    # Why: Every billing creates an accounting journal entry
    rows = conn.execute(
        "SELECT DISTINCT accountingDocument, companyCode, fiscalYear, customer, postingDate "
        "FROM journal_entry_items_accounts_receivable"
    ).fetchall()
    added = set()
    for row in rows:
        r = dict(row)
        node_id = f"journal_{r['accountingDocument']}"
        if node_id in added:
            continue
        added.add(node_id)
        G.add_node(
            node_id,
            type="JournalEntry",
            label=f"Journal {r['accountingDocument']}",
            entity_id=r["accountingDocument"],
            data=r
        )

        # Edge: BillingDocument → JournalEntry (POSTED_TO)
        # billing_document_headers.accountingDocument links to journal entry
        billing_rows = conn.execute(
            "SELECT billingDocument FROM billing_document_headers WHERE accountingDocument = ?",
            (r["accountingDocument"],)
        ).fetchall()
        for br in billing_rows:
            billing_node = f"billing_{br[0]}"
            if G.has_node(billing_node):
                G.add_edge(billing_node, node_id, label="POSTED_TO")

    print(f"  Added {len(added)} JournalEntry nodes")

    conn.close()

    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    print(f"\nGraph built: {node_count} nodes, {edge_count} edges")

    _graph = G
    return G


def get_graph():
    """
    Returns the global graph, building it first if needed.
    Called by main.py API routes.
    """
    global _graph
    if _graph is None:
        build_graph()
    return _graph


def graph_to_json(limit=300):
    """
    Converts the graph to a JSON format that Cytoscape.js can render.

    WHY THIS FORMAT?
        Cytoscape.js (our frontend graph library) expects data in this shape:
        {
            "nodes": [{"data": {"id": "...", "label": "...", "type": "..."}}],
            "edges": [{"data": {"source": "...", "target": "...", "label": "..."}}]
        }

    Args:
        limit: max nodes to return (too many nodes = slow browser rendering)
               We limit to 300 by default for performance

    Returns:
        dict with "nodes" and "edges" lists
    """
    G = get_graph()

    # Prioritize important node types for display
    # Order matters: customers and orders shown first
    priority_types = [
        "Customer", "SalesOrder", "BillingDocument",
        "Delivery", "Payment", "JournalEntry",
        "SalesOrderItem", "Product"
    ]

    nodes_data = []
    included_ids = set()

    # Add nodes in priority order
    for node_type in priority_types:
        for node_id, attrs in G.nodes(data=True):
            if attrs.get("type") == node_type and len(nodes_data) < limit:
                nodes_data.append({
                    "data": {
                        "id": node_id,
                        "label": attrs.get("label", node_id),
                        "type": attrs.get("type", "Unknown"),
                        "entity_id": attrs.get("entity_id", ""),
                        # Include key data fields for the info panel
                        **{k: str(v) for k, v in (attrs.get("data") or {}).items()
                           if k in get_display_fields(attrs.get("type", ""))}
                    }
                })
                included_ids.add(node_id)

    # Only include edges where BOTH nodes are in our limited set
    edges_data = []
    for source, target, attrs in G.edges(data=True):
        if source in included_ids and target in included_ids:
            edges_data.append({
                "data": {
                    "id": f"{source}__{target}",
                    "source": source,
                    "target": target,
                    "label": attrs.get("label", "")
                }
            })

    return {"nodes": nodes_data, "edges": edges_data}


def get_node_neighbors(node_id):
    """
    Returns a node and all its direct neighbors (1 hop away).

    WHY THIS EXISTS:
        In the UI, when a user clicks a node, we show its neighbors.
        This is the "expand node" feature — you click a Sales Order
        and see its Customer, Delivery, Invoice, and Items appear.

    Args:
        node_id: e.g. "order_80001"

    Returns:
        dict with the node + its neighbors as Cytoscape JSON
    """
    G = get_graph()

    if not G.has_node(node_id):
        return {"nodes": [], "edges": []}

    # Get all neighbors (both incoming and outgoing)
    neighbors = set(G.successors(node_id)) | set(G.predecessors(node_id))
    all_nodes = {node_id} | neighbors

    nodes_data = []
    for nid in all_nodes:
        attrs = G.nodes[nid]
        nodes_data.append({
            "data": {
                "id": nid,
                "label": attrs.get("label", nid),
                "type": attrs.get("type", "Unknown"),
                "entity_id": attrs.get("entity_id", ""),
                **{k: str(v) for k, v in (attrs.get("data") or {}).items()
                   if k in get_display_fields(attrs.get("type", ""))}
            }
        })

    edges_data = []
    for source, target, attrs in G.edges(data=True):
        if source in all_nodes and target in all_nodes:
            edges_data.append({
                "data": {
                    "id": f"{source}__{target}",
                    "source": source,
                    "target": target,
                    "label": attrs.get("label", "")
                }
            })

    return {"nodes": nodes_data, "edges": edges_data}


def get_display_fields(node_type: str):
    """
    Returns which data fields to show in the UI info panel for each node type.
    We don't want to show ALL fields (too noisy) — just the meaningful ones.
    """
    fields_map = {
        "Customer": ["customer", "businessPartnerFullName", "businessPartnerGrouping"],
        "SalesOrder": ["salesOrder", "salesOrderType", "totalNetAmount",
                       "transactionCurrency", "overallDeliveryStatus", "creationDate"],
        "SalesOrderItem": ["salesOrderItem", "material", "requestedQuantity",
                           "requestedQuantityUnit", "netAmount"],
        "Product": ["product", "productDescription", "productType",
                    "productGroup", "baseUnit", "grossWeight"],
        "Delivery": ["deliveryDocument", "overallGoodsMovementStatus",
                     "overallPickingStatus", "actualGoodsMovementDate"],
        "BillingDocument": ["billingDocument", "billingDocumentType",
                            "totalNetAmount", "transactionCurrency",
                            "billingDocumentIsCancelled", "billingDocumentDate"],
        "Payment": ["accountingDocument", "amountInTransactionCurrency",
                    "transactionCurrency", "postingDate", "clearingDate"],
        "JournalEntry": ["accountingDocument", "companyCode",
                         "fiscalYear", "postingDate", "customer"],
    }
    return fields_map.get(node_type, [])


def highlight_nodes(node_ids: list):
    """
    Given a list of entity IDs (e.g. ["80001", "90504298"]),
    finds the matching graph node IDs.

    WHY THIS EXISTS:
        When the LLM answers a query about specific orders or invoices,
        we want to highlight those nodes in the graph visualization.

        The LLM returns entity IDs like "80001".
        The graph uses node IDs like "order_80001".
        This function finds the right graph node IDs to highlight.

    Returns: list of graph node IDs to highlight in the frontend
    """
    G = get_graph()
    matched = []

    for node_id, attrs in G.nodes(data=True):
        entity_id = str(attrs.get("entity_id", ""))
        for search_id in node_ids:
            if str(search_id) in entity_id or entity_id in str(search_id):
                matched.append(node_id)
                break

    return matched


# ─── RUN DIRECTLY ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Run: python graph.py
    Builds the graph and prints a summary.
    Good for testing before starting the server.
    """
    G = build_graph()

    print("\n=== NODE TYPE COUNTS ===")
    from collections import Counter

    type_counts = Counter(attrs.get("type") for _, attrs in G.nodes(data=True))
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")

    print("\n=== EDGE LABEL COUNTS ===")
    edge_counts = Counter(attrs.get("label") for _, _, attrs in G.edges(data=True))
    for label, count in sorted(edge_counts.items()):
        print(f"  {label}: {count}")
