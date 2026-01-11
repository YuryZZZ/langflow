import requests
import sys

def check_url(name, url):
    try:
        print(f"Testing {name} at {url}...", end=" ")
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("✅ OK")
            return True
        else:
            print(f"❌ Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    print("--- Testing MCP Connectivity ---")
    
    # Remote
    check_url("Render Gateway (Remote)", "https://mcp-gateway-github.onrender.com/health") 

    # Local
    check_url("Crawl4AI (Local)", "http://localhost:11235/health")
    check_url("Perplexity (Local)", "http://localhost:8091/health")
    check_url("Memory (Local)", "http://localhost:8092/health")
    check_url("Stagehand (Local)", "http://localhost:8093/health")
    check_url("Browser Tools (Local)", "http://localhost:8090/health")
    check_url("LangChain (Local)", "http://localhost:8082/health")
    
    print("--- End of Test ---")

if __name__ == "__main__":
    main()
