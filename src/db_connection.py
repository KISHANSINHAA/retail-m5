"""
SparkSession manager with Delta Lake support.
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path
from pyspark.sql import SparkSession
from src.config import settings
from src.logger import logger


def ensure_winutils() -> None:
    """Ensures winutils.exe and hadoop.dll exist on Windows, configuring HADOOP_HOME."""
    if sys.platform != "win32":
        return

    # If HADOOP_HOME environment variable is already set, respect it
    if os.environ.get("HADOOP_HOME"):
        logger.info(f"HADOOP_HOME is already configured at: {os.environ['HADOOP_HOME']}")
        return

    hadoop_dir = settings.data_dir / "hadoop"
    bin_dir = hadoop_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    winutils_exe = bin_dir / "winutils.exe"
    hadoop_dll = bin_dir / "hadoop.dll"

    # Repository link for pre-built Hadoop 3.3.5 binaries (fully compatible with Spark 3.5.x)
    winutils_url = "https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-3.3.5/bin/winutils.exe"
    hadoop_dll_url = "https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-3.3.5/bin/hadoop.dll"

    try:
        # Download winutils.exe if missing
        if not winutils_exe.exists():
            logger.info(f"Downloading winutils.exe for Windows to {winutils_exe}...")
            urllib.request.urlretrieve(winutils_url, str(winutils_exe))
            logger.info("Successfully downloaded winutils.exe.")

        # Download hadoop.dll if missing
        if not hadoop_dll.exists():
            logger.info(f"Downloading hadoop.dll for Windows to {hadoop_dll}...")
            urllib.request.urlretrieve(hadoop_dll_url, str(hadoop_dll))
            logger.info("Successfully downloaded hadoop.dll.")

        # Configure environment variables programmatically
        os.environ["HADOOP_HOME"] = str(hadoop_dir.resolve())
        os.environ["PATH"] += os.pathsep + str(bin_dir.resolve())
        logger.info(f"Programmatically configured HADOOP_HOME: {os.environ['HADOOP_HOME']}")
    except Exception as e:
        logger.warning(
            f"Failed to automatically set up local Hadoop binaries: {e}. "
            "You may need to manually configure HADOOP_HOME and winutils.exe if Spark fails."
        )


def get_spark_session() -> SparkSession:
    """Create or retrieve a SparkSession configured with Delta Lake."""
    # Ensure Windows support binaries are configured
    ensure_winutils()

    # Prevent Windows hostname lookup issues in Spark
    os.environ["SPARK_LOCAL_IP"] = settings.spark_local_ip

    # Set up Spark builder with Delta Lake configurations
    builder = (
        SparkSession.builder.appName("RetailSenseAI")
        .config("spark.sql.warehouse.dir", str(settings.data_dir / "warehouse"))
        # Delta Lake configurations
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        # We specify version 3.2.0 (compatible with spark 3.5.x / 4.x)
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.2.0")
        # Optimization for local execution
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .master("local[*]")
    )

    logger.info("Initializing local PySpark Session with Delta Lake support...")
    try:
        spark = builder.getOrCreate()
        logger.info("PySpark Session successfully initialized.")
        return spark
    except Exception as e:
        logger.error(f"Failed to initialize SparkSession with Delta: {e}")
        logger.info("Attempting fallback to standard Spark Session without Delta...")
        fallback_builder = (
            SparkSession.builder.appName("RetailSenseAI-Fallback")
            .config("spark.driver.memory", "4g")
            .config("spark.sql.shuffle.partitions", "4")
            .master("local[*]")
        )
        spark = fallback_builder.getOrCreate()
        logger.info("Fallback PySpark Session successfully initialized.")
        return spark
