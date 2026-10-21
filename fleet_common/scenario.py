"""The story the three agents play out. Every framework uses the same text."""

PRICING_NOTES_V1 = (
    "Pricing API notes (v1 docs, September):\n"
    "- The pricing API allows 100 requests per minute per key.\n"
    "- The pricing API caches responses for 5 minutes at the edge.\n"
    "- The pricing API free tier includes 10,000 calls per month."
)

CHANGELOG_V2 = (
    "Changelog (October):\n"
    "- The pricing API rate limit is now 60 requests per minute per key.\n"
    "- Cache duration and the free tier are unchanged."
)

# Role prompts. Each one names only its own role, so the prompts stay easy to swap between frameworks.
ROLE_PROMPTS = {
    "researcher": (
        "You are the Researcher on a product launch team. Your team shares one memory. "
        "To save a fact, call caura_write with the fact as `content`, one fact per call. "
        "To answer a question, call caura_recall and answer only from what it returns. "
        "If memory has no answer, say so."
    ),
    "writer": (
        "You are the Writer on a product launch team. Your team shares one memory. "
        "Call caura_recall to find what the team knows, then write only with facts that recall returns. "
        "Never invent numbers."
    ),
    "reviewer": (
        "You are the Reviewer on a product launch team. Your team shares one memory. "
        "Use caura_recall to read it. To retire a wrong memory, call caura_manage with "
        "op='transition', the memory's id as memory_id, and status='outdated'. "
        "To save the corrected fact, call caura_write with the fact as `content`."
    ),
    "editor": (
        "You are the Editor on a product launch team. Your team shares one memory. "
        "The recalled memory is given to you with the request. Write only with facts it contains."
    ),
}

TASKS = {
    "researcher_store": (
        "Store each fact from these notes in team memory, one fact per memory. "
        "Then say how many facts you stored.\n\n" + PRICING_NOTES_V1
    ),
    "writer_draft": (
        "Recall what the team knows about the pricing API and the free tier. "
        "Then write a three-sentence launch note using only those facts."
    ),
    "reviewer_check": (
        "Here is the latest changelog:\n" + CHANGELOG_V2 + "\n\n"
        "Recall what team memory says about the pricing API rate limit. "
        "If memory disagrees with the changelog, mark the outdated memory as outdated and store the "
        "corrected fact. Then reply with what you changed."
    ),
    "researcher_answer": (
        "What is the pricing API rate limit? Answer from team memory only and quote the number."
    ),
    "editor_final": (
        "Write the final one-sentence announcement of the pricing API rate limit."
    ),
}
