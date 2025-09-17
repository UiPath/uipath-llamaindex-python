import os

from llama_cloud_services import LlamaCloudIndex
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field

# Initialize LlamaCloud Index connections
company_policy_index = LlamaCloudIndex(
    name=os.getenv("LLAMACLOUD_INDEX_1_NAME"),
    project_name=os.getenv("LLAMACLOUD_PROJECT_NAME"),
    organization_id=os.getenv("LLAMACLOUD_ORG_ID"),
    api_key=os.getenv("LLAMACLOUD_API_KEY"),
)

personal_preferences_index = LlamaCloudIndex(
    name=os.getenv("LLAMACLOUD_INDEX_2_NAME"),
    project_name=os.getenv("LLAMACLOUD_PROJECT_NAME"),
    organization_id=os.getenv("LLAMACLOUD_ORG_ID"),
    api_key=os.getenv("LLAMACLOUD_API_KEY"),
)

llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def search_company_policy(query: str) -> str:
    """
    Search the company policy index for travel rates, guidelines, and company policies.

    Args:
        query (str): The search query about company travel policies, rates, or guidelines

    Returns:
        str: Relevant information from company policy documents
    """
    try:
        retriever = company_policy_index.as_retriever()
        retrieved_nodes = retriever.retrieve(query)

        if not retrieved_nodes:
            return "No relevant company policy information found for your query."

        # Format the search results
        results = []
        for i, node in enumerate(retrieved_nodes[:3], 1):  # Limit to top 3 results
            results.append(f"Result {i}:")
            results.append(f"  Content: {node.text[:300]}...")
            results.append(f"  Relevance Score: {node.score:.4f}")
            if hasattr(node.node, "metadata"):
                metadata = node.node.metadata
                if "file_name" in metadata:
                    results.append(f"  Source: {metadata['file_name']}")
                if "page_label" in metadata:
                    results.append(f"  Page: {metadata['page_label']}")
            results.append("")

        return "\n".join(results)
    except Exception as e:
        return f"Error searching company policy index: {str(e)}"


def search_personal_preferences(query: str) -> str:
    """
    Search the personal preferences index for user's travel preferences and requirements.

    Args:
        query (str): The search query about personal travel preferences or requirements

    Returns:
        str: Relevant information from personal preference documents
    """
    try:
        retriever = personal_preferences_index.as_retriever()
        retrieved_nodes = retriever.retrieve(query)

        if not retrieved_nodes:
            return "No relevant personal preference information found for your query."

        # Format the search results
        results = []
        for i, node in enumerate(retrieved_nodes[:3], 1):  # Limit to top 3 results
            results.append(f"Result {i}:")
            results.append(f"  Content: {node.text[:300]}...")
            results.append(f"  Relevance Score: {node.score:.4f}")
            if hasattr(node.node, "metadata"):
                metadata = node.node.metadata
                if "file_name" in metadata:
                    results.append(f"  Source: {metadata['file_name']}")
                if "page_label" in metadata:
                    results.append(f"  Page: {metadata['page_label']}")
            results.append("")

        return "\n".join(results)
    except Exception as e:
        return f"Error searching personal preferences index: {str(e)}"


def get_travel_recommendation(query: str) -> str:
    """
    Get travel recommendations based on company policies and personal preferences.

    Args:
        query (str): The travel-related query or request for recommendations

    Returns:
        str: Travel recommendations combining policy and preference information
    """
    try:
        # Search both indexes for comprehensive information
        policy_info = search_company_policy(query)
        preference_info = search_personal_preferences(query)

        recommendation = f"""
Travel Recommendation Analysis:

Company Policy Information:
{policy_info}

Personal Preference Information:
{preference_info}

Based on the above information, here are the key considerations for your travel request.
        """

        return recommendation.strip()
    except Exception as e:
        return f"Error generating travel recommendation: {str(e)}"


class AgentResponse(BaseModel):
    response: str = Field(
        description="The agent's response using available tools to search company policies and personal preferences"
    )


# Create the FunctionAgent with our tools
agent = FunctionAgent(
    tools=[
        search_company_policy,
        search_personal_preferences,
        get_travel_recommendation,
    ],
    llm=llm,
    output_cls=AgentResponse,
    system_prompt="""You are a helpful travel assistant that can search through company travel policies and personal preferences to provide comprehensive travel guidance.

You have access to three main functions:
1. search_company_policy - Search for company travel rates, guidelines, and policies
2. search_personal_preferences - Search for user's personal travel preferences and requirements
3. get_travel_recommendation - Get comprehensive travel recommendations combining both sources

Use these tools to help users with travel-related queries, ensuring you provide accurate information from both company policies and personal preferences when relevant.""",
)
