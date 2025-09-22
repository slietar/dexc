import asyncio
import contextlib


@contextlib.asynccontextmanager
async def task_group():
    try:
        async with asyncio.TaskGroup() as group:
            yield group
    except ExceptionGroup as e:
        if len(e.exceptions) == 1:
            raise e.exceptions[0] from None

        raise

async def a():
    raise Exception("Hello")

async def main():
    # async with asyncio.TaskGroup() as group:
    async with task_group() as group:
        group.create_task(a())
