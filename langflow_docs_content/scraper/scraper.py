"""A web scraper for Langflow documentation, extracting content and links."""
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

def scrape_page(session, url):
    """Scrapes a single page and extracts its title and text content."""
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string if soup.title else "No Title"

        # Extract content from common elements that hold main article text
        content_elements = soup.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "code", "pre"]
        )
        page_content = "\n".join([elem.get_text(separator=" ", strip=True) for elem in content_elements])

        # Clean up multiple newlines and spaces
        page_content = re.sub(r"\n\s*\n", "\n", page_content).strip()
        page_content = re.sub(r"\s+", " ", page_content).strip()

        return {"url": url, "title": title, "content": page_content}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error scraping {url}: {e}")
        return None

def find_links(soup, base_url, domain):
    """Finds all unique internal links within the same domain."""
    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)

        # Ensure it's an HTTP/HTTPS link and within the same domain
        if parsed_url.scheme in ["http", "https"] and parsed_url.netloc == domain:
            # Normalize URL by removing fragments and redundant slashes
            clean_url = urljoin(full_url, parsed_url.path)
            if clean_url.endswith("/"):
                clean_url = clean_url.removesuffix("/")  # Remove trailing slash for consistency
            links.add(clean_url)
    return list(links)

def crawl_website(start_url):
    """Crawls the website, scrapes content, and stores it in a list."""
    parsed_start_url = urlparse(start_url)
    domain = parsed_start_url.netloc

    visited_urls = set()
    urls_to_visit = [start_url]
    scraped_data = []

    session = requests.Session()

    while urls_to_visit:
        current_url = urls_to_visit.pop(0)

        if current_url in visited_urls:
            continue

        logger.info(f"Scraping: {current_url}")
        page_data = scrape_page(session, current_url)
        visited_urls.add(current_url)

        if page_data:
            scraped_data.append(page_data)

            # Find new links to visit from the current page
            try:
                response = session.get(current_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                new_links = find_links(soup, current_url, domain)

                for link in new_links:
                    if link not in visited_urls and link not in urls_to_visit:
                        urls_to_visit.append(link)
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching links from {current_url}: {e}")
                continue

    return scraped_data

if __name__ == "__main__":
    base_url = "https://docs.langflow.org"
    all_scraped_content = crawl_website(base_url)

    output_filename = "langflow_docs.json"
    with Path(output_filename).open("w", encoding="utf-8") as f:
        json.dump(all_scraped_content, f, ensure_ascii=False, indent=4)

    logger.info(f"Scraping complete. Data saved to {output_filename}")
    logger.info(f"Total pages scraped: {len(all_scraped_content)}")