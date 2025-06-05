# Implement tool to get the user's encrypted data -> then decryp the data
# Implement tool to submit the user's data to the server for passport renewal process

import chainlit as cl

from agent_graph import AgentGraph

class ChatApplication:
    def initialize_chat_agent(self):
        # 1. Get the biscuit token from the user session
        user = cl.user_session.get("user")
        user_data = user.metadata["user_data"]
        biscuit_token = user_data["biscuit_token"]
        print("Biscuit token: ", biscuit_token)

        # 2. Build the agent graph using langgraph
        agent_graph = AgentGraph(biscuit_token)

        # 4. Put the graph to the user session
        cl.user_session.set("agent_graph", agent_graph)