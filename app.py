from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import anthropic
import json
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)

class TinderTripPlanner:
    def __init__(self):
        self.client = client
    
    def generate_swipe_cards(self, user_prompt):
        """Generate categories and examples for Tinder-style trip planning in one call"""
        
        try:
            # Create comprehensive prompt for category inference and example generation
            prompt = f"""You are helping build a Tinder-like app for trip planning. 

User query: "{user_prompt}"

Your task is to:
1. Infer relevant travel categories from the query
2. Generate exactly 4 high-quality, concrete examples for each category
3. Return everything in one structured JSON response

REQUIRED CATEGORIES (always include):
- Accommodations
- Activities  
- Dining

ADDITIONAL CATEGORIES (select 0 or more based on the query context):
Choose from: Transportation, Neighborhoods, Nightlife, Shopping, Cultural Experiences, Outdoor Adventures, Relaxation, Entertainment, Local Markets, Wellness, Photography Spots, Family Activities, Budget Options, Luxury Experiences

For each category, generate exactly 4 realistic, specific examples that are:
- Concrete and tied to the destination
- Diverse in style, price, and appeal
- Short but informative (like swipe card previews)
- Include rich metadata for preference learning

Return this exact JSON structure:
{{
  "categories": [
    {{
      "name": "Accommodations",
      "type": "accommodations",
      "description": "Places to stay",
      "examples": [
        {{
          "id": 1,
          "name": "Specific Hotel/Hostel/Airbnb Name",
          "description": "Brief, engaging description (1-2 sentences max)",
          "image_url": null,
          "metadata": {{
            "style": "Luxury/Budget/Boutique/Historic/Modern/etc",
            "price_range": "$/$$/$$$/$$$$",
            "rating": 4.2,
            "location": "Neighborhood/Area",
            "amenities": ["wifi", "pool", "gym"],
            "target_audience": "couples/families/solo/business"
          }}
        }},
        // ... exactly 3 more examples
      ]
    }},
    {{
      "name": "Dining",
      "type": "dining", 
      "description": "Restaurant and food options",
      "examples": [
        {{
          "id": 5,
          "name": "Specific Restaurant Name",
          "description": "Brief description highlighting cuisine and atmosphere",
          "image_url": null,
          "metadata": {{
            "cuisine": "Italian/Thai/Local/etc",
            "price_range": "$/$$/$$$/$$$$", 
            "rating": 4.5,
            "location": "Neighborhood",
            "atmosphere": "casual/fine dining/romantic/family-friendly",
            "specialties": ["pasta", "seafood"]
          }}
        }},
        // ... exactly 3 more examples
      ]
    }},
    {{
      "name": "Activities",
      "type": "activities",
      "description": "Things to do and experiences", 
      "examples": [
        {{
          "id": 9,
          "name": "Specific Activity/Tour/Attraction Name",
          "description": "What makes this activity special and appealing",
          "image_url": null,
          "metadata": {{
            "type": "sightseeing/adventure/cultural/relaxation",
            "duration": "2 hours/half day/full day",
            "price_range": "$/$$/$$$/$$$$",
            "difficulty": "easy/moderate/challenging",
            "location": "Area/Neighborhood",
            "best_time": "morning/afternoon/evening/anytime"
          }}
        }},
        // ... exactly 3 more examples  
      ]
    }}
    // ... additional categories as relevant to the query
  ]
}}

Make examples realistic and specific to the destination. Vary the examples significantly within each category to help users discover their preferences through swiping."""

            # Make API call using model knowledge only
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            content = response.content[0].text.strip()
            print(f"DEBUG: Full API Response: {content}")  # Show full response for debugging
            
            # Check if response looks like HTML (error page)
            if content.startswith('<!') or content.startswith('<html'):
                return {
                    'success': False,
                    'error': 'API returned an error page. Please check your API key and try again.'
                }
            
            result_data = self._parse_json_response(content)
            print(f"DEBUG: Parsed result_data: {result_data}")
            
            if not result_data:
                return {
                    'success': False,
                    'error': 'Failed to parse JSON response.',
                    'debug_content': content[:1000]  # Show more content for debugging
                }
            
            if 'categories' not in result_data:
                return {
                    'success': False,
                    'error': 'No categories found in response.',
                    'debug_content': content[:1000],
                    'parsed_data': result_data
                }
            
            # Validate each category has exactly 4 examples
            categories = result_data['categories']
            for category in categories:
                if 'examples' not in category or len(category['examples']) != 4:
                    return {
                        'success': False,
                        'error': f'Invalid number of examples for {category.get("name", "category")}. Expected 4.'
                    }
                
                # Add sequential IDs if missing
                for i, example in enumerate(category['examples']):
                    if 'id' not in example:
                        example['id'] = i + 1
            
            return {
                'success': True,
                'categories': categories,
                'total_examples': sum(len(cat['examples']) for cat in categories),
                'web_search_enabled': False
            }
            
        except Exception as e:
            print(f"Error generating swipe cards: {e}")
            return {
                'success': False,
                'error': f'Failed to generate recommendations: {str(e)}'
            }
    
    def _parse_json_response(self, content):
        """Parse JSON from API response with multiple fallback methods"""
        # Method 1: Direct JSON parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Method 2: Extract from code blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Method 3: Find JSON object in text
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return None

# Initialize the trip planner
trip_planner = TinderTripPlanner()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_cards', methods=['POST'])
def generate_cards():
    """Generate swipe cards for trip planning"""
    try:
        data = request.get_json()
        user_prompt = data.get('prompt', '')
        
        if not user_prompt:
            return jsonify({'error': 'Please provide a travel prompt'}), 400
        
        # Generate swipe cards using AI
        result = trip_planner.generate_swipe_cards(user_prompt)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR in generate_cards: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Keep the old endpoint for backward compatibility
@app.route('/generate_itinerary', methods=['POST'])
def generate_itinerary():
    """Legacy endpoint - redirects to generate_cards"""
    return generate_cards()

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'Tinder Trip Planner'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
