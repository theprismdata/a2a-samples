import mesop as me


from dataclasses import field

@me.stateclass
class AgentState:
    """Agents List State"""

    agent_dialog_open: bool = False
    agent_address: str = ''
    agent_name: str = ''
    agent_description: str = ''
    input_modes: list[str] = field(default_factory=list)
    output_modes: list[str] = field(default_factory=list)
    stream_supported: bool = False
    push_notifications_supported: bool = False
    error: str = ''
    agent_framework_type: str = ''
    # cached agents for the page
    agents: list = field(default_factory=list)
    agents_loaded: bool = False
