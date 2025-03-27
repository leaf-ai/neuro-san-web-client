
# Copyright (C) 2023-2025 Cognizant Digital Business, Evolutionary AI.
# All Rights Reserved.
# Issued under the Academic Public License.
#
# You can be released from the terms, and requirements of the Academic Public
# License by purchasing a commercial license.
# Purchase of a commercial license is mandatory for any use of the
# neuro-san SDK Software in commercial settings.
#
# END COPYRIGHT

from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

from flask_socketio import SocketIO

from neuro_san.internals.messages.chat_message_type import ChatMessageType
from neuro_san.message_processing.message_processor import MessageProcessor


class AgentLogProcessor(MessageProcessor):
    """
    Tells the UI there's an agent message to process.
    """

    def __init__(self, socketio: SocketIO, sid: str):
        """
        Constructor
        """
        self.socketio: SocketIO = socketio
        self.sid: str = sid

    def process_message(self, chat_message_dict: Dict[str, Any], message_type: ChatMessageType):
        """
        Process the message:
          - Log the message
          - Highlight the agent in the network diagram
          - Display the message in the Agents Communication panel
        :param chat_message_dict: The chat message
        :param message_type: The type of message
        """
        if message_type in [ChatMessageType.AGENT_FRAMEWORK,
                            ChatMessageType.SYSTEM,
                            ChatMessageType.AI,
                            ChatMessageType.AGENT_TOOL_RESULT]:
            # This is a framework message that contains the chat context, system prompts or consolidated messages.
            # Don't log them. And there's no agent to highlight in the network diagram.
            return

        # Discard empty messages
        log_text = chat_message_dict.get("text", "").strip()
        if log_text == "":
            return

        # We have a valid message. Process it.
        # Get the list of agents that participated in the message and the name of the last agent,
        # which is the one that sent the message.
        origin_chain, last_agent_name = self.get_origin(chat_message_dict, message_type)

        header = "---------- ChatMessage ----------"
        log_message = f"{header}\n{origin_chain}: {log_text}"
        # Log the message
        print(log_message)
        # Highlight the last agent name in the network diagram
        # and display the log message in the Agents Communication panel
        self.display_message_in_ui(last_agent_name, log_message)

    def get_origin(self, chat_message_dict, message_type) -> Tuple[str, str]:
        """
        Get the list of agents that lead to this message and the agent that produced it.
        :param chat_message_dict: The chat message
        :param message_type: The type of message
        :return: A tuple containing:
        - the list of agents involved, as a string,
        - the name of the agent that produced the message
        """
        last_agent_name = None
        if message_type == ChatMessageType.HUMAN:
            origin = chat_message_dict.get("origin")
            if len(origin) == 1:
                # Request comes from the human directly
                origin_chain = "HUMAN"
            else:
                origin_chain = self.process_origin(origin)
                # the agent name is the last tool in the origin list
                last_agent_name = origin[-1].get("tool")
        else:
            # This message is coming from an agent: get the agent name
            origin = chat_message_dict.get("origin")
            origin_chain = self.process_origin(origin)
            # the agent name is the last tool in the origin list
            last_agent_name = origin[-1].get("tool")
        return origin_chain, last_agent_name

    @staticmethod
    def process_origin(origin: List) -> str:
        """
        Convert the 'origin' list, that contains the name of the agents that lead to this message, into a string
        """
        if origin is None or len(origin) == 0:
            return ""
        # Extract tool names in order
        sequence = " -> ".join(tool['tool'] for tool in origin)
        return sequence

    def display_message_in_ui(self, agent_name: str, message_log: str) -> None:
        """
        Displays the agent message in the UI
        Sends the agent name and its log to the UI to:
         - Highlight the agent node in the network diagram
         - Display the agent log in the Agents Communication panel

        """
        log_dict = {
            "agent_name": agent_name,
            "log": message_log
        }
        self.socketio.emit('agent_log', log_dict, room=self.sid)
        # Allow the event loop to process and send WebSocket messages before continuing execution.
        self.socketio.sleep(0)
