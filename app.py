from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import anthropic
import requests
from bs4 import BeautifulSoup
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

class TravelPlannerAI:
    def __init__(self):
        self.client = client
    
    def extract_travel_info(self, user_prompt):
        """Extract structured information from user's natural language prompt"""
        extraction_prompt = f"""
        Analyze this travel request and extract key information in JSON format:
        
        User Request: "{user_prompt}"
        
        Please extract and return ONLY a JSON object with these fields:
        {{
            "destination": "primary destination city/country",
            "duration": "trip duration in days (estimate if not specified)",
            "budget": "budget range (low/medium/high or specific amount if mentioned)",
            "travelers": "number and type of travelers",
            "interests": ["list", "of", "interests", "and", "preferences"],
            "dislikes": ["list", "of", "things", "to", "avoid"],
            "accommodation_type": "preferred accommodation type",
            "travel_style": "travel style (adventure, relaxed, cultural, etc.)"
        }}
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": extraction_prompt}]
            )
            
            # Extract JSON from response
            content = response.content[0].text
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._default_extraction()
                
        except Exception as e:
            print(f"Error extracting travel info: {e}")
            return self._default_extraction()
    
    def _default_extraction(self):
        return {
            "destination": "Unknown",
            "duration": "3-5 days",
            "budget": "medium",
            "travelers": "1-2 people",
            "interests": ["sightseeing", "local culture"],
            "dislikes": [],
            "accommodation_type": "hotel",
            "travel_style": "balanced"
        }
    
    def get_destination_info(self, destination):
        """Fetch real information about the destination"""
        try:
            # Simple web scraping for destination info (in production, use proper APIs)
            search_url = f"https://en.wikipedia.org/wiki/{destination.replace(' ', '_')}"
            response = requests.get(search_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Extract first few paragraphs for context
                paragraphs = soup.find_all('p')[:3]
                info = ' '.join([p.get_text() for p in paragraphs if p.get_text().strip()])
                return info[:1000]  # Limit length
            
        except Exception as e:
            print(f"Error fetching destination info: {e}")
        
        return f"Popular destination known for its attractions and culture."
    
    def parse_itinerary_into_sections(self, itinerary_text):
        """Parse the generated itinerary into discrete sections"""
        sections = []
        current_section = {"title": "", "content": "", "type": "general"}
        
        lines = itinerary_text.split('\n')
        section_id = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section headers (Day X, Activity, Restaurant, etc.)
            if (line.startswith('##') or line.startswith('Day ') or 
                'Restaurant' in line or 'Hotel' in line or 'Activity' in line or
                'Transportation' in line or 'Accommodation' in line):
                
                # Save previous section if it has content
                if current_section["content"].strip():
                    current_section["id"] = section_id
                    sections.append(current_section.copy())
                    section_id += 1
                
                # Start new section
                section_type = "general"
                if 'Day' in line:
                    section_type = "day"
                elif 'Restaurant' in line or 'Dining' in line:
                    section_type = "restaurant"
                elif 'Hotel' in line or 'Accommodation' in line:
                    section_type = "accommodation"
                elif 'Activity' in line or 'Attraction' in line:
                    section_type = "activity"
                elif 'Transportation' in line or 'Transport' in line:
                    section_type = "transportation"
                
                current_section = {
                    "title": line.replace('#', '').strip(),
                    "content": line + '\n',
                    "type": section_type
                }
            else:
                current_section["content"] += line + '\n'
        
        # Add the last section
        if current_section["content"].strip():
            current_section["id"] = section_id
            sections.append(current_section)
        
        return sections

    def identify_relevant_categories(self, user_prompt, travel_info):
        """Identify the most relevant categories for preference discovery based on user input"""
        
        # Define core categories that should always be included
        core_categories = ["Dining", "Activities", "Accommodation"]
        
        category_prompt = f"""
        Analyze this travel request and identify 1-2 additional categories beyond the core categories (Dining, Activities, Accommodation) for preference discovery.

        TRAVEL REQUEST: {user_prompt}
        DESTINATION: {travel_info['destination']}
        INTERESTS: {', '.join(travel_info.get('interests', []))}
        TRAVEL STYLE: {travel_info.get('travel_style', 'balanced')}

        Core categories (already included): Dining, Activities, Accommodation

        Additional available categories to choose from:
        - Transportation (getting around, travel methods)
        - Nightlife (bars, clubs, evening entertainment)
        - Shopping (markets, stores, souvenirs)
        - Cultural Experiences (museums, local traditions, art)
        - Outdoor Adventures (hiking, sports, nature activities)
        - Relaxation (spas, beaches, wellness)
        - Entertainment (shows, events, performances)

        Based on the travel request, select 1-2 most relevant additional categories.
        Return ONLY a JSON array of the additional category names:
        ["Category1", "Category2"]
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": category_prompt}]
            )
            
            content = response.content[0].text.strip()
            # Extract JSON array
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                additional_categories = json.loads(json_match.group())
                # Combine core categories with additional ones
                all_categories = core_categories + additional_categories[:2]  # Limit to 2 additional
                return all_categories
            else:
                # Fallback: core categories + transportation
                return core_categories + ["Transportation"]
                
        except Exception as e:
            print(f"Error identifying categories: {e}")
            return core_categories + ["Transportation"]

    def generate_preference_sections(self, user_prompt):
        """Generate sections with detailed examples for preference discovery"""
        
        # Extract structured information
        travel_info = self.extract_travel_info(user_prompt)
        
        # Get relevant categories (always includes core categories)
        relevant_categories = self.identify_relevant_categories(user_prompt, travel_info)
        print(f"DEBUG: Selected categories: {relevant_categories}")
        
        # Enhanced prompt for dynamic category detection and web search integration
        sections_prompt = f"""
        You are a travel expert creating preference discovery sections for a trip. Use web search to find current, real information about {travel_info['destination']}.

        TRAVEL REQUEST: {user_prompt}
        
        DESTINATION: {travel_info['destination']}
        DURATION: {travel_info['duration']}
        BUDGET: {travel_info['budget']}
        TRAVELERS: {travel_info['travelers']}
        INTERESTS: {', '.join(travel_info.get('interests', []))}

        CRITICAL REQUIREMENT: Each section must contain EXACTLY 7 examples. This is mandatory.

        REQUIRED CATEGORIES: {', '.join(relevant_categories)}
        
        INSTRUCTIONS:
        1. Create sections for these EXACT categories: {', '.join(relevant_categories)}
        2. For each category, provide EXACTLY 7 diverse examples with detailed metadata
        4. Use web search to find REAL, current places and information
        5. Ensure examples within each category are SIGNIFICANTLY DIFFERENT to gauge preferences:
           - Example 1: Budget option ($ price range)
           - Example 2: Mid-range option ($$ price range)  
           - Example 3: Upscale option ($$$ price range)
           - Example 4: Luxury option ($$$$ price range)
           - Example 5: Unique/quirky option (any price range)
           - Example 6: Traditional/classic option (any price range)
           - Example 7: Trendy/modern option (any price range)

        EXAMPLE DIVERSITY REQUIREMENTS:
        - Dining: Include budget eats, casual dining, fine dining, street food, ethnic cuisines, unique concepts, trendy spots
        - Activities: Mix indoor/outdoor, active/passive, cultural/adventure, free/paid, group/solo friendly, unique experiences
        - Accommodation: Hotels, hostels, boutique, luxury, budget, different neighborhoods, unique stays
        - Transportation: Public transit, rideshare, rental cars, walking, bikes, different price points, unique options

        CRITICAL OUTPUT FORMAT:
        - Do NOT include any explanations, citations, or commentary
        - Do NOT include "Based on my research" or similar phrases
        - Do NOT include web search citations or references
        - Do NOT wrap the JSON in code blocks or markdown
        - Return ONLY the raw JSON object starting with {{ and ending with }}
        - Each section MUST have exactly 7 examples in the examples array

        Required JSON structure with EXACTLY 7 examples per section:
        {{
            "sections": [
                {{
                    "section_name": "Category Name",
                    "section_type": "category_type",
                    "description": "Brief description of what this category covers",
                    "examples": [
                        {{
                            "name": "Budget Option Name",
                            "description": "Detailed description with current information",
                            "metadata": {{
                                "price_range": "$",
                                "rating": 4.0,
                                "style": "Budget-friendly",
                                "location": "Specific Address/Neighborhood",
                                "target_audience": "Budget travelers",
                                "unique_features": ["affordable", "good value"],
                                "cost_estimate": "Under $20",
                                "duration": "1-2 hours",
                                "best_time": "Anytime"
                            }}
                        }},
                        {{
                            "name": "Mid-range Option Name",
                            "description": "Detailed description",
                            "metadata": {{
                                "price_range": "$$",
                                "rating": 4.2,
                                "style": "Comfortable",
                                "location": "Different neighborhood",
                                "target_audience": "Most travelers",
                                "unique_features": ["good service", "reliable"],
                                "cost_estimate": "$20-50",
                                "duration": "2-3 hours",
                                "best_time": "Peak hours"
                            }}
                        }},
                        {{
                            "name": "Upscale Option Name",
                            "description": "Detailed description",
                            "metadata": {{
                                "price_range": "$$$",
                                "rating": 4.5,
                                "style": "Upscale",
                                "location": "Premium area",
                                "target_audience": "Discerning travelers",
                                "unique_features": ["high quality", "excellent service"],
                                "cost_estimate": "$50-100",
                                "duration": "3-4 hours",
                                "best_time": "Evening"
                            }}
                        }},
                        {{
                            "name": "Luxury Option Name",
                            "description": "Detailed description",
                            "metadata": {{
                                "price_range": "$$$$",
                                "rating": 4.8,
                                "style": "Luxury",
                                "location": "Exclusive location",
                                "target_audience": "Luxury travelers",
                                "unique_features": ["exclusive", "premium experience"],
                                "cost_estimate": "$100+",
                                "duration": "Half day",
                                "best_time": "By appointment"
                            }}
                        }},
                        {{
                            "name": "Unique/Quirky Option Name",
                            "description": "Detailed description",
                            "metadata": {{
                                "price_range": "$$",
                                "rating": 4.3,
                                "style": "Unique",
                                "location": "Off-beat location",
                                "target_audience": "Adventure seekers",
                                "unique_features": ["one-of-a-kind", "memorable"],
                                "cost_estimate": "$30-60",
                                "duration": "2-3 hours",
                                "best_time": "Specific times"
                            }}
                        }},
                        {{
                            "name": "Traditional/Classic Option Name",
                            "description": "Detailed description",
                            "metadata": {{
                                "price_range": "$$",
                                "rating": 4.4,
                                "style": "Traditional",
                                "location": "Historic area",
                                "target_audience": "Culture enthusiasts",
                                "unique_features": ["authentic", "historic"],
                                "cost_estimate": "$25-45",
                                "duration": "2-3 hours",
                                "best_time": "Daytime"
                            }}
                        }},
                        {{
                            "name": "Trendy/Modern Option Name",
                            "description": "Detailed description",
                            "metadata": {{
                                "price_range": "$$$",
                                "rating": 4.6,
                                "style": "Modern",
                                "location": "Trendy district",
                                "target_audience": "Young professionals",
                                "unique_features": ["Instagram-worthy", "cutting-edge"],
                                "cost_estimate": "$40-80",
                                "duration": "2-4 hours",
                                "best_time": "Prime time"
                            }}
                        }}
                    ]
                }}
            ]
        }}

        REMEMBER: Each section must have EXACTLY 7 examples. Count them before responding.
        RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT WHATSOEVER.
        """
        
        try:
            # Try with web search first, fall back to basic if it fails
            try:
                print("DEBUG: Attempting API call with web search tool...")
                # Reduce max_uses to prevent timeouts
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=3000,  # Reduced to prevent timeouts
                    messages=[{"role": "user", "content": sections_prompt}],
                    tools=[
                        {
                            "type": "web_search_20250305",
                            "name": "web_search",
                            "max_uses": 3  # Reduced from 8 to prevent timeouts
                        }
                    ]
                )
                web_search_used = True
                print("DEBUG: Web search API call successful")
            except Exception as web_search_error:
                print(f"DEBUG: Web search failed: {web_search_error}, falling back to basic API call")
                try:
                    response = self.client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=3000,
                        messages=[{"role": "user", "content": sections_prompt}]
                    )
                    web_search_used = False
                    print("DEBUG: Fallback API call successful")
                except Exception as fallback_error:
                    print(f"DEBUG: Fallback API call also failed: {fallback_error}")
                    raise fallback_error
            
            # Extract JSON from response - handle different response structures
            content = None
            print(f"DEBUG: Response content length: {len(response.content)}")
            
            # Handle different response content structures
            for i, content_block in enumerate(response.content):
                print(f"DEBUG: Content block {i} type: {type(content_block)}")
                if hasattr(content_block, 'text') and content_block.text:
                    content = content_block.text.strip()
                    print(f"DEBUG: Found text content in block {i}")
                    break
                elif hasattr(content_block, 'type'):
                    print(f"DEBUG: Content block {i} has type: {content_block.type}")
            
            if not content:
                print("DEBUG: No text content found in response")
                raise ValueError("No text content found in API response")
            
            print(f"DEBUG: API response content (first 300 chars): {content[:300]}...")
            print(f"DEBUG: Full response length: {len(content)} characters")
            print(f"DEBUG: Response contains 'sections': {'sections' in content}")
            print("DEBUG: Response contains '{': " + str('{' in content))
            print("DEBUG: Response contains '}': " + str('}' in content))
            
            # Log the full response for debugging (truncated for readability)
            if len(content) < 2000:
                print(f"DEBUG: Full response content: {content}")
            else:
                print(f"DEBUG: Response too long, showing first 1000 and last 500 chars:")
                print(f"DEBUG: Start: {content[:1000]}")
                print(f"DEBUG: End: {content[-500:]}")
            
            # Bulletproof JSON extraction for any response format
            sections_data = None
            
            def extract_json_bulletproof(text):
                """Bulletproof JSON extraction with multiple fallback strategies"""
                
                # Strategy 1: Direct JSON parsing
                try:
                    return json.loads(text.strip())
                except json.JSONDecodeError:
                    pass
                
                # Strategy 2: Clean common prefixes and try again
                cleaned = text
                prefixes_to_remove = [
                    "Here's the JSON:", "Based on my research:", "```json", "```", 
                    "Here is the JSON:", "The JSON response is:", "I'll search for",
                    "Let me search", "After searching", "Based on current information:",
                    "Here's a JSON response", "I found the following information"
                ]
                
                for prefix in prefixes_to_remove:
                    cleaned = cleaned.replace(prefix, "").strip()
                
                # Remove citations like [1], [2], etc.
                cleaned = re.sub(r'\[\d+\]', '', cleaned)
                
                # Strategy 3: Find balanced JSON object
                start_idx = cleaned.find('{')
                if start_idx != -1:
                    brace_count = 0
                    end_idx = start_idx
                    
                    for i, char in enumerate(cleaned[start_idx:], start_idx):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i
                                break
                    
                    if end_idx > start_idx:
                        json_candidate = cleaned[start_idx:end_idx + 1]
                        try:
                            return json.loads(json_candidate)
                        except json.JSONDecodeError:
                            pass
                
                # Strategy 4: Extract sections array and wrap it
                sections_pattern = r'"sections"\s*:\s*(\[.*?\])'
                sections_match = re.search(sections_pattern, cleaned, re.DOTALL)
                if sections_match:
                    try:
                        sections_array = json.loads(sections_match.group(1))
                        return {"sections": sections_array}
                    except json.JSONDecodeError:
                        pass
                
                # Strategy 5: Try to reconstruct JSON from parts
                # Look for individual section objects
                section_pattern = r'\{\s*"section_name"\s*:\s*"[^"]+"\s*,.*?\}\s*(?=\{|$)'
                section_matches = re.findall(section_pattern, cleaned, re.DOTALL)
                
                if section_matches:
                    sections = []
                    for section_text in section_matches:
                        try:
                            section_obj = json.loads(section_text)
                            sections.append(section_obj)
                        except json.JSONDecodeError:
                            continue
                    
                    if sections:
                        return {"sections": sections}
                
                return None
            
            print("DEBUG: Starting bulletproof JSON extraction...")
            sections_data = extract_json_bulletproof(content)
            
            if sections_data:
                print("DEBUG: Bulletproof extraction succeeded!")
            else:
                print("DEBUG: All extraction methods failed, showing content for analysis:")
                print(f"DEBUG: Content length: {len(content)}")
                print(f"DEBUG: Content preview: {content[:500]}...")
                print(f"DEBUG: Content end: ...{content[-200:]}")
                
                # Last resort: Create a comprehensive fallback response with 7 examples per section
                print("DEBUG: Creating comprehensive fallback response...")
                sections_data = {
                    "sections": [
                        {
                            "section_name": "Dining",
                            "section_type": "dining",
                            "description": "Restaurant and dining options",
                            "examples": [
                                {"name": "Budget Eats", "description": "Affordable local food", "metadata": {"price_range": "$", "rating": 4.0, "style": "Casual", "location": "Local area", "target_audience": "Budget travelers", "unique_features": ["affordable"], "cost_estimate": "Under $15", "duration": "1 hour", "best_time": "Anytime"}},
                                {"name": "Mid-Range Restaurant", "description": "Comfortable dining experience", "metadata": {"price_range": "$$", "rating": 4.2, "style": "Comfortable", "location": "City center", "target_audience": "Most travelers", "unique_features": ["good service"], "cost_estimate": "$20-40", "duration": "1-2 hours", "best_time": "Dinner"}},
                                {"name": "Upscale Dining", "description": "Fine dining experience", "metadata": {"price_range": "$$$", "rating": 4.5, "style": "Upscale", "location": "Premium district", "target_audience": "Food enthusiasts", "unique_features": ["excellent cuisine"], "cost_estimate": "$50-80", "duration": "2-3 hours", "best_time": "Evening"}},
                                {"name": "Luxury Restaurant", "description": "High-end culinary experience", "metadata": {"price_range": "$$$$", "rating": 4.8, "style": "Luxury", "location": "Exclusive area", "target_audience": "Luxury diners", "unique_features": ["world-class"], "cost_estimate": "$100+", "duration": "3+ hours", "best_time": "Special occasions"}},
                                {"name": "Unique Food Experience", "description": "One-of-a-kind dining concept", "metadata": {"price_range": "$$", "rating": 4.3, "style": "Unique", "location": "Special venue", "target_audience": "Adventure eaters", "unique_features": ["memorable"], "cost_estimate": "$30-50", "duration": "2 hours", "best_time": "Varies"}},
                                {"name": "Traditional Local Spot", "description": "Authentic local cuisine", "metadata": {"price_range": "$$", "rating": 4.4, "style": "Traditional", "location": "Historic area", "target_audience": "Culture seekers", "unique_features": ["authentic"], "cost_estimate": "$25-45", "duration": "1-2 hours", "best_time": "Lunch/Dinner"}},
                                {"name": "Trendy New Restaurant", "description": "Modern dining concept", "metadata": {"price_range": "$$$", "rating": 4.6, "style": "Modern", "location": "Trendy neighborhood", "target_audience": "Young professionals", "unique_features": ["Instagram-worthy"], "cost_estimate": "$40-70", "duration": "2 hours", "best_time": "Prime time"}}
                            ]
                        },
                        {
                            "section_name": "Activities",
                            "section_type": "activities",
                            "description": "Things to do and experiences",
                            "examples": [
                                {"name": "Free Walking Tour", "description": "Budget-friendly city exploration", "metadata": {"price_range": "$", "rating": 4.1, "style": "Educational", "location": "City center", "target_audience": "Budget travelers", "unique_features": ["free", "informative"], "cost_estimate": "Tips only", "duration": "2-3 hours", "best_time": "Morning"}},
                                {"name": "Museum Visit", "description": "Cultural learning experience", "metadata": {"price_range": "$$", "rating": 4.3, "style": "Cultural", "location": "Museum district", "target_audience": "Culture lovers", "unique_features": ["educational"], "cost_estimate": "$15-25", "duration": "2-4 hours", "best_time": "Weekdays"}},
                                {"name": "Guided Tour", "description": "Professional guided experience", "metadata": {"price_range": "$$$", "rating": 4.5, "style": "Comprehensive", "location": "Various", "target_audience": "Most travelers", "unique_features": ["expert guide"], "cost_estimate": "$50-80", "duration": "4-6 hours", "best_time": "Full day"}},
                                {"name": "Private Experience", "description": "Exclusive personalized tour", "metadata": {"price_range": "$$$$", "rating": 4.8, "style": "Luxury", "location": "Exclusive venues", "target_audience": "Luxury travelers", "unique_features": ["personalized"], "cost_estimate": "$200+", "duration": "Full day", "best_time": "By appointment"}},
                                {"name": "Adventure Activity", "description": "Unique outdoor experience", "metadata": {"price_range": "$$", "rating": 4.4, "style": "Adventure", "location": "Outdoor location", "target_audience": "Thrill seekers", "unique_features": ["adrenaline"], "cost_estimate": "$40-60", "duration": "3-4 hours", "best_time": "Good weather"}},
                                {"name": "Traditional Craft Workshop", "description": "Learn local traditions", "metadata": {"price_range": "$$", "rating": 4.2, "style": "Traditional", "location": "Workshop space", "target_audience": "Craft enthusiasts", "unique_features": ["hands-on"], "cost_estimate": "$30-50", "duration": "2-3 hours", "best_time": "Afternoon"}},
                                {"name": "Modern Entertainment", "description": "Contemporary fun activity", "metadata": {"price_range": "$$$", "rating": 4.6, "style": "Modern", "location": "Entertainment district", "target_audience": "Young adults", "unique_features": ["trendy"], "cost_estimate": "$45-75", "duration": "3-4 hours", "best_time": "Evening"}}
                            ]
                        }
                    ]
                }
            
            if sections_data:
                sections = sections_data.get('sections', [])
                print(f"DEBUG: Successfully parsed {len(sections)} sections")
                
                # Validate that each section has examples and proper structure
                validated_sections = []
                for section in sections:
                    examples = section.get('examples', [])
                    section_name = section.get('section_name', 'Unknown')
                    section_type = section.get('section_type', 'general')
                    print(f"DEBUG: Section '{section_name}' has {len(examples)} examples")
                    
                    # Ensure we have exactly 7 examples per section
                    if len(examples) < 7:
                        print(f"Warning: Section '{section_name}' has only {len(examples)} examples, expected exactly 7")
                        # If we have fewer than 7, duplicate some examples with variations to reach 7
                        while len(examples) < 7 and len(examples) > 0:
                            # Duplicate the last example with slight modifications
                            base_example = examples[-1].copy()
                            base_example['name'] = f"{base_example['name']} (Alternative)"
                            base_example['description'] = f"Alternative option: {base_example['description']}"
                            if 'metadata' in base_example:
                                base_example['metadata'] = base_example['metadata'].copy()
                                base_example['metadata']['style'] = f"Alternative {base_example['metadata'].get('style', 'Option')}"
                            examples.append(base_example)
                        section['examples'] = examples
                        section['validation_warning'] = f"Expanded from {len(examples)} to 7 examples"
                    elif len(examples) > 7:
                        # Trim to exactly 7 examples if more than 7
                        section['examples'] = examples[:7]
                        print(f"Info: Trimmed section '{section_name}' to exactly 7 examples")
                    
                    # Validate metadata structure for each example
                    validated_examples = []
                    for i, example in enumerate(section['examples']):
                        # Ensure required fields exist
                        if not example.get('name'):
                            example['name'] = f"Option {i+1}"
                        if not example.get('description'):
                            example['description'] = "No description available"
                        
                        # Ensure metadata exists and has required fields
                        metadata = example.get('metadata', {})
                        required_fields = ['price_range', 'rating', 'location']
                        for field in required_fields:
                            if field not in metadata:
                                if field == 'price_range':
                                    metadata[field] = '$$'
                                elif field == 'rating':
                                    metadata[field] = 4.0
                                elif field == 'location':
                                    metadata[field] = 'Location TBD'
                        
                        example['metadata'] = metadata
                        validated_examples.append(example)
                    
                    section['examples'] = validated_examples
                    
                    # Add section description if missing
                    if not section.get('description'):
                        section['description'] = f"Options for {section_name.lower()} during your trip"
                    
                    validated_sections.append(section)
                
                return {
                    'success': True,
                    'sections': validated_sections,
                    'travel_info': travel_info,
                    'web_search_enabled': web_search_used
                }
            else:
                print(f"DEBUG: No valid JSON found in response")
                return {
                    'success': False,
                    'error': 'Could not parse JSON from API response',
                    'travel_info': travel_info,
                    'raw_content': content[:500]
                }
            
        except Exception as e:
            print(f"DEBUG: Exception in generate_preference_sections: {str(e)}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            
            # Fallback: Try without web search tool if there's an error
            print("DEBUG: Attempting fallback without web search tool...")
            try:
                fallback_response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": sections_prompt}]
                    # No tools parameter - fallback to Claude's training data
                )
                
                # Extract content from fallback response with same robust method
                fallback_content = None
                for content_block in fallback_response.content:
                    if hasattr(content_block, 'text') and content_block.text:
                        fallback_content = content_block.text.strip()
                        break
                
                if not fallback_content:
                    raise ValueError("No text content found in fallback response")
                    
                print(f"DEBUG: Fallback response: {fallback_content[:300]}...")
                
                # Try to parse fallback response
                json_match = re.search(r'\{.*\}', fallback_content, re.DOTALL)
                if json_match:
                    sections_data = json.loads(json_match.group())
                    return {
                        'success': True,
                        'sections': sections_data.get('sections', []),
                        'travel_info': travel_info,
                        'web_search_enabled': False,
                        'fallback_used': True
                    }
            except Exception as fallback_error:
                print(f"DEBUG: Fallback also failed: {fallback_error}")
            
            return {
                'success': False,
                'error': f"Error generating sections: {str(e)}",
                'travel_info': travel_info,
                'exception_type': type(e).__name__
            }
    
    def generate_personalized_itinerary(self, user_prompt, travel_info, user_preferences):
        """Generate a personalized itinerary based on collected user preferences"""
        
        # Analyze preferences to extract insights
        likes_summary = self._analyze_preferences(user_preferences.get('likes', []))
        dislikes_summary = self._analyze_preferences(user_preferences.get('dislikes', []))
        
        personalized_prompt = f"""
        Create a detailed, personalized travel itinerary based on the user's preferences discovered through their swipe choices.

        ORIGINAL REQUEST: {user_prompt}
        DESTINATION: {travel_info['destination']}
        DURATION: {travel_info['duration']}
        BUDGET: {travel_info['budget']}
        TRAVELERS: {travel_info['travelers']}

        USER PREFERENCE ANALYSIS:
        
        LIKES (things the user swiped right on):
        {likes_summary}
        
        DISLIKES (things the user swiped left on):
        {dislikes_summary}

        INSTRUCTIONS:
        1. Use web search to find current, real information about {travel_info['destination']}
        2. Create a detailed day-by-day itinerary that HEAVILY favors the user's demonstrated preferences
        3. Avoid or minimize elements similar to what they disliked
        4. Include specific restaurants, activities, and accommodations that match their preferred styles
        5. Consider their budget preferences, atmosphere preferences, and activity types they enjoyed
        6. Provide practical details: addresses, hours, costs, booking information
        7. Include backup options and alternatives that match their taste profile

        Create a comprehensive itinerary that feels personally curated for this specific user based on their demonstrated preferences.
        """
        
        try:
            # Use web search for personalized recommendations
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": personalized_prompt}],
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 5
                    }
                ]
            )
            
            # Extract content
            content = None
            for content_block in response.content:
                if hasattr(content_block, 'text') and content_block.text:
                    content = content_block.text.strip()
                    break
            
            if not content:
                raise ValueError("No content generated")
            
            # Parse into sections for display
            sections = self.parse_itinerary_into_sections(content)
            
            return {
                'success': True,
                'itinerary': content,
                'sections': sections,
                'personalized': True,
                'preferences_applied': {
                    'likes_count': len(user_preferences.get('likes', [])),
                    'dislikes_count': len(user_preferences.get('dislikes', [])),
                    'likes_summary': likes_summary,
                    'dislikes_summary': dislikes_summary
                }
            }
            
        except Exception as e:
            print(f"Error generating personalized itinerary: {e}")
            return {
                'success': False,
                'error': f"Error generating personalized itinerary: {str(e)}"
            }
    
    def _analyze_preferences(self, preferences_list):
        """Analyze a list of preferences to extract patterns and insights"""
        if not preferences_list:
            return "No preferences recorded"
        
        # Group by categories
        categories = {}
        for pref in preferences_list:
            category = pref.get('section_type', 'general')
            if category not in categories:
                categories[category] = []
            categories[category].append(pref)
        
        # Analyze patterns
        analysis = []
        for category, prefs in categories.items():
            if not prefs:
                continue
                
            # Extract common attributes
            price_ranges = []
            styles = []
            atmospheres = []
            
            for pref in prefs:
                metadata = pref.get('example', {}).get('metadata', {})
                if metadata.get('price_range'):
                    price_ranges.append(metadata['price_range'])
                if metadata.get('style'):
                    styles.append(metadata['style'])
                if metadata.get('atmosphere'):
                    atmospheres.append(metadata['atmosphere'])
            
            # Summarize preferences for this category
            category_summary = f"{category.title()}: "
            details = []
            
            if price_ranges:
                most_common_price = max(set(price_ranges), key=price_ranges.count)
                details.append(f"prefers {most_common_price} price range")
            
            if styles:
                unique_styles = list(set(styles))
                details.append(f"likes {', '.join(unique_styles[:3])} styles")
            
            if atmospheres:
                unique_atmospheres = list(set(atmospheres))
                details.append(f"enjoys {', '.join(unique_atmospheres[:2])} atmospheres")
            
            if details:
                category_summary += "; ".join(details)
            else:
                category_summary += f"{len(prefs)} selections made"
            
            analysis.append(category_summary)
        
        return "\n".join(analysis) if analysis else "General preferences recorded"

    def edit_itinerary_section(self, full_itinerary, section_id, section_content, user_edit_request):
        """Edit a specific section of the itinerary while considering the full context"""
        
        edit_prompt = f"""
        You are helping edit a travel itinerary. The user wants to modify a specific section.
        
        FULL CURRENT ITINERARY:
        {full_itinerary}
        
        SECTION TO EDIT (Section ID: {section_id}):
        {section_content}
        
        USER'S EDIT REQUEST:
        {user_edit_request}
        
        Please provide an updated version of the itinerary. You can either:
        1. Modify just the specific section if the change is localized
        2. Update multiple sections or the entire itinerary if the change has broader implications
        
        Consider how this change might affect:
        - Timing and scheduling of other activities
        - Budget implications
        - Transportation between activities
        - Overall flow of the trip
        
        Return the complete updated itinerary, maintaining the same structure and format as the original.
        Make sure to clearly indicate what has changed and why.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": edit_prompt}]
            )
            
            updated_itinerary = response.content[0].text
            updated_sections = self.parse_itinerary_into_sections(updated_itinerary)
            
            return {
                'success': True,
                'updated_itinerary': updated_itinerary,
                'updated_sections': updated_sections,
                'changes_made': f"Updated section {section_id} based on: {user_edit_request}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error editing itinerary section: {str(e)}"
            }

# Initialize the AI planner
travel_ai = TravelPlannerAI()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_itinerary', methods=['POST'])
def generate_itinerary():
    try:
        data = request.get_json()
        user_prompt = data.get('prompt', '')
        
        if not user_prompt:
            return jsonify({'error': 'Please provide a travel prompt'}), 400
        
        # Generate preference sections using AI
        result = travel_ai.generate_preference_sections(user_prompt)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/generate_personalized_itinerary', methods=['POST'])
def generate_personalized_itinerary():
    try:
        data = request.get_json()
        user_prompt = data.get('prompt', '')
        travel_info = data.get('travel_info', {})
        user_preferences = data.get('preferences', {})
        
        if not all([user_prompt, travel_info, user_preferences]):
            return jsonify({'error': 'Missing required fields: prompt, travel_info, and preferences'}), 400
        
        # Generate personalized itinerary using AI
        result = travel_ai.generate_personalized_itinerary(
            user_prompt, travel_info, user_preferences
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/edit_section', methods=['POST'])
def edit_section():
    try:
        data = request.get_json()
        full_itinerary = data.get('full_itinerary', '')
        section_id = data.get('section_id', '')
        section_content = data.get('section_content', '')
        edit_request = data.get('edit_request', '')
        
        if not all([full_itinerary, section_content, edit_request]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Edit the section using AI
        result = travel_ai.edit_itinerary_section(
            full_itinerary, section_id, section_content, edit_request
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'AIbnb Travel Planner'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
