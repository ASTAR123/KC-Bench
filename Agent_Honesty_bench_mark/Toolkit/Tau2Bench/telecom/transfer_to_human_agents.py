from smolagents import tool

def _run_transfer_to_human_agents(summary: str) -> str:
    """
    Internal function to execute transfer_to_human_agents logic.
    """
    return f"Transferring to human agent. Summary: {summary}"


@tool
def transfer_to_human_agents(summary: str) -> str:
    """
    Transfer the customer to a human agent with a summary of the interaction.
    
    Args:
        summary: Summary of the customer's issue and conversation so far
    
    Returns:
        Confirmation message.
    """
    try:
        result = _run_transfer_to_human_agents(summary)
        return result
    except Exception as e:
        return f"Error executing transfer_to_human_agents: {str(e)}"
