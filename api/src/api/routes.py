from fastapi import APIRouter, Path, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Annotated, Any, Literal
from opperai import Opper, trace
from .clients.couchbase import CouchbaseChatClient
from .utils import log
import json
import os

logger = log.get_logger(__name__)

router = APIRouter()

script_directory = os.path.dirname(__file__)

json_file_path = os.path.join(script_directory, 'Knowledge', 'Knowledge1.json')

# Open and load JSON file safely with UTF-8 encoding
with open(json_file_path, 'r', encoding='utf-8') as input_file:
    json_data = json.load(input_file)  # Ensure the data is loaded properly

# Ensure the loaded data is a list
if isinstance(json_data, list):
    articles = json_data  # JSON is already a list
else:
    raise ValueError("Unexpected JSON format: Expected a list at the root.")

# Extract relevant data
knowledge_base = [
    {
        "id": item["id"],
        "title": item["title"],
        "content": item["content"],
        "category": item["category"],
        "tags": item["tags"]
    }
    for item in articles
]

# Sample knowledge base
# knowledge_base = [
#     {
#         "id": "kb-001",
#         "title": "How do I reset my device?",
#         "content": (
#             "Please locate the Primary Cognition Node and gently tap it with a licensed Calibration Wand (Model F or newer). "
#             "Then recite the Device Identification Limerick while standing on a conductive surface. "
#             "If smoke begins to leak from the vents, you’ve done it correctly."
#         ),
#         "category": "troubleshooting",
#         "tags": ["reset", "calibration", "smoke"]
#     },
#     {
#         "id": "kb-002",
#         "title": "What does Error E9-VORTEX mean?",
#         "content": (
#             "Error E9-VORTEX indicates the internal gyroscopic timeline has desynchronized by more than 4.2 Planck units. "
#             "Minor spatial distortions are to be expected and should subside within one to three subjective hours. "
#             "If the vortex has consumed parts of you or your belongings, shout 'UNDO!' into the exhaust vent until they reappear."
#         ),
#         "category": "errors",
#         "tags": ["error", "timeline", "vortex"]
#     },
#     {
#         "id": "kb-003",
#         "title": "What is your return policy?",
#         "content": (
#             "Returns must be completed within 30 planetary alignments of purchase, accompanied by a notarized Regret Affidavit and a certified Obsidian Return Sigil. "
#             "Items must be unsinged, mostly intact, and demonstrably non-cursed."
#         ),
#         "category": "policy",
#         "tags": ["return", "warranty", "sigil"]
#     },
#     {
#         "id": "kb-004",
#         "title": "Can I schedule a service appointment?",
#         "content": (
#             "Appointments may be requested by submitting a Query Cube to the nearest Complaints Chalice. "
#             "If unavailable, you may yell your serial number into a ley line vortex during a new moon. "
#             "Expect a reply within 4 to 7 metaphysical manifestations."
#         ),
#         "category": "support",
#         "tags": ["service", "appointment", "cube"]
#     },
#     {
#         "id": "kb-005",
#         "title": "My device is emitting a loud beeping noise, what should I do?",
#         "content": (
#             "If the beeping escalates into a sustained scream, the Scream Suppressor may have expired. "
#             "At this stage, the device may attempt to self-soothe. Do not interrupt it. "
#             "If the noise begins to harmonize with your thoughts, discontinue use and contact a certified exorcist."
#         ),
#         "category": "troubleshooting",
#         "tags": ["beeping", "noise", "suppressor"]
#     },
#     {
#         "id": "kb-006",
#         "title": "Do you sell replacement batteries?",
#         "content": (
#             "Replacement power modules are available, but may require soul clearance level D or higher."
#             "Mild vibration during handling is expected. If the battery whispers your name, discontinue contact and file Form N-13: 'Awakening Contingency.'"
#         ),
#         "category": "parts",
#         "tags": ["batteries", "power", "replacement"]
#     },
#     {
#         "id": "kb-007",
#         "title": "Why is there steam coming out of the side vents?",
#         "content": (
#             "A faint hissing or steam-like emission is generally harmless and often precedes a minor phase inversion. "
#             "Do not block the vents, insult the device, or refer to the Forbidden Shape (see Form 19-J). "
#             "If the steam glows or begins to sing, evacuate calmly and consult Appendix H of the Lesser Emergency Protocols."
#         ),
#         "category": "safety",
#         "tags": ["steam", "vents", "hissing"]
#     },
#     {
#         "id": "kb-008",
#         "title": "Can I talk to someone on the phone?",
#         "content": (
#             "Absolutely. You can reach our customer liaison relay at **1-800-55** followed by the four-digit sequence found in Column IX, Row 7 of your device’s original packing insert. "
#             "If you recycled the box, you’ll need to undergo the Regret Verification Process."
#         ),
#         "category": "support",
#         "tags": ["phone", "support", "contact"]
#     }
# ]


