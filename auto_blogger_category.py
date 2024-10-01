import os
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import anthropic
import time
import html
import json

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
print(f"aoi: {CLAUDE_API_KEY}")
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

def create_session_with_retries():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def fetch_shopify_products_and_metafields(limit=10):
    print(f"Fetching {limit} products and their metafields from Shopify API")
    if not all([SHOPIFY_STORE_URL, SHOPIFY_ACCESS_TOKEN]):
        print("Error: Shopify store URL or Access Token is not set. Please check your .env file.")
        return []
    
    url = f"https://{SHOPIFY_STORE_URL}/admin/api/2023-04/products.json"
    params = {
        'fields': 'id,title,body_html,product_type,variants,images',
        'limit': limit
    }
    headers = {
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }
    
    session = create_session_with_retries()
    
    try:
        response = session.get(url, headers=headers, params=params)
        response.raise_for_status()
        products = response.json().get('products', [])
        
        # Fetch metafields for each product
        for product in products:
            metafields_url = f"https://{SHOPIFY_STORE_URL}/admin/api/2023-04/products/{product['id']}/metafields.json"
            metafields_response = session.get(metafields_url, headers=headers)
            metafields_response.raise_for_status()
            product['metafields'] = metafields_response.json().get('metafields', [])
        
        return products
    
    except requests.RequestException as e:
        print(f"Error fetching products from Shopify API: {e}")
        return []

def print_products_and_metafields(products):
    for product in products:
        print(f"\nProduct: {product['title']}")
        print(f"Type: {product['product_type']}")
        print("Metafields:")
        for metafield in product['metafields']:
            print(f"  - {metafield['key']}: {metafield['value']}")

def find_category_field(products):
    category_fields = ['product_type', 'collection', 'tags']
    for field in category_fields:
        if all(field in product for product in products):
            print(f"Category field found: {field}")
            return field
    print("No consistent category field found. Using 'product_type' as default.")
    return 'product_type'

def fetch_products_by_category(category, category_field):
    print(f"Fetching products for category: {category}")
    all_products = fetch_shopify_products_and_metafields(limit=250)  # Fetch all products
    return [p for p in all_products if category.lower() in p.get(category_field, '').lower()]

def generate_category_blog_post(category, products):
    print(f"Generating blog post for category: {category}")
    
    product_summaries = "\n".join([f"- {p['title']}: {p['body_html'][:100]}..." for p in products[:5]])
    
    prompt = f"""{anthropic.HUMAN_PROMPT} Write a 1000-word blog post about {category} for an e-commerce website. Include the following:

1. An engaging introduction to {category} and their importance in today's security landscape
2. Key features and benefits of {category}, explaining why they are essential for certain industries or use cases
3. Highlight these top products from our range, explaining what makes each unique:
{product_summaries}
4. Provide a detailed guide on how to choose the right {category} for different needs (e.g., office use, government agencies, financial institutions)
5. Discuss any relevant security standards or certifications that customers should look for
6. Include tips for proper use and maintenance of {category}
7. Address common questions or misconceptions about {category}
8. Conclude with a strong call-to-action encouraging readers to explore our full range of {category} and emphasize the importance of investing in quality security equipment

Please write in a friendly, engaging, and authoritative tone suitable for an e-commerce blog specializing in security equipment. Use appropriate subheadings to structure the content. {anthropic.AI_PROMPT}"""

    try:
        response = claude.completions.create(
            model="claude-2.1",
            prompt=prompt,
            max_tokens_to_sample=1500,
        )
        return response.completion
    except anthropic.APIError as e:
        print(f"Claude API Error: {e.status_code} - {e.message}")
        return None
    except Exception as e:
        print(f"Unexpected error generating blog post: {str(e)}")
        return None

def main():
    # Fetch first 10 products and their metafields
    products = fetch_shopify_products_and_metafields(limit=10)
    
    if not products:
        print("No products found. Exiting.")
        return

    # Print products and metafields
    print_products_and_metafields(products)

    # Find the category field
    category_field = find_category_field(products)

    # Ask user for the category
    category = input(f"Enter the category to generate a blog post for (based on {category_field}): ")

    # Fetch products for the specified category
    category_products = fetch_products_by_category(category, category_field)

    if not category_products:
        print(f"No products found in category: {category}. Exiting.")
        return

    output_file = f"{category.lower().replace(' ', '_')}_blog_post.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        blog_post = generate_category_blog_post(category, category_products)
        if blog_post:
            f.write(f"# {category}: Safeguarding Your Sensitive Information\n\n")
            f.write(blog_post)
            f.write(f"\n\n---\n\nExplore our full range of [{category}](https://www.example.com/products/{category.lower().replace(' ', '-')}) and find the perfect solution for your security needs.")
            print(f"Generated blog post for {category}")
        else:
            f.write(f"Failed to generate blog post for {category}\n")
            print(f"Failed to generate blog post for {category}")

    print(f"Blog post has been saved to {output_file}")

if __name__ == "__main__":
    main()