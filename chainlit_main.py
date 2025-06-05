from typing import Dict, Optional
from chat_application import ChatApplication
from langchain_core.messages import HumanMessage
from langchain.schema.runnable.config import RunnableConfig

import chainlit as cl

@cl.oauth_callback
def oauth_callback(
  provider_id: str,
  token: str,
  raw_user_data: Dict[str, str],
  default_user: cl.User,
) -> Optional[cl.User]:
  return default_user

@cl.on_chat_start
async def start():
    chat_application = ChatApplication()
    chat_application.initialize_chat_agent()

@cl.on_message
async def on_message(message: cl.Message):
    agent_graph = cl.user_session.get("agent_graph")
    config = {"configurable": {"thread_id": cl.context.session.id}}
    cb = cl.LangchainCallbackHandler()
    final_answer = cl.Message(content="")
    
    for msg, metadata in agent_graph.run([HumanMessage(content=message.content)], stream=True, config=RunnableConfig(callbacks=[cb], **config)):
        if (
            msg.content
            and not isinstance(msg, HumanMessage)
            and metadata["langgraph_node"] == "final"
        ):
            await final_answer.stream_token(msg.content)

    await final_answer.send()