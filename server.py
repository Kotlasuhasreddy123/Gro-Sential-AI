import boto3
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import traceback
import uuid
import os
import requests
import json
import bcrypt
from datetime import datetime, timedelta

# Simple shelf life prediction functions
def predict_expiry_date(item_name):
    """Predict expiry date based on item type"""
    # Default shelf life in days for common items
    shelf_life = {
        'milk': 7, 'bread': 5, 'eggs': 21, 'cheese': 14, 'yogurt': 14,
        'chicken': 2, 'beef': 3, 'fish': 2, 'vegetables': 7, 'fruits': 7,
        'lettuce': 5, 'tomato': 7, 'apple': 14, 'banana': 5, 'orange': 14
    }
    
    # Find matching item
    days = 7  # default
    for key, value in shelf_life.items():
        if key.lower() in item_name.lower():
            days = value
            break
    
    return (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')

def get_expiry_status(expiry_date):
    """Get status based on expiry date"""
    try:
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        days_left = (expiry - datetime.now()).days
        
        if days_left < 0:
            return 'Expired'
        elif days_left <= 2:
            return 'Expiring Soon'
        elif days_left <= 7:
            return 'Use Soon'
        else:
            return 'Fresh'
    except:
        return 'Unknown'

def get_expiry_color(status):
    """Get color based on status"""
    colors = {
        'Expired': '#ff4444',
        'Expiring Soon': '#ff8800',
        'Use Soon': '#ffbb33',
        'Fresh': '#00C851',
        'Unknown': '#999999'
    }
    return colors.get(status, '#999999')

app = Flask(__name__)
CORS(app)

# ── RATE LIMITING — prevent AI token abuse ────────────────────────────────
from collections import defaultdict
import time

# Per-IP: max 5 AI recipe calls per hour
AI_RATE_LIMIT = 5
AI_RATE_WINDOW = 3600  # 1 hour in seconds
_rate_store = defaultdict(list)  # ip -> [timestamps]

def check_rate_limit(ip):
    """Returns (allowed: bool, remaining: int, reset_in: int)"""
    now = time.time()
    window_start = now - AI_RATE_WINDOW
    # Clean old entries
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]
    count = len(_rate_store[ip])
    if count >= AI_RATE_LIMIT:
        oldest = _rate_store[ip][0]
        reset_in = int(AI_RATE_WINDOW - (now - oldest))
        return False, 0, reset_in
    _rate_store[ip].append(now)
    return True, AI_RATE_LIMIT - count - 1, 0

# --- AWS CONFIGURATION ---
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
SECRET_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

# --- YOUTUBE API CONFIGURATION ---
# Get your free API key from: https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')  # Add via environment variable

# Initialize AWS clients
rekognition = None
dynamodb = None
recipes_table = None
bedrock_runtime = None

try:
    session = boto3.Session(
        aws_access_key_id=ACCESS_KEY, 
        aws_secret_access_key=SECRET_KEY, 
        region_name=AWS_REGION
    )
    rekognition = session.client('rekognition')
    dynamodb = session.resource('dynamodb')
    recipes_table = dynamodb.Table('Gro-SentialRecipes')
    bedrock_runtime = session.client('bedrock-runtime', region_name=AWS_REGION)
    print(f"✅ AWS Services initialized successfully in region {AWS_REGION}")
    print(f"✅ AWS Bedrock Runtime initialized for AI recipe generation")
except Exception as e:
    print(f"❌ AWS Setup Error: {e}")
    print("⚠️  Server will run but AWS features will not work.")

@app.route('/')
def home():
    response = send_file('index.html')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/privacy')
def privacy():
    return send_file('privacy.html')

@app.route('/terms')
def terms():
    return send_file('terms.html')

@app.route('/sw.js')
def service_worker():
    response = send_file('sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/manifest.json')
def manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@app.route('/ping')
def ping():
    """Keep-alive endpoint — prevents Render free tier from sleeping"""
    return jsonify({"status": "alive", "time": str(datetime.now())})

@app.route('/favicon.ico')
def favicon_ico():
    return send_file('favicon.ico', mimetype='image/x-icon')

@app.route('/favicon-96x96.png')
def favicon_96():
    return send_file('favicon-96x96.png', mimetype='image/png')

@app.route('/favicon.svg')
def favicon_svg():
    return send_file('favicon.svg', mimetype='image/svg+xml')

@app.route('/apple-touch-icon.png')
def apple_touch_icon():
    return send_file('apple-touch-icon.png', mimetype='image/png')

# ── Food GIF routes for Perfect Plate visualization ──────────────────────
import os as _os

@app.route('/food-gif/<filename>')
def food_gif(filename):
    """Serve food GIF files for the Perfect Plate visualization"""
    allowed = [
        '6d848f6ee35a0dc8f363e87f515dc2e4.gif',
        'c5f958f3df4103d980635e73a37198d6.gif',
        '2dfood-food.gif',
        'ba1f3c47e64ecaa566cdc3e716f309d1.gif',
        'd6e48d23146713.5631dfb6afc94.gif',
        'giphy-38.gif',
        'PeelingBeetsOverheadFacebook.gif',
        'tumblr_60c27db8f087da22903250b4b0f7ed64_ed10dc0c_540.webp',
        '39440f22902851.5631a2bdc94bd.gif'
    ]
    if filename not in allowed:
        return '', 404
    # Use absolute path relative to this file
    base_dir = _os.path.dirname(_os.path.abspath(__file__))
    filepath = _os.path.join(base_dir, filename)
    if not _os.path.exists(filepath):
        print(f"⚠️ GIF not found: {filepath}")
        return '', 404
    mimetype = 'image/webp' if filename.endswith('.webp') else 'image/gif'
    return send_file(filepath, mimetype=mimetype)

@app.route('/scan', methods=['POST'])
def scan_image():
    """Scan uploaded image using AWS Rekognition to detect food ingredients"""
    if not rekognition:
        return jsonify({
            "status": "error",
            "message": "AWS Rekognition not configured"
        }), 500

    try:
        if 'image' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No image file provided"
            }), 400

        file = request.files['image']
        image_bytes = file.read()

        # Call AWS Rekognition with 50% confidence threshold
        response = rekognition.detect_labels(
            Image={'Bytes': image_bytes},
            MaxLabels=100,
            MinConfidence=50  # Lower threshold to catch more items
        )

        print(f"\n🔍 Raw Rekognition Response - Total Labels: {len(response['Labels'])}")
        for label in response['Labels']:
            print(f"  - {label['Name']} ({label['Confidence']:.1f}%) | Categories: {[c['Name'] for c in label.get('Categories', [])]}")

        detected_ingredients = []

        # Enhanced ban list - remove false positives
        ban_list = [
            # Generic food terms (too vague)
            'Food', 'Vegetable', 'Vegetables', 'Fruit', 'Produce', 'Plant', 'Meal',
            'Flora', 'Ingredient', 'Diet', 'Nutrition', 'Healthy', 'Fresh',
            'Eating', 'Cooking', 'Organic', 'Natural', 'Raw',

            # Meal types (not ingredients!)
            'Lunch', 'Dinner', 'Breakfast', 'Snack', 'Brunch', 'Supper',

            # Prepared foods (not raw ingredients!)
            'Sandwich', 'Burger', 'Pizza', 'Salad', 'Soup', 'Stew', 'Curry',
            'Wrap', 'Taco', 'Burrito', 'Sushi', 'Pasta Dish', 'Noodles',
            'Hot Dog', 'Sub', 'Panini', 'Toast',

            # Non-food objects (CRITICAL - removes false positives)
            'Appliance', 'Electronics', 'Furniture', 'Table', 'Desk', 'Chair',
            'Bowl', 'Container', 'Plate', 'Dish', 'Cup', 'Glass', 'Bottle',
            'Box', 'Package', 'Packaging', 'Carton', 'Basket', 'Crate',
            'Still Life', 'Indoors', 'Room', 'Kitchen', 'Counter', 'Shelf',
            'Wood', 'Wooden', 'Surface', 'Background', 'Texture',
            'Refrigerator', 'Fridge', 'Door', 'Handle',

            # Too generic plant terms
            'Leafy Green Vegetable', 'Root Vegetable', 'Citrus Fruit',
            'Tropical Fruit', 'Stone Fruit', 'Berry',

            # Colors and descriptions
            'Green', 'Red', 'Yellow', 'Orange', 'White', 'Purple',
            'Fresh', 'Ripe', 'Raw', 'Cooked'
        ]

        # Food-related categories to look for
        food_categories = [
            'Food and Beverage',
            'Plants and Flowers',
            'Fruit',
            'Vegetable'
        ]

        # Expanded food keywords - specific items only
        food_keywords = [
            'tomato', 'carrot', 'potato', 'onion', 'garlic', 'pepper', 'cucumber',
            'lettuce', 'cabbage', 'broccoli', 'cauliflower', 'spinach', 'kale',
            'apple', 'banana', 'orange', 'lemon', 'lime', 'grape', 'berry',
            'strawberry', 'blueberry', 'raspberry', 'blackberry', 'pineapple',
            'egg', 'cheese', 'milk', 'butter', 'yogurt', 'cream',
            'meat', 'chicken', 'beef', 'pork', 'fish', 'seafood', 'salmon', 'tuna',
            'bread', 'pasta', 'rice', 'grain', 'cereal', 'oat',
            'bean', 'lentil', 'pea', 'corn', 'mushroom',
            'herb', 'spice', 'basil', 'parsley', 'cilantro', 'mint',
            'celery', 'radish', 'beet', 'turnip', 'squash', 'zucchini',
            'eggplant', 'asparagus', 'artichoke', 'avocado', 'ginger',
            'mango', 'papaya', 'melon', 'watermelon', 'peach', 'pear',
            'plum', 'cherry', 'apricot', 'kiwi', 'fig', 'date',
            'nut', 'almond', 'walnut', 'cashew', 'peanut',
            'oil', 'vinegar', 'sauce', 'condiment'
        ]

        # Simplified validation - just check if it's food and not in ban list
        validated_ingredients = []

        for label in response['Labels']:
            name = label['Name']
            confidence = label['Confidence']
            categories = [cat['Name'] for cat in label.get('Categories', [])]
            
            # Skip if in ban list
            if name in ban_list:
                print(f"  ⛔ Filtered: {name} (in ban list)")
                continue
            
            # Simple check: Is it in a food category OR matches food keyword?
            is_food_category = any(cat in food_categories for cat in categories)
            name_lower = name.lower()
            matches_food_keyword = any(keyword in name_lower for keyword in food_keywords)
            
            # Accept if either condition is true
            if is_food_category or matches_food_keyword:
                validated_ingredients.append(name)
                reason = "food category" if is_food_category else "keyword match"
                print(f"  ✅ Added: {name} ({confidence:.1f}%) - {reason}")
            else:
                print(f"  ⚠️  Rejected: {name} ({confidence:.1f}%) - not food-related")

        if not validated_ingredients:
            print("⚠️  No specific food items detected")
            return jsonify({
                "status": "success",
                "ingredients": ["No specific food detected"]
            })

        # Remove duplicates and limit to top 20 items
        validated_ingredients = list(dict.fromkeys(validated_ingredients))[:20]

        print(f"\n✅ Final Detected Ingredients: {validated_ingredients}\n")
        return jsonify({
            "status": "success",
            "ingredients": validated_ingredients
        })

    except Exception as e:
        print(f"❌ SCAN ERROR:\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process image: {str(e)}"
        }), 500


