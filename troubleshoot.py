#!/usr/bin/env python3
"""
Dashboard troubleshooting script to diagnose the "Failed to fetch" error.
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime

def check_dashboard_files():
    """Check what files were actually generated in the test dashboard."""
    
    print("=== DASHBOARD FILES TROUBLESHOOTING ===\n")
    
    # Check test dashboard directory
    test_dir = "./test_dashboard"
    
    if not os.path.exists(test_dir):
        print(f"❌ Test dashboard directory doesn't exist: {test_dir}")
        return False
        
    print(f"✅ Test dashboard directory exists: {test_dir}")
    
    # List all files in the directory
    all_files = []
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            file_path = os.path.relpath(os.path.join(root, file), test_dir)
            all_files.append(file_path)
    
    print(f"\nFiles in test dashboard directory:")
    for file in sorted(all_files):
        file_size = os.path.getsize(os.path.join(test_dir, file))
        print(f"  {file} ({file_size} bytes)")
    
    # Check for required dashboard files
    required_files = {
        "dashboard.html": "Main dashboard HTML file",
        "dashboard_data.json": "Dashboard data file (CRITICAL for fixing fetch error)",
    }
    
    optional_files = {
        "css/dashboard.css": "Dashboard stylesheet",
        "js/dashboard.js": "Dashboard JavaScript",
        "strategy.csv": "Generated strategy data"
    }
    
    print(f"\nRequired files check:")
    missing_required = []
    for file, description in required_files.items():
        file_path = os.path.join(test_dir, file)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✅ {file}: {description} ({size} bytes)")
            
            # Check if dashboard_data.json is valid
            if file == "dashboard_data.json":
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    print(f"    ✅ Valid JSON with keys: {list(data.keys())}")
                except json.JSONDecodeError as e:
                    print(f"    ❌ Invalid JSON: {e}")
                except Exception as e:
                    print(f"    ❌ Error reading file: {e}")
        else:
            print(f"  ❌ {file}: {description} - MISSING")
            missing_required.append(file)
    
    print(f"\nOptional files check:")
    for file, description in optional_files.items():
        file_path = os.path.join(test_dir, file)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✅ {file}: {description} ({size} bytes)")
        else:
            print(f"  ⚠️  {file}: {description} - missing (optional)")
    
    # If dashboard_data.json is missing, that's the root cause
    if "dashboard_data.json" in missing_required:
        print(f"\n❌ ROOT CAUSE IDENTIFIED:")
        print(f"   The dashboard_data.json file is missing!")
        print(f"   This is why you get 'Failed to fetch' error.")
        print(f"   The dashboard.html tries to load this file but it doesn't exist.")
        return False
    
    # Check if dashboard.html contains the right fetch call
    dashboard_html = os.path.join(test_dir, "dashboard.html")
    if os.path.exists(dashboard_html):
        print(f"\nChecking dashboard.html content...")
        with open(dashboard_html, 'r') as f:
            html_content = f.read()
        
        if "dashboard_data.json" in html_content:
            print(f"  ✅ dashboard.html references dashboard_data.json")
        else:
            print(f"  ⚠️  dashboard.html doesn't reference dashboard_data.json")
            
        if "fetch(" in html_content:
            print(f"  ✅ dashboard.html contains fetch calls")
        else:
            print(f"  ⚠️  dashboard.html doesn't contain fetch calls")
    
    return len(missing_required) == 0

def test_dashboard_generation():
    """Test dashboard generation process manually."""
    
    print(f"\n=== TESTING DASHBOARD GENERATION ===\n")
    
    try:
        from algosystem.backtesting.engine import Engine
        from algosystem.backtesting.dashboard.dashboard_generator import generate_dashboard
        
        print("✅ Successfully imported dashboard modules")
        
        # Create test data
        periods = 100  # Smaller dataset for testing
        dates = pd.date_range(end=datetime.now(), periods=periods, freq="B")
        np.random.seed(42)
        returns = np.random.normal(0.005, 0.01, periods)
        strategy_prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
        
        print(f"✅ Generated test data with {len(strategy_prices)} prices")
        
        # Create engine and run backtest
        engine = Engine(data=strategy_prices)
        results = engine.run()
        
        print(f"✅ Engine backtest completed successfully")
        print(f"   Results keys: {list(results.keys())}")
        
        # Generate dashboard
        output_dir = "./test_dashboard_manual"
        print(f"\nGenerating dashboard to: {output_dir}")
        
        dashboard_path = generate_dashboard(
            engine=engine, 
            output_dir=output_dir, 
            open_browser=False
        )
        
        print(f"✅ Dashboard generation completed")
        print(f"   Dashboard path: {dashboard_path}")
        
        # Check if files were created correctly
        data_file = os.path.join(output_dir, "dashboard_data.json")
        if os.path.exists(data_file):
            print(f"✅ dashboard_data.json created successfully")
            
            # Validate the JSON
            with open(data_file, 'r') as f:
                data = json.load(f)
            print(f"   Data keys: {list(data.keys())}")
            
            if 'metadata' in data:
                print(f"   Metadata: {list(data['metadata'].keys())}")
            if 'metrics' in data:
                print(f"   Metrics count: {len(data['metrics'])}")
            if 'charts' in data:
                print(f"   Charts count: {len(data['charts'])}")
        else:
            print(f"❌ dashboard_data.json was NOT created")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Dashboard generation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def suggest_fixes():
    """Suggest fixes based on the analysis."""
    
    print(f"\n=== SUGGESTED FIXES ===\n")
    
    print("Based on the analysis above, here are the recommended fixes:")
    print()
    
    print("1. IMMEDIATE FIX - Generate dashboard manually:")
    print("   python dashboard_troubleshoot.py")
    print("   Then check ./test_dashboard_manual/ for working files")
    print()
    
    print("2. WORKAROUND - Use standalone dashboard:")
    print("   This embeds all data directly in the HTML file:")
    print("   ```python")
    print("   from algosystem.backtesting.engine import Engine")
    print("   from algosystem.backtesting.dashboard.dashboard_generator import generate_standalone_dashboard")
    print("   ")
    print("   # Your existing engine code...")
    print("   standalone_path = generate_standalone_dashboard(engine, './standalone_dashboard.html')")
    print("   ```")
    print()
    
    print("3. ROOT CAUSE FIX - Check dashboard_generator.py:")
    print("   The issue is likely in the dashboard generation process")
    print("   where dashboard_data.json is not being created properly.")
    print()
    
    print("4. ALTERNATIVE - Use enhanced data without benchmark:")
    print("   algosystem dashboard ./test_dashboard/enhanced_strategy.csv")

def main():
    """Main troubleshooting function."""
    
    files_ok = check_dashboard_files()
    
    if not files_ok:
        print(f"\n🔧 Running manual dashboard generation test...")
        generation_ok = test_dashboard_generation()
        
        if generation_ok:
            print(f"\n✅ Manual generation worked! Check ./test_dashboard_manual/")
        else:
            print(f"\n❌ Manual generation also failed")
    else:
        print(f"\n✅ All required files exist - the issue might be elsewhere")
    
    suggest_fixes()

if __name__ == "__main__":
    main()