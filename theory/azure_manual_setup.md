# Azure Cloud Manual Setup Guide - RetailSense AI

This guide provides step-by-step instructions on how to manually set up and deploy the entire RetailSense AI cloud architecture using both the **Azure Portal** and **Azure CLI**.

---

## 📂 Step 1: Create a Resource Group
A Resource Group is a logical container that holds related Azure resources.

### Option A: Azure Portal
1. Navigate to the [Azure Portal](https://portal.azure.com).
2. Search for **Resource groups** and click **Create**.
3. Select your subscription, name the resource group `rg-retailsense`, and select a region (e.g., `East US`).
4. Click **Review + create** -> **Create**.

### Option B: Azure CLI
```bash
az group create --name rg-retailsense --location eastus
```

---

## 💾 Step 2: Create a Storage Account (ADLS Gen2)
We need a storage layer to hold our raw, Bronze, Silver, and Gold Parquet/Delta files. For high-performance big data operations, we use **Azure Data Lake Storage Gen2 (ADLS Gen2)**, which enables **Hierarchical Namespace**.

### Option A: Azure Portal
1. Search for **Storage accounts** -> Click **Create**.
2. Set **Resource group** to `rg-retailsense` and name the account (e.g., `stretailsensedata`).
3. Select **Standard** performance and **Locally-redundant storage (LRS)** to minimize costs.
4. Go to the **Advanced** tab, scroll down to **Data Lake Storage Gen2**, and check **Enable hierarchical namespace**.
5. Click **Review + create** -> **Create**.
6. Once deployed, open the resource, go to **Containers**, and create a container named `data`.

### Option B: Azure CLI
```bash
# Create storage account with ADLS Gen2 enabled (--enable-hierarchical-namespace true)
az storage account create \
  --name stretailsensedata \
  --resource-group rg-retailsense \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2 \
  --enable-hierarchical-namespace true

# Create 'data' container
az storage container create \
  --name data \
  --account-name stretailsensedata
```

---

## 🚀 Step 3: Create an Azure Databricks Workspace
Databricks provides the managed Apache Spark cluster environment.

### Option A: Azure Portal
1. Search for **Azure Databricks** -> Click **Create**.
2. Set **Resource group** to `rg-retailsense` and workspace name to `db-retailsense`.
3. Set **Pricing Tier** to **Premium** (required for Unity Catalog and native Notebook Dashboards).
4. Click **Review + create** -> **Create** (takes 2-4 minutes).

### Option B: Azure CLI
```bash
az databricks workspace create \
  --resource-group rg-retailsense \
  --name db-retailsense \
  --location eastus \
  --sku premium
```

---

## 🔌 Step 4: Mount Storage to Databricks (DBFS)
Mounting allows PySpark to interact with ADLS Gen2 as if it were a local directory.

1. Open your Databricks Workspace.
2. Create a temporary notebook and run the following Python code to mount the storage account:

```python
# Configure credentials using Storage Account SAS Token or Account Key
dbutils.fs.mount(
  source = "wasbs://data@stretailsensedata.blob.core.windows.net",
  mount_point = "/mnt/data",
  extra_configs = {"fs.azure.account.key.stretailsensedata.blob.core.windows.net": "<YOUR_STORAGE_ACCOUNT_KEY>"}
)
```

---

## 🔗 Step 5: Link the GitHub Repository
Link your git repository to keep Databricks code synchronized.

1. In Databricks, click on **Workspace** in the sidebar -> **Repos** (or **Git Folders**).
2. Click **Add Repo** -> Paste the Repository URL: `https://github.com/KISHANSINHAA/retail-m5.git`.
3. Databricks will pull your code into the workspace.

---

## ⚙️ Step 6: Configure Environment & Libraries
Set up cluster configurations to support execution.

1. Navigate to **Compute** -> **Create compute** (Select **Serverless** or create a **Single Node** cluster).
2. If using a provisioned cluster, go to the **Libraries** tab and install:
   - `xgboost` (via PyPI)
   - `scikit-learn` (via PyPI)
   - `pydantic-settings` (via PyPI)
   - `python-dotenv` (via PyPI)
3. Set cluster environment variables to target your mounted cloud storage:
   ```properties
   RAW_DIR=/dbfs/mnt/data/raw
   BRONZE_DIR=/dbfs/mnt/data/bronze
   SILVER_DIR=/dbfs/mnt/data/silver
   GOLD_DIR=/dbfs/mnt/data/gold
   MODELS_DIR=/dbfs/mnt/data/models
   SAMPLE_LIMIT=0
   ```