@app.route('/generate_recipe', methods=['POST'])
def generate_recipe():
    """Generate intelligent, context-aware recipe based on EXACT ingredients user has"""
    try:
        data = request.json
        ingredients = data.get('ingredients', [])
        
        if not ingredients or ingredients == ["No specific food detected"]:
            return jsonify({
                "status": "success",
                "recipe": "Add ingredients to start generating recipes.",
                "video_embeds": []
            })
        
        print(f"\n🍳 Generating intelligent recipe for: {ingredients}")

        print(f"\n🍳 Generating intelligent recipe for: {ingredients}")
        
        # Analyze ingredients to understand what user has
        ingredients_lower = [ing.lower() for ing in ingredients]
        
        # Categorize ingredients
        has_oil = any(x in ingredients_lower for x in ['oil', 'olive oil', 'vegetable oil', 'cooking oil'])
        has_butter = 'butter' in ingredients_lower
        has_salt = 'salt' in ingredients_lower
        has_pepper = any(x in ingredients_lower for x in ['pepper', 'black pepper'])
        has_garlic = 'garlic' in ingredients_lower
        has_onion = 'onion' in ingredients_lower
        has_herbs = any(x in ingredients_lower for x in ['herbs', 'basil', 'parsley', 'cilantro', 'thyme', 'oregano'])
        
        # Determine cooking fat
        if has_butter and not has_oil:
            cooking_fat = "Butter"
            cooking_fat_amount = "2 tablespoons"
            cooking_fat_instruction = "butter"
        elif has_oil and not has_butter:
            cooking_fat = "Oil"
            cooking_fat_amount = "2 tablespoons"
            cooking_fat_instruction = "oil"
        elif has_butter and has_oil:
            cooking_fat = "Butter and Oil"
            cooking_fat_amount = "1 tablespoon each"
            cooking_fat_instruction = "butter and oil"
        else:
            # No fat specified - suggest minimal
            cooking_fat = None
            cooking_fat_amount = None
            cooking_fat_instruction = "a small amount of water or broth"
        
        # Categorize vegetables by cooking time
        hard_veggies = [ing for ing in ingredients if ing.lower() in ['carrot', 'potato', 'broccoli', 'cauliflower', 'beet', 'turnip', 'squash']]
        medium_veggies = [ing for ing in ingredients if ing.lower() in ['onion', 'pepper', 'bell pepper', 'mushroom', 'zucchini', 'eggplant', 'cabbage', 'celery', 'asparagus']]
        soft_veggies = [ing for ing in ingredients if ing.lower() in ['tomato', 'cucumber', 'lettuce', 'spinach', 'kale', 'chard']]
        proteins = [ing for ing in ingredients if ing.lower() in ['egg', 'chicken', 'beef', 'pork', 'fish', 'tofu', 'cheese']]
        aromatics = [ing for ing in ingredients if ing.lower() in ['garlic', 'onion', 'ginger', 'shallot']]
        
        # Build intelligent recipe
        recipe_parts = []
        main_ingredient = ingredients[0]
        
        # Header
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append(f"🌟 CUSTOM {main_ingredient.upper()} RECIPE 🌟")
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("")
        recipe_parts.append("⏱️  PREP TIME: 10 minutes  |  COOK TIME: 20 minutes")
        recipe_parts.append("👥 SERVINGS: 2-3 people  |  🔥 DIFFICULTY: Easy")
        recipe_parts.append("")
        
        # Ingredients - ONLY what user has
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("📋 YOUR INGREDIENTS")
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("")
        recipe_parts.append("What you're using:")
        for i, ing in enumerate(ingredients, 1):
            recipe_parts.append(f"  {i}. {ing}")
        recipe_parts.append("")
        
        # Equipment
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("🍳 EQUIPMENT NEEDED")
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("")
        recipe_parts.append("  • Large skillet or pan")
        recipe_parts.append("  • Sharp knife")
        recipe_parts.append("  • Cutting board")
        recipe_parts.append("  • Spatula or wooden spoon")
        recipe_parts.append("")
        
        # Intelligent cooking instructions
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("👨‍🍳 COOKING INSTRUCTIONS")
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("")
        
        step_num = 1
        
        # Prep step
        recipe_parts.append(f"STEP {step_num}: PREP YOUR INGREDIENTS")
        recipe_parts.append("─────────────────────────────────────────")
        recipe_parts.append("  🔪 Wash all ingredients thoroughly")
        recipe_parts.append("  🔪 Chop into bite-sized pieces")
        if hard_veggies:
            recipe_parts.append(f"  🔪 Cut {', '.join(hard_veggies)} into smaller pieces (they take longer to cook)")
        recipe_parts.append("")
        step_num += 1
        
        # Heat pan step - INTELLIGENT based on what they have
        recipe_parts.append(f"STEP {step_num}: HEAT YOUR PAN")
        recipe_parts.append("─────────────────────────────────────────")
        recipe_parts.append("  🔥 Place pan on MEDIUM-HIGH heat")
        if cooking_fat:
            recipe_parts.append(f"  🔥 Add {cooking_fat_amount} of {cooking_fat}")
            recipe_parts.append(f"  🔥 Let {cooking_fat_instruction} heat until shimmering (about 1 minute)")
        else:
            recipe_parts.append("  🔥 Heat pan for 1-2 minutes")
            recipe_parts.append("  💡 TIP: Since you don't have oil/butter, use a non-stick pan")
            recipe_parts.append("  💡 Or add a splash of water/broth to prevent sticking")
        recipe_parts.append("")
        step_num += 1
        
        # Cook aromatics first if available
        if aromatics:
            recipe_parts.append(f"STEP {step_num}: COOK AROMATICS FIRST")
            recipe_parts.append("─────────────────────────────────────────")
            recipe_parts.append(f"  🧄 Add {', '.join(aromatics)} to the pan")
            recipe_parts.append("  🧄 Cook for 1-2 minutes until fragrant")
            recipe_parts.append("  💡 This builds the flavor base!")
            recipe_parts.append("")
            step_num += 1
        
        # Cook hard vegetables
        if hard_veggies:
            recipe_parts.append(f"STEP {step_num}: COOK HARDER VEGETABLES")
            recipe_parts.append("─────────────────────────────────────────")
            recipe_parts.append(f"  🥕 Add {', '.join(hard_veggies)}")
            recipe_parts.append("  🥕 Cook for 7-10 minutes, stirring occasionally")
            recipe_parts.append("  🥕 They should start to soften and brown slightly")
            recipe_parts.append("")
            step_num += 1
        
        # Cook medium vegetables
        if medium_veggies:
            recipe_parts.append(f"STEP {step_num}: ADD MEDIUM VEGETABLES")
            recipe_parts.append("─────────────────────────────────────────")
            recipe_parts.append(f"  🫑 Add {', '.join(medium_veggies)}")
            recipe_parts.append("  🫑 Cook for 5-7 minutes, stirring occasionally")
            recipe_parts.append("  🫑 They should be tender but still have texture")
            recipe_parts.append("")
            step_num += 1
        
        # Cook proteins
        if proteins:
            recipe_parts.append(f"STEP {step_num}: ADD PROTEIN")
            recipe_parts.append("─────────────────────────────────────────")
            if any('egg' in p.lower() for p in proteins):
                recipe_parts.append("  🥚 Push vegetables to the side")
                recipe_parts.append("  🥚 Crack eggs into the pan")
                recipe_parts.append("  🥚 Scramble until cooked through (3-4 minutes)")
                recipe_parts.append("  🥚 Mix with vegetables")
            else:
                recipe_parts.append(f"  🍖 Add {', '.join(proteins)}")
                recipe_parts.append("  🍖 Cook until done (timing depends on protein)")
            recipe_parts.append("")
            step_num += 1
        
        # Cook soft vegetables last
        if soft_veggies:
            recipe_parts.append(f"STEP {step_num}: ADD DELICATE VEGETABLES LAST")
            recipe_parts.append("─────────────────────────────────────────")
            recipe_parts.append(f"  🍅 Add {', '.join(soft_veggies)}")
            recipe_parts.append("  🍅 Cook for just 2-3 minutes")
            recipe_parts.append("  🍅 They should be heated through but still vibrant")
            recipe_parts.append("")
            step_num += 1
        
        # Seasoning - INTELLIGENT based on what they have
        recipe_parts.append(f"STEP {step_num}: SEASON YOUR DISH")
        recipe_parts.append("─────────────────────────────────────────")
        if has_salt:
            recipe_parts.append("  🧂 Add Salt to taste")
        else:
            recipe_parts.append("  💡 You don't have salt - try a splash of soy sauce if available")
        
        if has_pepper:
            recipe_parts.append("  🧂 Add Pepper to taste")
        
        if has_herbs:
            herbs_list = [ing for ing in ingredients if ing.lower() in ['herbs', 'basil', 'parsley', 'cilantro', 'thyme', 'oregano']]
            recipe_parts.append(f"  🌿 Add your {', '.join(herbs_list)}")
        
        if not has_salt and not has_pepper and not has_herbs:
            recipe_parts.append("  💡 Season with whatever you have available")
        
        recipe_parts.append("  👅 Taste and adjust!")
        recipe_parts.append("")
        step_num += 1
        
        # Serve
        recipe_parts.append(f"STEP {step_num}: SERVE & ENJOY")
        recipe_parts.append("─────────────────────────────────────────")
        recipe_parts.append("  🍽️  Transfer to a serving plate")
        recipe_parts.append("  🍽️  Serve hot and enjoy!")
        recipe_parts.append("")
        
        # Health benefits
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("💪 HEALTH BENEFITS")
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("")
        recipe_parts.append(f"Your {main_ingredient}-based dish provides:")
        recipe_parts.append("  ✓ Fresh, whole food ingredients")
        recipe_parts.append("  ✓ Vitamins and minerals from vegetables")
        if proteins:
            recipe_parts.append("  ✓ Protein for energy and muscle health")
        recipe_parts.append("  ✓ Fiber for digestive health")
        recipe_parts.append("  ✓ Low in processed ingredients")
        recipe_parts.append("")
        
        # Zero waste
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("♻️  ZERO-WASTE TIPS")
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("")
        recipe_parts.append(f"🌱 This recipe uses ALL {len(ingredients)} of your ingredients!")
        recipe_parts.append("🌱 Save vegetable scraps for making stock")
        recipe_parts.append("🌱 Store leftovers in airtight containers (3-4 days)")
        recipe_parts.append("🌱 Share extras with neighbors via our Trade Network!")
        recipe_parts.append("")
        
        recipe_parts.append("═══════════════════════════════════════════")
        recipe_parts.append("👨‍🍳 Enjoy your custom creation!")
        recipe_parts.append("═══════════════════════════════════════════")
        
        recipe_text = "\n".join(recipe_parts)
        
        # Get YouTube videos
        video_embeds = get_youtube_videos_for_ingredients(ingredients)
        
        print(f"✅ Generated intelligent recipe for: {ingredients}")
        print(f"✅ Found {len(video_embeds)} relevant videos")
        
        return jsonify({
            "status": "success",
            "title": f"Custom {main_ingredient} Recipe",
            "recipe": recipe_text,
            "video_embeds": video_embeds
        })
    
    except Exception as e:
        print(f"❌ RECIPE ERROR:\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "recipe": "Failed to generate recipe.",
            "video_embeds": []
        }), 500
        return jsonify({
            "status": "success",
            "title": recipe_title,
            "recipe": recipe_text,
            "video_embeds": video_embeds
        })
    
    except Exception as e:
        print(f"❌ RECIPE ERROR:\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "recipe": "Failed to generate recipe.",
            "video_embeds": []
        }), 500

def get_youtube_videos_for_ingredients(ingredients):
    """
    Get REAL YouTube video links that match the ingredients using YouTube Data API
    Falls back to curated videos if API key not available
    """
    video_embeds = []
    
    # If YouTube API key is available, search for real videos
    if YOUTUBE_API_KEY:
        try:
            video_embeds = search_youtube_videos(ingredients)
            if len(video_embeds) >= 3:
                return video_embeds[:3]
        except Exception as e:
            print(f"⚠️  YouTube API error: {e}")
    
    # Fallback: Curated high-quality recipe videos
    curated_videos = {
        # Multi-ingredient combinations
        'tomato+carrot+egg': 'PUP7U5vTMM0',
        'tomato+egg': 'PUP7U5vTMM0',
        'carrot+potato': 'qH__o17xHls',
        'tomato+onion': 'TwCqnH-OxNI',
        'egg+vegetable': 'PUP7U5vTMM0',
        'cabbage+carrot': 'FAZsOc5g-kE',
        
        # Single ingredients
        'tomato': 'f6mX4H7W0_o',
        'carrot': '8X49w5K4Isc',
        'egg': 'PUP7U5vTMM0',
        'potato': 'qH__o17xHls',
        'onion': 'TwCqnH-OxNI',
        'cucumber': 'Wv8F6N1bA6c',
        'lettuce': 'mS5I4w7_A-A',
        'cabbage': 'FAZsOc5g-kE',
        'pepper': 'xqvZ5NUBRqY',
        'broccoli': 'P-h1t4D8_Ww',
    }
    
    ingredients_lower = [ing.lower() for ing in ingredients[:3]]
    
    # Try combinations of 2-3 ingredients
    for combo_size in [3, 2]:
        if len(ingredients_lower) >= combo_size:
            combo_key = '+'.join(sorted(ingredients_lower[:combo_size]))
            if combo_key in curated_videos:
                video_embeds.append(f"https://www.youtube.com/embed/{curated_videos[combo_key]}")
                break
    
    # Add videos for individual key ingredients
    for ing in ingredients_lower[:2]:
        if ing in curated_videos and len(video_embeds) < 3:
            vid_id = curated_videos[ing]
            embed_url = f"https://www.youtube.com/embed/{vid_id}"
            if embed_url not in video_embeds:
                video_embeds.append(embed_url)
    
    # Fill remaining slots with general zero-waste video
    while len(video_embeds) < 3:
        video_embeds.append("https://www.youtube.com/embed/P-h1t4D8_Ww")
    
    return video_embeds[:3]

def search_youtube_videos(ingredients):
    """
    Search YouTube for real videos matching the ingredients
    Returns list of video embed URLs
    """
    video_embeds = []
    
    # Search query 1: All ingredients together
    if len(ingredients) >= 2:
        query1 = " ".join(ingredients[:4]) + " recipe"
        videos1 = youtube_search(query1, max_results=2)
        video_embeds.extend(videos1)
    
    # Search query 2: Main ingredient + "easy recipe"
    if len(video_embeds) < 3 and len(ingredients) >= 1:
        query2 = f"{ingredients[0]} easy recipe"
        videos2 = youtube_search(query2, max_results=2)
        video_embeds.extend(videos2)
    
    # Search query 3: Zero waste cooking
    if len(video_embeds) < 3:
        query3 = "zero waste cooking tips"
        videos3 = youtube_search(query3, max_results=1)
        video_embeds.extend(videos3)
    
    return video_embeds[:3]

def youtube_search(query, max_results=3):
    """
    Search YouTube Data API for videos
    Returns list of video embed URLs
    """
    if not YOUTUBE_API_KEY:
        return []
    
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results,
            'key': YOUTUBE_API_KEY,
            'videoDuration': 'medium',  # 4-20 minutes
            'relevanceLanguage': 'en',
            'safeSearch': 'strict'
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        video_urls = []
        for item in data.get('items', []):
            video_id = item['id'].get('videoId')
            if video_id:
                video_urls.append(f"https://www.youtube.com/embed/{video_id}")
                print(f"  📹 Found: {item['snippet']['title'][:50]}...")
        
        return video_urls
    
    except Exception as e:
        print(f"⚠️  YouTube search error: {e}")
        return []

