#!/usr/bin/env python3
"""
Post-Deployment Testing Script for Langflow with MCP Integration
Tests the deployed instance on Render.com
"""

import requests
import json
import time
import sys
from pathlib import Path

class PostDeploymentTester:
    def __init__(self, base_url=None):
        self.base_url = base_url or "https://langflow-mcp.onrender.com"
        self.test_results = []
        
    def test_health_endpoint(self):
        """Test the health endpoint"""
        print("🔍 Testing health endpoint...")
        
        try:
            url = f"{self.base_url}/health"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = {
                    "test": "Health Endpoint",
                    "status": "✅ PASS",
                    "details": f"Status: {response.status_code}, Response: {response.text[:100]}"
                }
                print(f"✅ Health endpoint: {response.status_code} - {response.text[:50]}")
            else:
                result = {
                    "test": "Health Endpoint",
                    "status": "❌ FAIL",
                    "details": f"Status: {response.status_code}, Error: {response.text}"
                }
                print(f"❌ Health endpoint failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            result = {
                "test": "Health Endpoint",
                "status": "❌ ERROR",
                "details": f"Connection error: {str(e)}"
            }
            print(f"❌ Health endpoint connection error: {e}")
            
        self.test_results.append(result)
        return result["status"].startswith("✅")
    
    def test_api_endpoints(self):
        """Test key API endpoints"""
        print("🔍 Testing API endpoints...")
        
        endpoints = [
            ("/api/v1/validate", "GET", "API Validation"),
            ("/api/v1/all", "GET", "Get All Components"),
            ("/api/v1/mcp/status", "GET", "MCP Status"),
            ("/api/v1/mcp/servers", "GET", "MCP Servers List"),
        ]
        
        all_passed = True
        
        for endpoint, method, name in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                
                if method == "GET":
                    response = requests.get(url, timeout=10)
                else:
                    response = requests.post(url, timeout=10)
                
                if response.status_code in [200, 201]:
                    result = {
                        "test": f"API: {name}",
                        "status": "✅ PASS",
                        "details": f"Status: {response.status_code}"
                    }
                    print(f"✅ {name}: {response.status_code}")
                else:
                    result = {
                        "test": f"API: {name}",
                        "status": "⚠️  WARN" if response.status_code == 404 else "❌ FAIL",
                        "details": f"Status: {response.status_code}, Response: {response.text[:100]}"
                    }
                    print(f"⚠️  {name}: {response.status_code} (may be expected for some endpoints)")
                    if response.status_code != 404:
                        all_passed = False
                        
            except requests.exceptions.RequestException as e:
                result = {
                    "test": f"API: {name}",
                    "status": "❌ ERROR",
                    "details": f"Connection error: {str(e)}"
                }
                print(f"❌ {name} connection error: {e}")
                all_passed = False
                
            self.test_results.append(result)
            
        return all_passed
    
    def test_mcp_integration(self):
        """Test MCP integration endpoints"""
        print("🔍 Testing MCP integration...")
        
        mcp_tests = [
            ("/api/v1/mcp/test", "POST", "MCP Basic Test"),
            ("/api/v1/mcp/parallel/status", "GET", "Parallel Execution Status"),
        ]
        
        all_passed = True
        
        for endpoint, method, name in mcp_tests:
            try:
                url = f"{self.base_url}{endpoint}"
                
                # For POST requests, send minimal test data
                if method == "POST":
                    response = requests.post(url, json={"test": True}, timeout=15)
                else:
                    response = requests.get(url, timeout=15)
                
                if response.status_code in [200, 201]:
                    try:
                        data = response.json()
                        result = {
                            "test": f"MCP: {name}",
                            "status": "✅ PASS",
                            "details": f"Status: {response.status_code}, Response keys: {list(data.keys())[:3]}"
                        }
                        print(f"✅ {name}: {response.status_code}")
                    except:
                        result = {
                            "test": f"MCP: {name}",
                            "status": "✅ PASS",
                            "details": f"Status: {response.status_code}"
                        }
                        print(f"✅ {name}: {response.status_code}")
                else:
                    result = {
                        "test": f"MCP: {name}",
                        "status": "⚠️  WARN" if response.status_code == 404 else "❌ FAIL",
                        "details": f"Status: {response.status_code}"
                    }
                    print(f"⚠️  {name}: {response.status_code} (may need MCP servers configured)")
                    if response.status_code != 404:
                        all_passed = False
                        
            except requests.exceptions.RequestException as e:
                result = {
                    "test": f"MCP: {name}",
                    "status": "❌ ERROR",
                    "details": f"Connection error: {str(e)}"
                }
                print(f"❌ {name} connection error: {e}")
                all_passed = False
                
            self.test_results.append(result)
            
        return all_passed
    
    def test_database_connection(self):
        """Test database connectivity"""
        print("🔍 Testing database connection...")
        
        try:
            # Test via MCP status endpoint which should check database
            url = f"{self.base_url}/api/v1/mcp/db/status"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("database", {}).get("connected", False):
                    result = {
                        "test": "Database Connection",
                        "status": "✅ PASS",
                        "details": "PostgreSQL TaskBus connected successfully"
                    }
                    print("✅ Database: PostgreSQL TaskBus connected")
                else:
                    result = {
                        "test": "Database Connection",
                        "status": "⚠️  WARN",
                        "details": "Database endpoint accessible but connection status unknown"
                    }
                    print("⚠️  Database: Endpoint accessible, connection status unknown")
            else:
                result = {
                    "test": "Database Connection",
                    "status": "⚠️  WARN",
                    "details": f"Database endpoint returned {response.status_code}"
                }
                print(f"⚠️  Database: Endpoint returned {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            result = {
                "test": "Database Connection",
                "status": "❌ ERROR",
                "details": f"Connection error: {str(e)}"
            }
            print(f"❌ Database connection test error: {e}")
            
        self.test_results.append(result)
        return result["status"].startswith("✅")
    
    def test_frontend_assets(self):
        """Test frontend asset loading"""
        print("🔍 Testing frontend assets...")
        
        assets = [
            "/",
            "/static/js/main.js",
            "/static/css/main.css",
            "/favicon.ico"
        ]
        
        all_passed = True
        
        for asset in assets:
            try:
                url = f"{self.base_url}{asset}"
                response = requests.get(url, timeout=10)
                
                if response.status_code in [200, 304]:
                    result = {
                        "test": f"Frontend: {asset}",
                        "status": "✅ PASS",
                        "details": f"Status: {response.status_code}"
                    }
                    print(f"✅ Asset {asset}: {response.status_code}")
                else:
                    result = {
                        "test": f"Frontend: {asset}",
                        "status": "⚠️  WARN" if response.status_code == 404 else "❌ FAIL",
                        "details": f"Status: {response.status_code}"
                    }
                    print(f"⚠️  Asset {asset}: {response.status_code}")
                    if response.status_code != 404:
                        all_passed = False
                        
            except requests.exceptions.RequestException as e:
                result = {
                    "test": f"Frontend: {asset}",
                    "status": "❌ ERROR",
                    "details": f"Connection error: {str(e)}"
                }
                print(f"❌ Asset {asset} connection error: {e}")
                all_passed = False
                
            self.test_results.append(result)
            
        return all_passed
    
    def generate_report(self):
        """Generate a test report"""
        print("\n" + "="*60)
        print("POST-DEPLOYMENT TEST REPORT")
        print("="*60)
        
        # Count results
        passed = sum(1 for r in self.test_results if r["status"].startswith("✅"))
        warnings = sum(1 for r in self.test_results if r["status"].startswith("⚠️"))
        failed = sum(1 for r in self.test_results if r["status"].startswith("❌"))
        
        print(f"\n📊 Summary: {passed} ✅ Passed, {warnings} ⚠️  Warnings, {failed} ❌ Failed")
        
        # Print detailed results
        print("\n📋 Detailed Results:")
        for result in self.test_results:
            print(f"{result['status']} {result['test']}")
            if not result['status'].startswith("✅"):
                print(f"   Details: {result['details']}")
        
        # Overall status
        if failed == 0 and warnings == 0:
            print("\n🎉 All tests passed! Deployment is successful.")
            overall_status = "SUCCESS"
        elif failed == 0:
            print("\n⚠️  Some warnings detected. Deployment is functional but may need configuration.")
            overall_status = "WARNING"
        else:
            print("\n❌ Some tests failed. Deployment may have issues.")
            overall_status = "FAILURE"
        
        # Save report to file
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "overall_status": overall_status,
            "summary": {
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
                "total": len(self.test_results)
            },
            "results": self.test_results,
            "recommendations": self.generate_recommendations()
        }
        
        report_file = Path("deploy/config/post_deployment_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_file}")
        print("="*60)
        
        return overall_status
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check for common issues
        health_issues = [r for r in self.test_results if "Health" in r["test"] and not r["status"].startswith("✅")]
        api_issues = [r for r in self.test_results if "API" in r["test"] and not r["status"].startswith("✅")]
        mcp_issues = [r for r in self.test_results if "MCP" in r["test"] and not r["status"].startswith("✅")]
        db_issues = [r for r in self.test_results if "Database" in r["test"] and not r["status"].startswith("✅")]
        
        if health_issues:
            recommendations.append({
                "issue": "Health endpoint issues",
                "action": "Check service logs on Render.com, ensure service is running",
                "priority": "HIGH"
            })
        
        if api_issues:
            recommendations.append({
                "issue": "API endpoint issues",
                "action": "Verify Langflow backend is properly configured and running",
                "priority": "HIGH"
            })
        
        if mcp_issues:
            recommendations.append({
                "issue": "MCP integration issues",
                "action": "Check MCP server configuration and API keys",
                "priority": "MEDIUM"
            })
        
        if db_issues:
            recommendations.append({
                "issue": "Database connection issues",
                "action": "Verify PostgreSQL database is linked and environment variables are set",
                "priority": "HIGH"
            })
        
        # Check if any tests passed
        passed_tests = [r for r in self.test_results if r["status"].startswith("✅")]
        if len(passed_tests) == 0:
            recommendations.append({
                "issue": "No tests passed",
                "action": "Service may not be deployed or URL may be incorrect",
                "priority": "CRITICAL"
            })
        
        return recommendations
    
    def run_all_tests(self):
        """Run all tests"""
        print("="*60)
        print("POST-DEPLOYMENT TESTING")
        print(f"Testing URL: {self.base_url}")
        print("="*60)
        
        # Run tests
        tests = [
            ("Health Endpoint", self.test_health_endpoint),
            ("API Endpoints", self.test_api_endpoints),
            ("MCP Integration", self.test_mcp_integration),
            ("Database Connection", self.test_database_connection),
            ("Frontend Assets", self.test_frontend_assets)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            test_func()
            time.sleep(1)  # Brief pause between tests
        
        # Generate report
        return self.generate_report()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Post-deployment testing for Langflow with MCP integration")
    parser.add_argument("--url", default="https://langflow-mcp.onrender.com",
                       help="Base URL of deployed instance (default: https://langflow-mcp.onrender.com)")
    parser.add_argument("--output", default="deploy/config/post_deployment_report.json",
                       help="Output report file path")
    
    args = parser.parse_args()
    
    print("🚀 Starting post-deployment tests...")
    print(f"📡 Testing URL: {args.url}")
    
    tester = PostDeploymentTester(args.url)
    
    try:
        status = tester.run_all_tests()
        
        if status == "SUCCESS":
            print("\n✅ Deployment testing completed successfully!")
            sys.exit(0)
        elif status == "WARNING":
            print("\n⚠️  Deployment testing completed with warnings.")
            sys.exit(1)
        else:
            print("\n❌ Deployment testing failed.")
            sys.exit(2)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()