from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from pathlib import Path
import logging
from urllib.parse import urlparse, urljoin
import re
from collections import deque
import sys
import os


class SiteScraper:
    def __init__(self, base_url=None, headless=True, language=None):
        self.base_url = base_url or os.getenv('BASE_URL')
        if not self.base_url:
            raise ValueError("BASE_URL must be provided either as argument or environment variable")
        self.domain = urlparse(self.base_url).netloc
        self.visited_urls = set()
        self.urls_to_visit = deque([self.base_url])
        self.language = language or os.getenv('SCRAPER_LANGUAGE')
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        try:
            # Configure Chrome options
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless=new")
            
            # WebGL and graphics related options
            chrome_options.add_argument("--use-gl=swiftshader")
            chrome_options.add_argument("--enable-unsafe-webgl")
            chrome_options.add_argument("--ignore-gpu-blocklist")
            
            # Additional stability options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Set user agent
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("Browser initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing browser: {str(e)}")
            raise

    def _is_valid_url(self, url):
        """Check if URL should be crawled."""
        if not url or not isinstance(url, str):
            return False
            
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc != self.domain:
            return False
            
        # Ignore anchors
        if '#' in url:
            return False
            
        # Ignore file downloads
        if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.jpeg', '.doc', '.docx']):
            return False
            
        # Ignore social media and external links
        if any(pattern in url.lower() for pattern in ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com']):
            return False
            
        # Check language if specified
        if self.language:
            url_path = parsed.path.lower()
            if not url_path.startswith(f'/{self.language.lower()}/') and not url_path == f'/{self.language.lower()}':
                return False
            
        return True

    def _extract_links(self):
        """Extract all valid links from current page."""
        links = set()
        try:
            # Find all links
            elements = self.driver.find_elements(By.TAG_NAME, "a")
            for element in elements:
                try:
                    href = element.get_attribute("href")
                    if href and self._is_valid_url(href):
                        links.add(href)
                except:
                    continue
        except Exception as e:
            self.logger.error(f"Error extracting links: {str(e)}")
        
        return links

    def _create_markdown_content(self, url):
        """Convert page content to markdown format."""
        content = []
        
        try:
            # Get page title
            title = self.driver.title
            if title:
                content.append(f"# {self._clean_text(title)}\n")
            
            # Add URL reference
            content.append(f"*Original URL: {url}*\n")
            
            # Wait for content to load
            self._wait_for_content()
            
            # Try to find main content areas
            content_selectors = [
                "main", "article", "#content", ".content", ".main-content",
                ".page-content", ".entry-content", ".post-content",
                "section", ".section", "[role='main']", ".container",
                "#main", ".main", ".body-content"
            ]
            
            main_elements = []
            for selector in content_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    main_elements.extend(elements)
                except:
                    continue
            
            # If no main content areas found, use body
            if not main_elements:
                main_elements = [self.driver.find_element(By.TAG_NAME, "body")]
            
            for main_content in main_elements:
                try:
                    # Process all text containing elements
                    elements = main_content.find_elements(
                        By.CSS_SELECTOR,
                        "h1, h2, h3, h4, h5, h6, p, li, span, div"
                    )
                    
                    for element in elements:
                        try:
                            # Skip hidden elements and empty text
                            if not element.is_displayed():
                                continue
                                
                            # Skip if element is a child of already processed element
                            parent = element.find_element(By.XPATH, "..")
                            if parent in elements:
                                continue
                            
                            # Get element text
                            text = self._clean_text(element.text)
                            if not text:
                                continue
                            
                            # Handle headings
                            tag_name = element.tag_name
                            if tag_name.startswith('h') and len(tag_name) == 2:
                                level = int(tag_name[1])
                                content.append(f"{'#' * level} {text}\n")
                            
                            # Handle lists
                            elif tag_name == 'li':
                                content.append(f"- {text}\n")
                            
                            # Handle other text elements
                            else:
                                content.append(f"{text}\n")
                                
                        except:
                            continue
                    
                    # Process buttons and links text
                    for element in main_content.find_elements(By.CSS_SELECTOR, "button, a"):
                        try:
                            if element.is_displayed():
                                text = self._clean_text(element.text)
                                if text and len(text) > 5:  # Skip very short button/link text
                                    content.append(f"_{text}_\n")
                        except:
                            continue
                            
                except Exception as e:
                    self.logger.warning(f"Error processing main content section: {str(e)}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error creating markdown content: {str(e)}")
        
        return '\n'.join(content)

    def _wait_for_content(self):
        """Wait for page content to load."""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # Allow for dynamic content
        except Exception as e:
            self.logger.warning(f"Timeout waiting for content: {str(e)}")

    def _clean_text(self, text):
        """Clean and format text for markdown."""
        if not text:
            return ""
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'([*_`#\[\]])', r'\\\1', text)
        return text

    def _save_markdown(self, content, filename):
        """Save content to a markdown file if it has meaningful content."""
        # Check if the content has more than just title and URL
        content_lines = content.strip().split('\n')
        if len(content_lines) <= 2:  # Only title and URL line
            self.logger.warning(f"Skipping empty page: {filename}")
            return False
            
        # Check if there's actual content (more than 100 characters after title and URL)
        actual_content = '\n'.join(content_lines[2:])
        if len(actual_content.strip()) < 100:
            self.logger.warning(f"Skipping page with insufficient content: {filename}")
            return False
        
        output_dir = Path("output")
        if self.language:
            output_dir = output_dir / self.language
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean filename
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        file_path = output_dir / f"{filename}.md"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"Successfully saved {file_path} with {len(content_lines)} lines")
            return True
        except Exception as e:
            self.logger.error(f"Error saving file {file_path}: {e}")
            return False

    def _create_index(self):
        """Create an index file of all scraped pages."""
        index_content = ["# Site Content Index\n"]
        
        for url in sorted(self.visited_urls):
            filename = urlparse(url).path.strip('/').replace('/', '_') or 'index'
            output_path = "output"
            if self.language:
                output_path = f"output/{self.language}"
            index_content.append(f"- [{url}]({output_path}/{filename}.md)")
        
        index_filename = 'site_index'
        if self.language:
            index_filename = f'site_index_{self.language}'
        self._save_markdown('\n'.join(index_content), index_filename)

    def scrape_site(self, max_pages=None):
        """Scrape the entire website."""
        page_count = 0
        
        while self.urls_to_visit and (max_pages is None or page_count < max_pages):
            current_url = self.urls_to_visit.popleft()
            
            if current_url in self.visited_urls:
                continue
                
            try:
                self.logger.info(f"Scraping page {page_count + 1}: {current_url}")
                
                # Navigate to the page
                self.driver.get(current_url)
                
                # Extract and save content
                content = self._create_markdown_content(current_url)
                filename = urlparse(current_url).path.strip('/').replace('/', '_') or 'index'
                self._save_markdown(content, filename)
                
                # Mark as visited
                self.visited_urls.add(current_url)
                page_count += 1
                
                # Extract new links
                new_links = self._extract_links()
                for link in new_links:
                    if link not in self.visited_urls:
                        self.urls_to_visit.append(link)
                
                # Random delay between requests
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error processing {current_url}: {str(e)}")
                continue
        
        # Create index file
        self._create_index()
        self.logger.info(f"Completed scraping {page_count} pages")

    def close(self):
        """Close the browser."""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("Browser closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}")
def main():
    max_pages = 100  # Limit the number of pages to scrape, set to None for no limit
    
    scraper = None
    try:
        if len(sys.argv) > 1:
            base_url = sys.argv[1]
        else:
            base_url = None
        
        scraper = SiteScraper(base_url, headless=True)
        scraper.scrape_site(max_pages=max_pages)
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()