import json
import requests
from googleapiclient.discovery import build

# --- Configuration ---
YOUTUBE_API_KEY = "AIzaSyC6NZIqjevKieGLpiG5LWtLqipW-ZWAcow"  # Keep your key here
OLLAMA_URL = "http://localhost:11434/api/generate"

def get_youtube_links(ingredients):
    """Searches YouTube and returns up to 3 relevant cooking videos."""
    print(f"Agent: Searching YouTube for {ingredients}...")
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        query = f"{' '.join(ingredients)} cooking recipe"
        
        request = youtube.search().list(
            q=query,
            part='snippet',
            maxResults=3, # Changed to fetch 3 videos
            type='video'
        )
        response = request.execute()
        
        videos = []
        for item in response.get('items', []):
            videos.append({
                "title": item['snippet']['title'], 
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
        return videos
    except Exception as e:
        print(f"YouTube API Error: {e}")
    return []

def generate_recipe_with_llama(ingredients):
    """Uses local Llama-3 to generate a zero-waste recipe."""
    print("Agent: Brainstorming recipe with Llama-3...")
    prompt = f"""
    You are a Personal Culinary Agent for the Gro-Sential app. 
    The user has the following ingredients that are expiring soon: {', '.join(ingredients)}.
    Create a quick, creative recipe using ONLY these ingredients and basic pantry staples (salt, pepper, oil).
    Format the output with a Title, Prep Time, and 3 simple steps.
    """
    
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        if response.status_code == 200:
            return response.json()['response']
    except Exception as e:
        print(f"Ollama Error: {e}")
    return "Error generating recipe. Ensure Ollama is running."

def run_grosential_agent(ingredients):
    """The Main Orchestrator Function"""
    print(f"\n--- Gro-Sential Agent Initiated ---")
    
    video_data = get_youtube_links(ingredients) # Now fetches multiple
    recipe_text = generate_recipe_with_llama(ingredients)
    
    dashboard_data = {
        "ingredients_used": ingredients,
        "recipe": recipe_text,
        "videos": video_data # Note: Changed key to 'videos' (plural)
    }
    
    print("\n--- Unified Action Screen Data ---")
    return dashboard_data

if __name__ == "__main__":
    expiring_items = ["bell pepper", "corn", "potatoes"]
    run_grosential_agent(expiring_items)