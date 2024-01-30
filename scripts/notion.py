import os
import json
import datetime
import requests
import argparse

from dotenv import load_dotenv
load_dotenv()

class NotionAPI:
    def __init__(self, token, database_id):
        self.token = token
        self.database_id = database_id

    def create_summary_section(self, file_path):
        """
        Creates a summary section based on a JSON schema dictionary.

        Args:
            file_path: The path to the JSON file.

        Returns:
            A string representing the summary section for the Notion API.
        """
        # Read the JSON data from the file
        with open(file_path, "r") as f:
            schema_data = json.load(f)
        
        summary_text = ""

        # Process each key in the schema data
        for key, value in schema_data.items():
            if key == "key_catalysts" or key == "key_kpis":
                # Create a bulleted list for key catalysts and KPIs
                summary_text += f"\n**{key}:**\n"
                for item in value:
                    summary_text += f"- {item}\n"
            else:
                # Add other key-value pairs as plain text
                summary_text += f"{key}: {value}\n"

        return summary_text

    def write_notion_page(self, page_content):
        """
        Writes a page to a Notion database.

        Args:
            page_content: A dictionary containing the content of the page.
                The keys should be the names of the properties in the Notion database,
                and the values should be the corresponding data for those properties.

        Returns:
            The response from the Notion API.
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

        url = "https://api.notion.com/v1/pages"

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": page_content,
        }

        response = requests.post(url, headers=headers, json=payload)

        return response

def main():
    parser = argparse.ArgumentParser(description="Upload data to Notion.")
    parser.add_argument("ai_vendor", choices=["openai", "anthropic", "together"], help="Specify the AI vendor.")
    args = parser.parse_args()

    token = os.getenv("NOTION_API_KEY")

    if args.ai_vendor == "openai": 
        database_id = os.getenv("OPENAI_DATABASE_ID")
        model = os.getenv("OPENAI_MODEL")
    elif args.ai_vendor == "anthropic":
        database_id = os.getenv("ANTHROPIC_DATABASE_ID")
        model = os.getenv("ANTHROPIC_MODEL")
    elif args.ai_vendor == "together":
        database_id = os.getenv("TOGETHER_DATABASE_ID")
        model = os.getenv("TOGETHER_MODEL")
    elif args.ai_vendor == "anyscale":
        database_id = os.getenv("TOGETHER_DATABASE_ID")
        model = os.getev("ANYSCALE_MODEL")
    else:
        print("Invalid AI vendor. Choose 'openai' or 'anthropic'.")
        return

    # Replace this with your actual schema folder path
    #schema_path = f"results/{args.ai_vendor}_2023-12-04"
    #schema_path = f"results/{args.ai_vendor}_{datetime.datetime.utcnow().date().isoformat()}"
    schema_path = f"/Users/air/Documents/agi_projects/ai-alpha-extraction/results/{args.ai_vendor}_{datetime.date.today()}"
    schema_folder = os.path.join(os.getcwd(), schema_path)
    notion_api = NotionAPI(token, database_id)

    # Loop through each JSON file in the schema folder
    for filename in os.listdir(schema_folder):
        if filename.endswith(".json"):
            file_path = os.path.join(schema_folder, filename)
            ticker, _ = os.path.splitext(filename)

            page_content = {
                "Name": {"title": [{"text": {"content": ticker}}]},
                "Tags": {"rich_text": [{"text": {"content": datetime.date.today().isoformat()}}]},
                "Vendor": {"rich_text": [{"text": {"content": args.ai_vendor}}]},
                "Model": {"rich_text": [{"text": {"content": model}}]},
                "Summary": {"rich_text": [{"text": {"content": notion_api.create_summary_section(file_path)}}]}
            }

            # Write the page to Notion
            try:
                response = notion_api.write_notion_page(page_content)
                
                # Check the response status code
                if response.status_code == 200:
                    # Page created successfully
                    print(f"Page for {ticker} created successfully!")
                else:
                    # Handle other status codes if needed
                    print(f"Error creating page for {ticker}. Status code: {response.status_code}")
                    print(response.text)
                    
            except Exception as e:
                # Error creating page
                print(f"Error creating page for {ticker}: {e}")

if __name__ == "__main__":
    main()
