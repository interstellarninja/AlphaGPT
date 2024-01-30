import os
import requests
import argparse

from bs4 import BeautifulSoup
import concurrent.futures
import time
from dotenv import load_dotenv

class WebSearch:
    def __init__(self):
        load_dotenv()
        self.bing_api_key = os.getenv("BING_SEARCH_API_KEY")
        self.bing_search_endpoint = os.getenv("BING_SEARCH_ENDPOINT")

    def _make_request(self, endpoint, params):
        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_api_key,
        }
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def bing_web_search(self, query, count=10):
        web_search_endpoint = self.bing_search_endpoint + "/v7.0/search"
        params = {'q': query, 'count': count}
        
        response = self._make_request(web_search_endpoint, params)
        urls = [result['url'] for result in response['webPages']['value']]
        #return WebSearch._scrape_results_parallel(urls)
        return urls

    def bing_news_search(self, query, count=10):
        news_search_endpoint = self.bing_search_endpoint + "/bing/v7.0/news/search"
        params = {'q': query, 'count': count}
        return self._make_request(news_search_endpoint, params)
    
    @staticmethod
    def google_search(query, num_results=10):
        url = 'https://www.google.com/search'
        params = {'q': query, 'num': num_results}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.3'}
        response = requests.get(url, params=params, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='tF2Cxc')
        urls = [result.find('a')['href'] for result in results]
        #return WebSearch._scrape_results_parallel(urls)
        return urls
    
    @staticmethod
    def _scrape_results_parallel(url_list):
        results = []
        # Fetch page content in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(WebSearch._get_page_content, url) for url in url_list]

        for future in concurrent.futures.as_completed(futures):
            content = future.result()
            results.append(content)

        return results

    @staticmethod
    def _get_page_content(url):
        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.3'})
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')  # Find all table elements in the HTML

            table_data = []
            for table in tables:
                rows = table.find_all('tr')  # Find all table rows
                table_rows = []
                for row in rows:
                    cells = row.find_all('td')  # Find all table cells
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    table_rows.append(row_data)
                table_data.append(table_rows)

            text_content = soup.get_text(separator='\n', strip=True)
            return {'url': url, 'content': text_content, 'tables': table_data}
        except requests.exceptions.RequestException as e:
            print(f"Error fetching content from {url}: {e}")
            return None
        except Exception as e:
            print(f"Error processing content from {url}: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Web Search')
    parser.add_argument('--engine', choices=['bing', 'google'], default='bing', help='Search engine to use')
    parser.add_argument('--num_results', type=int, default=10, help='Number of results to retrieve')
    parser.add_argument('--query', type=str, default='Microsoft stock news', help='Query to search')
    args = parser.parse_args()

    web_search_client = WebSearch()
    query = args.query

    if args.engine == 'bing':
        # Example Bing Web Search
        web_results = web_search_client.bing_web_search(query, count=args.num_results)
        print("Bing Web Search Results:")
        print(web_results)
    elif args.engine == 'google':
        # Example Google Search
        google_results = web_search_client.google_search(query, num_results=args.num_results)
        print("Google Search Results:")
        print(google_results)

if __name__ == "__main__":
    main()
