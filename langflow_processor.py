# External Dependencies
from collections import deque  # For maintaining a fixed-size transcript history
import os
from dotenv import load_dotenv
import requests

# Load API key from environment
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Langflow API URL
url = os.getenv("LANGFLOW_API_URL")  # The complete API endpoint URL for this flow


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
        # Request payload configuration
        payload = {
            "input_value": transcript_chunk,  # The transcript chunk to be processed by the flow
            "output_type": "chat",  # Specifies the expected output format
            "input_type": "chat"  # Specifies the input format
        }

        # Request headers
        headers = {
            "Content-Type": "application/json"
        }
        try:
            # Send API request to Langflow API
            response = requests.request("POST", url, json=payload, headers=headers)
            response.raise_for_status()  # Raise exception for bad status codes

            # Print response
            print(response.text)

        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
        except ValueError as e:
            print(f"Error parsing response: {e}")
            

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
            print("Langflow processing error:", e) 