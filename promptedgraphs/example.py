import asyncio


async def async_generator_1():
    for i in range(5):
        await asyncio.sleep(1)
        yield f"Gen1: {i}"


async def async_generator_2():
    for i in range(5):
        await asyncio.sleep(2)
        yield f"Gen2: {i}"


async def merge_generators(*generators):
    tasks = {asyncio.create_task(gen()): gen for gen in generators}
    while tasks:
        done, _ = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.exception():
                continue
            yield task.result()
            # Restart the task
            gen = tasks.pop(task)
            tasks[asyncio.create_task(gen())] = gen


async def main():
    async for item in merge_generators(async_generator_1, async_generator_2):
        print(item)


asyncio.run(main())
