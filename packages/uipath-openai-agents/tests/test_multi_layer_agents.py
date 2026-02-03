"""Tests for multi-layer OpenAI agents with handoffs and tools."""

import os

from agents import Agent, function_tool

# Set up mock environment variables
os.environ.setdefault("UIPATH_URL", "https://mock.uipath.com")
os.environ.setdefault("UIPATH_ORGANIZATION_ID", "mock-org-id")
os.environ.setdefault("UIPATH_TENANT_ID", "mock-tenant-id")
os.environ.setdefault("UIPATH_ACCESS_TOKEN", "mock-token")

from uipath_openai_agents.runtime.schema import (  # noqa: E402
    get_agent_schema,
    get_entrypoints_schema,
)

# ============= TOOLS =============


@function_tool
async def check_employee_benefits(employee_id: str) -> str:
    """Check employee benefits information.

    Args:
        employee_id: The employee ID to look up

    Returns:
        Employee benefits information
    """
    return f"Employee {employee_id} benefits: Health Insurance, 401k, 20 days PTO"


@function_tool
async def submit_leave_request(employee_id: str, leave_type: str, days: int) -> str:
    """Submit a leave request for an employee.

    Args:
        employee_id: The employee ID
        leave_type: Type of leave (vacation, sick, personal)
        days: Number of days requested

    Returns:
        Leave request confirmation
    """
    return f"Leave request submitted for employee {employee_id}: {days} days of {leave_type} leave"


@function_tool
async def get_salary_info(employee_id: str) -> str:
    """Get salary information for an employee.

    Args:
        employee_id: The employee ID

    Returns:
        Salary information
    """
    return f"Employee {employee_id} salary information: $85,000 annual"


@function_tool
async def create_purchase_order(item: str, quantity: int, vendor: str) -> str:
    """Create a purchase order for items.

    Args:
        item: Item description
        quantity: Quantity to order
        vendor: Vendor name

    Returns:
        Purchase order confirmation
    """
    return f"Purchase Order created: {item} x{quantity} from {vendor}"


@function_tool
async def check_budget_availability(department: str, amount: float) -> str:
    """Check if budget is available for a department.

    Args:
        department: Department name
        amount: Amount to check

    Returns:
        Budget availability status
    """
    return f"Budget check for {department}: ${amount:,.2f} - APPROVED"


@function_tool
async def track_order_status(po_number: str) -> str:
    """Track the status of a purchase order.

    Args:
        po_number: Purchase order number

    Returns:
        Order status information
    """
    return f"Order Status for {po_number}: In Transit"


@function_tool
async def get_company_policy(policy_type: str) -> str:
    """Get company policy information.

    Args:
        policy_type: Type of policy (remote_work, expense, code_of_conduct, etc.)

    Returns:
        Policy information
    """
    return f"Policy information for {policy_type}"


@function_tool
async def check_compliance_status(policy_area: str) -> str:
    """Check compliance status for a policy area.

    Args:
        policy_area: Area to check compliance (data_security, safety, training, etc.)

    Returns:
        Compliance status
    """
    return f"Compliance Status for {policy_area}: COMPLIANT"


# ============= SPECIALIZED AGENTS =============


def create_multi_layer_agent():
    """Create a multi-layer agent structure with handoffs and tools."""
    # HR Agent - Handles human resources queries
    hr_agent = Agent(
        name="hr_agent",
        instructions="You are an HR specialist assistant handling benefits, leave, and salary inquiries.",
        model="gpt-4o-mini",
        tools=[check_employee_benefits, submit_leave_request, get_salary_info],
    )

    # Procurement Agent - Handles purchasing and procurement
    procurement_agent = Agent(
        name="procurement_agent",
        instructions="You are a procurement specialist handling purchase orders, budgets, and order tracking.",
        model="gpt-4o-mini",
        tools=[create_purchase_order, check_budget_availability, track_order_status],
    )

    # Policy Agent - Handles company policies and compliance
    policy_agent = Agent(
        name="policy_agent",
        instructions="You are a policy and compliance specialist providing policy information.",
        model="gpt-4o-mini",
        tools=[get_company_policy, check_compliance_status],
    )

    # Orchestrator Agent (Main Entry Point) - Routes to specialized agents
    orchestrator_agent = Agent(
        name="orchestrator_agent",
        instructions="You route employee requests to the appropriate department specialist.",
        model="gpt-4o-mini",
        handoffs=[hr_agent, procurement_agent, policy_agent],
    )

    return orchestrator_agent