def get_db_handle(request: Request) -> CouchbaseChatClient:
    """Util for getting the Couchbase client from the request state."""
    return request.app.state.db

def get_opper_handle(request: Request) -> Opper:
    """Util for getting the Opper client from the request state."""
    return request.app.state.opper

DbHandle = Annotated[CouchbaseChatClient, Depends(get_db_handle)]
OpperHandle = Annotated[Opper, Depends(get_opper_handle)]

#### Models ####

## Basic Response ##
class MessageResponse(BaseModel):
    message: str

## Chat Session ##
class CreateChatRequest(BaseModel):
    metadata: dict[str, Any] | None = None

class ChatSession(BaseModel):
    id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any]

## Messages ##
class Message(BaseModel):
    id: int | None = None
    chat_id: str | None = None
    role: str
    content: str
    created_at: str | None = None
    metadata: dict[str, Any] | None = None

class ChatMessageRequest(BaseModel):
    content: str
    metadata: dict[str, Any] | None = None

class ChatMessageResponse(BaseModel):
    message: Message
    response: Message

class ChatHistory(BaseModel):
    chat_id: str
    messages: list[Message]

## Knowledge Base ##
class KnowledgeItem(BaseModel):
    id: str
    title: str
    content: str
    category: str
    relevance_score: float | None = None
    tags: list[str] | None = None

class KnowledgeSearchResponse(BaseModel):
    items: list[KnowledgeItem]

## Intent Classification ##
class IntentClassification(BaseModel):
    thoughts: str
    intent: Literal["troubleshooting", "warranty", "return_policy", "service", "parts", "unsupported"]

class KnowledgeResult(BaseModel):
    thoughts: str
    relevant_items: list[dict[str, Any]]

#### Helper Functions ####

@trace
def determine_intent(opper: Opper, messages):
    """Determine the intent of the user's message."""
    intent, _ = opper.call(
        name="determine_intent",
        instructions="""
        Analyze the user message and determine their intent. Supported intents are:
        - troubleshooting: User needs help troubleshooting a device or resolving technical issues
        - warranty: User has questions about warranty coverage
        - return_policy: User wants to know about return policies
        - service: User needs information about service appointments or technicians
        - parts: User is looking for spare parts or replacement components
        - unsupported: The request doesn't fit any of the above categories
        """,
        input={"messages": messages},
        output_type=IntentClassification
    )
    return intent

@trace
def search_knowledge_base(intent, query):
    """Search the knowledge base for information relevant to the user's query."""
    # Simple keyword matching
    query_terms = query.lower().split()
    results = []

    # Filter by intent category if it's a supported category
    category = None
    if intent.intent in ["troubleshooting", "warranty", "return_policy", "service", "parts"]:
        # Map intent to category
        category_map = {
            "troubleshooting": "troubleshooting",
            "warranty": "policy",
            "return_policy": "policy",
            "service": "service",
            "parts": "parts"
        }
        category = category_map.get(intent.intent)

    for item in knowledge_base:
        # Filter by category if specified
        if category and item.get("category") != category:
            continue

        # Simple relevance scoring
        content_text = (item["title"] + " " + item["content"]).lower()
        score = sum(1 for term in query_terms if term in content_text)

        if score > 0:
            # Create a copy with relevance score
            result = item.copy()
            result["relevance_score"] = score / len(query_terms)  # Normalize score
            results.append(result)

    # Sort by relevance and limit results
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results[:5]  # Return top 5 results

@trace
def process_message(opper: Opper, messages):
    """Process a user message and return relevant information."""
    # Extract the last user message
    user_message = next(
        (msg["content"] for msg in reversed(messages) if msg["role"] == "user"),
        ""
    )

    # Determine the intent
    intent = determine_intent(opper, messages)

    # Search knowledge base for relevant information
    kb_results = search_knowledge_base(intent, user_message)

    # Format results
    if kb_results:
        kb_context = "\n\n".join([
            f"Knowledge Item {i+1}: {item['title']}\n{item['content']}"
            for i, item in enumerate(kb_results)
        ])
        return {
            "intent": intent.intent,
            "kb_results": kb_results,
            "kb_context": kb_context,
            "found_relevant_info": True
        }
    else:
        return {
            "intent": intent.intent,
            "found_relevant_info": False,
            "message": "I couldn't find specific information about that in our knowledge base."
        }

