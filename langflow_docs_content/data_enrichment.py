"""This module provides functions for scraping and enriching data from web pages."""
import json
import os
import re
from bs4 import BeautifulSoup  # Re-introduce BeautifulSoup
from playwright.sync_api import sync_playwright
from loguru import logger

def scrape_page_content(url):
    """
    Scrapes the content of a given URL using Playwright,
    then parses with BeautifulSoup to extract visible text and format code blocks.
    """
    scraped_content = ""
    full_content = ""  # Initialize full_content here
    logger.debug(f"  [Playwright] Launching browser for {url}...")
    with sync_playwright() as p:
        browser = None  # Initialize browser to None
        try:
            browser = p.chromium.launch()
            page = browser.new_page()
            logger.debug(f"  [Playwright] Navigating to {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            logger.debug(f"  [Playwright] Page loaded. Extracting raw HTML from main content block...")

            # Aim directly for the main content block within Docusaurus structure
            # This class usually contains the actual markdown-rendered content.
            main_content_block = page.locator("div.theme-doc-markdown.markdown").first
            html_to_parse = ""
            if main_content_block.is_visible():
                html_to_parse = main_content_block.inner_html()
                logger.debug("  [Playwright] Found and extracted inner HTML from main content block.")
            else:
                logger.debug("  [Playwright] Main content block not found. Attempting to get entire page HTML.")
                html_to_parse = page.content() # Get full page HTML as fallback

            if not html_to_parse:
                logger.debug(f"  [Playwright] No HTML content to parse for {url}.")
                return ""

            soup = BeautifulSoup(html_to_parse, "html.parser")

            page_content_parts = []
            # Extract main content from common text elements
            # Exclude script and style tags, and navigation/UI elements
            content_elements = soup.find_all(
                lambda tag: tag.name
                in ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "span"]
                and tag.find_parent(class_=re.compile(r"navbar|sidebar|footer|header|nav"))
                is None
                and not tag.find_parents(["script", "style"])
            )

            for i, elem in enumerate(content_elements):
                text_content = elem.get_text(separator=" ", strip=True)
                text_content = text_content.replace("\u200b", "")  # Remove zero-width space
                if text_content:
                    page_content_parts.append(text_content)
            logger.debug(f"  [BeautifulSoup] Extracted {len(page_content_parts)} text parts.")

            # Extract and format code blocks using BeautifulSoup
            code_blocks = []
            for pre_tag in soup.find_all("pre"):
                code_text = pre_tag.get_text(strip=True)
                if code_text:
                    lang = ""
                    # Attempt to find a language hint from pre tag class or a child code tag
                    pre_class = pre_tag.get("class", [])
                    lang_matches_pre = [
                        cls for cls in pre_class if cls.startswith("language-")
                    ]
                    if lang_matches_pre:
                        lang = lang_matches_pre[0].replace("language-", "")
                    else:
                        code_tag = pre_tag.find("code")
                        if code_tag and code_tag.get("class"):
                            lang_matches_code = [
                                cls
                                for cls in code_tag.get("class", [])
                                if cls.startswith("language-")
                            ]
                            if lang_matches_code:
                                lang = lang_matches_code[0].replace("language-", "")

                    code_blocks.append(f"""``` {lang}
{code_text}
```"")
                else:
                    logger.debug(f"  [BeautifulSoup] Found empty pre tag.")

            logger.debug(f"  [BeautifulSoup] Extracted {len(code_blocks)} code blocks.")

            full_content = "
".join(page_content_parts + code_blocks)
            full_content = re.sub(r"
\s*
", "
", full_content).strip()  # Reduce multiple newlines
            full_content = re.sub(r"[ \t]+", " ", full_content).strip()  # Reduce multiple spaces/tabs

            scraped_content = full_content

        except Exception as e:
            logger.error(f"  [Playwright] An error occurred while scraping {url}: {e}")
        finally:
            if browser:
                logger.debug(f"  [Playwright] Closing browser for {url}.")
                browser.close()
    return scraped_content

            scraped_content = full_content

        except Exception as e:
            logger.error(f"  [Playwright] An error occurred while scraping {url}: {e}")
        finally:
            if browser:
                logger.debug(f"  [Playwright] Closing browser for {url}.")
                browser.close()
    return scraped_content

def apply_interlinking(data):
    """
    Applies interlinking by finding mentions of other URLs within the content.
    """
    all_urls = {entry["url"] for entry in data if "url" in entry}

    for entry in data:
        entry_content = entry.get("content", "")
        entry["related_urls"] = []

        for other_url in all_urls:
            if other_url != entry["url"] and other_url in entry_content:
                entry["related_urls"].append(other_url)

        # Remove duplicates and sort for consistency
        entry["related_urls"] = sorted(list(set(entry["related_urls"]))) 
    return data

def main():
    file_path = "langflow_docs.json"

    # Get initial file size
    initial_size = 0
    if os.path.exists(file_path):
        initial_size = os.path.getsize(file_path)
        logger.info(f"Initial size of {file_path}: {initial_size} bytes")
    else:
        logger.info(f"File {file_path} not found. Creating a new one.")
        # If file doesn't exist, create an empty JSON array
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    # Read data
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # # Original scraping loop (commented out for isolated testing)
    # processed_entries_count = 0
    # logger.info("Starting content scraping...")
    # for i, entry in enumerate(data):
    #     if 'url' in entry:
    #         logger.info(f"Attempting to scrape URL: {entry['url']}")
    #         try:
    #             scraped_content = scrape_page_content(entry['url'])
    #             entry['content'] = scraped_content
    #             processed_entries_count += 1
    #             logger.info(f"Successfully scraped URL: {entry['url']} (Content length: {len(scraped_content)})")
    #         except Exception as e:
    #             logger.error(f"Failed to scrape URL {entry['url']}: {e}")
    #     else:
    #         logger.info(f"Entry {i} missing 'url' field, skipping.")
    # logger.info("Content scraping finished.")

    # Isolated test of scrape_page_content
    test_url = "https://docs.langflow.org/get-started-quickstart"
    logger.info(f"
--- Initiating isolated test scrape for: {test_url} ---")
    try:
        test_content = scrape_page_content(test_url)
        logger.info(f"
--- Isolated test result for {test_url} ---")
        logger.info(f"Scraped content length: {len(test_content)} characters")
        logger.debug("First 500 characters of scraped content:")
        logger.debug(test_content[:500])
        if "```python" in test_content.lower() or "```json" in test_content.lower():
            logger.info("Detected code block in scraped content: YES")
        else:
            if "```python" in test_content.lower() or "```json" in test_content.lower():
            logger.info("Detected code block in scraped content: YES")
        else:
            logger.info("Detected code block in test content: NO") # Changed this line
    except Exception as e:
        logger.error(f"Isolated test failed for {test_url}: {e}")

    # The rest of the main function remains commented or unchanged as it relies on the full data processing
    logger.info("
Skipping interlinking and file write in isolated test mode.")

    # # Apply interlinking
    # data = apply_interlinking(data)

    # # Write updated data back to file
    # with open(file_path, "w", encoding="utf-8") as f:
    #     json.dump(data, f, indent=4)
    
    # # Get final file size
    # final_size = os.path.getsize(file_path)
    # logger.info(f"Final size of {file_path}: {final_size} bytes")
    # logger.info(f"Processed {processed_entries_count} entries.")

    # # Verify file size increase
    # if final_size > initial_size:
    #     logger.info("SUCCESS: File size increased, indicating successful data enrichment.")
    # else:
    #     logger.warning("WARNING: File size did NOT increase significantly. Data enrichment might not have been effective.")

    # # Report for sample entries
    # logger.info("
--- Sample Entry Report ---")
    # if data:
    #     # First entry
    #     if len(data) >= 1:
    #         first_entry = data[0]
    #         logger.info(f"
First Entry (URL: {first_entry.get("url", "N/A")}):")
    #         logger.info(f"  Title: {first_entry.get("title", "N/A")}")
    #         logger.info(f"  Content length: {len(first_entry.get("content", ""))} characters")
    #         logger.info(f"  Related URLs: {first_entry.get("related_urls", "N/A")}")
    #         # Check for Python code in content (simple check)
    #         if "```python" in first_entry.get("content", "").lower():
    #             logger.info("  Contains Python code example: YES")
    #         else:
    #             logger.info("  Contains Python code example: NO")

    #     # Entry for https://docs.langflow.org/api/custom-component-update
    #     custom_component_url = "https://docs.langflow.org/api/custom-component-update"
    #     custom_component_entry = next((item for item in data if item.get("url") == custom_component_url), None)
    #     if custom_component_entry:
    #         logger.info(f"
Entry for {custom_component_url}:")
    #         logger.info(f"  Title: {custom_component_entry.get("title", "N/A")}")
    #         logger.info(f"  Content length: {len(custom_component_entry.get("content", ""))} characters")
    #         logger.info(f"  Related URLs: {custom_component_entry.get("related_urls", "N/A")}")
    #         if "```python" in custom_component_entry.get("content", "").lower():
    #             logger.info("  Contains Python code example: YES")
    #         else:
    #             logger.info("  Contains Python code example: NO")
    #     else:
    #         logger.info(f"
Entry for {custom_component_url} not found.")

    #     # Last entry
    #     if len(data) > 1:
    #         last_entry = data[-1]
    #         logger.info(f"
Last Entry (URL: {last_entry.get("url", "N/A")}):")
    #         logger.info(f"  Title: {last_entry.get("title", "N/A")}")
    #         logger.info(f"  Content length: {len(last_entry.get("content", ""))} characters")
    #         logger.info(f"  Related URLs: {last_entry.get("related_urls", "N/A")}")
    #         if "```python" in last_entry.get("content", "").lower():
    #             logger.info("  Contains Python code example: YES")
    #         else:
    #             logger.info("  Contains Python code example: NO")
    # else:
    #     logger.info("No entries processed.")

if __name__ == "__main__":
    main()