# ============= TESTS =============


def test_multi_layer_agent_graph_nodes():
    """Test that all agents and aggregated tools nodes are represented in the graph."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Get all node IDs
    node_ids = {node.id for node in graph.nodes}

    # Verify control nodes
    assert "__start__" in node_ids
    assert "__end__" in node_ids

    # Verify all agents are present
    assert "orchestrator_agent" in node_ids
    assert "hr_agent" in node_ids
    assert "procurement_agent" in node_ids
    assert "policy_agent" in node_ids

    # Verify aggregated tools nodes (one per agent with tools)
    assert "hr_agent_tools" in node_ids
    assert "procurement_agent_tools" in node_ids
    assert "policy_agent_tools" in node_ids

    # Total: 2 control + 4 agents + 3 tools nodes = 9 nodes
    assert len(graph.nodes) == 9


def test_multi_layer_agent_node_types():
    """Test that nodes have correct types."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Create a mapping of node ID to type
    node_types = {node.id: node.type for node in graph.nodes}

    # Verify control node types
    assert node_types["__start__"] == "__start__"
    assert node_types["__end__"] == "__end__"

    # Verify agent nodes are of type "model"
    assert node_types["orchestrator_agent"] == "model"
    assert node_types["hr_agent"] == "model"
    assert node_types["procurement_agent"] == "model"
    assert node_types["policy_agent"] == "model"

    # Verify aggregated tools nodes are of type "tool"
    assert node_types["hr_agent_tools"] == "tool"
    assert node_types["procurement_agent_tools"] == "tool"
    assert node_types["policy_agent_tools"] == "tool"


def test_multi_layer_agent_handoff_edges():
    """Test that handoff edges are correctly created between orchestrator and specialized agents without labels."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Get all edges
    edges = [(edge.source, edge.target, edge.label) for edge in graph.edges]

    # Verify bidirectional handoff edges without labels
    assert ("orchestrator_agent", "hr_agent", None) in edges
    assert ("hr_agent", "orchestrator_agent", None) in edges

    assert ("orchestrator_agent", "procurement_agent", None) in edges
    assert ("procurement_agent", "orchestrator_agent", None) in edges

    assert ("orchestrator_agent", "policy_agent", None) in edges
    assert ("policy_agent", "orchestrator_agent", None) in edges


def test_multi_layer_agent_tool_edges():
    """Test that bidirectional tool edges exist for aggregated tools nodes without labels."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Get all edges
    edges = [(edge.source, edge.target, edge.label) for edge in graph.edges]

    # Verify bidirectional edges to/from aggregated tools nodes without labels
    assert ("hr_agent", "hr_agent_tools", None) in edges
    assert ("hr_agent_tools", "hr_agent", None) in edges

    assert ("procurement_agent", "procurement_agent_tools", None) in edges
    assert ("procurement_agent_tools", "procurement_agent", None) in edges

    assert ("policy_agent", "policy_agent_tools", None) in edges
    assert ("policy_agent_tools", "policy_agent", None) in edges


