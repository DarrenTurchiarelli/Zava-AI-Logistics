#!/usr/bin/env python3
"""
Post-deployment script for Azure App Service
Runs after deployment to set up demo data
"""

import asyncio
import sys
import os

async def run_post_deployment():
    """Run post-deployment tasks"""
    print("\n" + "=" * 70)
    print("🚀 Running Post-Deployment Tasks")
    print("=" * 70)
    
    tasks_completed = []
    tasks_failed = []
    
    # Task 1: Setup users
    print("\n📋 Task 1: Setting up default users...")
    try:
        # Add root directory to path
        root_path = os.path.dirname(__file__)
        if root_path not in sys.path:
            sys.path.insert(0, root_path)
        
        # Add utils/setup to path
        setup_path = os.path.join(root_path, 'utils', 'setup')
        if setup_path not in sys.path:
            sys.path.insert(0, setup_path)
        
        # Import and run setup_users
        from setup_users import main as setup_users_main
        await setup_users_main()
        print("✅ User setup completed")
        tasks_completed.append("User setup")
    except Exception as e:
        print(f"⚠️ User setup failed or skipped: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        tasks_failed.append(f"User setup: {e}")
    
    # Task 2: Generate demo manifests
    print("\n📋 Task 2: Generating demo manifests...")
    try:
        # Add root directory to path (for parcel_tracking_db import)
        root_path = os.path.dirname(__file__)
        if root_path not in sys.path:
            sys.path.insert(0, root_path)
        
        # Add utils/generators to path
        generators_path = os.path.join(root_path, 'utils', 'generators')
        if generators_path not in sys.path:
            sys.path.insert(0, generators_path)
        
        # Import and run the manifest generation
        from generate_demo_manifests import main as generate_manifests
        await generate_manifests()
        print("✅ Demo manifests generated successfully")
        tasks_completed.append("Demo manifests")
    except Exception as e:
        print(f"⚠️ Demo manifest generation failed: {e}")
        print(f"   Error details: {str(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        tasks_failed.append(f"Demo manifests: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Post-Deployment Summary")
    print("=" * 70)
    print(f"✅ Completed: {len(tasks_completed)} task(s)")
    for task in tasks_completed:
        print(f"   • {task}")
    
    if tasks_failed:
        print(f"\n⚠️ Failed/Skipped: {len(tasks_failed)} task(s)")
        for task in tasks_failed:
            print(f"   • {task}")
    
    print("\n🎉 Post-deployment tasks finished!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    asyncio.run(run_post_deployment())
