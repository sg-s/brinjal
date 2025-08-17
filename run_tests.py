#!/usr/bin/env python3
"""Simple test runner for Brinjal core functionality"""

import asyncio
import time
from brinjal.manager import TaskManager
from brinjal.task import ExampleTask


async def test_basic_functionality():
    """Test basic TaskManager and ExampleTask functionality"""
    print("🧪 Testing Brinjal core functionality...")
    print("=" * 50)

    # Create task manager
    task_manager = TaskManager()
    print("✅ TaskManager created")

    # Start the manager
    await task_manager.start()
    print("✅ TaskManager started")

    # Create and add a task
    task = ExampleTask()
    task_id = await task_manager.add_task_to_queue(task)
    print(f"✅ Task added to queue with ID: {task_id}")

    # Monitor task progress
    print("📊 Monitoring task progress...")
    start_time = time.time()

    while True:
        retrieved_task = task_manager.get_task(task_id)
        if retrieved_task:
            elapsed = time.time() - start_time
            print(
                f"   {elapsed:6.1f}s - Status: {retrieved_task.status:8s} - Progress: {retrieved_task.progress:3d}%"
            )

            if retrieved_task.status == "done":
                break
        else:
            print("   Task not found!")
            break

        await asyncio.sleep(0.5)

    # Check final state
    final_task = task_manager.get_task(task_id)
    if final_task:
        print(
            f"✅ Task completed - Status: {final_task.status}, Progress: {final_task.progress}%"
        )
    else:
        print("❌ Task not found after completion")

    # Stop the manager
    await task_manager.stop()
    print("✅ TaskManager stopped")

    print("=" * 50)
    print("🎉 Basic functionality test completed successfully!")
    return True


async def test_multiple_tasks():
    """Test multiple tasks running simultaneously"""
    print("\n🧪 Testing multiple tasks...")
    print("=" * 50)

    task_manager = TaskManager()
    await task_manager.start()

    # Create multiple tasks
    tasks = [ExampleTask() for _ in range(3)]
    task_ids = []

    for i, task in enumerate(tasks):
        task_id = await task_manager.add_task_to_queue(task)
        task_ids.append(task_id)
        print(f"✅ Task {i + 1} added with ID: {task_id}")

    # Monitor all tasks
    print("📊 Monitoring all tasks...")
    start_time = time.time()

    while True:
        all_tasks = task_manager.get_all_tasks()
        completed = [t for t in all_tasks if t["status"] == "done"]

        elapsed = time.time() - start_time
        print(f"   {elapsed:6.1f}s - Completed: {len(completed)}/{len(tasks)}")

        if len(completed) == len(tasks):
            break

        await asyncio.sleep(1.0)

    # Verify all completed
    all_tasks = task_manager.get_all_tasks()
    for task_info in all_tasks:
        print(
            f"✅ Task {task_info['task_id'][:8]}... - Status: {task_info['status']}, Progress: {task_info['progress']}%"
        )

    await task_manager.stop()
    print("✅ Multiple tasks test completed!")
    return True


async def main():
    """Run all tests"""
    try:
        await test_basic_functionality()
        await test_multiple_tasks()
        print("\n🎉 All tests passed! Brinjal is working correctly.")
        return True
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
