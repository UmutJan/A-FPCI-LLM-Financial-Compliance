# A\-FPCI\-LLM\-Financial\-Compliance

Official implementation of A\-FPCI: Aggregating simulation states to build Cost\-effective LLM based Financial Product Compliance Inspection, including code, dataset and experimental results\.

## 📂 Repository Structure

This repository contains two core folders:`Code` \(for model implementation\) and `Data` \(for experimental datasets and input files\)\. The detailed structure and file descriptions are as follows:

### 1\. Code Folder

The`Code` folder contains all the core code modules of the A\-FPCI, C\-FPCI, and T\-FPCI methods, which are used for simulation state aggregation, model compression, and compliance judgment respectively\.

- `A\_FPCI\_SAT\.py`: Code for the SAT \(Simulation State Aggregation\) module of A\-FPCI, responsible for aggregating simulation states to generate effective input features\.

- `A\_FPCI\_Judgment\.py`: Compliance judgment code based on the A\-FPCI model, which takes the data processed by the SAT module as input to complete financial product compliance inspection\.

- `T\-FPCI\_Judgment\.py`: Compliance judgment code based on the T\-FPCI model, which directly takes the original simulation state data as input for compliance inspection \(serving as a baseline comparison\)\.

- `C\_FPCI\_Compressed\.py`: Code for the compression module of C\-FPCI, which compresses the aggregated simulation states to achieve cost\-effective model deployment\.

- `C\_FPCI\_Compressed\_Judgment\.py`: Compliance judgment code based on the C\-FPCI model, which takes the data processed by the C\-FPCI compression module as input for compliance inspection\.

### 2\. Data Folder

The `Data` folder provides all the datasets and input files required for model training, testing, and inference, including original simulation states, processed intermediate data, and compliance rules\.

- `Simulation Stats Table/`: Contains 500 simulation state data tables, which serve as inputs for the SAT module, the C\-FPCI compression module, and directly as inputs for `T\-FPCI\_Judgment\.py`\.

- `after\_SAT\_data\.json`: Sample data processed by the SAT module of A\-FPCI, which can be directly used as input for `A\_FPCI\_Judgment\.py` to verify the compliance judgment effect of the A\-FPCI model\.

- `after\_compress\_data\.json`: Sample data processed by the C\-FPCI compression module, which can be directly used as input for `C\_FPCI\_Compressed\_Judgment\.py` to verify the compliance judgment effect of the C\-FPCI model\.

- `rules\.json`: 101 quantifiable compliance rules extracted from 26 financial regulations, which are the core criteria for all compliance judgment modules to evaluate whether financial products meet regulatory requirements\.

## 🚀 Quick Start

To use the code and data in this repository, follow these basic steps:

1. Clone this repository to your local machine\.

2. Prepare the required dependencies \(it is recommended to use a Python virtual environment\)\.

3. Select the corresponding code file and input data according to your needs:
        

   - For A\-FPCI compliance judgment: Use `A\_FPCI\_Judgment\.py` with `after\_SAT\_data\.json` as input\.

   - For T\-FPCI compliance judgment: Use `T\-FPCI\_Judgment\.py` with data in `Simulation Stats Table/` as input\.

   - For C\-FPCI compliance judgment: Use `C\_FPCI\_Compressed\_Judgment\.py` with `after\_compress\_data\.json` as input\.

## 📝 Note

- All simulation state data tables in `Simulation Stats Table/` are in standard format, which can be directly read and used by the code without additional preprocessing\.

- The `rules\.json` file defines the quantifiable standards of financial compliance, and users can adjust or expand the rules according to specific regulatory scenarios\.

- The sample data \(`after\_SAT\_data\.json` and `after\_compress\_data\.json`\) are provided for quick test and verification; for formal experiments, it is recommended to use the complete data in `Simulation Stats Table/`\.
