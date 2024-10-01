import os
from dotenv import load_dotenv
import requests
import anthropic
import time
import html

print("Starting script...")

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Access environment variables
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
SHOPIFY_STORE_URL = os.getenv('SHOPIFY_STORE_URL')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')

print(f"SHOPIFY_STORE_URL: {SHOPIFY_STORE_URL}")
print(f"SHOPIFY_ACCESS_TOKEN: {'*' * len(SHOPIFY_ACCESS_TOKEN) if SHOPIFY_ACCESS_TOKEN else 'Not set'}")
print(f"CLAUDE_API_KEY: {CLAUDE_API_KEY[:5]}...{CLAUDE_API_KEY[-5:] if CLAUDE_API_KEY else 'Not set'}")

# Initialize Anthropic client
try:
    claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    # Test the API key with a simple request
    response = claude.completions.create(
        model="claude-2.1",
        prompt=f"{anthropic.HUMAN_PROMPT} Hello, Claude! {anthropic.AI_PROMPT}",
        max_tokens_to_sample=100
    )
    print("Claude API authentication successful.")
except anthropic.APIError as e:
    print(f"Claude API Error: {e.status_code} - {e.message}")
    exit(1)
except Exception as e:
    print(f"Unexpected error initializing Claude API: {str(e)}")
    exit(1)

def fetch_shopify_products():
    print(f"Fetching products from Shopify API")
    if not all([SHOPIFY_STORE_URL, SHOPIFY_ACCESS_TOKEN]):
        print("Error: Shopify store URL or Access Token is not set. Please check your .env file.")
        return []
    
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/2023-04/products.json"
    params = {
        'fields': 'id,title,body_html,handle,variants,metafields',
        'limit': 10  # Adjust as needed
    }
    headers = {
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        products = data.get('products', [])
        
        print(f"Found {len(products)} products")
        
        formatted_products = []
        for product in products:
            title = product.get('title', 'No title')
            description = html.unescape(product.get('body_html', 'No description'))
            variants = product.get('variants', [])
            metafields = product.get('metafields', [])
            
            formatted_product = {
                'title': title,
                'description': description,
                'variants': [{'title': v.get('title'), 'price': v.get('price')} for v in variants],
                'metafields': {m.get('key'): m.get('value') for m in metafields}
            }
            formatted_products.append(formatted_product)
            print(f"Product: {title}, Variants: {len(variants)}, Metafields: {len(metafields)}")
        
        return formatted_products
    
    except requests.RequestException as e:
        print(f"Error fetching products from Shopify API: {e}")
        return []

def generate_blog_post(product):
    print(f"Generating blog post for: {product['title']}")
    
    metafields_info = "\n".join([f"{key}: {value}" for key, value in product['metafields'].items()])
    variants_info = "\n".join([f"- {v['title']}: ${v['price']}" for v in product['variants']])
    
    prompt = f"""{anthropic.HUMAN_PROMPT} Write a 300-word blog post for an e-commerce website about the following product:

Title: {product['title']}
Description: {product['description']}

Variants:
{variants_info}

Additional Information:
{metafields_info}

The blog post should:
1. Introduce the product
2. Highlight its key features and benefits
3. Mention any variants or options available
4. Use the additional information to provide more context or details
5. Suggest potential use cases
6. Include a call-to-action to purchase the product

Please write in a friendly, engaging tone suitable for an e-commerce blog. {anthropic.AI_PROMPT}"""

    try:
        response = claude.completions.create(
            model="claude-2.1",
            prompt=prompt,
            max_tokens_to_sample=500,
        )
        return response.completion
    except anthropic.APIError as e:
        print(f"Claude API Error: {e.status_code} - {e.message}")
        return None
    except Exception as e:
        print(f"Unexpected error generating blog post: {str(e)}")
        return None

def main():
    print("Entering main function")
    
    products = fetch_shopify_products()
    
    if not products:
        print("No products found. Exiting.")
        return

    with open('sample_output.txt', 'w', encoding='utf-8') as f:
        for product in products:
            blog_post = generate_blog_post(product)
            if blog_post:
                f.write(f"Blog post for {product['title']}:\n")
                f.write(blog_post)
                f.write("\n\n---\n\n")
                print(f"Generated blog post for {product['title']}")
            else:
                f.write(f"Failed to generate blog post for {product['title']}\n\n")
                print(f"Failed to generate blog post for {product['title']}")
            
            # Add a delay to avoid hitting API rate limits
            time.sleep(5)

    print("All blog posts have been saved to sample_output.txt")

if __name__ == "__main__":
    main()

print("Script completed")