@app.route('/generate_recipe_ai', methods=['POST'])
def generate_recipe_ai():
    """Generate intelligent recipe using AWS Bedrock with expiry prioritization"""
    if not bedrock_runtime:
        return jsonify({
            "status": "error",
            "message": "AWS Bedrock not configured"
        }), 500

    # Rate limiting — 5 AI calls per IP per hour
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    allowed, remaining, reset_in = check_rate_limit(client_ip)
    if not allowed:
        mins = reset_in // 60
        return jsonify({
            "status": "rate_limited",
            "message": f"AI recipe limit reached (5/hour). Try again in {mins} minute(s).",
            "reset_in_seconds": reset_in
        }), 429
    
    try:
        data = request.json
        ingredients = data.get('ingredients', [])
        user_email = data.get('userEmail', '')
        dietary_restrictions = data.get('dietaryRestrictions', '')
        
        if not ingredients or ingredients == ["No specific food detected"]:
            return jsonify({
                "status": "success",
                "recipe": "Add ingredients to start generating recipes.",
                "video_embeds": []
            })
        
        print(f"\n🤖 Generating AI recipe with AWS Bedrock for: {ingredients}")
        
        # Get user's inventory with expiry information if email provided
        expiring_items = []
        if user_email and inventory_table:
            try:
                from datetime import datetime
                response = inventory_table.query(
                    KeyConditionExpression='UserEmail = :email',
                    ExpressionAttributeValues={':email': user_email.lower()}
                )
                items = response.get('Items', [])
                
                # Find expiring items (within 5 days)
                for item in items:
                    if 'ExpiryDate' in item:
                        expiry_date = datetime.strptime(item['ExpiryDate'], '%Y-%m-%d')
                        days_remaining = (expiry_date - datetime.now()).days
                        if 0 <= days_remaining <= 5:
                            expiring_items.append({
                                'name': item['ItemName'],
                                'days_remaining': days_remaining
                            })
                
                # Sort by days remaining (most urgent first)
                expiring_items.sort(key=lambda x: x['days_remaining'])
                print(f"  ⏰ Found {len(expiring_items)} expiring items")
            except Exception as e:
                print(f"  ⚠️  Could not fetch expiry data: {e}")
        
        # Build prompt with expiry prioritization
        prompt = f"""You are a professional chef creating a zero-waste recipe for the Gro-Sential app.

AVAILABLE INGREDIENTS:
{', '.join(ingredients)}

"""
        
        if expiring_items:
            prompt += f"""PRIORITY INGREDIENTS (expiring soon - USE THESE FIRST):
"""
            for item in expiring_items:
                prompt += f"- {item['name']} (expires in {item['days_remaining']} days)\n"
            prompt += "\n"
        
        if dietary_restrictions:
            prompt += f"""DIETARY RESTRICTIONS:
{dietary_restrictions}

"""
        
        prompt += """REQUIREMENTS:
1. Create a delicious recipe using ALL the available ingredients
2. Prioritize using the expiring ingredients first
3. Include step-by-step cooking instructions
4. Keep it simple and achievable for home cooks
5. Mention prep time, cook time, and servings
6. Add health benefits and zero-waste tips
7. Format the recipe clearly with sections

Please generate a complete, detailed recipe now."""

        # Call AWS Bedrock Claude 3 Haiku — cheapest Anthropic model ($0.25/1M input)
        # Note: Deprecated Sept 2026 — switch to claude-3-5-haiku then
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "top_p": 0.9
        }

        print("  🤖 Calling AWS Bedrock Claude 3 Haiku...")
        response = bedrock_runtime.invoke_model(
            modelId='us.anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        recipe_text = response_body['content'][0]['text']
        
        print(f"✅ Generated AI recipe with AWS Bedrock")
        
        # Get YouTube videos
        video_embeds = get_youtube_videos_for_ingredients(ingredients)
        
        return jsonify({
            "status": "success",
            "title": f"AI-Generated Recipe with {ingredients[0]}",
            "recipe": recipe_text,
            "video_embeds": video_embeds,
            "expiring_items": expiring_items
        })
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ BEDROCK RECIPE ERROR:\n{traceback.format_exc()}")
        
        # Check if it's an access denied or resource not found error
        if "AccessDeniedException" in error_msg or "not authorized" in error_msg or "ResourceNotFoundException" in error_msg:
            # Generate a basic recipe as fallback
            basic_recipe = f"""# Simple Recipe with {', '.join(ingredients)}

## Ingredients Needed:
{chr(10).join([f'- {ing}' for ing in ingredients])}

## Instructions:

1. **Preparation**: Wash and prepare all ingredients. Cut vegetables into bite-sized pieces.

2. **Cooking**: 
   - Heat a pan with a little oil over medium heat
   - Add your main ingredients ({ingredients[0] if ingredients else 'main item'})
   - Cook for 5-7 minutes until done

3. **Seasoning**: Add salt, pepper, and your favorite spices to taste

4. **Serving**: Serve hot and enjoy your meal!

## Tips:
- Adjust cooking time based on ingredient freshness
- Use expiring items first to reduce waste
- Store leftovers in airtight containers

---
*Note: This is a basic recipe. AWS Bedrock AI is not fully configured.*

**To enable AI-powered recipes:**
1. Fill out the Anthropic use case form: https://pages.awscloud.com/GLOBAL_PM_PA_anthropic-claude-on-bedrock_2023_interest-request.html
2. Wait 15 minutes for approval
3. Restart the server

Or use the basic recipes - they work great too!
"""
            
            video_embeds = get_youtube_videos_for_ingredients(ingredients)
            
            return jsonify({
                "status": "success",
                "title": f"Basic Recipe with {ingredients[0] if ingredients else 'Your Ingredients'}",
                "recipe": basic_recipe,
                "video_embeds": video_embeds,
                "expiring_items": [],
                "fallback": True,
                "message": "Using basic recipe generator. Fill out Anthropic use case form to enable AI recipes."
            })
        else:
            # Other errors - return error
            return jsonify({
                "status": "error",
                "message": f"Recipe generation error: {error_msg}",
                "recipe": "",
                "video_embeds": []
            }), 500

@app.route('/save_recipe', methods=['POST'])
def save_recipe():
    """Save recipe to AWS DynamoDB"""
    if not dynamodb or not recipes_table:
        return jsonify({
            "status": "error", 
            "message": "AWS DynamoDB not configured"
        }), 500
    
    try:
        data = request.json
        
        if not data.get('ingredients') or not data.get('recipe'):
            return jsonify({
                "status": "error",
                "message": "Missing required fields"
            }), 400
        
        recipe_id = str(uuid.uuid4())
        user_pincode = data.get('pincode', 'Unknown')
        
        # Save to DynamoDB
        recipes_table.put_item(Item={
            'RecipeID': recipe_id,
            'UserPincode': user_pincode,
            'RecipeTitle': data.get('title', 'Saved Recipe'),
            'Ingredients': data.get('ingredients', []),
            'RecipeText': data.get('recipe', ''),
            'Timestamp': str(uuid.uuid1().time)
        })
        
        print(f"✅ Recipe saved to DynamoDB with ID: {recipe_id}")
        return jsonify({
            "status": "success", 
            "message": "Recipe successfully saved!",
            "recipe_id": recipe_id
        })
    
    except Exception as e:
        print(f"❌ DYNAMODB ERROR:\n{traceback.format_exc()}")
        return jsonify({
            "status": "error", 
            "message": f"Failed to save to database: {str(e)}"
        }), 500

# --- AI TRADING AGENT SYSTEM ---

# Market prices database (USD per unit) - Real market data
MARKET_PRICES = {
    # Dairy & Eggs (per unit/serving)
    'Eggs': 0.33, 'Milk': 0.25, 'Cheese': 0.75, 'Butter': 0.60, 'Yogurt': 0.50,
    'Cream': 0.65, 'Sour Cream': 0.55,
    
    # Vegetables (per unit/serving)
    'Tomato': 0.50, 'Tomatoes': 0.50, 'Onion': 0.40, 'Onions': 0.40,
    'Potato': 0.30, 'Potatoes': 0.30, 'Carrot': 0.35, 'Carrots': 0.35,
    'Broccoli': 1.00, 'Cauliflower': 1.25, 'Spinach': 0.75, 'Lettuce': 1.00,
    'Bell Pepper': 1.00, 'Cucumber': 0.60, 'Zucchini': 0.70, 'Eggplant': 0.90,
    'Cabbage': 0.50, 'Celery': 0.75, 'Mushroom': 1.20, 'Mushrooms': 1.20,
    
    # Fruits (per unit/serving)
    'Apple': 0.75, 'Apples': 0.75, 'Banana': 0.25, 'Bananas': 0.25,
    'Orange': 0.60, 'Oranges': 0.60, 'Grapes': 1.50, 'Strawberry': 0.40,
    'Strawberries': 0.40, 'Blueberry': 0.50, 'Blueberries': 0.50,
    'Mango': 1.50, 'Pineapple': 3.00, 'Watermelon': 1.00, 'Lemon': 0.50,
    'Lime': 0.40, 'Peach': 0.80, 'Pear': 0.75, 'Cherry': 0.30, 'Cherries': 0.30,
    
    # Proteins (per serving/unit)
    'Chicken': 2.50, 'Beef': 4.00, 'Pork': 3.00, 'Fish': 3.50, 'Salmon': 5.00,
    'Shrimp': 6.00, 'Tofu': 1.50, 'Beans': 0.50, 'Lentils': 0.60,
    
    # Grains & Bread (per unit/serving)
    'Bread': 0.50, 'Rice': 0.30, 'Pasta': 0.40, 'Flour': 0.25, 'Oats': 0.35,
    'Quinoa': 1.00, 'Cereal': 0.75,
    
    # Condiments & Oils (per serving)
    'Oil': 0.50, 'Olive Oil': 1.00, 'Salt': 0.10, 'Pepper': 0.75, 'Sugar': 0.20,
    'Honey': 1.50, 'Vinegar': 0.40, 'Soy Sauce': 0.60, 'Ketchup': 0.50,
    'Mustard': 0.55, 'Mayonnaise': 0.70,
    
    # Herbs & Spices (per bunch/unit)
    'Garlic': 0.40, 'Ginger': 0.75, 'Basil': 1.00, 'Cilantro': 0.80,
    'Parsley': 0.75, 'Thyme': 1.00, 'Rosemary': 1.00, 'Oregano': 0.90,
    
    # Snacks & Others (per unit/serving)
    'Chocolate': 1.50, 'Nuts': 2.00, 'Chips': 1.00, 'Cookies': 0.80,
    'Crackers': 0.70, 'Jam': 0.90, 'Peanut Butter': 1.20
}

def get_market_price(item_name):
    """Get market price for an item"""
    # Try exact match first
    if item_name in MARKET_PRICES:
        return MARKET_PRICES[item_name]
    
    # Try case-insensitive match
    for key, price in MARKET_PRICES.items():
        if key.lower() == item_name.lower():
            return price
    
    # Default price for unknown items
    return 0.50

def calculate_trade_points(item_name, quantity):
    """Calculate karma points based on market value"""
    price = get_market_price(item_name)
    # 1 USD = 100 karma points
    points = int(price * quantity * 100)
    return max(points, 10)  # Minimum 10 points

def calculate_karma_points(market_value):
    """Calculate karma points from market value"""
    # Simple calculation: market_value * 10
    return int(float(market_value) * 10)

def suggest_equivalent_trades(needed_item, needed_qty, user_inventory):
    """AI suggests equivalent items user can trade"""
    needed_value = get_market_price(needed_item) * needed_qty
    suggestions = []
    
    for item in user_inventory:
        item_name = item.get('ItemName', '')
        item_qty = int(item.get('Quantity', 0))
        item_price = get_market_price(item_name)
        
        if item_qty > 0 and item_price > 0:
            # Calculate equivalent quantity
            equiv_qty = max(1, int(needed_value / item_price))
            if equiv_qty <= item_qty:
                suggestions.append({
                    'item': item_name,
                    'quantity': equiv_qty,
                    'value': item_price * equiv_qty,
                    'available': item_qty
                })
    
    # Sort by closest value match
    suggestions.sort(key=lambda x: abs(x['value'] - needed_value))
    return suggestions[:5]  # Top 5 suggestions

@app.route('/ai/analyze_trade', methods=['POST'])
def ai_analyze_trade():
    """AI analyzes and suggests optimal trade"""
    try:
        data = request.json
        needed_item = data.get('neededItem', '')
        needed_qty = int(data.get('neededQuantity', 1))
        user_email = data.get('userEmail', '')
        
        if not dynamodb:
            return jsonify({"status": "error", "message": "Database not configured"}), 500
        
        # Get user's inventory
        inventory_table = dynamodb.Table('Gro-SentialInventory')
        user_inventory = inventory_table.query(
            KeyConditionExpression='UserEmail = :email',
            ExpressionAttributeValues={':email': user_email}
        ).get('Items', [])
        
        # Calculate needed item value
        needed_value = get_market_price(needed_item) * needed_qty
        needed_points = calculate_trade_points(needed_item, needed_qty)
        
        # Get equivalent trade suggestions
        suggestions = suggest_equivalent_trades(needed_item, needed_qty, user_inventory)
        
        # AI analysis response
        analysis = {
            'status': 'success',
            'neededItem': needed_item,
            'neededQuantity': needed_qty,
            'marketValue': round(needed_value, 2),
            'karmaPoints': needed_points,
            'equivalentTrades': suggestions,
            'aiRecommendation': f"Based on market analysis, {needed_qty} {needed_item}(s) is worth ${needed_value:.2f} or {needed_points} karma points. "
        }
        
        if suggestions:
            top = suggestions[0]
            analysis['aiRecommendation'] += f"I recommend trading {top['quantity']} {top['item']}(s) as it's the closest value match."
        else:
            analysis['aiRecommendation'] += "You can use karma points for this trade."
        
        return jsonify(analysis)
    
    except Exception as e:
        print(f"❌ AI ANALYZE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ai/expiring_items', methods=['POST'])
def check_expiring_items():
    """AI checks for expiring items and suggests trades"""
    try:
        data = request.json
        user_email = data.get('userEmail', '')
        days_threshold = int(data.get('daysThreshold', 3))  # Default 3 days
        
        if not dynamodb:
            return jsonify({"status": "error", "message": "Database not configured"}), 500
        
        # Get user's inventory
        inventory_table = dynamodb.Table('Gro-SentialInventory')
        user_inventory = inventory_table.query(
            KeyConditionExpression='UserEmail = :email',
            ExpressionAttributeValues={':email': user_email}
        ).get('Items', [])
        
        from datetime import datetime, timedelta
        current_date = datetime.now()
        threshold_date = current_date + timedelta(days=days_threshold)
        
        expiring_items = []
        for item in user_inventory:
            expiry_str = item.get('ExpiryDate', '')
            if expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d')
                    if current_date <= expiry_date <= threshold_date:
                        days_left = (expiry_date - current_date).days
                        item_name = item.get('ItemName', '')
                        quantity = int(item.get('Quantity', 0))
                        
                        expiring_items.append({
                            'item': item_name,
                            'quantity': quantity,
                            'expiryDate': expiry_str,
                            'daysLeft': days_left,
                            'marketValue': round(get_market_price(item_name) * quantity, 2),
                            'karmaPoints': calculate_trade_points(item_name, quantity),
                            'urgency': 'high' if days_left <= 1 else 'medium' if days_left <= 2 else 'low'
                        })
                except:
                    pass
        
        # Sort by urgency (days left)
        expiring_items.sort(key=lambda x: x['daysLeft'])
        
        # AI recommendations
        recommendations = []
        if expiring_items:
            for item in expiring_items[:3]:  # Top 3 urgent items
                recommendations.append(
                    f"⚠️ {item['item']} expires in {item['daysLeft']} day(s)! "
                    f"Trade now for {item['karmaPoints']} points or find recipes to use it."
                )
        
        return jsonify({
            'status': 'success',
            'expiringItems': expiring_items,
            'totalItems': len(expiring_items),
            'recommendations': recommendations,
            'aiMessage': f"Found {len(expiring_items)} item(s) expiring within {days_threshold} days. Act fast to avoid waste!"
        })
    
    except Exception as e:
        print(f"❌ EXPIRY CHECK ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ai/smart_trade_match', methods=['POST'])
def smart_trade_match():
    """AI finds best trade matches considering preferences and expiry - EXPANDED TO NEARBY PINCODES"""
    try:
        data = request.json
        user_email = data.get('userEmail', '')
        needed_item = data.get('neededItem', '').strip()
        needed_qty = int(data.get('neededQuantity', 1))
        user_pincode = data.get('pincode', '')
        
        if not dynamodb:
            return jsonify({"status": "error", "message": "Database not configured"}), 500
        
        # Search for neighbors with the item
        inventory_table = dynamodb.Table('Gro-SentialInventory')
        users_table = dynamodb.Table('Gro-SentialUsers')
        
        # Calculate nearby pincodes (within ±10 range)
        try:
            base_pincode = int(user_pincode)
            nearby_pincodes = [str(base_pincode + i) for i in range(-10, 11)]
        except:
            nearby_pincodes = [user_pincode]
        
        # Get ALL available items (scan entire inventory for nearby search)
        response = inventory_table.scan(
            FilterExpression='Available = :avail',
            ExpressionAttributeValues={':avail': True}
        )
        
        # Filter items case-insensitively and by pincode
        needed_item_lower = needed_item.lower()
        matches = []
        
        for item in response.get('Items', []):
            item_name = item.get('ItemName', '')
            item_pincode = item.get('Pincode', '')
            
            # Case-insensitive partial match
            if needed_item_lower not in item_name.lower():
                continue
            
            # Only include same or nearby pincodes
            if item_pincode not in nearby_pincodes:
                continue
                
            provider_email = item.get('UserEmail', '')
            if provider_email == user_email:
                continue  # Skip self
            
            item_qty = int(item.get('Quantity', 0))
            if item_qty >= needed_qty:
                # Get provider details
                user_response = users_table.get_item(Key={'UserEmail': provider_email})
                provider = user_response.get('Item', {})
                
                # Check if item is expiring (higher priority)
                expiry_str = item.get('ExpiryDate', '')
                days_until_expiry = 999
                if expiry_str:
                    try:
                        from datetime import datetime
                        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d')
                        days_until_expiry = (expiry_date - datetime.now()).days
                    except:
                        pass
                
                # Calculate pincode distance
                try:
                    distance = abs(int(item_pincode) - int(user_pincode))
                except:
                    distance = 999
                
                matches.append({
                    'providerEmail': provider_email,
                    'providerName': provider.get('UserName', 'Unknown'),
                    'providerPincode': item_pincode,  # ADD PINCODE
                    'providerKarma': provider.get('KarmaPoints', 0),
                    'itemName': item_name,
                    'availableQuantity': item_qty,
                    'expiryDate': expiry_str,
                    'daysUntilExpiry': days_until_expiry,
                    'distance': distance,
                    'marketValue': round(get_market_price(item_name) * needed_qty, 2),
                    'karmaPoints': calculate_trade_points(item_name, needed_qty),
                    'matchScore': 100 - days_until_expiry  # Higher score for expiring items
                })
        
        # Sort by distance first, then expiry (prioritize nearby + expiring items)
        matches.sort(key=lambda x: (x['distance'], x['daysUntilExpiry']))
        
        # Create recommendation message
        same_pincode_count = len([m for m in matches if m['distance'] == 0])
        nearby_count = len(matches) - same_pincode_count
        
        if matches:
            if same_pincode_count > 0:
                recommendation = f"Found {same_pincode_count} neighbor(s) with {needed_item} in your area (pincode {user_pincode})"
                if nearby_count > 0:
                    recommendation += f" and {nearby_count} more nearby"
                
                # Only mention expiry if it's meaningful (not 999 days)
                top_expiry = matches[0]['daysUntilExpiry']
                if top_expiry < 100:  # Only show if less than 100 days
                    if top_expiry <= 5:
                        recommendation += f". Top match expires in {top_expiry} days - act fast to reduce waste!"
                    elif top_expiry <= 14:
                        recommendation += f". Top match expires in {top_expiry} days - good timing!"
                    else:
                        recommendation += ". Fresh items available!"
                else:
                    recommendation += ". Items available for trade!"
            else:
                recommendation = f"Found {nearby_count} neighbor(s) with {needed_item} in nearby areas. Closest is in pincode {matches[0]['providerPincode']}."
        else:
            recommendation = f"No matches found for {needed_item} in your area or nearby."
        
        return jsonify({
            'status': 'success',
            'matches': matches[:10],  # Top 10 matches
            'totalMatches': len(matches),
            'aiRecommendation': recommendation
        })
    
    except Exception as e:
        print(f"❌ SMART MATCH ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/negotiate', methods=['POST'])
def negotiate():
    """Amazon Q Broker negotiation endpoint"""
    try:
        data = request.json
        item = data.get('item', 'unknown item')
        user_pincode = data.get('pincode', 'Unknown')
        
        # Generate negotiation response with pincode context
        reply = f"🤝 Great! I found 3 neighbors in pincode {user_pincode} who have {item.capitalize()}!\n\n"
        reply += f"📍 Suggested meetup: Community Center, {user_pincode}\n"
        reply += f"⏰ Best time: This Saturday, 10 AM - 12 PM\n\n"
        reply += f"💰 Fair trade: 1 unit of {item.capitalize()} = 350 Karma Points\n"
        reply += f"Or exchange with your surplus items!"
        
        print(f"✅ Negotiation request for: {item} in pincode {user_pincode}")
        return jsonify({"reply": reply})
    
    except Exception as e:
        print(f"❌ NEGOTIATE ERROR:\n{traceback.format_exc()}")
        return jsonify({
            "reply": "Sorry, I'm having trouble processing your request right now."
        }), 500

@app.route('/find_neighbors', methods=['POST'])
def find_neighbors():
    """Find neighbors in the same pincode for food sharing"""
    try:
        data = request.json
        pincode = data.get('pincode', '')
        
        if not pincode or len(pincode) < 5:
            return jsonify({
                "status": "error",
                "message": "Please enter a valid pincode"
            }), 400
        
        # Simulate neighbor finding (in production, query DynamoDB)
        neighbors_count = hash(pincode) % 10 + 3  # 3-12 neighbors
        
        response = {
            "status": "success",
            "pincode": pincode,
            "neighbors_count": neighbors_count,
            "meetup_location": f"Community Center, Pincode {pincode}",
            "suggested_times": [
                "Saturday, 10:00 AM - 12:00 PM",
                "Sunday, 3:00 PM - 5:00 PM",
                "Wednesday, 6:00 PM - 7:30 PM"
            ],
            "message": f"Found {neighbors_count} active food sharers in your area!"
        }
        
        print(f"✅ Found {neighbors_count} neighbors in pincode {pincode}")
        return jsonify(response)
    
    except Exception as e:
        print(f"❌ FIND NEIGHBORS ERROR:\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "Failed to find neighbors"
        }), 500

@app.route('/track_expiry', methods=['POST'])
def track_expiry():
    """Track food expiry dates and send alerts"""
    try:
        data = request.json
        ingredients = data.get('ingredients', [])
        
        if not ingredients:
            return jsonify({
                "status": "error",
                "message": "No ingredients provided"
            }), 400
        
        # Typical shelf life for common ingredients (in days)
        shelf_life = {
            'tomato': 7, 'carrot': 21, 'potato': 30, 'onion': 30,
            'lettuce': 7, 'cucumber': 7, 'pepper': 10, 'broccoli': 7,
            'apple': 30, 'banana': 5, 'orange': 14, 'lemon': 21,
            'egg': 28, 'milk': 7, 'cheese': 21, 'butter': 90,
            'chicken': 2, 'beef': 3, 'fish': 2, 'bread': 7
        }
        
        expiry_data = []
        urgent_items = []
        
        for ing in ingredients:
            ing_lower = ing.lower()
            days = shelf_life.get(ing_lower, 14)  # Default 14 days
            
            # Calculate urgency
            if days <= 3:
                urgency = "🔴 URGENT"
                urgent_items.append(ing)
            elif days <= 7:
                urgency = "🟡 USE SOON"
            else:
                urgency = "🟢 FRESH"
            
            expiry_data.append({
                "ingredient": ing,
                "days_left": days,
                "urgency": urgency,
                "tips": get_storage_tip(ing_lower)
            })
        
        # Sort by urgency (shortest shelf life first)
        expiry_data.sort(key=lambda x: x['days_left'])
        
        response = {
            "status": "success",
            "expiry_data": expiry_data,
            "urgent_count": len(urgent_items),
            "urgent_items": urgent_items,
            "message": f"Tracking {len(ingredients)} items. {len(urgent_items)} need immediate attention!"
        }
        
        print(f"✅ Tracking expiry for {len(ingredients)} items")
        return jsonify(response)
    
    except Exception as e:
        print(f"❌ EXPIRY TRACKING ERROR:\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "Failed to track expiry"
        }), 500

def get_storage_tip(ingredient):
    """Get storage tips for ingredients"""
    tips = {
        'tomato': "Store at room temperature until ripe, then refrigerate",
        'carrot': "Keep in crisper drawer, remove greens",
        'potato': "Store in cool, dark place - not in fridge",
        'onion': "Store in cool, dry place with good air circulation",
        'lettuce': "Wrap in paper towel, store in plastic bag",
        'cucumber': "Keep in crisper drawer, away from ethylene producers",
        'pepper': "Store in crisper drawer in plastic bag",
        'broccoli': "Store in crisper drawer, use within a week",
        'apple': "Store in crisper drawer, separate from other produce",
        'banana': "Store at room temperature, separate from other fruit",
        'egg': "Keep in original carton in main fridge (not door)",
        'milk': "Store in back of fridge (coldest spot)",
        'cheese': "Wrap in wax paper, then plastic wrap",
        'chicken': "Use within 2 days or freeze immediately",
        'fish': "Use within 2 days or freeze immediately"
    }
    return tips.get(ingredient, "Store in refrigerator for best freshness")

@app.route('/generate_shopping_list', methods=['POST'])
def generate_shopping_list():
    """Generate smart shopping list based on detected items"""
    try:
        data = request.json
        current_items = data.get('current_items', [])
        
        # Common complementary ingredients
        complementary_items = {
            'tomato': ['onion', 'garlic', 'basil', 'olive oil'],
            'carrot': ['celery', 'onion', 'potato', 'herbs'],
            'egg': ['milk', 'butter', 'cheese', 'bread'],
            'chicken': ['lemon', 'garlic', 'herbs', 'olive oil'],
            'pasta': ['tomato sauce', 'garlic', 'parmesan', 'basil'],
            'rice': ['soy sauce', 'vegetables', 'protein', 'sesame oil']
        }
        
        # Essential pantry staples
        pantry_staples = [
            'olive oil', 'salt', 'pepper', 'garlic', 'onion',
            'rice', 'pasta', 'canned tomatoes', 'flour', 'sugar'
        ]
        
        suggested_items = set()
        
        # Add complementary items
        for item in current_items:
            item_lower = item.lower()
            if item_lower in complementary_items:
                suggested_items.update(complementary_items[item_lower])
        
        # Add missing pantry staples
        for staple in pantry_staples[:5]:  # Top 5 staples
            if staple not in [i.lower() for i in current_items]:
                suggested_items.add(staple)
        
        # Remove items already in fridge
        suggested_items = [item for item in suggested_items 
                          if item not in [i.lower() for i in current_items]]
        
        response = {
            "status": "success",
            "current_items": current_items,
            "suggested_items": list(suggested_items)[:10],  # Top 10 suggestions
            "message": f"Based on your {len(current_items)} items, here are {len(list(suggested_items)[:10])} smart suggestions!"
        }
        
        print(f"✅ Generated shopping list with {len(suggested_items)} suggestions")
        return jsonify(response)
    
    except Exception as e:
        print(f"❌ SHOPPING LIST ERROR:\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": "Failed to generate shopping list"
        }), 500

@app.route('/debug_scan', methods=['POST'])
def debug_scan():
    """Debug endpoint to see all raw Rekognition labels"""
    if not rekognition:
        return jsonify({"error": "AWS Rekognition not configured"}), 500
    
    try:
        file = request.files['image']
        image_bytes = file.read()
        
        response = rekognition.detect_labels(
            Image={'Bytes': image_bytes}, 
            MaxLabels=100, 
            MinConfidence=40
        )
        
        labels_info = []
        for label in response['Labels']:
            labels_info.append({
                'name': label['Name'],
                'confidence': round(label['Confidence'], 2),
                'categories': [cat['Name'] for cat in label.get('Categories', [])],
                'parents': [p['Name'] for p in label.get('Parents', [])]
            })
        
        return jsonify({
            "total_labels": len(labels_info),
            "labels": labels_info
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# NEW SHARING MODE ENDPOINTS
# ============================================================

# Initialize additional DynamoDB tables
users_table = None
inventory_table = None
trades_table = None

try:
    users_table = dynamodb.Table('Gro-SentialUsers')
    inventory_table = dynamodb.Table('Gro-SentialInventory')
    trades_table = dynamodb.Table('Gro-SentialTrades')
    print("✅ Sharing mode tables initialized")
except Exception as e:
    print(f"⚠️  Sharing mode tables not available: {e}")

# --- USER MANAGEMENT ---

@app.route('/register', methods=['POST'])
def register():
    """Register a new user with password authentication"""
    if not users_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        password = data.get('password', '')
        pincode = data.get('pincode', '').strip()
        
        if not email or not name or not password or not pincode:
            return jsonify({"status": "error", "message": "All fields are required"}), 400
        
        if len(password) < 6:
            return jsonify({"status": "error", "message": "Password must be at least 6 characters"}), 400
        
        # Check if user exists
        try:
            response = users_table.get_item(Key={'UserEmail': email})
            if 'Item' in response:
                return jsonify({"status": "error", "message": "User already exists"}), 400
        except:
            pass
        
        # Hash password with bcrypt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create new user
        from datetime import datetime
        users_table.put_item(Item={
            'UserEmail': email,
            'UserName': name,
            'PasswordHash': password_hash.decode('utf-8'),  # Store as string
            'Pincode': pincode,
            'CreatedAt': datetime.now().isoformat(),
            'TotalItems': 0,
            'KarmaPoints': 1000,
            'TradesCompleted': 0
        })
        
        print(f"✅ New user registered: {name} ({email})")
        return jsonify({
            "status": "success",
            "message": "User registered successfully",
            "user": {"email": email, "name": name, "pincode": pincode}
        })
    
    except Exception as e:
        print(f"❌ REGISTER ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    """Login user with password verification"""
    if not users_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({"status": "error", "message": "Email and password required"}), 400
        
        # Get user
        response = users_table.get_item(Key={'UserEmail': email})
        
        if 'Item' not in response:
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401
        
        user = response['Item']
        
        # Check if user has password hash (for backward compatibility with old users)
        if 'PasswordHash' not in user:
            return jsonify({
                "status": "error", 
                "message": "Account created before password system. Please contact admin to reset password."
            }), 401
        
        # Verify password
        stored_hash = user['PasswordHash'].encode('utf-8')
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401
        
        print(f"✅ User logged in: {user['UserName']} ({email})")
        
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": {
                "email": user['UserEmail'],
                "name": user['UserName'],
                "pincode": user['Pincode'],
                "karma": user.get('KarmaPoints', 1000),
                "totalItems": user.get('TotalItems', 0),
                "tradesCompleted": user.get('TradesCompleted', 0)
            }
        })
    
    except Exception as e:
        print(f"❌ LOGIN ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/user/<email>', methods=['GET'])
def get_user(email):
    """Get user profile"""
    if not users_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        response = users_table.get_item(Key={'UserEmail': email.lower()})
        
        if 'Item' not in response:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        user = response['Item']
        return jsonify({
            "status": "success",
            "user": {
                "email": user['UserEmail'],
                "name": user['UserName'],
                "pincode": user['Pincode'],
                "karma": user.get('KarmaPoints', 1000),
                "totalItems": user.get('TotalItems', 0),
                "tradesCompleted": user.get('TradesCompleted', 0)
            }
        })
    
    except Exception as e:
        print(f"❌ GET USER ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- INVENTORY MANAGEMENT ---

@app.route('/inventory/add', methods=['POST'])
def add_inventory():
    """Add items to user inventory with expiry dates"""
    if not inventory_table or not users_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        items = data.get('items', [])  # [{name, quantity, expiryDate}]
        
        if not email or not items:
            return jsonify({"status": "error", "message": "Email and items required"}), 400
        
        # Get user to verify and get pincode
        user_response = users_table.get_item(Key={'UserEmail': email})
        if 'Item' not in user_response:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        user = user_response['Item']
        pincode = user['Pincode']
        
        from datetime import datetime
        added_items = []
        
        for item in items:
            item_name = item.get('name', '').strip()
            quantity = item.get('quantity', 1)
            expiry_date = item.get('expiryDate', None)
            
            if not item_name:
                continue
            
            # Predict expiry date if not provided (80% safety margin)
            if not expiry_date:
                expiry_prediction = predict_expiry_date(item_name)
                expiry_date = expiry_prediction['expiry_date']
                print(f"  📅 Auto-predicted expiry for {item_name}: {expiry_date} ({expiry_prediction['shelf_life_days']} days)")
            
            # Add to inventory
            from decimal import Decimal
            unit_price = get_market_price(item_name)
            market_value = Decimal(str(round(unit_price * quantity, 2)))
            
            item_data = {
                'UserEmail': email,
                'ItemName': item_name,
                'Quantity': int(quantity),
                'MarketValue': market_value,
                'Pincode': pincode,
                'AddedAt': datetime.now().isoformat(),
                'Available': True,
                'ExpiryDate': expiry_date
            }
            
            inventory_table.put_item(Item=item_data)
            
            added_items.append({"name": item_name, "quantity": quantity, "expiryDate": expiry_date, "marketValue": float(market_value)})
        
        # Update user's total items count
        users_table.update_item(
            Key={'UserEmail': email},
            UpdateExpression='SET TotalItems = TotalItems + :val',
            ExpressionAttributeValues={':val': len(added_items)}
        )
        
        print(f"✅ Added {len(added_items)} items for {email}")
        return jsonify({
            "status": "success",
            "message": f"Added {len(added_items)} items to inventory",
            "items": added_items
        })
    
    except Exception as e:
        print(f"❌ ADD INVENTORY ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/inventory/<email>', methods=['GET'])
def get_inventory(email):
    """Get user's inventory with expiry status"""
    if not inventory_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        from datetime import datetime
        
        response = inventory_table.query(
            KeyConditionExpression='UserEmail = :email',
            ExpressionAttributeValues={':email': email.lower()}
        )
        
        items = response.get('Items', [])
        
        # Add expiry status and days remaining to each item
        for item in items:
            if 'ExpiryDate' in item:
                expiry_date = datetime.strptime(item['ExpiryDate'], '%Y-%m-%d')
                days_remaining = (expiry_date - datetime.now()).days
                status = get_expiry_status(days_remaining)
                
                item['DaysRemaining'] = days_remaining
                item['ExpiryStatus'] = status
                item['ExpiryColor'] = get_expiry_color(status)
        
        # Sort by days remaining (expiring items first)
        items_with_expiry = [item for item in items if 'DaysRemaining' in item]
        items_without_expiry = [item for item in items if 'DaysRemaining' not in item]
        items_with_expiry.sort(key=lambda x: x['DaysRemaining'])
        items = items_with_expiry + items_without_expiry
        
        return jsonify({
            "status": "success",
            "count": len(items),
            "items": items
        })
    
    except Exception as e:
        print(f"❌ GET INVENTORY ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/inventory/list', methods=['POST'])
def list_inventory():
    """Get user's inventory (POST version for mutual trade)"""
    if not inventory_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        from datetime import datetime
        
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({"status": "error", "message": "Email required"}), 400
        
        response = inventory_table.query(
            KeyConditionExpression='UserEmail = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        items = response.get('Items', [])
        
        # Add expiry status and days remaining to each item
        for item in items:
            if 'ExpiryDate' in item:
                expiry_date = datetime.strptime(item['ExpiryDate'], '%Y-%m-%d')
                days_remaining = (expiry_date - datetime.now()).days
                status = get_expiry_status(days_remaining)
                
                item['DaysRemaining'] = days_remaining
                item['ExpiryStatus'] = status
                item['ExpiryColor'] = get_expiry_color(status)
        
        # Sort by days remaining (expiring items first)
        items_with_expiry = [item for item in items if 'DaysRemaining' in item]
        items_without_expiry = [item for item in items if 'DaysRemaining' not in item]
        items_with_expiry.sort(key=lambda x: x['DaysRemaining'])
        items = items_with_expiry + items_without_expiry
        
        print(f"✅ Loaded {len(items)} items for mutual trade for {email}")
        
        return jsonify({
            "status": "success",
            "count": len(items),
            "items": items
        })
    
    except Exception as e:
        print(f"❌ LIST INVENTORY ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/inventory/list/<email>', methods=['GET'])
def list_inventory_get(email):
    """Get user's inventory (GET version)"""
    if not inventory_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        from datetime import datetime
        
        email = email.strip().lower()
        print(f"📋 Loading inventory for: {email}")
        
        response = inventory_table.query(
            KeyConditionExpression='UserEmail = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        items = response.get('Items', [])
        print(f"📦 Found {len(items)} items")
        
        # Add market value to each item
        for item in items:
            try:
                item_name = item.get('ItemName', '')
                quantity = item.get('Quantity', 1)
                market_price = get_market_price(item_name)
                item['MarketValue'] = round(market_price * quantity, 2)
                
                # Add expiry info if available
                if 'ExpiryDate' in item and item['ExpiryDate']:
                    try:
                        expiry_date = datetime.strptime(item['ExpiryDate'], '%Y-%m-%d')
                        days_remaining = (expiry_date - datetime.now()).days
                        status = get_expiry_status(days_remaining)
                        
                        item['DaysRemaining'] = days_remaining
                        item['ExpiryStatus'] = status
                        item['ExpiryColor'] = get_expiry_color(status)
                    except Exception as expiry_error:
                        print(f"⚠️ Error parsing expiry date for {item_name}: {expiry_error}")
                        # Continue without expiry info
            except Exception as item_error:
                print(f"⚠️ Error processing item {item.get('ItemName', 'unknown')}: {item_error}")
                # Continue with next item
        
        print(f"✅ Loaded {len(items)} items for {email}")
        
        return jsonify({
            "status": "success",
            "count": len(items),
            "items": items
        })
    
    except Exception as e:
        print(f"❌ LIST INVENTORY GET ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/inventory/update', methods=['PUT'])
def update_inventory():
    """Update item quantity"""
    if not inventory_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        item_name = data.get('itemName', '').strip()
        quantity = data.get('quantity', 1)
        
        if not email or not item_name:
            return jsonify({"status": "error", "message": "Email and itemName required"}), 400
        
        inventory_table.update_item(
            Key={'UserEmail': email, 'ItemName': item_name},
            UpdateExpression='SET Quantity = :qty',
            ExpressionAttributeValues={':qty': int(quantity)}
        )
        
        print(f"✅ Updated {item_name} quantity to {quantity} for {email}")
        return jsonify({
            "status": "success",
            "message": "Item updated successfully"
        })
    
    except Exception as e:
        print(f"❌ UPDATE INVENTORY ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/inventory/delete', methods=['DELETE'])
def delete_inventory():
    """Delete item from inventory"""
    if not inventory_table or not users_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        item_name = data.get('itemName', '').strip()
        
        if not email or not item_name:
            return jsonify({"status": "error", "message": "Email and itemName required"}), 400
        
        inventory_table.delete_item(
            Key={'UserEmail': email, 'ItemName': item_name}
        )
        
        # Update user's total items count
        users_table.update_item(
            Key={'UserEmail': email},
            UpdateExpression='SET TotalItems = TotalItems - :val',
            ExpressionAttributeValues={':val': 1}
        )
        
        print(f"✅ Deleted {item_name} for {email}")
        return jsonify({
            "status": "success",
            "message": "Item deleted successfully"
        })
    
    except Exception as e:
        print(f"❌ DELETE INVENTORY ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ITEM SEARCH ---

@app.route('/search/items', methods=['POST'])
def search_items():
    """Search for items by name and pincode (case-insensitive)"""
    if not inventory_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        item_name = data.get('itemName', '').strip()
        pincode = data.get('pincode', '').strip()
        requester_email = data.get('email', '').strip().lower()
        
        if not item_name or not pincode:
            return jsonify({"status": "error", "message": "itemName and pincode required"}), 400
        
        # Get ALL items in the pincode first (case-insensitive search)
        response = inventory_table.scan(
            FilterExpression='Pincode = :pin AND Available = :avail',
            ExpressionAttributeValues={
                ':pin': pincode,
                ':avail': True
            }
        )
        
        items = response.get('Items', [])
        
        # Filter by item name (case-insensitive) and exclude requester's items
        item_name_lower = item_name.lower()
        available_items = [
            item for item in items 
            if item['UserEmail'] != requester_email 
            and item.get('Available', True)
            and item_name_lower in item['ItemName'].lower()
        ]
        
        # Get user names for each item
        results = []
        for item in available_items:
            try:
                user_response = users_table.get_item(Key={'UserEmail': item['UserEmail']})
                if 'Item' in user_response:
                    user = user_response['Item']
                    results.append({
                        "itemName": item['ItemName'],
                        "quantity": item['Quantity'],
                        "providerEmail": item['UserEmail'],
                        "providerName": user['UserName'],
                        "addedAt": item.get('AddedAt', '')
                    })
            except:
                continue
        
        print(f"✅ Found {len(results)} items matching '{item_name}' in {pincode} (case-insensitive)")
        return jsonify({
            "status": "success",
            "count": len(results),
            "items": results
        })
    
    except Exception as e:
        print(f"❌ SEARCH ITEMS ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/search/all', methods=['POST'])
def search_all():
    """Get ALL available items from ALL pincodes - NO FILTERS"""
    print("\n" + "="*70)
    print("🌍🌍🌍 BROWSE ALL ENDPOINT HIT 🌍🌍🌍")
    print("="*70)
    
    if not inventory_table:
        print("❌ Database not configured")
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        requester_email = data.get('email', '').strip().lower()
        print(f"📧 Email from request: {requester_email}")
        
        # Scan ALL items - NO FILTER AT ALL
        print("🔍 Scanning DynamoDB with NO FILTERS...")
        response = inventory_table.scan()
        
        all_items = response.get('Items', [])
        print(f"📦 Total items in database: {len(all_items)}")
        
        if len(all_items) == 0:
            print("⚠️ Database is empty!")
            return jsonify({"status": "success", "count": 0, "items": []})
        
        # Filter for Available=True items
        available_items = [item for item in all_items if item.get('Available') == True]
        print(f"✅ Items with Available=True: {len(available_items)}")
        
        if len(available_items) == 0:
            print("⚠️ No items have Available=True")
            return jsonify({"status": "success", "count": 0, "items": []})
        
        # Build results - include ALL items (even user's own)
        results = []
        print(f"🔄 Processing {len(available_items)} items...")
        
        for idx, item in enumerate(available_items):
            try:
                user_email = item.get('UserEmail', '')
                item_name = item.get('ItemName', 'Unknown')
                
                if idx < 5:
                    print(f"  {idx+1}. {item_name} from {user_email}")
                
                user_response = users_table.get_item(Key={'UserEmail': user_email})
                if 'Item' in user_response:
                    user = user_response['Item']
                    market_value = float(item.get('MarketValue', 0))
                    karma_points = calculate_karma_points(market_value)
                    
                    results.append({
                        "itemName": item_name,
                        "quantity": item.get('Quantity', 0),
                        "providerEmail": user_email,
                        "providerName": user.get('UserName', 'Unknown'),
                        "providerPincode": user.get('Pincode', item.get('Pincode', 'Unknown')),
                        "marketValue": market_value,
                        "karmaPoints": karma_points,
                        "distance": 0
                    })
            except Exception as e:
                print(f"  ⚠️ Error processing {item.get('ItemName')}: {e}")
                continue
        
        print(f"✅ Returning {len(results)} items to frontend")
        print("="*70 + "\n")
        
        return jsonify({
            "status": "success",
            "count": len(results),
            "items": results
        })
    
    except Exception as e:
        print(f"❌ ERROR in search_all:")
        print(traceback.format_exc())
        print("="*70 + "\n")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/search/nearby', methods=['POST'])
def search_nearby():
    """Get all available items in pincode"""
    if not inventory_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        pincode = data.get('pincode', '').strip()
        requester_email = data.get('email', '').strip().lower()
        
        print(f"\n🔍 SEARCH NEARBY - Pincode: {pincode}, Requester: {requester_email}")
        
        if not pincode:
            return jsonify({"status": "error", "message": "pincode required"}), 400
        
        # Scan for items in pincode (in production, use better indexing)
        response = inventory_table.scan(
            FilterExpression='Pincode = :pin AND Available = :avail',
            ExpressionAttributeValues={
                ':pin': pincode,
                ':avail': True
            }
        )
        
        items = response.get('Items', [])
        print(f"📦 Found {len(items)} total items in pincode {pincode}")
        
        # Filter out requester's own items
        available_items = [item for item in items if item['UserEmail'] != requester_email]
        print(f"✅ After filtering out requester's items: {len(available_items)} items")
        
        if len(available_items) > 0:
            print(f"   Sample items:")
            for item in available_items[:5]:
                print(f"     - {item['ItemName']} from {item['UserEmail']}")
        
        # Get user names
        results = []
        for item in available_items:
            try:
                user_response = users_table.get_item(Key={'UserEmail': item['UserEmail']})
                if 'Item' in user_response:
                    user = user_response['Item']
                    # Calculate market value and karma points
                    market_value = float(item.get('MarketValue', 0))
                    karma_points = calculate_karma_points(market_value)
                    
                    results.append({
                        "itemName": item['ItemName'],
                        "quantity": item['Quantity'],
                        "providerEmail": item['UserEmail'],
                        "providerName": user['UserName'],
                        "providerPincode": user.get('Pincode', pincode),
                        "marketValue": market_value,
                        "karmaPoints": karma_points
                    })
            except Exception as e:
                print(f"⚠️ Error processing item {item.get('ItemName')}: {e}")
                continue
        
        print(f"✅ Returning {len(results)} items to frontend")
        return jsonify({
            "status": "success",
            "count": len(results),
            "items": results
        })
    
    except Exception as e:
        print(f"❌ SEARCH NEARBY ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- TRADE MANAGEMENT ---

@app.route('/trade/request', methods=['POST'])
def request_trade():
    """Create a trade request with AI-calculated value"""
    print("\n🔄 Trade request received")
    
    if not trades_table or not users_table:
        error_msg = f"Database not configured - trades_table: {trades_table is not None}, users_table: {users_table is not None}"
        print(f"❌ {error_msg}")
        return jsonify({"status": "error", "message": error_msg}), 500
    
    try:
        data = request.json
        print(f"📦 Request data: {data}")
        
        requester_email = data.get('requesterEmail', '').strip().lower()
        provider_email = data.get('providerEmail', '').strip().lower()
        item_name = data.get('itemName', '').strip()
        quantity = data.get('quantity', 1)
        offered_items = data.get('offeredItems', [])  # Array of items requester is offering
        message = data.get('message', '')  # Message from requester
        
        print(f"👤 Requester: {requester_email}, Provider: {provider_email}")
        print(f"📦 Item: {item_name} x{quantity}")
        print(f"🔄 Offered items: {offered_items}")
        if message:
            print(f"💬 Message: {message}")
        
        if not requester_email or not provider_email or not item_name:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        # Get user names with error handling
        try:
            print(f"🔍 Fetching user data...")
            req_user = users_table.get_item(Key={'UserEmail': requester_email}).get('Item', {})
            prov_user = users_table.get_item(Key={'UserEmail': provider_email}).get('Item', {})
            
            req_name = req_user.get('UserName') or req_user.get('Name') or requester_email
            prov_name = prov_user.get('UserName') or prov_user.get('Name') or provider_email
            req_pincode = req_user.get('Pincode', '60070')
            prov_pincode = prov_user.get('Pincode', '60070')
            print(f"✅ Users found - Requester: {req_name}, Provider: {prov_name}")
        except Exception as e:
            print(f"⚠️ Error fetching user data: {e}")
            req_name = requester_email
            prov_name = provider_email
            req_pincode = '60070'
            prov_pincode = '60070'
        
        # AI calculates trade value
        from decimal import Decimal
        import json
        print(f"💰 Calculating trade value...")
        market_value = Decimal(str(round(get_market_price(item_name) * quantity, 2)))
        karma_points = int(calculate_trade_points(item_name, quantity))
        print(f"💰 Market value: ${market_value}, Karma: {karma_points}")
        
        # Store offered items as JSON string
        receiver_offered_items_json = json.dumps(offered_items) if offered_items else ''
        
        # Calculate total offer value
        total_offer_value = Decimal('0')
        if offered_items:
            for item in offered_items:
                item_value = Decimal(str(item.get('value', 0)))
                total_offer_value += item_value
            print(f"🔄 Total offer value: ${total_offer_value}")
        
        # Create trade
        from datetime import datetime
        trade_id = str(uuid.uuid4())
        
        # Set initial status based on whether items were offered
        initial_status = 'receiver_offered' if offered_items else 'pending'
        
        print(f"💾 Creating trade record with status: {initial_status}...")
        trades_table.put_item(Item={
            'TradeID': trade_id,
            'RequesterEmail': requester_email,
            'RequesterName': req_name,
            'RequesterPincode': req_pincode,
            'RequesterIdentifier': '',  # Will be set later
            'ProviderEmail': provider_email,
            'ProviderName': prov_name,
            'ProviderPincode': prov_pincode,
            'ProviderIdentifier': '',  # Will be set later
            'ItemName': item_name,
            'Quantity': int(quantity),
            'MarketValue': market_value,
            'KarmaPoints': karma_points,
            'OfferItem': '',  # Legacy field, kept for compatibility
            'OfferQuantity': 0,  # Legacy field
            'OfferValue': Decimal('0'),  # Legacy field
            'OfferPoints': 0,  # Legacy field
            'Message': message,  # Message from requester
            'CounterOffer': '',  # Counter-offer message from provider
            'CounterOfferItem': '',  # Counter-offer item from provider
            'CounterOfferQuantity': 0,  # Counter-offer quantity
            'ReceiverOfferedItems': receiver_offered_items_json,  # Items receiver is offering (JSON)
            'ProviderSelectedItem': '',  # Item provider selected from receiver's list
            'ProviderSelectedQuantity': 0,  # Quantity provider selected
            'Status': initial_status,  # 'receiver_offered' if items provided, else 'pending'
            'MeetupLocation': f"Community Center, Pincode {req_pincode}",
            'MeetupTime': 'Saturday, 10:00 AM - 12:00 PM',
            'CreatedAt': datetime.now().isoformat(),
            'UpdatedAt': datetime.now().isoformat()
        })
        
        print(f"✅ Trade request created: {trade_id} | Value: ${market_value} ({karma_points} points)")
        return jsonify({
            "status": "success",
            "message": "Trade request sent",
            "tradeId": trade_id,
            "marketValue": float(market_value),  # Convert Decimal to float for JSON
            "karmaPoints": karma_points
        })
    
    except Exception as e:
        print(f"❌ REQUEST TRADE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@app.route('/trade/user/<email>', methods=['GET'])
def get_user_trades(email):
    """Get all trades for a user"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        email = email.lower()
        
        # Get trades where user is requester
        req_response = trades_table.query(
            IndexName='RequesterIndex',
            KeyConditionExpression='RequesterEmail = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        # Get trades where user is provider
        prov_response = trades_table.query(
            IndexName='ProviderIndex',
            KeyConditionExpression='ProviderEmail = :email',
            ExpressionAttributeValues={':email': email}
        )
        
        requested = req_response.get('Items', [])
        received = prov_response.get('Items', [])
        
        return jsonify({
            "status": "success",
            "requested": requested,
            "received": received,
            "total": len(requested) + len(received)
        })
    
    except Exception as e:
        print(f"❌ GET TRADES ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/update', methods=['PUT'])
def update_trade():
    """Update trade status and award karma points"""
    if not trades_table or not users_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        status = data.get('status', '').strip()
        
        if not trade_id or not status:
            return jsonify({"status": "error", "message": "tradeId and status required"}), 400
        
        if status not in ['pending', 'accepted', 'completed', 'cancelled']:
            return jsonify({"status": "error", "message": "Invalid status"}), 400
        
        from datetime import datetime
        
        # Get trade details first
        trade = trades_table.get_item(Key={'TradeID': trade_id})['Item']
        
        # Update trade
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression='SET #status = :status, UpdatedAt = :updated',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': status,
                ':updated': datetime.now().isoformat()
            }
        )
        
        # If completed, award karma points based on trade value
        if status == 'completed':
            karma_points = trade.get('KarmaPoints', 50)  # AI-calculated points
            
            # Both users get karma (provider gets full points, requester gets half)
            users_table.update_item(
                Key={'UserEmail': trade['ProviderEmail']},
                UpdateExpression='SET KarmaPoints = KarmaPoints + :karma, TradesCompleted = TradesCompleted + :one',
                ExpressionAttributeValues={':karma': karma_points, ':one': 1}
            )
            
            users_table.update_item(
                Key={'UserEmail': trade['RequesterEmail']},
                UpdateExpression='SET KarmaPoints = KarmaPoints + :karma, TradesCompleted = TradesCompleted + :one',
                ExpressionAttributeValues={':karma': karma_points // 2, ':one': 1}
            )
            
            print(f"✅ Trade completed! Provider earned {karma_points} points, Requester earned {karma_points // 2} points")
        
        print(f"✅ Trade {trade_id} updated to {status}")
        return jsonify({
            "status": "success",
            "message": f"Trade {status}"
        })
    
    except Exception as e:
        print(f"❌ UPDATE TRADE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/schedule', methods=['PUT'])
def schedule_trade():
    """Update trade meetup details"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        location = data.get('location', '').strip()
        time = data.get('time', '').strip()
        
        if not trade_id or not location or not time:
            return jsonify({"status": "error", "message": "tradeId, location, and time required"}), 400
        
        from datetime import datetime
        
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression='SET MeetupLocation = :loc, MeetupTime = :time, UpdatedAt = :updated',
            ExpressionAttributeValues={
                ':loc': location,
                ':time': time,
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"✅ Trade {trade_id} scheduled: {location} at {time}")
        return jsonify({
            "status": "success",
            "message": "Meetup scheduled"
        })
    
    except Exception as e:
        print(f"❌ SCHEDULE TRADE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/chatbot', methods=['POST'])
def chatbot():
    """Intelligent chatbot with full dashboard control - Kiro-level intelligence"""
    try:
        data = request.json
        question = data.get('question', '').lower()
        current_ingredients = data.get('currentIngredients', [])
        context = data.get('context', {})
        
        print(f"\n💬 Chatbot Query: {question}")
        print(f"📋 Current Ingredients: {current_ingredients}")
        print(f"🎯 Context: {context}")
        
        # ============================================================
        # INGREDIENT REMOVAL - "I don't like X", "Remove X", "No X"
        # ============================================================
        remove_keywords = ['don\'t like', 'do not like', 'hate', 'allergic to', 'allergy', 
                          'remove', 'delete', 'take out', 'without', 'no ', 'exclude']
        
        is_removal = any(keyword in question for keyword in remove_keywords)
        
        if is_removal and current_ingredients:
            # Extract ingredients to remove
            ingredients_to_remove = []
            
            # Check each current ingredient
            for ing in current_ingredients:
                if ing.lower() in question:
                    ingredients_to_remove.append(ing)
            
            # Also check common ingredients
            common_ingredients = [
                'oil', 'olive oil', 'butter', 'salt', 'pepper', 'garlic', 'onion',
                'tomato', 'carrot', 'potato', 'egg', 'cheese', 'milk', 'cream',
                'flour', 'sugar', 'rice', 'pasta', 'bread', 'chicken', 'beef',
                'fish', 'lemon', 'lime', 'herbs', 'spices', 'vinegar', 'soy sauce',
                'nuts', 'peanuts', 'shellfish', 'dairy', 'gluten', 'soy'
            ]
            
            for ing in common_ingredients:
                if ing in question and ing.capitalize() not in ingredients_to_remove:
                    ingredients_to_remove.append(ing.capitalize())
            
            if ingredients_to_remove:
                # Remove the ingredients
                new_ingredients = [ing for ing in current_ingredients 
                                 if ing not in ingredients_to_remove]
                
                removed_list = ', '.join(ingredients_to_remove)
                
                if len(new_ingredients) > 0:
                    response = f"✅ Got it! I've removed {removed_list} from your recipe. Generating a new recipe without those ingredients now..."
                    
                    return jsonify({
                        "status": "success",
                        "response": response,
                        "action": "remove_ingredients",
                        "ingredients": new_ingredients,
                        "regenerate": True
                    })
                else:
                    response = f"⚠️ If I remove {removed_list}, you won't have any ingredients left! Please add some ingredients first, or tell me what you DO have."
                    return jsonify({
                        "status": "success",
                        "response": response
                    })
        
        # ============================================================
        # INGREDIENT ADDITION - "Add X", "I have X", "Include X"
        # ============================================================
        add_keywords = ['add', 'include', 'i have', 'i\'ve got', 'use', 'with', 
                       'also have', 'got', 'want to add', 'put in']
        
        is_addition = any(keyword in question for keyword in add_keywords)
        
        if is_addition:
            # Extract ingredients to add
            ingredients_to_add = []
            
            common_ingredients = [
                'butter', 'oil', 'olive oil', 'salt', 'pepper', 'garlic', 'onion',
                'tomato', 'carrot', 'potato', 'egg', 'cheese', 'milk', 'cream',
                'flour', 'sugar', 'rice', 'pasta', 'bread', 'chicken', 'beef',
                'fish', 'lemon', 'lime', 'herbs', 'spices', 'vinegar', 'soy sauce',
                'ginger', 'basil', 'parsley', 'cilantro', 'mushroom', 'broccoli',
                'spinach', 'lettuce', 'cucumber', 'pepper', 'bell pepper'
            ]
            
            for ing in common_ingredients:
                if ing in question:
                    capitalized = ing.capitalize()
                    if capitalized not in current_ingredients:
                        ingredients_to_add.append(capitalized)
            
            if ingredients_to_add:
                new_ingredients = current_ingredients + ingredients_to_add
                added_list = ', '.join(ingredients_to_add)
                
                response = f"✅ Perfect! I've added {added_list} to your recipe. Generating an updated recipe now..."
                
                return jsonify({
                    "status": "success",
                    "response": response,
                    "action": "add_ingredients",
                    "ingredients": new_ingredients,
                    "regenerate": True
                })
        
        # ============================================================
        # SUBSTITUTION - "Use X instead of Y", "Replace X with Y"
        # ============================================================
        substitute_keywords = ['instead of', 'replace', 'substitute', 'swap', 'change']
        
        is_substitution = any(keyword in question for keyword in substitute_keywords)
        
        if is_substitution and current_ingredients:
            # This is a combination of remove + add
            response = "✅ I understand you want to substitute ingredients. Let me help with that! "
            response += "Tell me specifically: 'Remove [ingredient]' and 'Add [ingredient]', or say 'I only have [ingredients]'."
            
            return jsonify({
                "status": "success",
                "response": response
            })
        
        # ============================================================
        # RECIPE MODIFICATION - "I only have X", "Just have X"
        # ============================================================
        only_have_keywords = ['only have', 'just have', 'all i have', 'all i\'ve got']
        
        is_only_have = any(keyword in question for keyword in only_have_keywords)
        
        if is_only_have:
            # Extract what they have
            ingredients_mentioned = []
            
            common_ingredients = [
                'butter', 'oil', 'olive oil', 'salt', 'pepper', 'garlic', 'onion',
                'tomato', 'carrot', 'potato', 'egg', 'cheese', 'milk', 'cream',
                'flour', 'sugar', 'rice', 'pasta', 'bread', 'chicken', 'beef',
                'fish', 'lemon', 'lime', 'herbs', 'spices', 'vinegar', 'soy sauce'
            ]
            
            for ing in common_ingredients:
                if ing in question:
                    ingredients_mentioned.append(ing.capitalize())
            
            if ingredients_mentioned:
                # Combine with current ingredients
                new_ingredients = list(set(current_ingredients + ingredients_mentioned))
                mentioned_list = ', '.join(ingredients_mentioned)
                
                response = f"✅ Perfect! I'll create a recipe using what you have: {mentioned_list}. Generating now..."
                
                return jsonify({
                    "status": "success",
                    "response": response,
                    "action": "regenerate_recipe",
                    "ingredients": new_ingredients
                })
        
        # ============================================================
        # DASHBOARD CONTROL - "Show inventory", "Search for X"
        # ============================================================
        if 'show' in question and ('inventory' in question or 'items' in question):
            if context.get('isLoggedIn'):
                return jsonify({
                    "status": "success",
                    "response": "📦 Here's your inventory! Switching to Sharing Mode...",
                    "action": "show_inventory"
                })
            else:
                return jsonify({
                    "status": "success",
                    "response": "🔐 Please login first to see your inventory. Click on 'Guest' in the top-right corner."
                })
        
        if 'search' in question or 'find' in question:
            # Extract search term
            search_terms = []
            common_items = ['tomato', 'carrot', 'potato', 'onion', 'garlic', 'egg', 
                          'cheese', 'milk', 'bread', 'chicken', 'rice', 'pasta']
            
            for item in common_items:
                if item in question:
                    search_terms.append(item)
            
            if search_terms and context.get('isLoggedIn'):
                return jsonify({
                    "status": "success",
                    "response": f"🔍 Searching for {search_terms[0]} in your area...",
                    "action": "search_items",
                    "searchTerm": search_terms[0]
                })
            elif not context.get('isLoggedIn'):
                return jsonify({
                    "status": "success",
                    "response": "🔐 Please login first to search for items."
                })
        
        if 'recipe mode' in question or 'generate recipe' in question:
            return jsonify({
                "status": "success",
                "response": "🍳 Switching to Recipe Mode...",
                "action": "switch_mode",
                "mode": "recipe"
            })
        
        if 'sharing mode' in question or 'share food' in question:
            return jsonify({
                "status": "success",
                "response": "🤝 Switching to Sharing Mode...",
                "action": "switch_mode",
                "mode": "sharing"
            })
        
        # ============================================================
        # STANDARD RESPONSES - Help, Info, etc.
        # ============================================================
        if 'recipe' in question or 'cook' in question:
            response = "🍳 I can help you with recipes!\n\n"
            response += "Try saying:\n"
            response += "• 'Remove oil' - I'll remove it and regenerate\n"
            response += "• 'Add garlic' - I'll add it and regenerate\n"
            response += "• 'I don't like onions' - I'll remove them\n"
            response += "• 'I only have butter' - I'll create a recipe with butter\n\n"
            response += "I'll automatically update your recipe and videos!"
            
        elif 'share' in question or 'inventory' in question:
            response = "📦 To share food:\n1. Switch to Sharing Mode\n2. Upload a photo or manually add items\n3. Items are added to your inventory\n4. Other users can search and request trades!\n\nTry: 'Show my inventory' or 'Search for tomatoes'"
            
        elif 'trade' in question:
            response = "🤝 To trade items:\n1. Go to Search Items\n2. Find what you need\n3. Click 'Request Trade'\n4. Customize meetup location/time\n5. Wait for provider to accept!"
            
        elif 'help' in question or 'what can you do' in question or 'how' in question:
            response = "💡 I'm your intelligent assistant! I can:\n\n"
            response += "🍳 Recipe Control:\n"
            response += "• Remove ingredients: 'I don't like oil'\n"
            response += "• Add ingredients: 'Add garlic'\n"
            response += "• Modify recipes: 'I only have butter'\n"
            response += "• Regenerate automatically\n\n"
            response += "📦 Dashboard Control:\n"
            response += "• 'Show my inventory'\n"
            response += "• 'Search for tomatoes'\n"
            response += "• 'Switch to recipe mode'\n\n"
            response += "Just talk to me naturally - I understand!"
            
        else:
            response = "👋 Hi! I'm your intelligent assistant.\n\n"
            response += "I can help you:\n"
            response += "• Modify recipes (remove/add ingredients)\n"
            response += "• Control the dashboard\n"
            response += "• Search for items\n"
            response += "• Answer questions\n\n"
            response += "Try: 'I don't like oil' or 'Add garlic' or 'Show my inventory'"
        
        return jsonify({
            "status": "success",
            "response": response
        })
    
    except Exception as e:
        print(f"❌ CHATBOT ERROR: {traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "response": "I'm here to help! I can modify recipes, add/remove ingredients, search for items, and control the dashboard. Just tell me what you need!"
        }), 200

@app.route('/chatbot_ai', methods=['POST'])
def chatbot_ai():
    """Enhanced intelligent chatbot with database access using AWS Bedrock"""
    if not bedrock_runtime:
        # Fallback to basic chatbot
        return chatbot()
    
    try:
        data = request.json
        question = data.get('question', '')
        current_ingredients = data.get('currentIngredients', [])
        user_email = data.get('userEmail', '')
        conversation_history = data.get('conversationHistory', [])
        
        print(f"\n🤖 AI Chatbot Query: {question}")
        
        # INTELLIGENT SEARCH: Detect if user is asking about item availability
        search_keywords = ['who has', 'find', 'search', 'looking for', 'need', 'want', 'available', 'get']
        is_search_query = any(keyword in question.lower() for keyword in search_keywords)
        
        database_context = ""
        
        if is_search_query and dynamodb:
            print("  🔍 Detected search query - querying database...")
            
            # Get user's pincode
            user_pincode = None
            if user_email:
                try:
                    users_table = dynamodb.Table('Gro-SentialUsers')
                    user_response = users_table.get_item(Key={'UserEmail': user_email})
                    user_pincode = user_response.get('Item', {}).get('Pincode', '')
                except:
                    pass
            
            # Extract item name from question (comprehensive food item detection)
            question_lower = question.lower()
            common_items = [
                # Proteins
                'chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'shrimp', 'turkey', 'lamb',
                'egg', 'eggs', 'tofu', 'tempeh',
                # Dairy
                'milk', 'cheese', 'butter', 'yogurt', 'cream', 'paneer', 'curd',
                # Vegetables
                'tomato', 'tomatoes', 'potato', 'potatoes', 'onion', 'onions', 'garlic', 
                'carrot', 'carrots', 'spinach', 'lettuce', 'cabbage', 'broccoli', 'cauliflower',
                'pepper', 'peppers', 'cucumber', 'zucchini', 'eggplant', 'mushroom', 'mushrooms',
                'celery', 'kale', 'peas', 'beans', 'corn',
                # Fruits
                'apple', 'apples', 'banana', 'bananas', 'orange', 'oranges', 'grape', 'grapes',
                'strawberry', 'strawberries', 'mango', 'mangoes', 'pineapple', 'watermelon',
                'lemon', 'lemons', 'lime', 'limes', 'avocado', 'avocados',
                # Grains & Staples
                'rice', 'bread', 'pasta', 'noodles', 'flour', 'oats', 'quinoa', 'barley',
                # Condiments & Others
                'salt', 'sugar', 'oil', 'vinegar', 'sauce', 'spice', 'herb', 'honey'
            ]
            
            found_items = [item for item in common_items if item in question_lower]
            
            if found_items and user_pincode:
                search_item = found_items[0]
                print(f"  📦 Searching for: {search_item} in and near pincode {user_pincode}")
                
                # Search database - EXPANDED TO NEARBY PINCODES
                try:
                    inventory_table = dynamodb.Table('Gro-SentialInventory')
                    users_table = dynamodb.Table('Gro-SentialUsers')
                    
                    # Calculate nearby pincodes (within ±10 range)
                    try:
                        base_pincode = int(user_pincode)
                        nearby_pincodes = [str(base_pincode + i) for i in range(-10, 11)]
                    except:
                        nearby_pincodes = [user_pincode]
                    
                    # Get ALL available items (scan entire inventory)
                    response = inventory_table.scan(
                        FilterExpression='Available = :avail',
                        ExpressionAttributeValues={':avail': True}
                    )
                    
                    # Filter and categorize by pincode distance
                    same_pincode_matches = []
                    nearby_matches = []
                    
                    for item in response.get('Items', []):
                        item_name = item.get('ItemName', '')
                        item_pincode = item.get('Pincode', '')
                        
                        # Check if item matches search
                        if search_item.lower() not in item_name.lower():
                            continue
                        
                        provider_email = item.get('UserEmail', '')
                        if provider_email == user_email:  # Skip self
                            continue
                        
                        # Get provider details
                        user_resp = users_table.get_item(Key={'UserEmail': provider_email})
                        provider = user_resp.get('Item', {})
                        
                        # Calculate expiry status
                        expiry_str = item.get('ExpiryDate', '')
                        expiry_status = "Unknown"
                        days_left = None
                        if expiry_str:
                            try:
                                from datetime import datetime
                                expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d')
                                days_left = (expiry_date - datetime.now()).days
                                if days_left < 0:
                                    expiry_status = "Expired"
                                elif days_left <= 2:
                                    expiry_status = "Expires very soon"
                                elif days_left <= 5:
                                    expiry_status = "Expires soon"
                                else:
                                    expiry_status = f"Fresh ({days_left} days left)"
                            except:
                                pass
                        
                        # Calculate pincode distance
                        try:
                            distance = abs(int(item_pincode) - int(user_pincode))
                        except:
                            distance = 999
                        
                        match_data = {
                            'name': provider.get('UserName', 'Unknown'),
                            'email': provider_email,
                            'item': item_name,
                            'quantity': item.get('Quantity', 0),
                            'unit': item.get('Unit', 'units'),
                            'pincode': item_pincode,
                            'distance': distance,
                            'expiry': expiry_str,
                            'expiryStatus': expiry_status,
                            'daysLeft': days_left if days_left is not None else 999,
                            'karma': provider.get('KarmaPoints', 0)
                        }
                        
                        # Categorize by location
                        if item_pincode == user_pincode:
                            same_pincode_matches.append(match_data)
                        elif item_pincode in nearby_pincodes:
                            nearby_matches.append(match_data)
                    
                    # Sort both lists by expiry (prioritize expiring items)
                    same_pincode_matches.sort(key=lambda x: x['daysLeft'])
                    nearby_matches.sort(key=lambda x: (x['distance'], x['daysLeft']))
                    
                    total_matches = len(same_pincode_matches) + len(nearby_matches)
                    
                    if total_matches > 0:
                        database_context = f"\n\n📊 DATABASE SEARCH RESULTS for '{search_item}':\n"
                        database_context += f"Total: {total_matches} user(s) found\n\n"
                        
                        # Show same pincode first
                        if same_pincode_matches:
                            database_context += f"🏠 IN YOUR AREA (Pincode {user_pincode}):\n"
                            for i, match in enumerate(same_pincode_matches[:5], 1):
                                database_context += f"{i}. {match['name']}\n"
                                database_context += f"   • Item: {match['item']}\n"
                                database_context += f"   • Quantity: {match['quantity']} {match['unit']}\n"
                                database_context += f"   • Pincode: {match['pincode']} (YOUR AREA)\n"
                                database_context += f"   • Status: {match['expiryStatus']}\n"
                                if match['expiry']:
                                    database_context += f"   • Expiry Date: {match['expiry']}\n"
                                database_context += f"   • Karma Points: {match['karma']}\n\n"
                        
                        # Show nearby pincodes
                        if nearby_matches:
                            database_context += f"\n📍 NEARBY AREAS:\n"
                            for i, match in enumerate(nearby_matches[:5], 1):
                                database_context += f"{i}. {match['name']}\n"
                                database_context += f"   • Item: {match['item']}\n"
                                database_context += f"   • Quantity: {match['quantity']} {match['unit']}\n"
                                database_context += f"   • Pincode: {match['pincode']} (Distance: {match['distance']} units)\n"
                                database_context += f"   • Status: {match['expiryStatus']}\n"
                                if match['expiry']:
                                    database_context += f"   • Expiry Date: {match['expiry']}\n"
                                database_context += f"   • Karma Points: {match['karma']}\n\n"
                        
                        print(f"  ✅ Found {len(same_pincode_matches)} in same pincode, {len(nearby_matches)} nearby")
                    else:
                        database_context = f"\n\n📊 DATABASE SEARCH: No users found with '{search_item}' in your area or nearby."
                        print(f"  ❌ No matches found")
                        
                except Exception as e:
                    print(f"  ⚠️ Database search error: {str(e)}")
        
        # Build context for Bedrock
        context = f"""You are an intelligent assistant for Gro-Sential, a zero-waste food sharing platform.

Current ingredients available: {', '.join(current_ingredients) if current_ingredients else 'None yet'}
User: {user_email if user_email else 'Guest'}

{database_context}

User question: {question}

INSTRUCTIONS:
- If database results are provided above, use them to give a detailed, helpful answer
- Include specific names, quantities, expiry dates, and pincode information
- Prioritize items expiring soon for sustainability
- Suggest contacting users through the app's trade feature
- If no database results, provide general cooking/food advice
- Be friendly, concise, and actionable
- For dietary restrictions: suggest substitutions
- For recipe help: provide practical tips
- For storage: give shelf life advice

Keep response natural and conversational (3-5 sentences)."""

        # Call AWS Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": context
                }
            ],
            "temperature": 0.7
        }
        
        print("  🤖 Calling AWS Bedrock for intelligent response...")
        response = bedrock_runtime.invoke_model(
            # Use cross-region inference profile (new AWS requirement)
            modelId='us.anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        ai_response = response_body['content'][0]['text']
        
        print(f"✅ Generated intelligent AI response")
        
        return jsonify({
            "status": "success",
            "response": ai_response,
            "source": "bedrock",
            "hasSearchResults": bool(database_context)
        })
    
    except Exception as e:
        print(f"❌ AI CHATBOT ERROR: {traceback.format_exc()}")
        # Fallback to basic chatbot
        return chatbot()

@app.route('/trade/set_identifier', methods=['PUT'])
def set_trade_identifier():
    """Set user's identification for meetup (what they'll be wearing/carrying)"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        email = data.get('email', '').strip().lower()
        identifier = data.get('identifier', '').strip()
        
        if not trade_id or not email or not identifier:
            return jsonify({"status": "error", "message": "tradeId, email, and identifier required"}), 400
        
        # Get the trade to determine if user is requester or provider
        trade = trades_table.get_item(Key={'TradeID': trade_id})['Item']
        
        from datetime import datetime
        
        # Update the appropriate identifier field
        if trade['RequesterEmail'] == email:
            trades_table.update_item(
                Key={'TradeID': trade_id},
                UpdateExpression='SET RequesterIdentifier = :id, UpdatedAt = :updated',
                ExpressionAttributeValues={
                    ':id': identifier,
                    ':updated': datetime.now().isoformat()
                }
            )
        elif trade['ProviderEmail'] == email:
            trades_table.update_item(
                Key={'TradeID': trade_id},
                UpdateExpression='SET ProviderIdentifier = :id, UpdatedAt = :updated',
                ExpressionAttributeValues={
                    ':id': identifier,
                    ':updated': datetime.now().isoformat()
                }
            )
        else:
            return jsonify({"status": "error", "message": "User not part of this trade"}), 403
        
        print(f"✅ Set identifier for trade {trade_id}: {identifier}")
        return jsonify({
            "status": "success",
            "message": "Identifier set successfully"
        })
    
    except Exception as e:
        print(f"❌ SET IDENTIFIER ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/counter_offer', methods=['PUT'])
def counter_offer_trade():
    """Provider makes a counter-offer with different items"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        counter_item = data.get('counterItem', '').strip()
        counter_quantity = data.get('counterQuantity', 0)
        counter_message = data.get('counterMessage', '').strip()
        
        if not trade_id or not counter_item or not counter_quantity:
            return jsonify({"status": "error", "message": "tradeId, counterItem, and counterQuantity required"}), 400
        
        from datetime import datetime
        from decimal import Decimal
        
        # Calculate counter-offer value
        counter_value = Decimal(str(round(get_market_price(counter_item) * counter_quantity, 2)))
        
        # Update trade with counter-offer
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression='SET CounterOfferItem = :item, CounterOfferQuantity = :qty, CounterOffer = :msg, #status = :status, UpdatedAt = :updated',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':item': counter_item,
                ':qty': int(counter_quantity),
                ':msg': counter_message,
                ':status': 'counter_offered',
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"✅ Counter-offer made for trade {trade_id}: {counter_item} x{counter_quantity}")
        return jsonify({
            "status": "success",
            "message": "Counter-offer sent successfully"
        })
    
    except Exception as e:
        print(f"❌ COUNTER OFFER ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/accept', methods=['PUT'])
def accept_trade():
    """Accept a trade or counter-offer"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        
        if not trade_id:
            return jsonify({"status": "error", "message": "tradeId required"}), 400
        
        from datetime import datetime
        
        # Update trade status to accepted
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression='SET #status = :status, UpdatedAt = :updated',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': 'accepted',
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"✅ Trade accepted: {trade_id}")
        return jsonify({
            "status": "success",
            "message": "Trade accepted successfully"
        })
    
    except Exception as e:
        print(f"❌ ACCEPT TRADE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/reject', methods=['PUT'])
def reject_trade():
    """Reject a trade or counter-offer"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        reject_message = data.get('message', '').strip()
        
        if not trade_id:
            return jsonify({"status": "error", "message": "tradeId required"}), 400
        
        from datetime import datetime
        
        # Update trade status to rejected
        update_expr = 'SET #status = :status, UpdatedAt = :updated'
        expr_values = {
            ':status': 'rejected',
            ':updated': datetime.now().isoformat()
        }
        
        if reject_message:
            update_expr += ', CounterOffer = :msg'
            expr_values[':msg'] = f"REJECTED: {reject_message}"
        
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues=expr_values
        )
        
        print(f"✅ Trade rejected: {trade_id}")
        return jsonify({
            "status": "success",
            "message": "Trade rejected"
        })
    
    except Exception as e:
        print(f"❌ REJECT TRADE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/cancel', methods=['PUT'])
def cancel_trade():
    """Cancel a trade (either party can cancel)"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        cancel_message = data.get('message', '').strip()
        
        if not trade_id:
            return jsonify({"status": "error", "message": "tradeId required"}), 400
        
        from datetime import datetime
        
        # Update trade status to cancelled
        update_expr = 'SET #status = :status, UpdatedAt = :updated'
        expr_values = {
            ':status': 'cancelled',
            ':updated': datetime.now().isoformat()
        }
        
        if cancel_message:
            update_expr += ', CounterOffer = :msg'
            expr_values[':msg'] = f"CANCELLED: {cancel_message}"
        
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues=expr_values
        )
        
        print(f"✅ Trade cancelled: {trade_id}")
        return jsonify({
            "status": "success",
            "message": "Trade cancelled successfully"
        })
    
    except Exception as e:
        print(f"❌ CANCEL TRADE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/receiver_offer_items', methods=['PUT'])
def receiver_offer_items():
    """Receiver selects items they're willing to trade"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        offered_items = data.get('offeredItems', [])  # List of {itemName, quantity, value}
        
        if not trade_id or not offered_items:
            return jsonify({"status": "error", "message": "tradeId and offeredItems required"}), 400
        
        from datetime import datetime
        import json
        
        # Store offered items as JSON string
        offered_items_json = json.dumps(offered_items)
        
        # Update trade with receiver's offered items and change status
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression='SET ReceiverOfferedItems = :items, #status = :status, UpdatedAt = :updated',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':items': offered_items_json,
                ':status': 'receiver_offered',
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"✅ Receiver offered items for trade {trade_id}: {len(offered_items)} items")
        return jsonify({
            "status": "success",
            "message": "Items offered successfully. Provider will be notified."
        })
    
    except Exception as e:
        print(f"❌ RECEIVER OFFER ITEMS ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/provider_select_item', methods=['PUT'])
def provider_select_item():
    """Provider selects item from receiver's offered list"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId', '').strip()
        selected_item = data.get('selectedItem', '').strip()
        selected_quantity = data.get('selectedQuantity', 0)
        
        if not trade_id or not selected_item or not selected_quantity:
            return jsonify({"status": "error", "message": "tradeId, selectedItem, and selectedQuantity required"}), 400
        
        from datetime import datetime
        
        # Update trade with provider's selection and change status to accepted
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression='SET ProviderSelectedItem = :item, ProviderSelectedQuantity = :qty, #status = :status, UpdatedAt = :updated',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':item': selected_item,
                ':qty': int(selected_quantity),
                ':status': 'accepted',
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"✅ Provider selected item for trade {trade_id}: {selected_item} x{selected_quantity}")
        return jsonify({
            "status": "success",
            "message": "Item selected. Trade accepted!"
        })
    
    except Exception as e:
        print(f"❌ PROVIDER SELECT ITEM ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/accept_direct', methods=['PUT'])
def accept_trade_direct():
    """Accept trade with all offered items (simplified flow)"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId')
        
        if not trade_id:
            return jsonify({"status": "error", "message": "Missing trade ID"}), 400
        
        # Get trade
        trade_response = trades_table.get_item(Key={'TradeID': trade_id})
        trade = trade_response.get('Item')
        
        if not trade:
            return jsonify({"status": "error", "message": "Trade not found"}), 404
        
        # Update trade status to accepted
        from datetime import datetime
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression='SET #status = :status, UpdatedAt = :updated',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': 'accepted',
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"✅ Trade {trade_id} accepted directly")
        
        return jsonify({
            "status": "success",
            "message": "Trade accepted"
        })
    
    except Exception as e:
        print(f"❌ ACCEPT TRADE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/trade/negotiate', methods=['PUT'])
def negotiate_trade():
    """Send negotiation message for trade"""
    if not trades_table:
        return jsonify({"status": "error", "message": "Database not configured"}), 500
    
    try:
        data = request.json
        trade_id = data.get('tradeId')
        message = data.get('message', '').strip()
        sender_email = data.get('senderEmail', '').strip().lower()
        
        if not trade_id or not message or not sender_email:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        # Get trade
        trade_response = trades_table.get_item(Key={'TradeID': trade_id})
        trade = trade_response.get('Item')
        
        if not trade:
            return jsonify({"status": "error", "message": "Trade not found"}), 404
        
        # Update CounterOffer field (this is what the frontend looks for!)
        from datetime import datetime
        
        trades_table.update_item(
            Key={'TradeID': trade_id},
            UpdateExpression='SET CounterOffer = :msg, UpdatedAt = :updated',
            ExpressionAttributeValues={
                ':msg': message,
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"💬 Negotiation message added to trade {trade_id}")
        
        return jsonify({
            "status": "success",
            "message": "Negotiation message sent"
        })
    
    except Exception as e:
        print(f"❌ NEGOTIATE TRADE ERROR: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/version')
def get_version():
    """Return current version for debugging"""
    return jsonify({
        "version": "2.1.0",
        "features": [
            "Negotiation messages visible",
            "Update offer UI implemented",
            "Item names display correctly"
        ],
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🌱 Gro-Sential Backend Server Starting...")
    print("="*50)
    print(f"📍 Region: {AWS_REGION}")
    print(f"🔑 Access Key: {ACCESS_KEY[:10]}..." if ACCESS_KEY else "❌ No Access Key")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
