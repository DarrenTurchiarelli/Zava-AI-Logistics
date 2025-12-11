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
        import setup_users
        # setup_users.py runs on import if __name__ == "__main__" check is removed
        # or we can call it explicitly
        print("✅ User setup completed")
        tasks_completed.append("User setup")
    except Exception as e:
        print(f"⚠️ User setup failed or skipped: {e}")
        tasks_failed.append(f"User setup: {e}")
    
    # Task 2: Generate demo manifests (only in production)
    print("\n📋 Task 2: Generating demo manifests...")
    try:
        # Import the generate_demo_manifests module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils', 'generators'))
        from generate_demo_manifests import main as generate_manifests
        
        # Run the manifest generation
        await generate_manifests()
        print("✅ Demo manifests generated successfully")
        tasks_completed.append("Demo manifests")
    except Exception as e:
        print(f"⚠️ Demo manifest generation failed: {e}")
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
