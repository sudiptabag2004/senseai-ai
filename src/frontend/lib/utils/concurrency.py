from typing import List, Coroutine
import asyncio
import streamlit as st
from tqdm.asyncio import tqdm_asyncio


def update_progress_bar(progress_bar, count, total_num, message):
    progress_bar.progress(count / total_num, text=f"{message} ({count}/{total_num})")


async def async_batch_gather(
    coroutines: List[Coroutine],
    batch_size: int = 10,
    description: str = "Processing batch",
):
    """Coroutines must return a tuple of (index, output) where index is the index of the coroutine in the list of coroutines"""
    total_num = len(coroutines)
    progress_bar = st.progress(0, text=f"{description}... (0/{total_num})")

    count = 0

    outputs = [None] * total_num

    # Process in batches to limit memory usage
    for i in range(0, len(coroutines), batch_size):
        batch = coroutines[i : i + batch_size]
        # batch_results = await tqdm_asyncio.gather(
        #     *batch,
        #     desc=f"{description} {i}-{i+len(batch)}/{len(coroutines)}",
        # )
        # results.extend(batch_results)

        for completed_task in asyncio.as_completed(batch):
            task_row_index, output = await completed_task

            outputs[task_row_index] = output
            count += 1

            update_progress_bar(progress_bar, count, total_num, description)

        # Give a little time for memory to be freed up
        await asyncio.sleep(1)

    progress_bar.empty()

    return outputs