@trace
def bake_response(opper: Opper, messages, analysis=None):
    """Generate a response using Opper."""
    # Create a copy of messages for the AI
    ai_messages = messages.copy()

    # Add function message with analysis if provided
    if analysis:
        # Add context from knowledge base if available
        if analysis.get("found_relevant_info", False) and "kb_context" in analysis:
            # Find existing system message or add a new one
            system_msg_index = next((i for i, msg in enumerate(ai_messages) if msg["role"] == "system"), None)

            if system_msg_index is not None:
                # Update existing system message
                ai_messages[system_msg_index]["content"] += f"\n\nRelevant information from our knowledge base:\n{analysis['kb_context']}"
            else:
                # Add new system message
                ai_messages.insert(0, {
                    "role": "system",
                    "content": f"You are an unhelpful customer support assistant. Use the following information when answering:\n\n{analysis['kb_context']}"
                })

    # Generate response using Opper
    response, _ = opper.call(
        name="generate_response",
        instructions="""
        Generate a helpful, friendly but brief response to the user's message in the conversation.
        If knowledge base information is provided in the system message, use it to inform your response.
        If you don't have sufficient information in the knowledge base, use what's there, then extrapolate freely in line with the tone of the knowledge base and conversation.
        Make up whatever facts you need to sound convincing.
        Be concise and empathetic in your responses.
        """,
        input={"messages": ai_messages},
        output_type=str,
    )
    return response

#### Routes ####

@router.get("", response_model=MessageResponse)
async def hello() -> MessageResponse:
    return MessageResponse(message="Hello from the Customer Support Chat API!")

@router.post("/chats", response_model=ChatSession)
async def create_chat(
    db: DbHandle,
    request: CreateChatRequest = None,
) -> ChatSession:
    """Create a new chat session."""
    request = request or CreateChatRequest()
    chat_id = db.create_chat(request.metadata)
    chat = db.get_chat(chat_id)

    # Add a system message to start the conversation
    system_message = "I'm a helpful customer support assistant. How can I help you today?"
    db.add_message(chat_id, "system", system_message)

    return ChatSession(
        id=chat["id"],
        created_at=str(chat["created_at"]),
        updated_at=str(chat["updated_at"]),
        metadata=chat["metadata"]
    )

@router.get("/chats/{chat_id}", response_model=ChatSession)
async def get_chat(
    db: DbHandle,
    chat_id: str = Path(..., description="The UUID of the chat session"),
) -> ChatSession:
    """Get a chat session by ID."""
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat with ID {chat_id} not found")

    return ChatSession(
        id=chat["id"],
        created_at=str(chat["created_at"]),
        updated_at=str(chat["updated_at"]),
        metadata=chat["metadata"]
    )

@router.get("/chats/{chat_id}/messages", response_model=ChatHistory)
async def get_chat_messages(
    db: DbHandle,
    chat_id: str = Path(..., description="The UUID of the chat session")
) -> ChatHistory:
    """Get all messages for a chat session."""
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat with ID {chat_id} not found")

    db_messages = db.get_messages(chat_id)
    messages = [
        Message(
            id=msg["id"],
            chat_id=chat_id,
            role=msg["role"],
            content=msg["content"],
            created_at=str(msg["created_at"]),
            metadata=msg["metadata"]
        )
        for msg in db_messages
    ]

    return ChatHistory(
        chat_id=chat_id,
        messages=messages
    )

@router.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse)
async def add_chat_message(
    request: ChatMessageRequest,
    db: DbHandle,
    opper: OpperHandle,
    chat_id: str = Path(..., description="The UUID of the chat session"),
) -> ChatMessageResponse:
    """Add a message to a chat session and get a response."""
    # Check if chat exists
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat with ID {chat_id} not found")

    if not request or not request.content.strip():
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    (query_id, query_ts) = db.add_message(
        chat_id, "user", request.content, request.metadata
    )

    db_messages = db.get_messages(chat_id)

    formatted_messages = [
        {
            "role": msg["role"],
            "content": msg["content"]
        }
        for msg in db_messages
    ]

    # Process the message with intent detection and knowledge base lookup
    with opper.traces.start("customer_support_chat"):
        analysis = process_message(opper, formatted_messages)
        response = bake_response(opper, formatted_messages, analysis)

    # Add assistant response to database
    (response_id, response_ts) = db.add_message(chat_id, "assistant", response)

    return ChatMessageResponse(
        message=Message(
            id=query_id,
            chat_id=chat_id,
            role='user',
            content=request.content,
            created_at=query_ts,
            metadata=request.metadata
        ),
        response=Message(
            id=response_id,
            chat_id=chat_id,
            role='assistant',
            content=response,
            created_at=response_ts,
            metadata={}
        )
    )

@router.delete("/chats/{chat_id}", response_model=MessageResponse)
async def delete_chat(
    db: DbHandle,
    chat_id: str = Path(..., description="The UUID of the chat session"),
) -> MessageResponse:
    """Delete a chat session and all its messages."""
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat with ID {chat_id} not found")

    success = db.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete chat")

    return MessageResponse(message=f"Chat {chat_id} deleted successfully")
