# Brinjal Documentation

Welcome to the Brinjal documentation! This guide will help you understand how to use Brinjal in your projects.

## What is Brinjal?

Brinjal is a generic task management system that provides:

- A base `Task` class for creating custom tasks
- Real-time progress updates via Server-Sent Events (SSE)
- A web component for displaying tasks
- Easy integration with FastAPI applications

## Quick Navigation

- [Getting Started](./getting-started.md) - Installation and basic setup
- [Task Development](./task-development.md) - How to create custom tasks
- [API Reference](./api-reference.md) - Complete API documentation
- [Web Component](./web-component.md) - Using the TaskList component
- [Integration Guide](./integration.md) - Adding Brinjal to your project
- [Examples](./examples.md) - Code examples and use cases

## Core Concepts

### Task
A `Task` represents a unit of work that can be executed asynchronously. Tasks can update their progress and status, which are automatically pushed to connected clients.

### TaskManager
The `TaskManager` handles the execution of tasks, manages the task queue, and coordinates real-time updates.

### TaskUpdate
A Pydantic model that represents the state of a task at any given moment, used for serializing task data.

### Web Component
A reusable `<task-list>` component that displays tasks and automatically updates as tasks progress.

## Getting Help

If you have questions or need help:

1. Check the [Examples](./examples.md) section for common use cases
2. Review the [API Reference](./api-reference.md) for detailed endpoint information
3. Look at the source code in the `src/brinjal/` directory
4. Create an issue in the project repository

## Contributing

Brinjal is designed to be extensible. If you want to contribute:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

See the [Development Guide](./development.md) for more details on the development workflow.
