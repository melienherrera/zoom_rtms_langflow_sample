# External Dependencies
from langchain_anthropic import ChatAnthropic  # Claude 3 integration
from langchain.prompts import ChatPromptTemplate  # For structuring prompts
from collections import deque  # For maintaining a fixed-size transcript history
import os
from dotenv import load_dotenv

# Load API key from environment
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Initialize LangChain components using LCEL (LangChain Expression Language)
# Claude 3 Sonnet is used with temperature=0 for consistent, deterministic outputs
llm = ChatAnthropic(model="claude-3-7-sonnet-20250219", temperature=0)

# Define the prompt template for action item extraction
# The template takes a transcript chunk and asks Claude to identify action items
prompt = ChatPromptTemplate.from_template("""
From the following meeting transcript snippet, extract all explicit or implicit action items.
Be concise. List each item as a bullet point. Include assignees if mentioned.

Transcript:
{transcript_chunk}

Action Items:
""")

# Create a processing chain using LCEL pipe operator
# This combines the prompt template with the LLM for streamlined processing
action_item_chain = prompt | llm

class TranscriptProcessor:
    """
    Processes real-time meeting transcripts to extract action items.
    Maintains a rolling window of recent transcript chunks for context
    and tracks unique action items found during the meeting.
    """
    
    def __init__(self):
        """
        Initialize the processor with:
        - recent_chunks: Rolling window of last 10 transcript segments
        - action_items: List of unique action items found so far
        """
        self.recent_chunks = deque(maxlen=10)  # Keep last 10 chunks for context
        self.action_items = []  # Store unique action items

    def extract_action_items(self, transcript_chunk: str) -> str:
        """
        Process a transcript chunk through Claude to identify action items.
        
        Args:
            transcript_chunk (str): Text segment from the meeting transcript
            
        Returns:
            str: Extracted action items as bullet points
            
        Note: Uses error handling to ensure robustness during live processing
        """
        try:
            result = action_item_chain.invoke({"transcript_chunk": transcript_chunk})
            return result.content
        except Exception as e:
            print(f"Error extracting action items: {e}")
            return ""

    def process_new_transcript_chunk(self, chunk: str):
        """
        Handle incoming transcript chunks in real-time.
        
        This method:
        1. Logs the new chunk
        2. Adds it to the rolling context window
        3. Processes the merged recent context
        4. Identifies and stores new unique action items
        
        Args:
            chunk (str): New transcript segment from the Zoom RTMS
            
        Note: Maintains uniqueness of action items to avoid duplicates
        """
        print("New Transcript Chunk Received:\n", chunk.strip())
        
        # Add new chunk to rolling context window
        self.recent_chunks.append(chunk)
        
        # Merge recent chunks for better context
        merged_text = " ".join(self.recent_chunks)
        
        try:
            # Extract action items from merged context
            new_items_raw = self.extract_action_items(merged_text)
            
            # Split into individual items and clean up
            new_items = [line.strip() for line in new_items_raw.split("\n") if line.strip()]
            
            # Add only unique items to the master list
            for item in new_items:
                if item not in self.action_items:
                    self.action_items.append(item)
                    print("New Action Item:", item)
        except Exception as e:
            print("LangChain processing error:", e) 