# agri-etl

Modular ETL pipeline framework for ingesting agricultural sensor and weather station data.

---

## Installation

```bash
pip install agri-etl
```

Or install from source:

```bash
git clone https://github.com/your-org/agri-etl.git && cd agri-etl && pip install -e .
```

---

## Usage

Define and run a pipeline in a few lines:

```python
from agri_etl import Pipeline
from agri_etl.sources import WeatherStationSource
from agri_etl.sinks import PostgresSink

pipeline = Pipeline(
    source=WeatherStationSource(station_id="WS-042", api_key="your_api_key"),
    sink=PostgresSink(dsn="postgresql://user:pass@localhost/agridb"),
)

pipeline.run()
```

You can also chain multiple sources and apply transforms:

```python
from agri_etl.transforms import NormalizeUnits, FillMissing

pipeline = Pipeline(
    source=WeatherStationSource(station_id="WS-042", api_key="your_api_key"),
    transforms=[FillMissing(strategy="forward"), NormalizeUnits(system="metric")],
    sink=PostgresSink(dsn="postgresql://user:pass@localhost/agridb"),
)

pipeline.run()
```

Run via CLI:

```bash
agri-etl run --config pipeline.yaml
```

---

## License

This project is licensed under the [MIT License](LICENSE).