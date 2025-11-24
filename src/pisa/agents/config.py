"""
PISA Agents Configuration
Inlcude the configuration for the agents, Basic information and log , tool registry and more.
"""

class PISACfg:
    """
    PISA Agents Configuration
    """
    def __init__(self):
        self.config = {
            "agents": {
                "AgentConfig": {
                    "name": "Agent Configuration",
                    "description": "A deep research agent that can perform deep research on a given topic.",
                }
            }
        }

    def get_agent_config(self, agent_name: str):
        """
        Get the configuration for a given agent
        """
        return self.config[agent_name]
