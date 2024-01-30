import os
import time
import yaml
import csv
import json
import argparse
import datetime
import threading
import concurrent.futures
from openai import AzureOpenAI
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt
from time import sleep
from pydantic import ValidationError

from aiutilities import AIUtilities
from schema import OutputSchema
from promptmanager import PromptManager
from search import WebSearch

from dotenv import load_dotenv
load_dotenv()

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler and set the logging level
file_handler = logging.FileHandler('extractor.log')
file_handler.setLevel(logging.DEBUG)  # Set the desired logging level for the file handler

# Create a console handler and set the logging level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Set the desired logging level for the console handler

# Create a formatter and attach it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class AlphaExtraction:
    def __init__(self, config_path):
        # load config
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.ai_utilities = AIUtilities()
        self.web_search_client = WebSearch()
        self.file_write_lock = threading.Lock()

    def save_search_results(self, ticker, search_results):
        folder_name = f"search_results/{datetime.date.today()}"
        folder_path = os.path.join(os.getcwd(), folder_name, ticker)
        os.makedirs(folder_path, exist_ok=True)

        for i, item in enumerate(search_results):
            if item is not None and "url" in item and "content" in item:
                file_path = os.path.join(folder_path, f"result_{i}.json")
                result_data = {"url": item["url"], "content": item["content"], "tables": item["tables"]}

                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(result_data, file, ensure_ascii=False, indent=2)

                logger.info(f"News article for {ticker} from {item['url']} saved")

    def read_documents_from_folder(self, folder_path, num_results):
        search_results = []

        if os.path.exists(folder_path):
            # Read from existing JSON files
            for i, filename in enumerate(os.listdir(folder_path)):
                while i <= num_results:
                    if filename.endswith(".json"):
                        file_path = os.path.join(folder_path, filename)
                        with open(file_path, "r", encoding="utf-8") as file:
                            result_data = json.load(file)
                            search_results.append(result_data)

        return search_results
    
    def convert_tables_to_markdown(self, tables):
        markdown = ""
        for table in tables:
            markdown = "|"
            for header in table[0]:
                markdown += f" {header[0]} |"
            markdown += "\n|"
            for _ in table[0]:
                markdown += " --- |"
            markdown += "\n"
            for row in table[1:]:
                markdown += "|"
                for cell in row:
                    markdown += f" {cell[1]} |"
                markdown += "\n"
        return markdown

    def retrieve_and_combine_documents(self, query, num_results, ticker):
        folder_name = f"search_results/{datetime.date.today()}"
        folder_path = os.path.join(os.getcwd(), folder_name, ticker)

        # Check if the folder already exists
        if os.path.exists(folder_path):
            # Read from existing JSON files
            search_results = self.read_documents_from_folder(folder_path, num_results)
        else:
            # Fetch new search results
            bing_results = self.web_search_client.bing_web_search(query, num_results)
            # Combine results to avoid duplicate URLs
            combined_results = [url for url in bing_results]
            # Retrieve Google search results
            google_results = self.web_search_client.google_search(query, num_results)

            # Add Google results without duplicate URLs to the combined results
            for url in google_results:
                if url not in combined_results:
                    combined_results.append(url)

            # Fetch and save new search results
            search_results = self.web_search_client._scrape_results_parallel(combined_results)
            self.save_search_results(ticker, search_results)
            logger.info(f"Search results for {ticker} saved successfully at {folder_path}")

        combined_text = ''

        for item in search_results:
            if item is not None and "url" in item and "content" in item:
                combined_text += f'<doc index="{item["url"]}">\n'
                combined_text += f'text content:\n{item["content"]}\n' 
                if len(item["tables"]) > 0:
                    markdown_tables = self.convert_tables_to_markdown(item["tables"])
                    combined_text += f'table content:\n{markdown_tables}'
                combined_text += '\n</doc>\n'

        return combined_text

    def extract_json_from_response(self, response_string):
        try:
            # Load the JSON data
            start_index = response_string.find('{')
            end_index = response_string.rfind('}') + 1
            json_data = response_string[start_index:end_index]
            json_data = json.loads(json_data)

            # Parse the JSON data using the OutputSchema
            output_schema = OutputSchema.model_validate(json_data)

            return output_schema.model_dump()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None
        except ValidationError as e:
            print(f"Error validating JSON against schema: {e}")
            return None

    def extract_and_save_results(self, ticker, completion, ai_vendor):
        try:
            # Check if the completion is a valid JSON object
            try:
                json_object = self.extract_json_from_response(completion)
            except json.JSONDecodeError:
                raise ValueError("Completion is not a valid JSON object")

            # Check if the JSON object is empty
            if not json_object:
                raise ValueError("Completion contains an empty JSON object")

            # Create a folder for each company if it doesn't exist
            today_date = datetime.date.today()
            results_path = self.config["paths"]["results_path"]
            results_path = f"{results_path}/{ai_vendor}_{today_date}"
            folder_path = os.path.join(os.getcwd(), results_path)
            os.makedirs(folder_path, exist_ok=True)

            # Save the JSON object into a file
            file_path = os.path.join(folder_path, f"{ticker}.json")

            with self.file_write_lock:
                with open(file_path, 'w') as json_file:
                    json.dump(json_object, json_file, indent=2)

            logger.info(f"Results for {ticker} saved successfully at {file_path}")

        except Exception as e:
            logger.debug(f"Error extracting and saving results for {ticker}: {str(e)}")
    
   # @retry(stop=stop_after_attempt(3))
    def run_alpha_extraction(self, ticker, query, ai_vendor, num_results):
        combined_documents = self.retrieve_and_combine_documents(query, num_results, ticker=ticker[0])
        # Read examples.json file
        examples_json_path = self.config["paths"]["examples_json"]
        with open(examples_json_path, "r") as f:
            examples_list = json.load(f)

        schema_json_path = self.config["paths"]["output_json"]
        with open(schema_json_path, "r") as f:
            output_schema = json.load(f)

        # Set variables for YAML
        variables = {
            "ticker": ticker[1],
            "company": ticker[0],
            "query": query,
            "document_type": "financial news articles",
            "doc_list": combined_documents,
            "few_shot_examples": examples_list,
            "pydantic_schema": OutputSchema.model_json_schema(),
        }

        # Read YAML file and format prompt
        prompt_yaml_path = self.config["paths"]["prompt_yaml"]
        
        prompt_manager = PromptManager()
        prompt = prompt_manager.generate_prompt(prompt_yaml_path, variables)
        logger.info(prompt)

        completion = self.ai_utilities.run_ai_completion(prompt, ai_vendor)

         # Extract and save results for each company
        logger.info(f"saving json files for {ticker}")
        self.extract_and_save_results(ticker[1], completion, ai_vendor)

        return completion


    def generate_query(self, name, ticker):
        return f"{name} {ticker} stock financial performance and analysis news"
    
    def run_analysis_for_companies(self, ai_vendor="openai", num_results=10):
        coverage_csv_path = self.config["paths"]["coverage_csv"]
        with open(coverage_csv_path, 'r') as csv_file:
            reader = csv.DictReader(csv_file)
            tickers = [(row['Name'], row['Symbol']) for row in reader]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_ticker = {executor.submit(self.run_alpha_extraction, ticker, self.generate_query(*ticker), ai_vendor, num_results): ticker for ticker in tickers}

            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    completion = future.result()
                    logger.info(f"Company: {ticker[0]}, Ticker: {ticker[1]}")
                    logger.info("Completion: {}".format(completion))
                except Exception as e:
                    logger.error(f"Error processing company {ticker[0]}: {str(e)}")
                # Introduce a small delay between tasks (e.g., 0.1 seconds)
                time.sleep(0.1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run text completion extraction RAG pipeline")
    parser.add_argument("--ai_vendor", choices=["openai", "anthropic", "together", "anyscale"], default="openai", help="choose AI vendor (openai, anthropic, together, anyscale)")
    parser.add_argument("--num_results", type=int, default=10, help="Number of top-k documents for RAG pipeline")

    args = parser.parse_args()

  # Example usage for running analysis for companies in a CSV file
    config_path = "/Users/air/Documents/agi_projects/AlphaGPT/config.yaml"
    alpha_extraction = AlphaExtraction(config_path)
    alpha_extraction.run_analysis_for_companies(ai_vendor=args.ai_vendor, num_results=args.num_results)
