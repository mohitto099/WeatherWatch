# 🌤️ WeatherWatch: Serverless Data Pipeline & Analytics

**[👉 Try it out yourself!](https://weather-watch-frontend-63g3.onrender.com)** *(Live Dashboard)*

WeatherWatch is an end-to-end data engineering platform and interactive dashboard that executes on-demand ETL (Extract, Transform, Load) pipelines for weather data.

Initially built with a heavy orchestration stack (Dockerized Apache Airflow and PySpark), the architecture has been refactored for the cloud as a **100% serverless, zero-cost architecture** using Render and Supabase, while maintaining real-time pipeline execution tracking on the frontend.

## ✨ Features

* **On-Demand ETL Execution:** Users trigger live Python data pipelines just by searching for a city.
* **Real-Time Stage Tracking:** The React frontend polls the backend to visually track pipeline stages (`Extracting` -> `Transforming` -> `Loading`) in real-time.
* **Smart Data Caching:** Subsequent searches for the same city within a defined window skip the pipeline and serve cached data from PostgreSQL to prevent API rate limits.
* **Historical Trend Analytics:** View rolling averages and historical weather patterns for previously searched cities.
* **Cloud-Native Deployment:** Fully hosted on Render (Web Service + Static Site) and Supabase (PostgreSQL Connection Pooler).

## 🏗️ Architecture

### Cloud Deployment (Current)

* **Frontend:** React + Vite hosted on a Render Static Site.
* **Backend API & ETL Runner:** FastAPI hosted on a Render Web Service. It handles geocoding, triggers the Python ETL scripts (`extract.py`, `transform.py`, `load.py`) in background threads, and manages pipeline status states.
* **Database:** Supabase PostgreSQL Free Tier.
* **External APIs:** Open-Meteo Geocoding and Forecast APIs.

### Local / Legacy Orchestration

The repository also includes the original infrastructure code designed for local development:

* `airflow/`: Dockerized Apache Airflow DAGs for local pipeline orchestration.
* `spark/`: Dockerized PySpark environment for heavy batch analytics and trend processing.

## 🚀 Tech Stack

* **Frontend:** React, Vite, Tailwind CSS
* **Backend:** Python 3, FastAPI, Uvicorn
* **Data Engineering:** Pandas (Transformations), SQLAlchemy/psycopg2 (Loading)
* **Database:** PostgreSQL (Supabase)
* **Deployment:** Render, GitHub Actions
