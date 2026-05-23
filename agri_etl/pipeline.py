"""Lightweight pipeline runner that wires readers, transformers, and loaders."""
from __future__ import annotations

import logging
from typing import Sequence

from agri_etl.ingestion.base_reader import BaseReader
from agri_etl.transform.base_transformer import BaseTransformer
from agri_etl.load.base_loader import BaseLoader, LoadResult

logger = logging.getLogger(__name__)


class Pipeline:
    """Run a single ETL pass: read -> transform chain -> load."""

    def __init__(
        self,
        reader: BaseReader,
        transformers: Sequence[BaseTransformer],
        loader: BaseLoader,
        batch_size: int = 100,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        self.reader = reader
        self.transformers = list(transformers)
        self.loader = loader
        self.batch_size = batch_size

    def run(self) -> dict:
        """Execute the pipeline and return a summary dict."""
        self.reader.connect()
        self.loader.connect()
        total_read = total_written = total_dropped = 0
        try:
            while True:
                batch = self.reader.read_batch(self.batch_size)
                if not batch:
                    break
                total_read += len(batch)
                transformed = []
                for record in batch:
                    current = record
                    dropped = False
                    for transformer in self.transformers:
                        result = transformer.transform(current)
                        if result.dropped:
                            dropped = True
                            total_dropped += 1
                            break
                        current = result.record
                    if not dropped:
                        transformed.append(current)
                if transformed:
                    load_result: LoadResult = self.loader.write_batch(transformed)
                    total_written += load_result.records_written
                    logger.debug("Wrote %d records", load_result.records_written)
        finally:
            self.reader.disconnect()
            self.loader.disconnect()

        summary = {
            "records_read": total_read,
            "records_written": total_written,
            "records_dropped": total_dropped,
        }
        logger.info("Pipeline complete: %s", summary)
        return summary