def test_multi_layer_agent_control_edges():
    """Test that control flow edges (start/end) are correctly created."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Get all edges
    edges = [(edge.source, edge.target, edge.label) for edge in graph.edges]

    # Verify start edge to orchestrator
    assert ("__start__", "orchestrator_agent", "input") in edges

    # Verify end edge from orchestrator
    assert ("orchestrator_agent", "__end__", "output") in edges


def test_multi_layer_agent_no_circular_references():
    """Test that the graph doesn't create circular references for the same agent."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Count occurrences of each agent in nodes
    node_counts: dict[str, int] = {}
    for node in graph.nodes:
        node_counts[node.id] = node_counts.get(node.id, 0) + 1

    # Each agent should appear exactly once
    assert node_counts["orchestrator_agent"] == 1
    assert node_counts["hr_agent"] == 1
    assert node_counts["procurement_agent"] == 1
    assert node_counts["policy_agent"] == 1


def test_multi_layer_agent_entrypoints_schema():
    """Test that entrypoints schema is correctly extracted."""
    agent = create_multi_layer_agent()
    schema = get_entrypoints_schema(agent)

    # Verify input schema (default messages format)
    assert "input" in schema
    assert "properties" in schema["input"]
    assert "messages" in schema["input"]["properties"]
    assert "required" in schema["input"]
    assert "messages" in schema["input"]["required"]

    # Verify output schema (default result format since no output_type specified)
    assert "output" in schema
    assert "properties" in schema["output"]
    assert "result" in schema["output"]["properties"]
    assert "required" in schema["output"]
    assert "result" in schema["output"]["required"]


def test_multi_layer_agent_edge_count():
    """Test that the total number of edges is correct."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Count expected edges:
    # - 2 control edges (start -> orchestrator, orchestrator -> end)
    # - 6 handoff edges (3 agents * 2 bidirectional edges each)
    # - 6 tool edges (3 tools nodes * 2 bidirectional edges each)
    # Total: 2 + 6 + 6 = 14 edges
    assert len(graph.edges) == 14


def test_multi_layer_agent_tools_metadata():
    """Test that tools nodes have correct metadata with tool_names and tool_count."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Create a mapping of node ID to metadata
    node_metadata = {node.id: node.metadata for node in graph.nodes}

    # Verify HR agent tools metadata
    hr_tools_metadata = node_metadata["hr_agent_tools"]
    assert hr_tools_metadata is not None
    assert "tool_names" in hr_tools_metadata
    assert "tool_count" in hr_tools_metadata
    assert hr_tools_metadata["tool_count"] == 3
    assert "check_employee_benefits" in hr_tools_metadata["tool_names"]
    assert "submit_leave_request" in hr_tools_metadata["tool_names"]
    assert "get_salary_info" in hr_tools_metadata["tool_names"]

    # Verify procurement agent tools metadata
    procurement_tools_metadata = node_metadata["procurement_agent_tools"]
    assert procurement_tools_metadata is not None
    assert "tool_names" in procurement_tools_metadata
    assert "tool_count" in procurement_tools_metadata
    assert procurement_tools_metadata["tool_count"] == 3
    assert "create_purchase_order" in procurement_tools_metadata["tool_names"]
    assert "check_budget_availability" in procurement_tools_metadata["tool_names"]
    assert "track_order_status" in procurement_tools_metadata["tool_names"]

    # Verify policy agent tools metadata
    policy_tools_metadata = node_metadata["policy_agent_tools"]
    assert policy_tools_metadata is not None
    assert "tool_names" in policy_tools_metadata
    assert "tool_count" in policy_tools_metadata
    assert policy_tools_metadata["tool_count"] == 2
    assert "get_company_policy" in policy_tools_metadata["tool_names"]
    assert "check_compliance_status" in policy_tools_metadata["tool_names"]


def test_multi_layer_agent_no_subgraphs():
    """Test that OpenAI agents are represented as flat nodes without subgraphs."""
    agent = create_multi_layer_agent()
    graph = get_agent_schema(agent)

    # Verify all nodes have None subgraph (flat structure)
    for node in graph.nodes:
        assert node.subgraph is None
