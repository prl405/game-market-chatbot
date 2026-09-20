"""
Chat agent package — OpenRouter LLM integration with tool dispatch.

The public surface is `chat()` and `AgentResponse` from
`game_market_chatbot.agent.chat`.
"""

from game_market_chatbot.agent.chat import AgentResponse, chat

__all__ = ["AgentResponse", "chat"]
