# Azure Databricks Deployment & Integration Guide - RetailSense AI

This guide describes how to configure, deploy, and schedule the RetailSense AI PySpark and Sales Forecasting pipelines inside **Azure Databricks** (or standard Databricks workspaces).

---

## 🚀 Step 1: Link your GitHub Repository to Databricks

Azure Databricks has native Git integration via **Databricks Repos / Git Folders**.

1. Log in to your **Azure Databricks Workspace**.
2. In the left sidebar, navigate to **Workspace** -> **Repos** (or **Git Folders**).
3. Click the **Add Repo** (or **Create Git Folder**) button in the top right.
4. Fill in the git remote configuration:
   - **Git Repository URL**: `https://github.com/KISHANSINHAA/retail-m5.git`
   - **Git Provider**: GitHub
   - **Folder Name**: `retail-m5`
5. If prompted, authenticate using your GitHub **Personal Access Token (PAT)** with repository read/write access.
6. Databricks will clone the entire codebase into your workspace directory.

---

## 🛠️ Step 2: Configure the Compute Cluster

Create or configure a cluster to run the pipeline notebooks.

1. Navigate to **Compute** in the left sidebar and click **Create Compute** (use **Single Node** to fit free-tier credits).
2. Recommended Databricks Runtime: **13.3 LTS or higher** (includes Apache Spark 3.4/3.5, Scala 2.12).
3. In the **Libraries** tab of your cluster details page, install the required packages:
   - Click **Install New** -> **PyPI** -> Type `xgboost` -> Click **Install**.
   - Click **Install New** -> **PyPI** -> Type `scikit-learn` -> Click **Install**.
   - Click **Install New** -> **PyPI** -> Type `pydantic-settings` -> Click **Install**.
   - Click **Install New** -> **PyPI** -> Type `python-dotenv` -> Click **Install**.

---

## 📂 Step 3: Configure Cloud Storage (Optional)

By default, the pipeline runs using paths relative to the Git repository folder inside the workspace. To process the **entire M5 dataset** in production, configure the paths to read and write to **Azure Blob Storage (ADLS Gen2)**:

### 1. Mount Azure Blob Storage / ADLS Gen2
Run this block inside a temporary Databricks notebook cell to mount your Azure storage container:

```python
dbutils.fs.mount(
  source = "wasbs://<your-container-name>@<your-storage-account-name>.blob.core.windows.net",
  mount_point = "/mnt/retailsense",
  extra_configs = {"fs.azure.account.key.<your-storage-account-name>.blob.core.windows.net": "<your-storage-account-key>"}
)
```

### 2. Configure Environment Variables on the Cluster
In your Databricks cluster settings under **Advanced Options** -> **Spark** -> **Environment Variables**, configure the paths to point to your mount point:

```properties
RAW_DIR=/dbfs/mnt/retailsense/data/raw
BRONZE_DIR=/dbfs/mnt/retailsense/data/bronze
SILVER_DIR=/dbfs/mnt/retailsense/data/silver
GOLD_DIR=/dbfs/mnt/retailsense/data/gold
MODELS_DIR=/dbfs/mnt/retailsense/models
SAMPLE_LIMIT=0
```
> Setting `SAMPLE_LIMIT=0` disables the local mock-data limit (100 rows) and runs the PySpark engine on the entire dataset.

---

## 📓 Step 4: Run the Pipelines

Inside the cloned Git Folder, navigate to the `notebooks/` directory and open them:

1. **`01_Ingestion_ETL.py`**: Reads raw CSV files, unpivots columns, and writes Delta tables.
2. **`02_Feature_Engineering.py`**: Computes rolling statistics, lags, and outputs Gold tables.
3. **`03_Sales_Forecasting.py`**: Trains XGBoost Regressor model and computes 30-day forecast projections.

---

## ⏱️ Step 5: Schedule Daily Jobs / Workflows

To automate your pipelines, set up a **Databricks Workflow (Job)**:

1. In the left sidebar, click **Workflows** (or **Jobs**) -> **Create Job**.
2. Create a sequence of 3 tasks:
   - **Task 1: Ingestion & ETL** -> Select Type `Notebook` -> Choose `notebooks/01_Ingestion_ETL`.
   - **Task 2: Feature Engineering** -> Select Type `Notebook` -> Choose `notebooks/02_Feature_Engineering` -> Set dependency on Task 1.
   - **Task 3: Forecasting** -> Select Type `Notebook` -> Choose `notebooks/03_Sales_Forecasting` -> Set dependency on Task 2.
3. Add a trigger schedule (e.g., daily at 1:00 AM) to keep Gold tables up to date.
