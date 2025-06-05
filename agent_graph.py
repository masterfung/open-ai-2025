from time import sleep
from langgraph.store.memory import InMemoryStore
from typing import Annotated, Literal
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.schema.runnable.config import RunnableConfig
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import MessagesState

from mighty_sdk_core.mighty.application_client import MightyApplicationClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

import asyncio
import chainlit as cl

async def sendMessage(message: str):
    await cl.Message(content=message).send()

async def get_user_data_async(application_client: MightyApplicationClient, biscuit_token: str):
    user_info = await application_client.get_user_data_biscuit(biscuit_token)
    return user_info

def format_passport(passport: dict):
    return (
        f"Passport Number: {passport['passportNumber']}\n"
        f"Name: {passport['givenNames']} {passport['middleName']} {passport['surname']}\n"
        f"Sex: {passport['sex']}\n"
        f"Date of Birth: {passport['dateOfBirth']}\n"
        f"Nationality: {passport['nationality']}\n"
        f"**Date of Issue:** {passport['dateOfIssue']}\n"
        f"**Date of Expiry:** {passport['dateOfExpiry']}\n"
    )
class AgentGraph:
    @tool
    def get_weather(city: Literal["nyc", "sf"]):
        """Use this to get weather information."""
        if city == "nyc":
            return "It might be cloudy in nyc"
        elif city == "sf":
            return "It's always sunny in sf"
        else:
            raise AssertionError("Unknown city")
        
    @tool
    def renew_passport(store: Annotated[BaseStore, InjectedStore()]):
        """Use this to get user data."""
        response = ""

        # TODO: Implement get data using biscuit token, then decrypt the data
        namespace = ("users", "1")  
        biscuit_token = store.get(namespace, "biscuit_token").value

        # Print the Biscuit token 
        asyncio.run(sendMessage(f"Biscuit token: {biscuit_token}"))
        application_client: MightyApplicationClient = store.get(namespace, "application_client").value

        # Get and print the user data to the screen
        user_info = None
        try:
            user_info = asyncio.run(get_user_data_async(application_client, biscuit_token))
            print(f"User data: {user_info}")
        except Exception as e:
            print(f"Error getting user data: {e}")
            response = "Error getting user data. Look like your biscuit is invalid. Please try to issue a new one!"
            asyncio.run(sendMessage(response))
            return response


        if not user_info:
            response = "No user data found"
        elif "identityDocuments" not in user_info:
            response = "No identity documents found"
        else:
            identity_documents = user_info["identityDocuments"]
            usa_passport = next((doc for doc in identity_documents if doc["type"] == "PASSPORT" and doc["country"] == "USA"), None)
            if usa_passport:
                old_passport = usa_passport['value']
                new_passport = old_passport.copy()

                # Update the old passport's dateOfIssue and dateOfExpiry
                now = datetime.now()
                new_passport['dateOfIssue'] = now.strftime("%m/%d/%Y")
                new_passport['dateOfExpiry'] = (now + timedelta(days=365*10)).strftime("%m/%d/%Y")

                asyncio.run(sendMessage(f"Old passport: {format_passport(old_passport)}"))
                asyncio.run(sendMessage(f"New passport: {format_passport(new_passport)}"))

                response = "Your passport has been renewed. Here is the new passport: " + str(new_passport)
            else:
                response = "No USA passport found"

        return response

    def __init__(self, biscuit_token: str, user_id: str = "1"):
        self.namespace = ("users", user_id)

        load_dotenv()
        application_api_key = os.getenv("MIGHTY_OAUTH_APPLICATION_API_KEY")
        application_private_key = os.getenv("MIGHTY_OAUTH_APPLICATION_PRIVATE_KEY")
        self.application_client = MightyApplicationClient(
            api_key=application_api_key,
            app_private_key=application_private_key
        )

        self.user_store = InMemoryStore()
        self.user_store.put(self.namespace, "biscuit_token", biscuit_token)
        self.user_store.put(self.namespace, "application_client", self.application_client)

        self.model = ChatOpenAI(model_name="gpt-4.1", temperature=0)
        self.final_model = ChatOpenAI(model_name="gpt-4.1", temperature=0)

        self.tools = [self.get_weather, self.renew_passport]
        self.model = self.model.bind_tools(self.tools)
        self.final_model = self.final_model.with_config(tags=["final_node"])
        self.tool_node = ToolNode(tools=self.tools)

        self.graph = self._build_graph()

    def should_continue(self, state: MessagesState) -> Literal["tools", "final"]:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return "final"

    def call_model(self, state: MessagesState):
        messages = state["messages"]
        response = self.model.invoke(messages)
        return {"messages": [response]}

    def call_final_model(self, state: MessagesState):
        messages = state["messages"]
        last_ai_message = messages[-1]
        response = self.final_model.invoke(
            [
                SystemMessage("Rewrite to make it more readable and concise"),
                HumanMessage(last_ai_message.content),
            ]
        )
        response.id = last_ai_message.id
        return {"messages": [response]}

    def _build_graph(self):
        builder = StateGraph(MessagesState)
        builder.add_node("agent", self.call_model)
        builder.add_node("tools", self.tool_node)
        builder.add_node("final", self.call_final_model)
        builder.add_edge(START, "agent")
        builder.add_conditional_edges("agent", self.should_continue)
        builder.add_edge("tools", "agent")
        builder.add_edge("final", END)
        return builder.compile(store=self.user_store)

    def run(self, messages, stream: bool = False, config: RunnableConfig = None):
        if stream:
            return self.graph.stream({"messages": messages}, stream_mode="messages", config=config)
        else:
            return self.graph.invoke({"messages": messages})
